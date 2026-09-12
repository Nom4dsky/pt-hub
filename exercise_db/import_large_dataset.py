"""
Import exercises_large.json into the existing exercise database.

Standalone and additive — unlike seed.py, this does NOT wipe anything.
Run once after seed.py:

    python import_large_dataset.py

Safe to re-run: any exercise whose name already exists in the database
(from seed.py or a previous run of this script) is skipped with a
printed warning instead of being re-inserted. movement_patterns,
muscles, and equipment are resolved by exact name match against the
existing tables and only created if genuinely missing.

variant_of is resolved in two passes: every non-duplicate exercise in
this file is inserted first (so every name in the batch has an id), then
variant_of is set from a name -> id map covering both the pre-existing
exercises and everything just inserted. This handles a variant_of
target that appears later in the file, or one that points at a name
skipped as a duplicate (which still resolves — to the pre-existing row).
"""

import json
from pathlib import Path

from app.database import get_session
from app.models import (
    Equipment,
    Exercise,
    ExerciseEquipment,
    ExerciseMuscle,
    Muscle,
    MovementPattern,
)

DATA_PATH = Path(__file__).resolve().parent / "exercises_large.json"

# Names in this dataset that don't exact-match an existing lookup row but
# look like the same real-world muscle/equipment under a different label.
# Purely informational: printed in the summary, never auto-merged, since
# renaming/consolidating an existing lookup value is a decision for a
# person to make (e.g. via the Manage Lookups UI), not something to guess
# at silently here.
LIKELY_ALIASES = {
    "muscles": {
        "Quadriceps": "Quads",
        "Core": "Abs",
        "Shoulders": "Front Delts / Side Delts / Rear Delts",
        "Erectors": "Lower Back",
    },
    "equipment": {
        "Cable Machine": "Cable",
        "Band": "Resistance Band",
    },
}


def load_dataset() -> list[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)


def get_or_create(session, model, name: str, created_bucket: list[str]):
    obj = session.query(model).filter_by(name=name).one_or_none()
    if obj is None:
        obj = model(name=name)
        session.add(obj)
        session.flush()  # need obj.id for the exercises that reference it below
        created_bucket.append(name)
    return obj


def main() -> None:
    rows = load_dataset()
    session = get_session()

    try:
        # ---- resolve/create lookups up front ----
        patterns_by_name = {mp.name: mp for mp in session.query(MovementPattern)}
        muscles_by_name = {m.name: m for m in session.query(Muscle)}
        equipment_by_name = {e.name: e for e in session.query(Equipment)}

        new_patterns: list[str] = []
        new_muscles: list[str] = []
        new_equipment: list[str] = []

        for row in rows:
            pattern_name = row["movement_pattern"]
            if pattern_name not in patterns_by_name:
                patterns_by_name[pattern_name] = get_or_create(
                    session, MovementPattern, pattern_name, new_patterns
                )
            for muscle_name, _role in row["muscles"]:
                if muscle_name not in muscles_by_name:
                    muscles_by_name[muscle_name] = get_or_create(session, Muscle, muscle_name, new_muscles)
            for equipment_name, _is_required in row["equipment"]:
                if equipment_name not in equipment_by_name:
                    equipment_by_name[equipment_name] = get_or_create(
                        session, Equipment, equipment_name, new_equipment
                    )
        session.commit()

        # ---- pass 1: insert exercises (skip exact-name collisions), defer variant_of ----
        name_to_id: dict[str, int] = {name: id_ for id_, name in session.query(Exercise.id, Exercise.name)}
        inserted: list[str] = []
        skipped: list[str] = []
        pending_variant_of: dict[int, str] = {}  # new exercise id -> variant_of target name

        for row in rows:
            if row["name"] in name_to_id:
                skipped.append(row["name"])
                print(f"  skip (already exists): {row['name']!r}")
                continue

            exercise = Exercise(
                name=row["name"],
                movement_pattern_id=patterns_by_name[row["movement_pattern"]].id,
                exercise_type=row["exercise_type"],
                difficulty=row["difficulty"],
                unilateral=row["unilateral"],
                compound_or_isolation=row["compound_or_isolation"],
                tracking_type=row["tracking_type"],
                # dataset uses "" for "none" where the existing schema/seed
                # convention is NULL — normalize so IS NULL filters stay meaningful
                contraindications=row["contraindications"] or None,
                cue_notes=row["cue_notes"] or None,
                video_url=row.get("video_url") or None,
                variant_of=None,  # resolved in pass 2, once every new name has an id
            )
            session.add(exercise)
            session.flush()  # need exercise.id for its links, name_to_id, and pass 2

            name_to_id[exercise.name] = exercise.id
            inserted.append(exercise.name)
            if row["variant_of"]:
                pending_variant_of[exercise.id] = row["variant_of"]

            for muscle_name, role in row["muscles"]:
                session.add(
                    ExerciseMuscle(exercise_id=exercise.id, muscle_id=muscles_by_name[muscle_name].id, role=role)
                )
            for equipment_name, is_required in row["equipment"]:
                session.add(
                    ExerciseEquipment(
                        exercise_id=exercise.id,
                        equipment_id=equipment_by_name[equipment_name].id,
                        is_required=is_required,
                    )
                )

        session.commit()

        # ---- pass 2: resolve variant_of now that every new exercise has an id ----
        unresolved_variants: list[tuple[str, str]] = []
        for exercise_id, target_name in pending_variant_of.items():
            exercise = session.get(Exercise, exercise_id)
            target_id = name_to_id.get(target_name)
            if target_id is None:
                unresolved_variants.append((exercise.name, target_name))
            else:
                exercise.variant_of = target_id
        session.commit()

        # ---- summary ----
        print()
        print("=" * 60)
        print(f"Inserted:            {len(inserted)} exercises")
        print(f"Skipped (duplicate): {len(skipped)} exercises")
        print(f"New movement patterns created: {len(new_patterns)}" + (f" {new_patterns}" if new_patterns else ""))
        print(f"New muscles created:           {len(new_muscles)}" + (f" {new_muscles}" if new_muscles else ""))
        print(f"New equipment created:         {len(new_equipment)}" + (f" {new_equipment}" if new_equipment else ""))

        if unresolved_variants:
            print()
            print(f"WARNING: {len(unresolved_variants)} variant_of reference(s) could not be "
                  f"resolved and were left NULL:")
            for exercise_name, target_name in unresolved_variants:
                print(f"  {exercise_name!r} -> missing variant_of target {target_name!r}")

        alias_hits = {
            "muscles": [n for n in new_muscles if n in LIKELY_ALIASES["muscles"]],
            "equipment": [n for n in new_equipment if n in LIKELY_ALIASES["equipment"]],
        }
        if alias_hits["muscles"] or alias_hits["equipment"]:
            print()
            print("NOTE: possible naming duplicates were created as NEW rows, not merged:")
            for n in alias_hits["muscles"]:
                print(f"  muscle {n!r} may be the same as existing {LIKELY_ALIASES['muscles'][n]!r}")
            for n in alias_hits["equipment"]:
                print(f"  equipment {n!r} may be the same as existing {LIKELY_ALIASES['equipment'][n]!r}")
            print("  Not auto-merged — consolidate via the Manage Lookups UI if you want them combined.")
    finally:
        session.close()


if __name__ == "__main__":
    main()

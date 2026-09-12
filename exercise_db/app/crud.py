"""
Business logic for the exercise-management API: query building, the
exercise <-> muscle/equipment link replace-on-save, and the "block delete
if referenced" checks for lookup tables and exercises alike.

Raises fastapi.HTTPException directly (422 for bad references, 409 for
blocked deletes/duplicate names) rather than a separate exception layer —
this is a small single-user tool, and the routers stay one-line-per-verb
by letting these propagate.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Equipment,
    Exercise,
    ExerciseEquipment,
    ExerciseMuscle,
    Muscle,
    MovementPattern,
    WorkoutBlockExercise,
)
from app.schemas import (
    EquipmentLinkOut,
    ExerciseDetail,
    ExerciseIn,
    ExerciseListItem,
    ExerciseOption,
    LookupIn,
    LookupOut,
    MuscleLinkOut,
)


def _now() -> str:
    # Matches the schema's own datetime('now') format (SQLite, UTC, no
    # timezone suffix) so updated_at stays consistent between rows
    # inserted at the DB layer (seed.py) and rows updated through the API.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------
# Exercises
# ------------------------------------------------------------


def _primary_muscle_name(exercise: Exercise) -> str | None:
    primaries = [link for link in exercise.muscle_links if link.role == "primary"]
    if not primaries:
        return None
    primaries.sort(key=lambda link: link.muscle_id)
    return primaries[0].muscle.name


def _to_detail(exercise: Exercise) -> ExerciseDetail:
    muscles = sorted(exercise.muscle_links, key=lambda link: (link.role, link.muscle.name))
    equipment = sorted(exercise.equipment_links, key=lambda link: link.equipment.name)
    return ExerciseDetail(
        id=exercise.id,
        name=exercise.name,
        movement_pattern_id=exercise.movement_pattern_id,
        movement_pattern_name=exercise.movement_pattern.name,
        exercise_type=exercise.exercise_type,
        difficulty=exercise.difficulty,
        unilateral=exercise.unilateral,
        compound_or_isolation=exercise.compound_or_isolation,
        tracking_type=exercise.tracking_type,
        contraindications=exercise.contraindications,
        cue_notes=exercise.cue_notes,
        video_url=exercise.video_url,
        variant_of=exercise.variant_of,
        variant_of_name=exercise.base_exercise.name if exercise.variant_of else None,
        created_at=exercise.created_at,
        updated_at=exercise.updated_at,
        muscles=[
            MuscleLinkOut(muscle_id=link.muscle_id, muscle_name=link.muscle.name, role=link.role)
            for link in muscles
        ],
        equipment=[
            EquipmentLinkOut(
                equipment_id=link.equipment_id,
                equipment_name=link.equipment.name,
                is_required=link.is_required,
            )
            for link in equipment
        ],
    )


def list_exercises(
    db: Session,
    *,
    movement_pattern_id: int | None = None,
    muscle_id: int | None = None,
    equipment_id: int | None = None,
    exercise_type: str | None = None,
    difficulty_min: int | None = None,
    difficulty_max: int | None = None,
    compound_or_isolation: str | None = None,
    search: str | None = None,
) -> list[ExerciseListItem]:
    stmt = select(Exercise)
    conditions = []
    if movement_pattern_id is not None:
        conditions.append(Exercise.movement_pattern_id == movement_pattern_id)
    if exercise_type is not None:
        conditions.append(Exercise.exercise_type == exercise_type)
    if compound_or_isolation is not None:
        conditions.append(Exercise.compound_or_isolation == compound_or_isolation)
    if difficulty_min is not None:
        conditions.append(Exercise.difficulty >= difficulty_min)
    if difficulty_max is not None:
        conditions.append(Exercise.difficulty <= difficulty_max)
    if search:
        conditions.append(Exercise.name.ilike(f"%{search}%"))
    if muscle_id is not None:
        conditions.append(
            Exercise.id.in_(select(ExerciseMuscle.exercise_id).where(ExerciseMuscle.muscle_id == muscle_id))
        )
    if equipment_id is not None:
        conditions.append(
            Exercise.id.in_(
                select(ExerciseEquipment.exercise_id).where(ExerciseEquipment.equipment_id == equipment_id)
            )
        )
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(Exercise.name)

    exercises = db.execute(stmt).scalars().all()
    return [
        ExerciseListItem(
            id=e.id,
            name=e.name,
            movement_pattern_id=e.movement_pattern_id,
            movement_pattern_name=e.movement_pattern.name,
            primary_muscle=_primary_muscle_name(e),
            difficulty=e.difficulty,
            exercise_type=e.exercise_type,
            compound_or_isolation=e.compound_or_isolation,
        )
        for e in exercises
    ]


def get_exercise_detail(db: Session, exercise_id: int) -> ExerciseDetail | None:
    exercise = db.get(Exercise, exercise_id)
    return _to_detail(exercise) if exercise is not None else None


def list_exercise_options(db: Session, exclude_id: int | None = None) -> list[ExerciseOption]:
    """For the "variant of" searchable dropdown — excludes the exercise
    being edited so it can't be picked as its own variant."""
    stmt = select(Exercise.id, Exercise.name).order_by(Exercise.name)
    if exclude_id is not None:
        stmt = stmt.where(Exercise.id != exclude_id)
    return [ExerciseOption(id=row.id, name=row.name) for row in db.execute(stmt).all()]


def _validate_references(db: Session, payload: ExerciseIn, *, exercise_id: int | None = None) -> None:
    if db.get(MovementPattern, payload.movement_pattern_id) is None:
        raise HTTPException(422, f"movement_pattern_id {payload.movement_pattern_id} does not exist")

    if payload.variant_of is not None:
        if exercise_id is not None and payload.variant_of == exercise_id:
            raise HTTPException(422, "An exercise cannot be its own variant_of")
        if db.get(Exercise, payload.variant_of) is None:
            raise HTTPException(422, f"variant_of exercise id {payload.variant_of} does not exist")

    muscle_pairs = [(m.muscle_id, m.role) for m in payload.muscles]
    if len(muscle_pairs) != len(set(muscle_pairs)):
        raise HTTPException(422, "Duplicate muscle_id + role entries in muscles list")
    muscle_ids = {m.muscle_id for m in payload.muscles}
    if muscle_ids:
        found = {row[0] for row in db.execute(select(Muscle.id).where(Muscle.id.in_(muscle_ids)))}
        missing = muscle_ids - found
        if missing:
            raise HTTPException(422, f"muscle_id(s) not found: {sorted(missing)}")

    equipment_ids = [e.equipment_id for e in payload.equipment]
    if len(equipment_ids) != len(set(equipment_ids)):
        raise HTTPException(422, "Duplicate equipment_id entries in equipment list")
    if equipment_ids:
        found = {row[0] for row in db.execute(select(Equipment.id).where(Equipment.id.in_(equipment_ids)))}
        missing = set(equipment_ids) - found
        if missing:
            raise HTTPException(422, f"equipment_id(s) not found: {sorted(missing)}")


def _replace_links(db: Session, exercise: Exercise, payload: ExerciseIn) -> None:
    db.query(ExerciseMuscle).filter_by(exercise_id=exercise.id).delete()
    db.query(ExerciseEquipment).filter_by(exercise_id=exercise.id).delete()
    for m in payload.muscles:
        db.add(ExerciseMuscle(exercise_id=exercise.id, muscle_id=m.muscle_id, role=m.role))
    for eq in payload.equipment:
        db.add(
            ExerciseEquipment(
                exercise_id=exercise.id, equipment_id=eq.equipment_id, is_required=eq.is_required
            )
        )


def create_exercise(db: Session, payload: ExerciseIn) -> ExerciseDetail:
    _validate_references(db, payload)
    exercise = Exercise(
        name=payload.name,
        movement_pattern_id=payload.movement_pattern_id,
        exercise_type=payload.exercise_type,
        difficulty=payload.difficulty,
        unilateral=payload.unilateral,
        compound_or_isolation=payload.compound_or_isolation,
        tracking_type=payload.tracking_type,
        contraindications=payload.contraindications,
        cue_notes=payload.cue_notes,
        video_url=payload.video_url,
        variant_of=payload.variant_of,
    )
    db.add(exercise)
    db.flush()  # need exercise.id for the links below
    _replace_links(db, exercise, payload)
    db.commit()
    db.refresh(exercise)
    return _to_detail(exercise)


def update_exercise(db: Session, exercise_id: int, payload: ExerciseIn) -> ExerciseDetail | None:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        return None
    _validate_references(db, payload, exercise_id=exercise_id)

    exercise.name = payload.name
    exercise.movement_pattern_id = payload.movement_pattern_id
    exercise.exercise_type = payload.exercise_type
    exercise.difficulty = payload.difficulty
    exercise.unilateral = payload.unilateral
    exercise.compound_or_isolation = payload.compound_or_isolation
    exercise.tracking_type = payload.tracking_type
    exercise.contraindications = payload.contraindications
    exercise.cue_notes = payload.cue_notes
    exercise.video_url = payload.video_url
    exercise.variant_of = payload.variant_of
    exercise.updated_at = _now()  # no DB-side ON UPDATE trigger, so bump it here

    _replace_links(db, exercise, payload)
    db.commit()
    db.refresh(exercise)
    return _to_detail(exercise)


def delete_exercise(db: Session, exercise_id: int) -> bool:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        return False

    # workout_block_exercises.exercise_id has no ON DELETE clause — check
    # first for a clear message instead of letting SQLite reject the
    # DELETE with a raw IntegrityError.
    usage = db.execute(
        select(func.count()).select_from(WorkoutBlockExercise).where(
            WorkoutBlockExercise.exercise_id == exercise_id
        )
    ).scalar_one()
    if usage:
        raise HTTPException(
            409,
            f"Cannot delete '{exercise.name}': used in {usage} workout block(s). "
            "Remove it from those workouts first.",
        )

    db.delete(exercise)
    db.commit()
    return True


# ------------------------------------------------------------
# Lookup tables (movement_patterns, muscles, equipment)
# ------------------------------------------------------------


def list_lookup(db: Session, model: type) -> list[LookupOut]:
    rows = db.execute(select(model).order_by(model.name)).scalars().all()
    return [LookupOut(id=row.id, name=row.name) for row in rows]


def create_lookup(db: Session, model: type, payload: LookupIn) -> LookupOut:
    existing = db.execute(select(model).where(model.name == payload.name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, f"'{payload.name}' already exists")
    obj = model(name=payload.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return LookupOut(id=obj.id, name=obj.name)


def update_lookup(db: Session, model: type, item_id: int, payload: LookupIn) -> LookupOut | None:
    obj = db.get(model, item_id)
    if obj is None:
        return None
    duplicate = db.execute(
        select(model).where(model.name == payload.name, model.id != item_id)
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(409, f"'{payload.name}' already exists")
    obj.name = payload.name
    db.commit()
    db.refresh(obj)
    return LookupOut(id=obj.id, name=obj.name)


def delete_movement_pattern(db: Session, item_id: int) -> bool:
    obj = db.get(MovementPattern, item_id)
    if obj is None:
        return False
    count = db.execute(
        select(func.count()).select_from(Exercise).where(Exercise.movement_pattern_id == item_id)
    ).scalar_one()
    if count:
        raise HTTPException(409, f"Cannot delete '{obj.name}': used by {count} exercise(s).")
    db.delete(obj)
    db.commit()
    return True


def delete_muscle(db: Session, item_id: int) -> bool:
    obj = db.get(Muscle, item_id)
    if obj is None:
        return False
    count = db.execute(
        select(func.count()).select_from(ExerciseMuscle).where(ExerciseMuscle.muscle_id == item_id)
    ).scalar_one()
    if count:
        raise HTTPException(409, f"Cannot delete '{obj.name}': used by {count} exercise(s).")
    db.delete(obj)
    db.commit()
    return True


def delete_equipment(db: Session, item_id: int) -> bool:
    obj = db.get(Equipment, item_id)
    if obj is None:
        return False
    count = db.execute(
        select(func.count()).select_from(ExerciseEquipment).where(ExerciseEquipment.equipment_id == item_id)
    ).scalar_one()
    if count:
        raise HTTPException(409, f"Cannot delete '{obj.name}': used by {count} exercise(s).")
    db.delete(obj)
    db.commit()
    return True

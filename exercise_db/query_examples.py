"""
Sanity-check queries against the seeded exercise + workout database.

Run after `alembic upgrade head` and `python seed.py`:

    python query_examples.py
"""

import json

from sqlalchemy import select

from app.database import get_session
from app.models import (
    Equipment,
    Exercise,
    ExerciseEquipment,
    ExerciseMuscle,
    Muscle,
    MovementPattern,
    PrescribedSet,
    Workout,
    WorkoutBlock,
    WorkoutBlockExercise,
)


def print_exercises(title: str, exercises: list[Exercise]) -> None:
    print(f"\n{title} ({len(exercises)})")
    for ex in exercises:
        print(
            f"  - {ex.name:<32} diff={ex.difficulty}  "
            f"type={ex.exercise_type:<12} tracking={ex.tracking_type}"
        )


def get_exercise_by_name(session, name: str) -> Exercise | None:
    return session.execute(select(Exercise).where(Exercise.name == name)).scalar_one_or_none()


def get_workout_by_name(session, name: str) -> Workout | None:
    return session.execute(select(Workout).where(Workout.name == name)).scalar_one_or_none()


def beginner_hinge_with_dumbbells(session) -> list[Exercise]:
    """The example from the brief: beginner-friendly hinge exercises using dumbbells."""
    stmt = (
        select(Exercise)
        .join(MovementPattern, Exercise.movement_pattern_id == MovementPattern.id)
        .join(ExerciseEquipment, ExerciseEquipment.exercise_id == Exercise.id)
        .join(Equipment, Equipment.id == ExerciseEquipment.equipment_id)
        .where(
            MovementPattern.name == "hinge",
            Equipment.name == "Dumbbell",
            Exercise.difficulty <= 2,
        )
        .distinct()
        .order_by(Exercise.difficulty, Exercise.name)
    )
    return list(session.execute(stmt).scalars())


def bodyweight_only_by_pattern(session, pattern: str) -> list[Exercise]:
    """Exercises for a given movement pattern that need nothing but bodyweight."""
    stmt = (
        select(Exercise)
        .join(MovementPattern, Exercise.movement_pattern_id == MovementPattern.id)
        .where(
            MovementPattern.name == pattern,
            Exercise.id.in_(
                select(ExerciseEquipment.exercise_id).where(
                    ExerciseEquipment.equipment_id
                    == select(Equipment.id).where(Equipment.name == "Bodyweight").scalar_subquery()
                )
            ),
        )
        .order_by(Exercise.difficulty)
    )
    return list(session.execute(stmt).scalars())


def exercises_targeting_muscle_as_primary(session, muscle_name: str) -> list[Exercise]:
    stmt = (
        select(Exercise)
        .join(ExerciseMuscle, ExerciseMuscle.exercise_id == Exercise.id)
        .join(Muscle, Muscle.id == ExerciseMuscle.muscle_id)
        .where(Muscle.name == muscle_name, ExerciseMuscle.role == "primary")
        .order_by(Exercise.difficulty)
    )
    return list(session.execute(stmt).scalars())


def variants_of(session, base_name: str) -> list[Exercise]:
    stmt = select(Exercise).where(
        Exercise.variant_of
        == select(Exercise.id).where(Exercise.name == base_name).scalar_subquery()
    )
    return list(session.execute(stmt).scalars())


def get_compound_exercises_by_pattern(session, pattern: str) -> list[Exercise]:
    """
    The right way to query "find a main-lift substitute": movement_pattern
    ALWAYS paired with compound_or_isolation == 'compound'.

    movement_pattern alone isn't enough — isolation accessories share a
    pattern with the compound lift they support (Machine Leg Extension is
    'squat', Machine Leg Curl is 'hinge') but are never valid substitutes
    for the lift itself. See `main()` below for a side-by-side count that
    shows exactly what pairing this filter excludes.
    """
    stmt = (
        select(Exercise)
        .join(MovementPattern, Exercise.movement_pattern_id == MovementPattern.id)
        .where(
            MovementPattern.name == pattern,
            Exercise.compound_or_isolation == "compound",
        )
        .order_by(Exercise.difficulty, Exercise.name)
    )
    return list(session.execute(stmt).scalars())


# ------------------------------------------------------------
# PHASE 2: workout builder queries
# ------------------------------------------------------------


def build_workout_dict(session, workout_id: int) -> dict | None:
    """
    Full nested workout: workout -> blocks (by order_index) ->
    block_exercises (by order_index) -> prescribed_sets (by set_number).

    Returns None if workout_id doesn't exist. Use build_workout_json() for
    the JSON string.
    """
    workout = session.get(Workout, workout_id)
    if workout is None:
        return None

    blocks = list(
        session.execute(
            select(WorkoutBlock)
            .where(WorkoutBlock.workout_id == workout_id)
            .order_by(WorkoutBlock.order_index)
        ).scalars()
    )

    block_dicts = []
    for block in blocks:
        block_exercises = list(
            session.execute(
                select(WorkoutBlockExercise)
                .where(WorkoutBlockExercise.block_id == block.id)
                .order_by(WorkoutBlockExercise.order_index)
            ).scalars()
        )

        exercise_dicts = []
        for be in block_exercises:
            sets = list(
                session.execute(
                    select(PrescribedSet)
                    .where(PrescribedSet.workout_block_exercise_id == be.id)
                    .order_by(PrescribedSet.set_number)
                ).scalars()
            )
            exercise_dicts.append(
                {
                    "id": be.id,
                    "order_index": be.order_index,
                    "exercise_id": be.exercise_id,
                    "exercise_name": be.exercise.name,
                    "sets": [
                        {
                            "id": s.id,
                            "set_number": s.set_number,
                            "reps_min": s.reps_min,
                            "reps_max": s.reps_max,
                            "load_value": s.load_value,
                            "load_type": s.load_type,
                            "rir_min": s.rir_min,
                            "rir_max": s.rir_max,
                            "rest_seconds": s.rest_seconds,
                            "tempo": s.tempo,
                        }
                        for s in sets
                    ],
                }
            )

        block_dicts.append(
            {
                "id": block.id,
                "order_index": block.order_index,
                "block_type": block.block_type,
                "rounds": block.rounds,
                "duration_seconds": block.duration_seconds,
                "rest_between_rounds_seconds": block.rest_between_rounds_seconds,
                "notes": block.notes,
                "exercises": exercise_dicts,
            }
        )

    return {
        "id": workout.id,
        "name": workout.name,
        "notes": workout.notes,
        "created_at": workout.created_at,
        "updated_at": workout.updated_at,
        "blocks": block_dicts,
    }


def build_workout_json(session, workout_id: int) -> str | None:
    workout_dict = build_workout_dict(session, workout_id)
    if workout_dict is None:
        return None
    return json.dumps(workout_dict, indent=2)


def workouts_using_exercise(session, exercise_id: int) -> list[Workout]:
    """Reverse lookup: every workout that has this exercise in any block."""
    stmt = (
        select(Workout)
        .join(WorkoutBlock, WorkoutBlock.workout_id == Workout.id)
        .join(WorkoutBlockExercise, WorkoutBlockExercise.block_id == WorkoutBlock.id)
        .where(WorkoutBlockExercise.exercise_id == exercise_id)
        .distinct()
        .order_by(Workout.name)
    )
    return list(session.execute(stmt).scalars())


def main() -> None:
    session = get_session()
    try:
        print_exercises(
            "Beginner hinge exercises with dumbbells",
            beginner_hinge_with_dumbbells(session),
        )
        print_exercises(
            "Bodyweight-only squat pattern exercises",
            bodyweight_only_by_pattern(session, "squat"),
        )
        print_exercises(
            "Exercises with Glutes as a primary mover",
            exercises_targeting_muscle_as_primary(session, "Glutes"),
        )
        print_exercises(
            "Variants of Barbell Back Squat",
            variants_of(session, "Barbell Back Squat"),
        )

        # The guardrail: movement_pattern alone vs. paired with
        # compound_or_isolation='compound' for lift-substitute selection.
        for pattern in ("squat", "hinge"):
            all_in_pattern = session.execute(
                select(Exercise).where(
                    Exercise.movement_pattern_id
                    == select(MovementPattern.id).where(MovementPattern.name == pattern).scalar_subquery()
                )
            ).scalars().all()
            compound_only = get_compound_exercises_by_pattern(session, pattern)
            print(
                f"\n'{pattern}' pattern: {len(all_in_pattern)} exercises total, "
                f"{len(compound_only)} compound (main-lift-eligible)"
            )
            excluded = sorted(set(e.name for e in all_in_pattern) - set(e.name for e in compound_only))
            if excluded:
                print(f"  excluded as isolation: {', '.join(excluded)}")

        # Phase 2: full nested workout -> blocks -> block_exercises -> prescribed_sets
        circuit_workout = get_workout_by_name(session, "Full Body Circuit")
        print(f"\nFull nested JSON for '{circuit_workout.name}':")
        print(build_workout_json(session, circuit_workout.id))

        emom_workout = get_workout_by_name(session, "EMOM Conditioning")
        print(f"\nFull nested JSON for '{emom_workout.name}':")
        print(build_workout_json(session, emom_workout.id))

        # Phase 2: reverse lookup — every workout using a given exercise
        swing = get_exercise_by_name(session, "Kettlebell Swing")
        used_in = workouts_using_exercise(session, swing.id)
        print(f"\nWorkouts using '{swing.name}' ({len(used_in)}):")
        for w in used_in:
            print(f"  - {w.name}")
    finally:
        session.close()


if __name__ == "__main__":
    main()

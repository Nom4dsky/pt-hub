"""
Sanity-check queries against the seeded exercise database.

Run after `alembic upgrade head` and `python seed.py`:

    python query_examples.py
"""

from sqlalchemy import select

from app.database import get_session
from app.models import Equipment, Exercise, ExerciseEquipment, ExerciseMuscle, Muscle, MovementPattern


def print_exercises(title: str, exercises: list[Exercise]) -> None:
    print(f"\n{title} ({len(exercises)})")
    for ex in exercises:
        print(
            f"  - {ex.name:<32} diff={ex.difficulty}  "
            f"type={ex.exercise_type:<12} tracking={ex.tracking_type}"
        )


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
    finally:
        session.close()


if __name__ == "__main__":
    main()

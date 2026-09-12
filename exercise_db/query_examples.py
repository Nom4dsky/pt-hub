"""
Sanity-check queries against the seeded exercise + workout + program database.

Run after `alembic upgrade head` and `python seed.py`:

    python query_examples.py
"""

import json
from datetime import date, timedelta

from sqlalchemy import select

from app.database import get_session
from app.models import (
    AssignedDayWorkout,
    AssignedProgramDay,
    AssignedProgramWeek,
    Equipment,
    Exercise,
    ExerciseEquipment,
    ExerciseMuscle,
    LoggedSet,
    Muscle,
    MovementPattern,
    PrescribedSet,
    Program,
    ProgramAssignment,
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


def get_program_by_name(session, name: str) -> Program | None:
    return session.execute(select(Program).where(Program.name == name)).scalar_one_or_none()


def get_assignment_by_client_name(session, client_name: str) -> ProgramAssignment | None:
    return session.execute(
        select(ProgramAssignment).where(ProgramAssignment.client_name == client_name)
    ).scalar_one_or_none()


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


# ------------------------------------------------------------
# PHASE 3: program builder queries
# ------------------------------------------------------------


def clone_program_to_assignment(
    session, program_id: int, client_name: str, start_date: str, notes: str | None = None
) -> ProgramAssignment:
    """
    Clone a `programs` template into a new, independent `program_assignments`
    instance: copies the full week -> day -> workout structure into the
    assigned_* tables. After this call, editing the assignment (swapping a
    day's workout, adding a week, etc.) never touches the template or any
    other client's assignment, and vice versa — the tables are physically
    separate rows from here on.

    Modeling choice (not specified by the schema): assigned_program_days
    get a computed `scheduled_date`, laid out as consecutive calendar days
    starting at `start_date` — week N starts `7*(N-1)` days after
    start_date, and each week's days (ordered by day_number) fall on
    consecutive days from there. Adjust scheduled_date after cloning if a
    different cadence (e.g. specific weekdays) is wanted; that's exactly
    the kind of independent edit this clone is meant to allow.

    start_date: 'YYYY-MM-DD'.
    """
    program = session.get(Program, program_id)
    if program is None:
        raise ValueError(f"No program with id={program_id}")

    assignment = ProgramAssignment(
        program_id=program.id,
        client_name=client_name,
        start_date=start_date,
        duration_weeks=program.duration_weeks,
        status="active",
        notes=notes,
    )
    session.add(assignment)
    session.flush()  # need assignment.id for the weeks below

    start = date.fromisoformat(start_date)

    for week in program.weeks:  # relationship is already ordered by week_number
        assigned_week = AssignedProgramWeek(
            program_assignment_id=assignment.id,
            week_number=week.week_number,
            phase_label=week.phase_label,
            notes=week.notes,
        )
        session.add(assigned_week)
        session.flush()  # need assigned_week.id for the days below

        week_start = start + timedelta(weeks=week.week_number - 1)
        for day_index, day in enumerate(week.days):  # relationship is already ordered by day_number
            assigned_day = AssignedProgramDay(
                assigned_program_week_id=assigned_week.id,
                day_number=day.day_number,
                label=day.label,
                scheduled_date=(week_start + timedelta(days=day_index)).isoformat(),
            )
            session.add(assigned_day)
            session.flush()  # need assigned_day.id for the day workouts below

            for dw in day.day_workouts:  # relationship is already ordered by order_index
                session.add(
                    AssignedDayWorkout(
                        assigned_program_day_id=assigned_day.id,
                        workout_id=dw.workout_id,
                        order_index=dw.order_index,
                    )
                )

    session.commit()
    return assignment


def build_assignment_dict(session, program_assignment_id: int) -> dict | None:
    """
    Full nested view of a client's assigned program: assignment -> weeks
    (by week_number) -> days (by day_number) -> workouts (by order_index).

    Returns None if program_assignment_id doesn't exist. Use
    build_assignment_json() for the JSON string.
    """
    assignment = session.get(ProgramAssignment, program_assignment_id)
    if assignment is None:
        return None

    weeks = list(
        session.execute(
            select(AssignedProgramWeek)
            .where(AssignedProgramWeek.program_assignment_id == program_assignment_id)
            .order_by(AssignedProgramWeek.week_number)
        ).scalars()
    )

    week_dicts = []
    for week in weeks:
        days = list(
            session.execute(
                select(AssignedProgramDay)
                .where(AssignedProgramDay.assigned_program_week_id == week.id)
                .order_by(AssignedProgramDay.day_number)
            ).scalars()
        )

        day_dicts = []
        for day in days:
            day_workouts = list(
                session.execute(
                    select(AssignedDayWorkout)
                    .where(AssignedDayWorkout.assigned_program_day_id == day.id)
                    .order_by(AssignedDayWorkout.order_index)
                ).scalars()
            )
            day_dicts.append(
                {
                    "id": day.id,
                    "day_number": day.day_number,
                    "label": day.label,
                    "scheduled_date": day.scheduled_date,
                    "workouts": [
                        {
                            "id": dw.id,
                            "order_index": dw.order_index,
                            "workout_id": dw.workout_id,
                            "workout_name": dw.workout.name,
                        }
                        for dw in day_workouts
                    ],
                }
            )

        week_dicts.append(
            {
                "id": week.id,
                "week_number": week.week_number,
                "phase_label": week.phase_label,
                "notes": week.notes,
                "days": day_dicts,
            }
        )

    return {
        "id": assignment.id,
        "program_id": assignment.program_id,
        "client_name": assignment.client_name,
        "start_date": assignment.start_date,
        "duration_weeks": assignment.duration_weeks,
        "status": assignment.status,
        "notes": assignment.notes,
        "weeks": week_dicts,
    }


def build_assignment_json(session, program_assignment_id: int) -> str | None:
    assignment_dict = build_assignment_dict(session, program_assignment_id)
    if assignment_dict is None:
        return None
    return json.dumps(assignment_dict, indent=2)


def compare_prescribed_vs_actual(session, session_log_id: int) -> list[dict]:
    """
    Planned vs. actual for one completed session_logs entry.

    Joins logged_sets back to prescribed_sets via the pair
    (workout_block_exercise_id, set_number) — the same natural key
    prescribed_sets is uniquely constrained on — rather than via
    logged_sets.prescribed_set_id directly. That FK is nullable and only
    ever SET NULL, so matching on the natural key still finds the
    prescription even if that link was ever cleared, and an outer join
    means a logged set with no matching prescription (an extra, unplanned
    set) still shows up with prescribed_* as None instead of being dropped.
    """
    logged_sets = list(
        session.execute(
            select(LoggedSet)
            .where(LoggedSet.session_log_id == session_log_id)
            .order_by(LoggedSet.workout_block_exercise_id, LoggedSet.set_number)
        ).scalars()
    )

    rows = []
    for logged in logged_sets:
        prescribed = session.execute(
            select(PrescribedSet).where(
                PrescribedSet.workout_block_exercise_id == logged.workout_block_exercise_id,
                PrescribedSet.set_number == logged.set_number,
            )
        ).scalar_one_or_none()

        rows.append(
            {
                "exercise_name": logged.workout_block_exercise.exercise.name,
                "set_number": logged.set_number,
                "prescribed_reps": (
                    f"{prescribed.reps_min}-{prescribed.reps_max}" if prescribed else None
                ),
                "actual_reps": logged.actual_reps,
                "prescribed_load": (
                    f"{prescribed.load_value} ({prescribed.load_type})"
                    if prescribed and prescribed.load_value is not None
                    else None
                ),
                "actual_load": (
                    f"{logged.actual_load_value} ({logged.actual_load_type})"
                    if logged.actual_load_value is not None
                    else None
                ),
                "prescribed_rir": (
                    f"{prescribed.rir_min}-{prescribed.rir_max}"
                    if prescribed and prescribed.rir_min is not None
                    else None
                ),
                "actual_rir": logged.actual_rir,
            }
        )
    return rows


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

        # Phase 3: clone a template into a fresh assignment for a second
        # mock client, proving the clone function works standalone (the
        # seeded 'Alex Rivera' assignment already exercises it once via
        # seed.py) — guarded so re-running this script doesn't pile up
        # duplicate demo clients.
        program = get_program_by_name(session, "12-Week HYROX Prep")
        demo_client = "Jamie Chen (demo clone)"
        demo_assignment = get_assignment_by_client_name(session, demo_client)
        if demo_assignment is None:
            demo_assignment = clone_program_to_assignment(
                session, program.id, demo_client, "2026-02-02",
                notes="Ad-hoc clone created by query_examples.main() to demonstrate cloning.",
            )
        print(
            f"\nCloned '{program.name}' for '{demo_client}' "
            f"-> assignment id={demo_assignment.id}, "
            f"{len(demo_assignment.assigned_weeks)} weeks copied."
        )

        # Phase 3: full nested view of the seeded 'Alex Rivera' assignment
        alex_assignment = get_assignment_by_client_name(session, "Alex Rivera")
        print(f"\nFull nested JSON for assignment id={alex_assignment.id} (client '{alex_assignment.client_name}'):")
        print(build_assignment_json(session, alex_assignment.id))

        # Prove the clone is independently editable: week 4 / day 3 was
        # swapped in the assignment but the template is untouched.
        template_week4 = next(w for w in program.weeks if w.week_number == 4)
        template_day3 = next(d for d in template_week4.days if d.day_number == 3)
        assigned_week4 = next(w for w in alex_assignment.assigned_weeks if w.week_number == 4)
        assigned_day3 = next(d for d in assigned_week4.days if d.day_number == 3)
        print(
            f"\nWeek 4 / Day 3 — template workout: "
            f"'{template_day3.day_workouts[0].workout.name}', "
            f"'{alex_assignment.client_name}' assignment workout: "
            f"'{assigned_day3.day_workouts[0].workout.name}' (edited after cloning)"
        )

        # Phase 3: prescribed vs. actual for the one completed session
        alex_week1 = next(w for w in alex_assignment.assigned_weeks if w.week_number == 1)
        alex_day1 = next(d for d in alex_week1.days if d.day_number == 1)
        session_log = alex_day1.session_logs[0]
        print(
            f"\nPrescribed vs. actual for session_log id={session_log.id} "
            f"({alex_day1.label}, {alex_day1.scheduled_date}):"
        )
        print(f"  notes: {session_log.session_notes}")
        for row in compare_prescribed_vs_actual(session, session_log.id):
            print(
                f"  - {row['exercise_name']:<20} set {row['set_number']}: "
                f"reps {row['prescribed_reps']} -> {row['actual_reps']}, "
                f"load {row['prescribed_load']} -> {row['actual_load']}, "
                f"RIR {row['prescribed_rir']} -> {row['actual_rir']}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()

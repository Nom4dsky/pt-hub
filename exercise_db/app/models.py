"""
SQLAlchemy models mirroring phase1_schema.sql, phase2_schema.sql, and
phase3_schema.sql exactly.

Target DB is SQLite for now (migration path to Postgres later if the app
goes multi-user), so a few SQLite-specific defaults (datetime('now') as
TEXT) are intentional rather than an oversight.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    REAL,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------
# LOOKUP TABLES
# ------------------------------------------------------------


class Muscle(Base):
    __tablename__ = "muscles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    exercise_links: Mapped[list["ExerciseMuscle"]] = relationship(
        back_populates="muscle", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Muscle(id={self.id!r}, name={self.name!r})"


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    exercise_links: Mapped[list["ExerciseEquipment"]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Equipment(id={self.id!r}, name={self.name!r})"


class MovementPattern(Base):
    __tablename__ = "movement_patterns"
    # e.g. squat, hinge, push_horizontal, push_vertical, pull_horizontal,
    # pull_vertical, carry, rotation, anti_rotation, anti_extension, gait

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    exercises: Mapped[list["Exercise"]] = relationship(back_populates="movement_pattern")

    def __repr__(self) -> str:
        return f"MovementPattern(id={self.id!r}, name={self.name!r})"


# ------------------------------------------------------------
# CORE EXERCISE TABLE
# ------------------------------------------------------------


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "exercise_type IN ('strength', 'mobility', 'conditioning', 'plyometric', 'stability')",
            name="ck_exercises_exercise_type",
        ),
        CheckConstraint("difficulty BETWEEN 1 AND 6", name="ck_exercises_difficulty"),
        CheckConstraint(
            "compound_or_isolation IN ('compound', 'isolation')",
            name="ck_exercises_compound_or_isolation",
        ),
        CheckConstraint(
            "tracking_type IN ('reps_weight', 'reps_only', 'time', 'distance', "
            "'time_distance', 'reps_time')",
            name="ck_exercises_tracking_type",
        ),
        Index("idx_exercises_movement_pattern", "movement_pattern_id"),
        Index("idx_exercises_type", "exercise_type"),
        Index("idx_exercises_difficulty", "difficulty"),
        Index("idx_exercises_variant_of", "variant_of"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "Barbell Row"
    variant_of: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("exercises.id", ondelete="SET NULL"), nullable=True
    )
    movement_pattern_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movement_patterns.id"), nullable=False
    )

    exercise_type: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)

    unilateral: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    compound_or_isolation: Mapped[str] = mapped_column(Text, nullable=False)

    tracking_type: Mapped[str] = mapped_column(Text, nullable=False)

    contraindications: Mapped[str | None] = mapped_column(Text, nullable=True)
    cue_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )

    movement_pattern: Mapped["MovementPattern"] = relationship(back_populates="exercises")
    variants: Mapped[list["Exercise"]] = relationship(
        back_populates="base_exercise", remote_side="Exercise.variant_of"
    )
    base_exercise: Mapped["Exercise | None"] = relationship(
        back_populates="variants", remote_side="Exercise.id"
    )

    muscle_links: Mapped[list["ExerciseMuscle"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )
    equipment_links: Mapped[list["ExerciseEquipment"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )
    # No delete-orphan here: workout_block_exercises.exercise_id has no ON
    # DELETE clause in the schema, so the DB (not the ORM) is what stops an
    # in-use exercise from being deleted.
    block_usages: Mapped[list["WorkoutBlockExercise"]] = relationship(
        back_populates="exercise"
    )

    def __repr__(self) -> str:
        return f"Exercise(id={self.id!r}, name={self.name!r})"


# ------------------------------------------------------------
# JOIN TABLES
# ------------------------------------------------------------


class ExerciseMuscle(Base):
    __tablename__ = "exercise_muscles"
    __table_args__ = (
        CheckConstraint(
            "role IN ('primary', 'secondary', 'stabilizer')",
            name="ck_exercise_muscles_role",
        ),
        PrimaryKeyConstraint("exercise_id", "muscle_id", "role"),
        Index("idx_exercise_muscles_muscle", "muscle_id"),
    )

    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    muscle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("muscles.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)

    exercise: Mapped["Exercise"] = relationship(back_populates="muscle_links")
    muscle: Mapped["Muscle"] = relationship(back_populates="exercise_links")

    def __repr__(self) -> str:
        return (
            f"ExerciseMuscle(exercise_id={self.exercise_id!r}, "
            f"muscle_id={self.muscle_id!r}, role={self.role!r})"
        )


class ExerciseEquipment(Base):
    __tablename__ = "exercise_equipment"
    __table_args__ = (
        PrimaryKeyConstraint("exercise_id", "equipment_id"),
        Index("idx_exercise_equipment_equipment", "equipment_id"),
    )

    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )

    exercise: Mapped["Exercise"] = relationship(back_populates="equipment_links")
    equipment: Mapped["Equipment"] = relationship(back_populates="exercise_links")

    def __repr__(self) -> str:
        return (
            f"ExerciseEquipment(exercise_id={self.exercise_id!r}, "
            f"equipment_id={self.equipment_id!r}, is_required={self.is_required!r})"
        )


# ------------------------------------------------------------
# WORKOUTS (reusable templates, not scheduled instances)
# ------------------------------------------------------------


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )

    blocks: Mapped[list["WorkoutBlock"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutBlock.order_index",
    )
    # No delete-orphan on either of these: program_day_workouts.workout_id
    # and assigned_day_workouts.workout_id both have no ON DELETE clause,
    # so the DB (not the ORM) is what stops an in-use workout from being
    # deleted — same pattern as Exercise.block_usages above.
    program_day_links: Mapped[list["ProgramDayWorkout"]] = relationship(back_populates="workout")
    assigned_day_links: Mapped[list["AssignedDayWorkout"]] = relationship(back_populates="workout")

    def __repr__(self) -> str:
        return f"Workout(id={self.id!r}, name={self.name!r})"


# ------------------------------------------------------------
# WORKOUT BLOCKS
# A block is one "chunk" of a workout: a straight-set exercise, a
# superset/triset, a circuit, an EMOM, an AMRAP, or a for-time piece.
# ------------------------------------------------------------


class WorkoutBlock(Base):
    __tablename__ = "workout_blocks"
    __table_args__ = (
        CheckConstraint(
            "block_type IN ('straight_set', 'superset', 'triset', 'circuit', "
            "'emom', 'amrap', 'for_time')",
            name="ck_workout_blocks_block_type",
        ),
        UniqueConstraint("workout_id", "order_index", name="uq_workout_blocks_workout_order"),
        Index("idx_workout_blocks_workout", "workout_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workout_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)  # sequence within the workout

    block_type: Mapped[str] = mapped_column(Text, nullable=False)

    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # circuit/EMOM; null for AMRAP/for_time
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)  # EMOM/AMRAP/for_time time cap
    rest_between_rounds_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workout: Mapped["Workout"] = relationship(back_populates="blocks")
    block_exercises: Mapped[list["WorkoutBlockExercise"]] = relationship(
        back_populates="block",
        cascade="all, delete-orphan",
        order_by="WorkoutBlockExercise.order_index",
    )

    def __repr__(self) -> str:
        return f"WorkoutBlock(id={self.id!r}, workout_id={self.workout_id!r}, block_type={self.block_type!r})"


# ------------------------------------------------------------
# WORKOUT BLOCK EXERCISES
# Which exercises live in a block, and their order within it
# (A1/A2/A3 for supersets, or sequence within a circuit/EMOM)
# ------------------------------------------------------------


class WorkoutBlockExercise(Base):
    __tablename__ = "workout_block_exercises"
    __table_args__ = (
        UniqueConstraint("block_id", "order_index", name="uq_block_exercises_block_order"),
        Index("idx_block_exercises_block", "block_id"),
        Index("idx_block_exercises_exercise", "exercise_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    block_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workout_blocks.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)  # A1=0, A2=1, A3=2 etc within the block

    block: Mapped["WorkoutBlock"] = relationship(back_populates="block_exercises")
    exercise: Mapped["Exercise"] = relationship(back_populates="block_usages")
    prescribed_sets: Mapped[list["PrescribedSet"]] = relationship(
        back_populates="block_exercise",
        cascade="all, delete-orphan",
        order_by="PrescribedSet.set_number",
    )
    # No delete-orphan: logged_sets.workout_block_exercise_id has no ON
    # DELETE clause.
    logged_set_links: Mapped[list["LoggedSet"]] = relationship(
        back_populates="workout_block_exercise"
    )

    def __repr__(self) -> str:
        return (
            f"WorkoutBlockExercise(id={self.id!r}, block_id={self.block_id!r}, "
            f"exercise_id={self.exercise_id!r})"
        )


# ------------------------------------------------------------
# PRESCRIBED SETS
# The actual prescription. set_number doubles as "round number" for
# circuits/EMOM/AMRAP. Mandatory for every block type, including
# conditioning blocks (load prescribed per exercise).
# ------------------------------------------------------------


class PrescribedSet(Base):
    __tablename__ = "prescribed_sets"
    __table_args__ = (
        CheckConstraint(
            "load_type IN ('absolute', 'percent_1rm')", name="ck_prescribed_sets_load_type"
        ),
        UniqueConstraint(
            "workout_block_exercise_id", "set_number", name="uq_prescribed_sets_exercise_set"
        ),
        Index("idx_prescribed_sets_block_exercise", "workout_block_exercise_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workout_block_exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workout_block_exercises.id", ondelete="CASCADE"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)  # or round number, per block_type

    reps_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    load_value: Mapped[float | None] = mapped_column(REAL, nullable=True)  # absolute weight OR %1RM
    load_type: Mapped[str | None] = mapped_column(Text, nullable=True)  # interprets load_value

    rir_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rir_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tempo: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g. "3-1-1-0"

    block_exercise: Mapped["WorkoutBlockExercise"] = relationship(back_populates="prescribed_sets")
    # No delete-orphan: logged_sets.prescribed_set_id is ON DELETE SET NULL,
    # not CASCADE — a logged set outlives the prescription it was checked
    # against.
    logged_set_links: Mapped[list["LoggedSet"]] = relationship(back_populates="prescribed_set")

    def __repr__(self) -> str:
        return (
            f"PrescribedSet(id={self.id!r}, "
            f"workout_block_exercise_id={self.workout_block_exercise_id!r}, "
            f"set_number={self.set_number!r})"
        )


# ------------------------------------------------------------
# TEMPLATE LAYER (reusable, not tied to any client)
# ------------------------------------------------------------


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "12-Week HYROX Prep"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )

    weeks: Mapped[list["ProgramWeek"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramWeek.week_number",
    )
    # No delete-orphan: program_assignments.program_id is ON DELETE SET
    # NULL — an assignment survives deletion of the template it was cloned
    # from.
    assignments: Mapped[list["ProgramAssignment"]] = relationship(back_populates="program")

    def __repr__(self) -> str:
        return f"Program(id={self.id!r}, name={self.name!r})"


class ProgramWeek(Base):
    __tablename__ = "program_weeks"
    __table_args__ = (
        CheckConstraint(
            "phase_label IN ('accumulation', 'intensification', 'deload') OR phase_label IS NULL",
            name="ck_program_weeks_phase_label",
        ),
        UniqueConstraint("program_id", "week_number", name="uq_program_weeks_program_week"),
        Index("idx_program_weeks_program", "program_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)

    phase_label: Mapped[str | None] = mapped_column(Text, nullable=True)  # not every week needs one
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    program: Mapped["Program"] = relationship(back_populates="weeks")
    days: Mapped[list["ProgramDay"]] = relationship(
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="ProgramDay.day_number",
    )

    def __repr__(self) -> str:
        return f"ProgramWeek(id={self.id!r}, program_id={self.program_id!r}, week_number={self.week_number!r})"


class ProgramDay(Base):
    __tablename__ = "program_days"
    __table_args__ = (
        UniqueConstraint("program_week_id", "day_number", name="uq_program_days_week_day"),
        Index("idx_program_days_week", "program_week_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_week_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("program_weeks.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # flexible: however many days this week has
    label: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g. "Lower Body", "Conditioning"

    week: Mapped["ProgramWeek"] = relationship(back_populates="days")
    day_workouts: Mapped[list["ProgramDayWorkout"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="ProgramDayWorkout.order_index",
    )

    def __repr__(self) -> str:
        return f"ProgramDay(id={self.id!r}, program_week_id={self.program_week_id!r}, day_number={self.day_number!r})"


class ProgramDayWorkout(Base):
    __tablename__ = "program_day_workouts"
    __table_args__ = (
        UniqueConstraint("program_day_id", "order_index", name="uq_program_day_workouts_day_order"),
        Index("idx_program_day_workouts_day", "program_day_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("program_days.id", ondelete="CASCADE"), nullable=False
    )
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workouts.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )  # supports multiple workouts per day if ever needed

    day: Mapped["ProgramDay"] = relationship(back_populates="day_workouts")
    workout: Mapped["Workout"] = relationship(back_populates="program_day_links")

    def __repr__(self) -> str:
        return (
            f"ProgramDayWorkout(id={self.id!r}, program_day_id={self.program_day_id!r}, "
            f"workout_id={self.workout_id!r})"
        )


# ------------------------------------------------------------
# ASSIGNMENT LAYER (client-specific clones, independently editable)
# ------------------------------------------------------------


class ProgramAssignment(Base):
    __tablename__ = "program_assignments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'paused', 'cancelled')",
            name="ck_program_assignments_status",
        ),
        Index("idx_assignments_program", "program_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nullable: keeps a reference to the template it was cloned from, but
    # the assignment survives if the template is later deleted.
    program_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("programs.id", ondelete="SET NULL"), nullable=True
    )
    # TODO(clients table): swap for a client_id FK once a clients table
    # exists — flagged, not built, per this phase's scope.
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[str] = mapped_column(Text, nullable=False)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)  # copied at clone time, then independent
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default=text("'active'")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    program: Mapped["Program | None"] = relationship(back_populates="assignments")
    assigned_weeks: Mapped[list["AssignedProgramWeek"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignedProgramWeek.week_number",
    )

    def __repr__(self) -> str:
        return f"ProgramAssignment(id={self.id!r}, client_name={self.client_name!r})"


class AssignedProgramWeek(Base):
    __tablename__ = "assigned_program_weeks"
    __table_args__ = (
        CheckConstraint(
            "phase_label IN ('accumulation', 'intensification', 'deload') OR phase_label IS NULL",
            name="ck_assigned_program_weeks_phase_label",
        ),
        UniqueConstraint(
            "program_assignment_id", "week_number", name="uq_assigned_program_weeks_assignment_week"
        ),
        Index("idx_assigned_weeks_assignment", "program_assignment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_assignment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("program_assignments.id", ondelete="CASCADE"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)

    phase_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assignment: Mapped["ProgramAssignment"] = relationship(back_populates="assigned_weeks")
    days: Mapped[list["AssignedProgramDay"]] = relationship(
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="AssignedProgramDay.day_number",
    )

    def __repr__(self) -> str:
        return (
            f"AssignedProgramWeek(id={self.id!r}, "
            f"program_assignment_id={self.program_assignment_id!r}, week_number={self.week_number!r})"
        )


class AssignedProgramDay(Base):
    __tablename__ = "assigned_program_days"
    __table_args__ = (
        UniqueConstraint(
            "assigned_program_week_id", "day_number", name="uq_assigned_program_days_week_day"
        ),
        Index("idx_assigned_days_week", "assigned_program_week_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assigned_program_week_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assigned_program_weeks.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_date: Mapped[str | None] = mapped_column(Text, nullable=True)  # actual calendar date once scheduled

    week: Mapped["AssignedProgramWeek"] = relationship(back_populates="days")
    day_workouts: Mapped[list["AssignedDayWorkout"]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="AssignedDayWorkout.order_index",
    )
    session_logs: Mapped[list["SessionLog"]] = relationship(
        back_populates="assigned_day", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"AssignedProgramDay(id={self.id!r}, "
            f"assigned_program_week_id={self.assigned_program_week_id!r}, day_number={self.day_number!r})"
        )


class AssignedDayWorkout(Base):
    __tablename__ = "assigned_day_workouts"
    __table_args__ = (
        UniqueConstraint(
            "assigned_program_day_id", "order_index", name="uq_assigned_day_workouts_day_order"
        ),
        Index("idx_assigned_day_workouts_day", "assigned_program_day_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assigned_program_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assigned_program_days.id", ondelete="CASCADE"), nullable=False
    )
    # Can point to a different workout than the template if the client's
    # plan was edited after cloning.
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workouts.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    day: Mapped["AssignedProgramDay"] = relationship(back_populates="day_workouts")
    workout: Mapped["Workout"] = relationship(back_populates="assigned_day_links")

    def __repr__(self) -> str:
        return (
            f"AssignedDayWorkout(id={self.id!r}, "
            f"assigned_program_day_id={self.assigned_program_day_id!r}, workout_id={self.workout_id!r})"
        )


# ------------------------------------------------------------
# ACTUALS LAYER (lightweight — what really happened)
# ------------------------------------------------------------


class SessionLog(Base):
    __tablename__ = "session_logs"
    __table_args__ = (Index("idx_session_logs_day", "assigned_program_day_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assigned_program_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assigned_program_days.id", ondelete="CASCADE"), nullable=False
    )
    completed_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )
    session_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g. "felt flat today"

    assigned_day: Mapped["AssignedProgramDay"] = relationship(back_populates="session_logs")
    logged_sets: Mapped[list["LoggedSet"]] = relationship(
        back_populates="session_log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"SessionLog(id={self.id!r}, assigned_program_day_id={self.assigned_program_day_id!r})"


class LoggedSet(Base):
    __tablename__ = "logged_sets"
    __table_args__ = (
        CheckConstraint(
            "actual_load_type IN ('absolute', 'percent_1rm') OR actual_load_type IS NULL",
            name="ck_logged_sets_actual_load_type",
        ),
        Index("idx_logged_sets_session", "session_log_id"),
        Index("idx_logged_sets_prescribed", "prescribed_set_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_log_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("session_logs.id", ondelete="CASCADE"), nullable=False
    )
    # Nullable: link back to what was planned, if applicable.
    prescribed_set_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("prescribed_sets.id", ondelete="SET NULL"), nullable=True
    )
    workout_block_exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workout_block_exercises.id"), nullable=False
    )  # which exercise this actual belongs to
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)

    actual_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_load_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    actual_load_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_rir: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session_log: Mapped["SessionLog"] = relationship(back_populates="logged_sets")
    prescribed_set: Mapped["PrescribedSet | None"] = relationship(back_populates="logged_set_links")
    workout_block_exercise: Mapped["WorkoutBlockExercise"] = relationship(
        back_populates="logged_set_links"
    )

    def __repr__(self) -> str:
        return (
            f"LoggedSet(id={self.id!r}, session_log_id={self.session_log_id!r}, "
            f"set_number={self.set_number!r})"
        )

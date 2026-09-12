"""
SQLAlchemy models mirroring phase1_schema.sql and phase2_schema.sql exactly.

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

    def __repr__(self) -> str:
        return (
            f"PrescribedSet(id={self.id!r}, "
            f"workout_block_exercise_id={self.workout_block_exercise_id!r}, "
            f"set_number={self.set_number!r})"
        )

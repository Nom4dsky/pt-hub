"""
SQLAlchemy models mirroring phase1_schema.sql exactly.

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
    Text,
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

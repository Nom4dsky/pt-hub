"""SQLAlchemy models — Phase 1 (exercise database) only.

Mirrors the Phase 1 section of schema.sql exactly. Phase 2/3 tables
(clients, workouts, programs, ...) are intentionally not modeled here yet.
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # 'Chest', 'Lats', 'Glutes', 'Quads', ...


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # 'Barbell', 'Dumbbell', 'Cable', ...


class MovementPattern(Base):
    __tablename__ = "movement_patterns"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # 'Squat', 'Hinge', 'Push Horizontal', ...


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # 'knee-friendly', 'home-gym', ...


# Plain many-to-many join tables (no extra columns).
exercise_equipment = Table(
    "exercise_equipment",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("equipment_id", Integer, ForeignKey("equipment.id"), primary_key=True),
)

exercise_tags = Table(
    "exercise_tags",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class ExerciseMuscle(Base):
    """exercise_muscles join row — modeled as an association object (not a
    plain secondary table) because it carries the 'role' column."""

    __tablename__ = "exercise_muscles"
    __table_args__ = (CheckConstraint("role IN ('primary','secondary')", name="ck_exercise_muscles_role"),)

    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), primary_key=True)
    role = Column(String, nullable=False)

    exercise = relationship("Exercise", back_populates="exercise_muscles")
    muscle_group = relationship("MuscleGroup")


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint("difficulty IN ('beginner','intermediate','advanced')", name="ck_exercises_difficulty"),
        CheckConstraint(
            "tracking_type IN ('reps_weight','reps_only','time','distance','time_distance')",
            name="ck_exercises_tracking_type",
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)  # 'barbell-back-squat'
    movement_pattern_id = Column(Integer, ForeignKey("movement_patterns.id"))
    parent_exercise_id = Column(Integer, ForeignKey("exercises.id"))  # links variants, NULL if base
    unilateral = Column(Boolean, nullable=False, default=False)
    difficulty = Column(String)
    tracking_type = Column(String, nullable=False)
    cues = Column(Text)  # coaching cues / setup notes
    video_url = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    movement_pattern = relationship("MovementPattern")
    parent_exercise = relationship("Exercise", remote_side=[id])

    exercise_muscles = relationship(
        "ExerciseMuscle", back_populates="exercise", cascade="all, delete-orphan"
    )
    equipment = relationship("Equipment", secondary=exercise_equipment)
    tags = relationship("Tag", secondary=exercise_tags)

    @property
    def muscles(self):
        """Convenience alias so the API can expose `muscles` directly."""
        return self.exercise_muscles

"""
Pydantic request/response schemas for the exercise-management API.

Enum-like fields (exercise_type, compound_or_isolation, tracking_type,
muscle-link role) use Literal so FastAPI rejects a bad value with a 422
before it ever reaches the database — the same values as the CHECK
constraints in app/models.py / phase1_schema.sql, kept in sync by hand
since Pydantic can't read a SQLAlchemy CheckConstraint directly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExerciseType = Literal["strength", "mobility", "conditioning", "plyometric", "stability"]
CompoundOrIsolation = Literal["compound", "isolation"]
TrackingType = Literal["reps_weight", "reps_only", "time", "distance", "time_distance", "reps_time"]
MuscleRole = Literal["primary", "secondary", "stabilizer"]


# ------------------------------------------------------------
# Lookup tables (movement_patterns, muscles, equipment)
# ------------------------------------------------------------


class LookupIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class LookupOut(BaseModel):
    id: int
    name: str


# ------------------------------------------------------------
# Exercises
# ------------------------------------------------------------


class MuscleLinkIn(BaseModel):
    muscle_id: int
    role: MuscleRole


class MuscleLinkOut(BaseModel):
    muscle_id: int
    muscle_name: str
    role: MuscleRole


class EquipmentLinkIn(BaseModel):
    equipment_id: int
    is_required: bool = True


class EquipmentLinkOut(BaseModel):
    equipment_id: int
    equipment_name: str
    is_required: bool


class ExerciseIn(BaseModel):
    """Shared body for both create (POST) and update (PUT) — PUT replaces
    the whole record and its muscle/equipment links, same as the form."""

    name: str = Field(min_length=1, max_length=500)
    movement_pattern_id: int
    exercise_type: ExerciseType
    difficulty: int = Field(ge=1, le=6)
    unilateral: bool = False
    compound_or_isolation: CompoundOrIsolation
    tracking_type: TrackingType
    contraindications: str | None = None
    cue_notes: str | None = None
    video_url: str | None = None
    variant_of: int | None = None
    muscles: list[MuscleLinkIn] = []
    equipment: list[EquipmentLinkIn] = []


class ExerciseListItem(BaseModel):
    id: int
    name: str
    movement_pattern_id: int
    movement_pattern_name: str
    primary_muscle: str | None
    difficulty: int
    exercise_type: ExerciseType
    compound_or_isolation: CompoundOrIsolation


class ExerciseDetail(BaseModel):
    id: int
    name: str
    movement_pattern_id: int
    movement_pattern_name: str
    exercise_type: ExerciseType
    difficulty: int
    unilateral: bool
    compound_or_isolation: CompoundOrIsolation
    tracking_type: TrackingType
    contraindications: str | None
    cue_notes: str | None
    video_url: str | None
    variant_of: int | None
    variant_of_name: str | None
    created_at: str
    updated_at: str
    muscles: list[MuscleLinkOut]
    equipment: list[EquipmentLinkOut]


class ExerciseOption(BaseModel):
    """Minimal shape for the "variant of" searchable dropdown."""

    id: int
    name: str

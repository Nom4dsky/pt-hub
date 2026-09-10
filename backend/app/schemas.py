from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Difficulty = Literal["beginner", "intermediate", "advanced"]
TrackingType = Literal["reps_weight", "reps_only", "time", "distance", "time_distance"]
MuscleRole = Literal["primary", "secondary"]


# ---- reference tables ----------------------------------------------------

class MuscleGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class MovementPatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ExerciseMuscleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    muscle_group: MuscleGroupOut
    role: MuscleRole


# ---- exercises ------------------------------------------------------------

class ExerciseCreate(BaseModel):
    name: str
    slug: Optional[str] = Field(None, description="Auto-generated from name if omitted")
    movement_pattern: str
    parent_exercise_id: Optional[int] = None
    unilateral: bool = False
    difficulty: Optional[Difficulty] = None
    tracking_type: TrackingType
    cues: Optional[str] = None
    video_url: Optional[str] = None
    primary_muscles: List[str] = []
    secondary_muscles: List[str] = []
    equipment: List[str] = []
    tags: List[str] = []


class ExerciseUpdate(BaseModel):
    """All fields optional — only fields explicitly present in the request
    body are applied (see `.model_dump(exclude_unset=True)` in crud.py)."""

    name: Optional[str] = None
    slug: Optional[str] = None
    movement_pattern: Optional[str] = None
    parent_exercise_id: Optional[int] = None
    unilateral: Optional[bool] = None
    difficulty: Optional[Difficulty] = None
    tracking_type: Optional[TrackingType] = None
    cues: Optional[str] = None
    video_url: Optional[str] = None
    primary_muscles: Optional[List[str]] = None
    secondary_muscles: Optional[List[str]] = None
    equipment: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_exercise_id: Optional[int]
    unilateral: bool
    difficulty: Optional[str]
    tracking_type: str
    cues: Optional[str]
    video_url: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    movement_pattern: Optional[MovementPatternOut]
    muscles: List[ExerciseMuscleOut] = []
    equipment: List[EquipmentOut] = []
    tags: List[TagOut] = []

"""Query + mutation helpers for exercises and their reference tables.

Shared by both the FastAPI endpoints (main.py) and the seed script
(seed.py), so "get-or-create a muscle group by name" behaves identically
whether it happens during a seed load or a POST /exercises call.
"""
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Type

from sqlalchemy.orm import Session, joinedload, selectinload

from . import models, schemas
from .utils import slugify


# ---- get-or-create for the small reference tables -------------------------

def get_or_create(db: Session, model: Type, name: str):
    name = name.strip()
    obj = db.query(model).filter(model.name == name).first()
    if obj:
        return obj
    obj = model(name=name)
    db.add(obj)
    db.flush()  # assigns obj.id without committing the outer transaction
    return obj


# ---- exercise relation sync (used by both create and update) --------------

def sync_muscles(db: Session, exercise: models.Exercise, primary: List[str], secondary: List[str]) -> None:
    exercise.exercise_muscles = []
    db.flush()
    for name in primary or []:
        mg = get_or_create(db, models.MuscleGroup, name)
        db.add(models.ExerciseMuscle(exercise_id=exercise.id, muscle_group_id=mg.id, role="primary"))
    for name in secondary or []:
        mg = get_or_create(db, models.MuscleGroup, name)
        db.add(models.ExerciseMuscle(exercise_id=exercise.id, muscle_group_id=mg.id, role="secondary"))


def sync_equipment(db: Session, exercise: models.Exercise, names: List[str]) -> None:
    exercise.equipment = [get_or_create(db, models.Equipment, n) for n in (names or [])]


def sync_tags(db: Session, exercise: models.Exercise, names: List[str]) -> None:
    exercise.tags = [get_or_create(db, models.Tag, n) for n in (names or [])]


# ---- reads ------------------------------------------------------------------

def _exercise_query(db: Session):
    return db.query(models.Exercise).options(
        joinedload(models.Exercise.movement_pattern),
        selectinload(models.Exercise.exercise_muscles).joinedload(models.ExerciseMuscle.muscle_group),
        selectinload(models.Exercise.equipment),
        selectinload(models.Exercise.tags),
    )


def get_exercise(db: Session, identifier: str) -> Optional[models.Exercise]:
    """Look up by numeric id or by slug."""
    query = _exercise_query(db)
    if identifier.isdigit():
        return query.filter(models.Exercise.id == int(identifier)).first()
    return query.filter(models.Exercise.slug == identifier).first()


def list_exercises(
    db: Session,
    movement_pattern: Optional[List[str]] = None,
    muscle_group: Optional[List[str]] = None,
    muscle_role: Optional[str] = None,
    equipment: Optional[List[str]] = None,
    equipment_mode: str = "any",
    tag: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[models.Exercise]:
    """List exercises matching all given filters (AND across filter types).

    `equipment_mode`:
      - "any"    (default) exercise uses at least one of the listed equipment
      - "subset" exercise's *entire* equipment list is contained in the ones
                 given — e.g. "what can I do with only dumbbells" ->
                 equipment=Dumbbell&equipment_mode=subset
    """
    query = _exercise_query(db)

    if not include_inactive:
        query = query.filter(models.Exercise.is_active.is_(True))

    if difficulty:
        query = query.filter(models.Exercise.difficulty == difficulty)

    if movement_pattern:
        query = query.join(models.Exercise.movement_pattern).filter(
            models.MovementPattern.name.in_(movement_pattern)
        )

    if muscle_group:
        query = query.join(models.Exercise.exercise_muscles).join(models.ExerciseMuscle.muscle_group).filter(
            models.MuscleGroup.name.in_(muscle_group)
        )
        if muscle_role:
            query = query.filter(models.ExerciseMuscle.role == muscle_role)

    if tag:
        query = query.join(models.Exercise.tags).filter(models.Tag.name.in_(tag))

    if equipment and equipment_mode == "any":
        query = query.join(models.Exercise.equipment).filter(models.Equipment.name.in_(equipment))

    exercises = query.distinct().order_by(models.Exercise.name).all()

    if equipment and equipment_mode == "subset":
        allowed = {e.strip().lower() for e in equipment}
        exercises = [
            ex for ex in exercises
            if {eq.name.lower() for eq in ex.equipment}.issubset(allowed)
        ]

    return exercises[offset: offset + limit]


# ---- writes -----------------------------------------------------------------

def create_exercise(db: Session, data: schemas.ExerciseCreate) -> models.Exercise:
    slug = (data.slug or slugify(data.name)).strip()
    if db.query(models.Exercise).filter(models.Exercise.slug == slug).first():
        raise ValueError(f"An exercise with slug '{slug}' already exists")

    movement_pattern = get_or_create(db, models.MovementPattern, data.movement_pattern)

    exercise = models.Exercise(
        name=data.name.strip(),
        slug=slug,
        movement_pattern_id=movement_pattern.id,
        parent_exercise_id=data.parent_exercise_id,
        unilateral=data.unilateral,
        difficulty=data.difficulty,
        tracking_type=data.tracking_type,
        cues=data.cues,
        video_url=data.video_url,
    )
    db.add(exercise)
    db.flush()  # assigns exercise.id for the join-table rows below

    sync_muscles(db, exercise, data.primary_muscles, data.secondary_muscles)
    sync_equipment(db, exercise, data.equipment)
    sync_tags(db, exercise, data.tags)

    db.commit()
    db.refresh(exercise)
    return exercise


def update_exercise(db: Session, exercise: models.Exercise, data: schemas.ExerciseUpdate) -> models.Exercise:
    payload = data.model_dump(exclude_unset=True)

    if "slug" in payload and payload["slug"]:
        new_slug = payload["slug"].strip()
        clash = db.query(models.Exercise).filter(
            models.Exercise.slug == new_slug, models.Exercise.id != exercise.id
        ).first()
        if clash:
            raise ValueError(f"An exercise with slug '{new_slug}' already exists")
        exercise.slug = new_slug

    if "name" in payload:
        exercise.name = payload["name"].strip()

    if "movement_pattern" in payload and payload["movement_pattern"]:
        exercise.movement_pattern = get_or_create(db, models.MovementPattern, payload["movement_pattern"])

    for field in ("parent_exercise_id", "unilateral", "difficulty", "tracking_type", "cues", "video_url", "is_active"):
        if field in payload:
            setattr(exercise, field, payload[field])

    if "primary_muscles" in payload or "secondary_muscles" in payload:
        current_primary = [em.muscle_group.name for em in exercise.exercise_muscles if em.role == "primary"]
        current_secondary = [em.muscle_group.name for em in exercise.exercise_muscles if em.role == "secondary"]
        sync_muscles(
            db,
            exercise,
            payload.get("primary_muscles", current_primary),
            payload.get("secondary_muscles", current_secondary),
        )

    if "equipment" in payload:
        sync_equipment(db, exercise, payload["equipment"])

    if "tags" in payload:
        sync_tags(db, exercise, payload["tags"])

    exercise.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(exercise)
    return exercise


def set_exercise_active(db: Session, exercise: models.Exercise, is_active: bool) -> models.Exercise:
    """Soft delete/restore — exercises are never hard-deleted since
    workout_exercises (Phase 2) will reference these rows."""
    exercise.is_active = is_active
    exercise.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(exercise)
    return exercise

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import Base, engine, get_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="PT Hub — Exercise API",
    description="Phase 1: exercise database (movement patterns, muscles, equipment, tags).",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---- reference tables (useful for building filter UIs) --------------------

@app.get("/movement-patterns", response_model=List[schemas.MovementPatternOut])
def list_movement_patterns(db: Session = Depends(get_db)):
    return db.query(models.MovementPattern).order_by(models.MovementPattern.name).all()


@app.get("/muscle-groups", response_model=List[schemas.MuscleGroupOut])
def list_muscle_groups(db: Session = Depends(get_db)):
    return db.query(models.MuscleGroup).order_by(models.MuscleGroup.name).all()


@app.get("/equipment", response_model=List[schemas.EquipmentOut])
def list_equipment(db: Session = Depends(get_db)):
    return db.query(models.Equipment).order_by(models.Equipment.name).all()


@app.get("/tags", response_model=List[schemas.TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(models.Tag).order_by(models.Tag.name).all()


# ---- exercises --------------------------------------------------------------

@app.get("/exercises", response_model=List[schemas.ExerciseOut])
def list_exercises(
    movement_pattern: Optional[List[str]] = Query(None, description="Match ANY of these movement pattern names"),
    muscle_group: Optional[List[str]] = Query(None, description="Match ANY of these muscle group names"),
    muscle_role: Optional[schemas.MuscleRole] = Query(None, description="Restrict muscle_group match to this role"),
    equipment: Optional[List[str]] = Query(None, description="Equipment names to filter by"),
    equipment_mode: str = Query(
        "any",
        pattern="^(any|subset)$",
        description="'any': uses at least one listed equipment. 'subset': exercise needs nothing beyond what's listed (e.g. 'only dumbbells').",
    ),
    tag: Optional[List[str]] = Query(None, description="Match ANY of these tag names"),
    difficulty: Optional[schemas.Difficulty] = None,
    include_inactive: bool = Query(False, description="Include soft-deleted exercises"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return crud.list_exercises(
        db,
        movement_pattern=movement_pattern,
        muscle_group=muscle_group,
        muscle_role=muscle_role,
        equipment=equipment,
        equipment_mode=equipment_mode,
        tag=tag,
        difficulty=difficulty,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )


@app.get("/exercises/{identifier}", response_model=schemas.ExerciseOut)
def get_exercise(identifier: str, db: Session = Depends(get_db)):
    """`identifier` may be a numeric id or a slug (e.g. 'barbell-back-squat')."""
    exercise = crud.get_exercise(db, identifier)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@app.post("/exercises", response_model=schemas.ExerciseOut, status_code=201)
def create_exercise(payload: schemas.ExerciseCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_exercise(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.patch("/exercises/{exercise_id}", response_model=schemas.ExerciseOut)
def update_exercise(exercise_id: int, payload: schemas.ExerciseUpdate, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    try:
        return crud.update_exercise(db, exercise, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/exercises/{exercise_id}/deactivate", response_model=schemas.ExerciseOut)
def deactivate_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Soft delete — sets is_active=False. Never hard-deletes (Phase 2's
    workout_exercises will reference these rows)."""
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return crud.set_exercise_active(db, exercise, False)


@app.post("/exercises/{exercise_id}/reactivate", response_model=schemas.ExerciseOut)
def reactivate_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return crud.set_exercise_active(db, exercise, True)

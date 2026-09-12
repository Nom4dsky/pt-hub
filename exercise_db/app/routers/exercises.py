from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.schemas import (
    CompoundOrIsolation,
    ExerciseDetail,
    ExerciseIn,
    ExerciseListItem,
    ExerciseOption,
    ExerciseType,
)

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseListItem])
def list_exercises(
    movement_pattern_id: int | None = None,
    muscle_id: int | None = None,
    equipment_id: int | None = None,
    exercise_type: ExerciseType | None = None,
    difficulty_min: int | None = Query(None, ge=1, le=6),
    difficulty_max: int | None = Query(None, ge=1, le=6),
    compound_or_isolation: CompoundOrIsolation | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_exercises(
        db,
        movement_pattern_id=movement_pattern_id,
        muscle_id=muscle_id,
        equipment_id=equipment_id,
        exercise_type=exercise_type,
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
        compound_or_isolation=compound_or_isolation,
        search=search,
    )


@router.get("/options", response_model=list[ExerciseOption])
def list_exercise_options(exclude_id: int | None = None, db: Session = Depends(get_db)):
    """For the "variant of" searchable dropdown. Registered before
    /{exercise_id} so "options" isn't swallowed as a path param."""
    return crud.list_exercise_options(db, exclude_id=exclude_id)


@router.get("/{exercise_id}", response_model=ExerciseDetail)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    detail = crud.get_exercise_detail(db, exercise_id)
    if detail is None:
        raise HTTPException(404, "Exercise not found")
    return detail


@router.post("", response_model=ExerciseDetail, status_code=201)
def create_exercise(payload: ExerciseIn, db: Session = Depends(get_db)):
    return crud.create_exercise(db, payload)


@router.put("/{exercise_id}", response_model=ExerciseDetail)
def update_exercise(exercise_id: int, payload: ExerciseIn, db: Session = Depends(get_db)):
    detail = crud.update_exercise(db, exercise_id, payload)
    if detail is None:
        raise HTTPException(404, "Exercise not found")
    return detail


@router.delete("/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_exercise(db, exercise_id)
    if not deleted:
        raise HTTPException(404, "Exercise not found")

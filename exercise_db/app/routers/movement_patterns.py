from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.models import MovementPattern
from app.schemas import LookupIn, LookupOut

router = APIRouter(prefix="/api/movement-patterns", tags=["movement-patterns"])


@router.get("", response_model=list[LookupOut])
def list_movement_patterns(db: Session = Depends(get_db)):
    return crud.list_lookup(db, MovementPattern)


@router.post("", response_model=LookupOut, status_code=201)
def create_movement_pattern(payload: LookupIn, db: Session = Depends(get_db)):
    return crud.create_lookup(db, MovementPattern, payload)


@router.put("/{item_id}", response_model=LookupOut)
def update_movement_pattern(item_id: int, payload: LookupIn, db: Session = Depends(get_db)):
    result = crud.update_lookup(db, MovementPattern, item_id, payload)
    if result is None:
        raise HTTPException(404, "Movement pattern not found")
    return result


@router.delete("/{item_id}", status_code=204)
def delete_movement_pattern(item_id: int, db: Session = Depends(get_db)):
    if not crud.delete_movement_pattern(db, item_id):
        raise HTTPException(404, "Movement pattern not found")

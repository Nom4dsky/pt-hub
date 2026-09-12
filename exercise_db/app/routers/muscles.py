from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.models import Muscle
from app.schemas import LookupIn, LookupOut

router = APIRouter(prefix="/api/muscles", tags=["muscles"])


@router.get("", response_model=list[LookupOut])
def list_muscles(db: Session = Depends(get_db)):
    return crud.list_lookup(db, Muscle)


@router.post("", response_model=LookupOut, status_code=201)
def create_muscle(payload: LookupIn, db: Session = Depends(get_db)):
    return crud.create_lookup(db, Muscle, payload)


@router.put("/{item_id}", response_model=LookupOut)
def update_muscle(item_id: int, payload: LookupIn, db: Session = Depends(get_db)):
    result = crud.update_lookup(db, Muscle, item_id, payload)
    if result is None:
        raise HTTPException(404, "Muscle not found")
    return result


@router.delete("/{item_id}", status_code=204)
def delete_muscle(item_id: int, db: Session = Depends(get_db)):
    if not crud.delete_muscle(db, item_id):
        raise HTTPException(404, "Muscle not found")

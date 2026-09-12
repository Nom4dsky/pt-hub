from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.deps import get_db
from app.models import Equipment
from app.schemas import LookupIn, LookupOut

router = APIRouter(prefix="/api/equipment", tags=["equipment"])


@router.get("", response_model=list[LookupOut])
def list_equipment(db: Session = Depends(get_db)):
    return crud.list_lookup(db, Equipment)


@router.post("", response_model=LookupOut, status_code=201)
def create_equipment(payload: LookupIn, db: Session = Depends(get_db)):
    return crud.create_lookup(db, Equipment, payload)


@router.put("/{item_id}", response_model=LookupOut)
def update_equipment(item_id: int, payload: LookupIn, db: Session = Depends(get_db)):
    result = crud.update_lookup(db, Equipment, item_id, payload)
    if result is None:
        raise HTTPException(404, "Equipment not found")
    return result


@router.delete("/{item_id}", status_code=204)
def delete_equipment(item_id: int, db: Session = Depends(get_db)):
    if not crud.delete_equipment(db, item_id):
        raise HTTPException(404, "Equipment not found")

"""POST /api/transfers -- move money between two of the current user's own
accounts, recorded as a single Transaction row with type="transfer".
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/transfers", tags=["transfers"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transfer(
    transfer: schemas.TransferCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if transfer.from_account_id == transfer.to_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="from_account_id and to_account_id must be different",
        )
    from_account = crud.get_account(db, transfer.from_account_id, current_user.id)
    if from_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source account not found")
    to_account = crud.get_account(db, transfer.to_account_id, current_user.id)
    if to_account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Destination account not found"
        )
    return crud.create_transfer(db, current_user.id, transfer)

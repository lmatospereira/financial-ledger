"""GET/POST/PUT/DELETE /api/transactions, GET /api/summary"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api", tags=["transactions"], dependencies=[Depends(get_current_user)])


def _validate_month_year(month: int, year: int) -> None:
    if not (1 <= month <= 12):
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")
    if year < 1:
        raise HTTPException(status_code=422, detail="year must be a positive integer")


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    _validate_month_year(month, year)
    return crud.get_transactions(db, month, year)


@router.post("/transactions", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    if transaction.category_id is not None:
        category = crud.get_category(db, transaction.category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return crud.create_transaction(db, transaction)


@router.put("/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(
    transaction_id: int, transaction: schemas.TransactionUpdate, db: Session = Depends(get_db)
):
    db_transaction = crud.get_transaction(db, transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if transaction.category_id is not None:
        category = crud.get_category(db, transaction.category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return crud.update_transaction(db, db_transaction, transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    db_transaction = crud.get_transaction(db, transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    crud.delete_transaction(db, db_transaction)
    return None


@router.get("/summary", response_model=schemas.SummaryOut)
def summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    _validate_month_year(month, year)
    return crud.get_summary(db, month, year)

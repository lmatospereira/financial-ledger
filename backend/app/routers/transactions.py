"""GET/POST/PUT/DELETE /api/transactions, GET /api/summary -- scoped to the
current user (and optionally further scoped to one of their accounts).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
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
    account_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_month_year(month, year)
    if account_id is not None:
        account = crud.get_account(db, account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    # Generate any due recurring transactions for the current user
    crud.generate_due_recurring_transactions(db, current_user.id)
    return crud.get_transactions(db, current_user.id, month, year, account_id, status_filter)


@router.post("/transactions", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: schemas.TransactionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = crud.get_account(db, transaction.account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if transaction.category_id is not None:
        category = crud.get_category(db, transaction.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return crud.create_transaction(db, current_user.id, transaction)


@router.post("/transactions/installments", response_model=list[schemas.TransactionOut], status_code=status.HTTP_201_CREATED)
def create_installments(
    installment: schemas.InstallmentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = crud.get_account(db, installment.account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if installment.category_id is not None:
        category = crud.get_category(db, installment.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return crud.create_installments(db, current_user.id, installment)


@router.put("/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(
    transaction_id: int,
    transaction: schemas.TransactionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_transaction = crud.get_transaction(db, transaction_id, current_user.id)
    if db_transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    account = crud.get_account(db, transaction.account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if transaction.category_id is not None:
        category = crud.get_category(db, transaction.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return crud.update_transaction(db, db_transaction, transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_transaction = crud.get_transaction(db, transaction_id, current_user.id)
    if db_transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    crud.delete_transaction(db, db_transaction)
    return None


@router.post("/transactions/{transaction_id}/confirm", response_model=schemas.TransactionOut)
def confirm_transaction(
    transaction_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crud.confirm_transaction(db, transaction_id, current_user.id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Transaction already confirmed"
        )


@router.get("/summary", response_model=schemas.SummaryOut)
def summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    account_id: Optional[int] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_month_year(month, year)
    if account_id is not None:
        account = crud.get_account(db, account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return crud.get_summary(db, current_user.id, month, year, account_id)

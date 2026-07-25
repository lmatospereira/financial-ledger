"""GET/POST/PUT/DELETE /api/recurring-transactions -- scoped to the current user.

Recurring transactions are rules that automatically generate transactions on a
given day of each month. Lazy generation happens when list_transactions is called.
PUT supports toggling the `active` field.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/api/recurring-transactions",
    tags=["recurring-transactions"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.RecurringTransactionOut])
def list_recurring_transactions(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return crud.get_recurring_transactions(db, current_user.id)


@router.post("", response_model=schemas.RecurringTransactionOut, status_code=status.HTTP_201_CREATED)
def create_recurring_transaction(
    rt: schemas.RecurringTransactionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify account belongs to current user
    account = crud.get_account(db, rt.account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Verify category belongs to current user (if provided)
    if rt.category_id is not None:
        category = crud.get_category(db, rt.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db_rt = crud.create_recurring_transaction(db, current_user.id, rt)
    return db_rt


@router.put("/{recurring_transaction_id}", response_model=schemas.RecurringTransactionOut)
def update_recurring_transaction(
    recurring_transaction_id: int,
    rt: schemas.RecurringTransactionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_rt = crud.get_recurring_transaction(db, recurring_transaction_id, current_user.id)
    if db_rt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")

    # Verify account belongs to current user (if changed)
    if rt.account_id != db_rt.account_id:
        account = crud.get_account(db, rt.account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Verify category belongs to current user (if changed)
    if rt.category_id != db_rt.category_id and rt.category_id is not None:
        category = crud.get_category(db, rt.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db_rt = crud.update_recurring_transaction(db, db_rt, rt)
    return db_rt


@router.delete("/{recurring_transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_transaction(
    recurring_transaction_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_rt = crud.get_recurring_transaction(db, recurring_transaction_id, current_user.id)
    if db_rt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")
    crud.delete_recurring_transaction(db, db_rt)
    return None

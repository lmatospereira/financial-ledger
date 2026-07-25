"""GET/POST/PUT/DELETE /api/bills -- scoped to the current user.

Bills represent pending payments with due dates. POST /api/bills/{id}/pay creates
a transaction and marks the bill as paid.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/api/bills",
    tags=["bills"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.BillOut])
def list_bills(
    paid: Optional[bool] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_bills(db, current_user.id, paid=paid)


@router.post("", response_model=schemas.BillOut, status_code=status.HTTP_201_CREATED)
def create_bill(
    bill: schemas.BillCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify account belongs to current user (if provided)
    if bill.account_id is not None:
        account = crud.get_account(db, bill.account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Verify category belongs to current user (if provided)
    if bill.category_id is not None:
        category = crud.get_category(db, bill.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db_bill = crud.create_bill(db, current_user.id, bill)
    return db_bill


@router.put("/{bill_id}", response_model=schemas.BillOut)
def update_bill(
    bill_id: int,
    bill: schemas.BillUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_bill = crud.get_bill(db, bill_id, current_user.id)
    if db_bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Verify account belongs to current user (if changed)
    if bill.account_id is not None and bill.account_id != db_bill.account_id:
        account = crud.get_account(db, bill.account_id, current_user.id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Verify category belongs to current user (if changed)
    if bill.category_id is not None and bill.category_id != db_bill.category_id:
        category = crud.get_category(db, bill.category_id, current_user.id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db_bill = crud.update_bill(db, db_bill, bill)
    return db_bill


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(
    bill_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_bill = crud.get_bill(db, bill_id, current_user.id)
    if db_bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    crud.delete_bill(db, db_bill)
    return None


@router.post("/{bill_id}/pay", response_model=schemas.BillOut)
def pay_bill(
    bill_id: int,
    pay_req: schemas.BillPayRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_bill = crud.get_bill(db, bill_id, current_user.id)
    if db_bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    if db_bill.paid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bill already paid")

    # Verify account belongs to current user
    account = crud.get_account(db, pay_req.account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Create a transaction for this payment
    from datetime import date

    tx_create = schemas.TransactionCreate(
        date=date.today(),
        description=db_bill.description,
        amount=db_bill.amount,
        type="expense",
        category_id=db_bill.category_id,
        account_id=pay_req.account_id,
    )
    db_tx = crud.create_transaction(db, current_user.id, tx_create)

    # Update bill to mark as paid
    db_bill.paid = True
    db_bill.account_id = pay_req.account_id
    db_bill.paid_transaction_id = db_tx.id
    db.commit()
    db.refresh(db_bill)

    return db_bill

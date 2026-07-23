"""GET/POST/PUT/DELETE /api/accounts -- scoped to the current user.

Each account in list/get responses carries a computed `balance` field (all
transactions/transfers touching that account, all-time). Deleting an account
that still has transactions is blocked with 409 -- the caller must delete or
reassign those transactions first.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
    dependencies=[Depends(get_current_user)],
)


def _to_out(db: Session, account: models.Account) -> schemas.AccountOut:
    return schemas.AccountOut(
        id=account.id,
        name=account.name,
        type=account.type,
        color=account.color,
        balance=crud.get_account_balance(db, account.id),
    )


@router.get("", response_model=list[schemas.AccountOut])
def list_accounts(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    accounts = crud.get_accounts(db, current_user.id)
    return [_to_out(db, account) for account in accounts]


@router.post("", response_model=schemas.AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_account = crud.create_account(db, current_user.id, account)
    return _to_out(db, db_account)


@router.put("/{account_id}", response_model=schemas.AccountOut)
def update_account(
    account_id: int,
    account: schemas.AccountUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_account = crud.get_account(db, account_id, current_user.id)
    if db_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    db_account = crud.update_account(db, db_account, account)
    return _to_out(db, db_account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_account = crud.get_account(db, account_id, current_user.id)
    if db_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if crud.account_has_transactions(db, account_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an account that has transactions; delete or reassign them first",
        )
    crud.delete_account(db, db_account)
    return None

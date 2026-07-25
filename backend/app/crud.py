"""Database access helpers used by the routers."""
from datetime import date
from calendar import monthrange

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models, schemas


def _sum_where(db: Session, *filters) -> float:
    result = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).filter(*filters).scalar()
    )
    return float(result or 0.0)


# ---------- User ----------
def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.username).all()


def count_users(db: Session) -> int:
    return db.query(models.User).count()


def create_user(
    db: Session, username: str, name: str, password_hash: str, is_admin: bool = False
) -> models.User:
    user = models.User(username=username, name=name, password_hash=password_hash, is_admin=is_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, db_user: models.User, user: schemas.UserUpdate) -> models.User:
    db_user.username = user.username
    db_user.name = user.name
    db_user.is_admin = user.is_admin
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_password(db: Session, db_user: models.User, password_hash: str) -> models.User:
    db_user.password_hash = password_hash
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, db_user: models.User) -> None:
    # Explicit cascade: remove the user's transactions/accounts/categories
    # before the user row itself, rather than relying on ORM relationship
    # cascades (Transaction has two FKs into accounts, which complicates
    # relationship-based cascade configuration).
    db.query(models.Transaction).filter(models.Transaction.user_id == db_user.id).delete()
    db.query(models.Account).filter(models.Account.user_id == db_user.id).delete()
    db.query(models.Category).filter(models.Category.user_id == db_user.id).delete()
    db.delete(db_user)
    db.commit()


# ---------- Account ----------
def get_accounts(db: Session, user_id: int) -> list[models.Account]:
    return (
        db.query(models.Account)
        .filter(models.Account.user_id == user_id)
        .order_by(models.Account.name)
        .all()
    )


def get_account(db: Session, account_id: int, user_id: int) -> models.Account | None:
    return (
        db.query(models.Account)
        .filter(models.Account.id == account_id, models.Account.user_id == user_id)
        .first()
    )


def create_account(db: Session, user_id: int, account: schemas.AccountCreate) -> models.Account:
    db_account = models.Account(**account.model_dump(), user_id=user_id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def update_account(
    db: Session, db_account: models.Account, account: schemas.AccountUpdate
) -> models.Account:
    for field, value in account.model_dump().items():
        setattr(db_account, field, value)
    db.commit()
    db.refresh(db_account)
    return db_account


def delete_account(db: Session, db_account: models.Account) -> None:
    db.delete(db_account)
    db.commit()


def account_has_transactions(db: Session, account_id: int) -> bool:
    return (
        db.query(models.Transaction)
        .filter(
            or_(
                models.Transaction.account_id == account_id,
                models.Transaction.to_account_id == account_id,
            )
        )
        .first()
        is not None
    )


def get_account_balance(db: Session, account_id: int, before: date | None = None) -> float:
    """All-time (or, if `before` is given, as-of) balance of an account:
    +income, -expense, -transfers out, +transfers in.
    """
    out_filters = [models.Transaction.account_id == account_id]
    in_filters = [models.Transaction.to_account_id == account_id]
    if before is not None:
        out_filters.append(models.Transaction.date < before)
        in_filters.append(models.Transaction.date < before)

    income = _sum_where(db, models.Transaction.type == "income", *out_filters)
    expense = _sum_where(db, models.Transaction.type == "expense", *out_filters)
    transfer_out = _sum_where(db, models.Transaction.type == "transfer", *out_filters)
    transfer_in = _sum_where(db, models.Transaction.type == "transfer", *in_filters)
    return income - expense - transfer_out + transfer_in


# ---------- Category ----------
def get_categories(db: Session, user_id: int) -> list[models.Category]:
    return (
        db.query(models.Category)
        .filter(models.Category.user_id == user_id)
        .order_by(models.Category.name)
        .all()
    )


def get_category(db: Session, category_id: int, user_id: int) -> models.Category | None:
    return (
        db.query(models.Category)
        .filter(models.Category.id == category_id, models.Category.user_id == user_id)
        .first()
    )


def create_category(db: Session, user_id: int, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.model_dump(), user_id=user_id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def update_category(
    db: Session, db_category: models.Category, category: schemas.CategoryUpdate
) -> models.Category:
    for field, value in category.model_dump().items():
        setattr(db_category, field, value)
    db.commit()
    db.refresh(db_category)
    return db_category


def delete_category(db: Session, db_category: models.Category) -> None:
    db.delete(db_category)
    db.commit()


# ---------- Transaction ----------
def get_transactions(
    db: Session, user_id: int, month: int, year: int, account_id: int | None = None
) -> list[models.Transaction]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    query = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.date >= start,
        models.Transaction.date <= end,
    )
    if account_id is not None:
        # Include transfers landing in this account (to_account_id) as well
        # as transactions/transfers originating from it (account_id), so an
        # account's ledger shows every movement that touched its balance.
        query = query.filter(
            or_(
                models.Transaction.account_id == account_id,
                models.Transaction.to_account_id == account_id,
            )
        )
    return query.order_by(models.Transaction.date).all()


def get_transaction(db: Session, transaction_id: int, user_id: int) -> models.Transaction | None:
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == user_id)
        .first()
    )


def create_transaction(
    db: Session, user_id: int, transaction: schemas.TransactionCreate
) -> models.Transaction:
    db_transaction = models.Transaction(**transaction.model_dump(), user_id=user_id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def update_transaction(
    db: Session, db_transaction: models.Transaction, transaction: schemas.TransactionUpdate
) -> models.Transaction:
    for field, value in transaction.model_dump().items():
        setattr(db_transaction, field, value)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def delete_transaction(db: Session, db_transaction: models.Transaction) -> None:
    db.delete(db_transaction)
    db.commit()


def create_transfer(db: Session, user_id: int, transfer: schemas.TransferCreate) -> models.Transaction:
    db_transaction = models.Transaction(
        date=transfer.date,
        description=transfer.description,
        amount=transfer.amount,
        type="transfer",
        category_id=None,
        account_id=transfer.from_account_id,
        to_account_id=transfer.to_account_id,
        user_id=user_id,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


# ---------- Summary ----------
def _totals_for_range(
    db: Session, user_id: int, start: date, end: date, account_id: int | None = None
) -> tuple[float, float]:
    filters = [
        models.Transaction.user_id == user_id,
        models.Transaction.date >= start,
        models.Transaction.date <= end,
    ]
    if account_id is not None:
        filters.append(models.Transaction.account_id == account_id)
    income_total = _sum_where(db, models.Transaction.type == "income", *filters)
    expense_total = _sum_where(db, models.Transaction.type == "expense", *filters)
    return income_total, expense_total


def _totals_before(
    db: Session, user_id: int, start: date, account_id: int | None = None
) -> tuple[float, float]:
    filters = [models.Transaction.user_id == user_id, models.Transaction.date < start]
    if account_id is not None:
        filters.append(models.Transaction.account_id == account_id)
    income_total = _sum_where(db, models.Transaction.type == "income", *filters)
    expense_total = _sum_where(db, models.Transaction.type == "expense", *filters)
    return income_total, expense_total


def get_summary(
    db: Session, user_id: int, month: int, year: int, account_id: int | None = None
) -> schemas.SummaryOut:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    # income_total/expense_total always exclude type="transfer" transactions.
    income_total, expense_total = _totals_for_range(db, user_id, start, end, account_id)
    balance = income_total - expense_total

    if account_id is not None:
        # Per-account previous balance must reflect transfers in/out of this
        # specific account (they are real cash movements for it), consistent
        # with how get_account_balance computes /api/accounts' balance.
        previous_balance = get_account_balance(db, account_id, before=start)
    else:
        # Consolidated across all of the user's accounts: transfers between
        # two of their own accounts always net to zero, so excluding them
        # from the income/expense math gives the same result either way.
        prev_income, prev_expense = _totals_before(db, user_id, start)
        previous_balance = prev_income - prev_expense

    return schemas.SummaryOut(
        income_total=income_total,
        expense_total=expense_total,
        balance=balance,
        previous_balance=previous_balance,
    )


# ---------- Reports ----------
def get_monthly_trend(db: Session, user_id: int, year: int) -> list[schemas.MonthlyTrendOut]:
    results = []
    for month in range(1, 13):
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        income_total, expense_total = _totals_for_range(db, user_id, start, end)
        results.append(
            schemas.MonthlyTrendOut(month=month, income_total=income_total, expense_total=expense_total)
        )
    return results


def get_category_totals(db: Session, user_id: int, month: int, year: int) -> list[schemas.CategoryTotalOut]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    rows = (
        db.query(
            models.Category.id,
            models.Category.name,
            models.Category.color,
            func.sum(models.Transaction.amount),
        )
        .join(models.Transaction, models.Transaction.category_id == models.Category.id)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.type == "expense",
            models.Transaction.date >= start,
            models.Transaction.date <= end,
        )
        .group_by(models.Category.id)
        .all()
    )
    results = [
        schemas.CategoryTotalOut(category_id=cid, name=name, color=color, total=float(total))
        for cid, name, color, total in rows
    ]

    uncategorized_total = _sum_where(
        db,
        models.Transaction.user_id == user_id,
        models.Transaction.type == "expense",
        models.Transaction.category_id.is_(None),
        models.Transaction.date >= start,
        models.Transaction.date <= end,
    )
    if uncategorized_total > 0:
        results.append(
            schemas.CategoryTotalOut(
                category_id=None, name="Sem categoria", color="#9e9e9e", total=uncategorized_total
            )
        )
    return results

"""Database access helpers used by the routers."""
from datetime import date
from calendar import monthrange

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


# ---------- User ----------
def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


def count_users(db: Session) -> int:
    return db.query(models.User).count()


def create_user(db: Session, username: str, password_hash: str) -> models.User:
    user = models.User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------- Category ----------
def get_categories(db: Session) -> list[models.Category]:
    return db.query(models.Category).order_by(models.Category.name).all()


def get_category(db: Session, category_id: int) -> models.Category | None:
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def create_category(db: Session, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.model_dump())
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
def get_transactions(db: Session, month: int, year: int) -> list[models.Transaction]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.date >= start, models.Transaction.date <= end)
        .order_by(models.Transaction.date)
        .all()
    )


def get_transaction(db: Session, transaction_id: int) -> models.Transaction | None:
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()


def create_transaction(db: Session, transaction: schemas.TransactionCreate) -> models.Transaction:
    db_transaction = models.Transaction(**transaction.model_dump())
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


# ---------- Summary ----------
def _totals_for_range(db: Session, start: date, end: date) -> tuple[float, float]:
    income_total = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.type == "income",
            models.Transaction.date >= start,
            models.Transaction.date <= end,
        )
        .scalar()
    )
    expense_total = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.type == "expense",
            models.Transaction.date >= start,
            models.Transaction.date <= end,
        )
        .scalar()
    )
    return float(income_total or 0.0), float(expense_total or 0.0)


def get_summary(db: Session, month: int, year: int) -> schemas.SummaryOut:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    income_total, expense_total = _totals_for_range(db, start, end)
    balance = income_total - expense_total

    # previous_balance = accumulated balance from all prior months (all
    # transactions strictly before the first day of the requested month).
    prev_income = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(models.Transaction.type == "income", models.Transaction.date < start)
        .scalar()
    )
    prev_expense = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(models.Transaction.type == "expense", models.Transaction.date < start)
        .scalar()
    )
    previous_balance = float(prev_income or 0.0) - float(prev_expense or 0.0)

    return schemas.SummaryOut(
        income_total=income_total,
        expense_total=expense_total,
        balance=balance,
        previous_balance=previous_balance,
    )

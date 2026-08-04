"""SQLAlchemy ORM models: User, Account, Category, Transaction, Budget, RecurringTransaction, Bill, Goal."""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Always stored lowercase (enforced in schemas.py validators) so login
    # is effectively case-insensitive without needing a DB collation trick.
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Dashboard widget preferences: comma-separated list of hidden widget ids (e.g. "balance,alerts").
    # Stored as a comma-separated string to avoid a separate table for this small, display-only data.
    dashboard_hidden_widgets: Mapped[str | None] = mapped_column(String, nullable=True)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # "checking" | "savings" | "wallet" | "credit_card" | "other"
    type: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)  # hex color, e.g. "#FF0000"
    # Credit card specific: day of month (1-31) the billing cycle closes
    closing_day: Mapped[int | None] = mapped_column(nullable=True)
    # Credit card specific: day of month (1-31) the invoice is due (in the following month)
    due_day: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "income" | "expense"
    color: Mapped[str] = mapped_column(String, nullable=False)  # hex color, e.g. "#FF0000"

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "income" | "expense" | "transfer"
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    # Denormalized relative to account.user_id -- kept in sync at write time
    # so every transaction row can be scoped to its owner in a single filter.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    # Only set when type == "transfer": the destination account.
    to_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True, index=True
    )
    # Links to the recurring transaction rule that generated this transaction.
    recurring_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurring_transactions.id"), nullable=True
    )
    # Installment fields: set when this transaction is part of a parcelamento
    installment_number: Mapped[int | None] = mapped_column(nullable=True)  # 1-based
    installment_total: Mapped[int | None] = mapped_column(nullable=True)  # total count of installments
    installment_group_id: Mapped[str | None] = mapped_column(String, nullable=True)  # UUID hex string
    # "confirmed" (default, counts toward balance) | "pending" (excluded from balance/summary until confirmed)
    status: Mapped[str] = mapped_column(String, default="confirmed", server_default="confirmed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    category: Mapped["Category | None"] = relationship(back_populates="transactions")
    # No back_populates on Account: cascade-deleting a user's accounts is
    # handled explicitly in crud.delete_user (two FKs into accounts makes
    # ORM-level cascade="all, delete-orphan" ambiguous), so these stay
    # simple one-directional read relationships used only for serialization.
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    to_account: Mapped["Account | None"] = relationship(foreign_keys=[to_account_id])


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Unique constraint on (user_id, category_id): only one budget per category per user
    __table_args__ = (UniqueConstraint("user_id", "category_id", name="uq_budgets_user_category"),)


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "income" | "expense"
    day_of_month: Mapped[int] = mapped_column(nullable=False)  # 1-31
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paid_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    color: Mapped[str] = mapped_column(String, nullable=False)  # hex color, e.g. "#FF0000"
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    # "acao" | "fii" | "etf" | "bdr" | "outro"
    asset_type: Mapped[str] = mapped_column(String, nullable=False)
    # Manually-maintained current market price -- no live price feed exists
    # yet (per the user's own "manual first, API later" call on investments),
    # so profitability is only computable when the user keeps this updated.
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Unique constraint on (user_id, ticker): only one ticker per user
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_assets_user_ticker"),)


class InvestmentMovement(Base):
    __tablename__ = "investment_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # "compra" | "venda" | "bonificacao" | "provento" | "desdobramento" | "outro"
    movement_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class InvestmentPositionSnapshot(Base):
    __tablename__ = "investment_position_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Quantity held as of this date (after all movements up to and including this date)
    quantity_held: Mapped[float] = mapped_column(Float, nullable=False)
    # Total invested amount (cost basis) as of this date
    invested_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Unique constraint: one snapshot per (user_id, asset_id, date)
    __table_args__ = (
        UniqueConstraint("user_id", "asset_id", "date", name="uq_position_snapshots_user_asset_date"),
    )

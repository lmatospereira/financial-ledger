"""Pydantic v2 request/response models."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Full set of transaction types, used for read models. "transfer" rows can
# only be created via POST /api/transfers -- see CreateTransactionType below.
TransactionType = Literal["income", "expense", "transfer"]
# Transactions created/edited directly through /api/transactions may only be
# income or expense; posting type="transfer" here is rejected with a 422.
CreateTransactionType = Literal["income", "expense"]

AccountType = Literal["checking", "savings", "wallet", "credit_card", "other"]

# Guardrail: maximum transaction amount
MAX_AMOUNT = 999_999_999.99


# Usernames are always normalized to lowercase (both at registration and at
# login) so login is effectively case-insensitive -- "Test"/"TEST"/"test"
# all resolve to the same account, stored as "test".
def _normalize_username(v: str) -> str:
    return v.strip().lower()


# Date must be within 3 years before or after today.
def _validate_date_range(v: date) -> date:
    today = date.today()
    min_date = today.replace(year=today.year - 3)
    max_date = today.replace(year=today.year + 3)
    if not (min_date <= v <= max_date):
        raise ValueError(f"date must be between {min_date} and {max_date}")
    return v


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str

    _normalize_username = field_validator("username")(_normalize_username)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- User ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    is_admin: bool
    dashboard_hidden_widgets: list[str] = []

    @field_validator("dashboard_hidden_widgets", mode="before")
    @classmethod
    def _parse_dashboard_hidden_widgets(cls, v: str | None) -> list[str]:
        if v is None or v == "":
            return []
        return [w.strip() for w in v.split(",") if w.strip()]


class UserCreate(BaseModel):
    username: str
    name: str
    password: str = Field(min_length=8)
    is_admin: bool = False

    _normalize_username = field_validator("username")(_normalize_username)


class UserUpdate(BaseModel):
    username: str
    name: str
    is_admin: bool

    _normalize_username = field_validator("username")(_normalize_username)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8)


# ---------- Account ----------
class AccountBase(BaseModel):
    name: str
    type: AccountType
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    closing_day: Optional[int] = Field(default=None, ge=1, le=31)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(AccountBase):
    pass


class AccountOut(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    balance: float


class AccountRef(AccountBase):
    """Lightweight account embed for nesting inside TransactionOut.

    Deliberately excludes `balance` (unlike AccountOut): computing it is an
    aggregate query per account, and nesting the full AccountOut here would
    mean recomputing it for every transaction row via from_attributes on the
    raw ORM object, which doesn't even have a `.balance` attribute to read.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------- Category ----------
class CategoryBase(BaseModel):
    name: str
    type: Literal["income", "expense"]
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------- Transaction ----------
class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    type: CreateTransactionType
    category_id: Optional[int] = None
    account_id: int
    status: Literal["confirmed", "pending"] = "confirmed"

    _validate_date = field_validator("date")(_validate_date_range)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(TransactionBase):
    pass


class TransactionConfirm(BaseModel):
    # Lets the caller switch which account pays a pending transaction at
    # confirm time (mirrors the Bill pay flow) -- omit to keep the account
    # already set on the transaction.
    account_id: Optional[int] = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    description: str
    amount: float
    type: TransactionType
    category_id: Optional[int] = None
    account_id: int
    to_account_id: Optional[int] = None
    recurring_transaction_id: Optional[int] = None
    installment_number: Optional[int] = None
    installment_total: Optional[int] = None
    status: str
    created_at: datetime
    category: Optional[CategoryOut] = None
    account: Optional[AccountRef] = None
    to_account: Optional[AccountRef] = None


# ---------- Transfer ----------
class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    date: date
    description: str

    _validate_date = field_validator("date")(_validate_date_range)


# ---------- Summary ----------
class SummaryOut(BaseModel):
    income_total: float
    expense_total: float
    balance: float
    previous_balance: float


# ---------- Reports ----------
class MonthlyTrendOut(BaseModel):
    month: int
    income_total: float
    expense_total: float


class CategoryTotalOut(BaseModel):
    category_id: Optional[int] = None
    name: str
    color: str
    total: float


# ---------- Budget ----------
class BudgetBase(BaseModel):
    category_id: int
    amount: float = Field(gt=0, le=MAX_AMOUNT)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BudgetBase):
    pass


class BudgetOut(BudgetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class BudgetStatusOut(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    budget_amount: float
    spent_amount: float
    percentage: float
    over_budget: bool


# ---------- Recurring Transaction ----------
class RecurringTransactionBase(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    description: str
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    type: Literal["income", "expense"]
    day_of_month: int = Field(ge=1, le=31)
    start_date: date
    end_date: Optional[date] = None


# The date-range guardrail belongs on input schemas only -- Base is also the
# parent of Out (see below), and re-validating dates on read would reject
# perfectly valid old rows once they fall outside the rolling N-years-ago
# window as time passes (this happened in production: recurring transactions
# and bills older than 3 years started 500ing on every list/get call once
# "today" moved far enough past their date). Create/Update each declare the
# validator themselves instead of inheriting it via Base.
def _validate_recurring_end_date(cls, v: Optional[date]) -> Optional[date]:
    if v is None:
        return v
    return _validate_date_range(v)


class RecurringTransactionCreate(RecurringTransactionBase):
    _validate_start_date = field_validator("start_date")(_validate_date_range)
    _validate_end_date = field_validator("end_date")(_validate_recurring_end_date)


class RecurringTransactionUpdate(RecurringTransactionBase):
    active: Optional[bool] = None

    _validate_start_date = field_validator("start_date")(_validate_date_range)
    _validate_end_date = field_validator("end_date")(_validate_recurring_end_date)


class RecurringTransactionOut(RecurringTransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active: bool
    created_at: datetime


# ---------- Bill ----------
class BillBase(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    description: str
    amount: float = Field(gt=0, le=MAX_AMOUNT)
    due_date: date


# See the comment above RecurringTransactionCreate: the date-range guardrail
# is input-only and must not be inherited by BillOut via Base.
class BillCreate(BillBase):
    _validate_due_date = field_validator("due_date")(_validate_date_range)


class BillUpdate(BillBase):
    _validate_due_date = field_validator("due_date")(_validate_date_range)


class BillOut(BillBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paid: bool
    paid_transaction_id: Optional[int] = None
    created_at: datetime


class BillPayRequest(BaseModel):
    account_id: int


# ---------- Installment ----------
class InstallmentCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    description: str
    total_amount: float = Field(gt=0, le=MAX_AMOUNT)
    installments: int = Field(ge=1, le=420)
    type: CreateTransactionType
    first_date: date

    _validate_first_date = field_validator("first_date")(_validate_date_range)


# ---------- Goal ----------
class GoalBase(BaseModel):
    name: str
    target_amount: float = Field(gt=0, le=MAX_AMOUNT)
    account_id: int
    target_date: Optional[date] = None
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")

    _validate_target_date = field_validator("target_date")(
        lambda cls, v: _validate_date_range(v) if v is not None else v
    )


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = Field(default=None, gt=0, le=MAX_AMOUNT)
    account_id: Optional[int] = None
    target_date: Optional[date] = None
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

    _validate_target_date = field_validator("target_date")(
        lambda cls, v: _validate_date_range(v) if v is not None else v
    )


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_amount: float
    target_date: Optional[date] = None
    color: str
    created_at: datetime
    account: Optional[AccountRef] = None
    current_amount: float
    progress_percent: float


# ---------- Alerts ----------
class UpcomingAlertOut(BaseModel):
    """Unified alert for bills, recurring transactions, and installments."""

    kind: Literal["bill", "recurring", "installment"]
    id: int
    description: str
    amount: float
    due_date: date
    is_overdue: bool
    account: Optional[AccountRef] = None
    category: Optional[CategoryOut] = None


# ---------- Credit Card Invoice ----------
class CreditCardInvoiceOut(BaseModel):
    """Invoice (fatura) for a credit card account within a billing cycle."""

    period_start: date
    period_end: date
    due_date: Optional[date] = None
    total: float
    transactions: list[TransactionOut]


# ---------- Dashboard Preferences ----------
class DashboardPreferencesUpdate(BaseModel):
    hidden_widgets: list[str]


# ---------- Asset ----------
class AssetBase(BaseModel):
    ticker: str
    name: Optional[str] = None
    asset_type: Literal["acao", "fii", "etf", "bdr", "outro", "tesouro", "renda_fixa"]
    current_price: Optional[float] = Field(default=None, ge=0, le=MAX_AMOUNT)


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[Literal["acao", "fii", "etf", "bdr", "outro", "tesouro", "renda_fixa"]] = None
    current_price: Optional[float] = Field(default=None, ge=0, le=MAX_AMOUNT)


class AssetOut(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ---------- Investment Movement ----------
class InvestmentMovementBase(BaseModel):
    asset_id: int
    date: date
    movement_type: Literal["compra", "venda", "bonificacao", "provento", "desdobramento", "outro"]
    quantity: float = Field(gt=0, le=MAX_AMOUNT)
    # unit_price can be None or 0 for non-purchase movements (bonuses, splits, dividends)
    unit_price: Optional[float] = Field(default=None, ge=0, le=MAX_AMOUNT)
    # total_value can be 0 for non-purchase movements (bonuses, splits, dividends)
    total_value: float = Field(ge=0, le=MAX_AMOUNT)


# The date-range guardrail is input-only -- see the comment above
# RecurringTransactionCreate. It must not be inherited by InvestmentMovementOut
# via Base: this exact bug caused a real production 500 on GET
# /api/investments/movements once a legitimately-created movement's date aged
# past the rolling 3-year window.
class InvestmentMovementCreate(InvestmentMovementBase):
    _validate_date = field_validator("date")(_validate_date_range)


class InvestmentMovementUpdate(BaseModel):
    asset_id: Optional[int] = None
    date: Optional[date] = None
    movement_type: Optional[Literal["compra", "venda", "bonificacao", "provento", "desdobramento", "outro"]] = None
    quantity: Optional[float] = Field(default=None, gt=0, le=MAX_AMOUNT)
    unit_price: Optional[float] = Field(default=None, gt=0, le=MAX_AMOUNT)
    total_value: Optional[float] = Field(default=None, gt=0, le=MAX_AMOUNT)

    _validate_date = field_validator("date")(
        lambda cls, v: _validate_date_range(v) if v is not None else v
    )


class InvestmentMovementOut(InvestmentMovementBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ---------- Portfolio ----------
class PortfolioPositionOut(BaseModel):
    ticker: str
    name: Optional[str] = None
    asset_type: str
    quantity_held: float
    avg_price: float
    total_invested: float
    # Only populated when the asset's current_price has been set manually
    # (no live price feed exists yet) -- None means "unknown, not tracked".
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None


# ---------- Import Preview Response ----------
class ImportPreviewResponse(BaseModel):
    committed: bool = False
    raw_columns: list[str]
    detected_mapping: dict[str, Optional[str]]
    sample_rows: list[dict[str, Optional[str]]]
    row_count: int
    # True when the file's header row matches B3's own "Movimentação" export
    # exactly -- lets the frontend skip the manual column-review step and
    # go straight to a one-click confirmation instead.
    is_known_b3_format: bool = False


# ---------- Investment Position Snapshot ----------
class PositionSnapshotOut(BaseModel):
    date: date
    asset_id: int
    quantity_held: float
    invested_value: float


class ConsolidatedPositionOut(BaseModel):
    date: date
    total_invested_value: float


# ---------- Import Commit Response ----------
class ImportCommitResponse(BaseModel):
    committed: bool = True
    assets_created: int
    movements_created: int

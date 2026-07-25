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


# Usernames are always normalized to lowercase (both at registration and at
# login) so login is effectively case-insensitive -- "Test"/"TEST"/"test"
# all resolve to the same account, stored as "test".
def _normalize_username(v: str) -> str:
    return v.strip().lower()


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


class UserCreate(BaseModel):
    username: str
    name: str
    password: str
    is_admin: bool = False

    _normalize_username = field_validator("username")(_normalize_username)


class UserUpdate(BaseModel):
    username: str
    name: str
    is_admin: bool

    _normalize_username = field_validator("username")(_normalize_username)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ---------- Account ----------
class AccountBase(BaseModel):
    name: str
    type: AccountType
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


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
    amount: float = Field(gt=0)
    type: CreateTransactionType
    category_id: Optional[int] = None
    account_id: int


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(TransactionBase):
    pass


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
    created_at: datetime
    category: Optional[CategoryOut] = None
    account: Optional[AccountRef] = None
    to_account: Optional[AccountRef] = None


# ---------- Transfer ----------
class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(gt=0)
    date: date
    description: str


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

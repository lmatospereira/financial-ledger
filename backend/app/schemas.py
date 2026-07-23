"""Pydantic v2 request/response models."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Full set of transaction types, used for read models. "transfer" rows can
# only be created via POST /api/transfers -- see CreateTransactionType below.
TransactionType = Literal["income", "expense", "transfer"]
# Transactions created/edited directly through /api/transactions may only be
# income or expense; posting type="transfer" here is rejected with a 422.
CreateTransactionType = Literal["income", "expense"]

AccountType = Literal["checking", "savings", "wallet", "credit_card", "other"]


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- User ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_admin: bool


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    username: str
    is_admin: bool


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

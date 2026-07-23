"""Pydantic v2 request/response models."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TransactionType = Literal["income", "expense"]


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Category ----------
class CategoryBase(BaseModel):
    name: str
    type: TransactionType
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
    type: TransactionType
    category_id: Optional[int] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(TransactionBase):
    pass


class TransactionOut(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    category: Optional[CategoryOut] = None


# ---------- Summary ----------
class SummaryOut(BaseModel):
    income_total: float
    expense_total: float
    balance: float
    previous_balance: float

"""Transaction request/response schemas."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.category import CategoryBrief
from app.schemas.common import PaginationMeta

TxnType = Literal["INCOME", "EXPENSE"]
PaymentMethod = Literal[
    "DEBIT_CARD",
    "CREDIT_CARD",
    "CASH",
    "E_TRANSFER",
    "DIRECT_DEPOSIT",
    "PRE_AUTH",
    "OTHER",
]

Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=["84.20"])]


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TxnType = Field(..., examples=["EXPENSE"])
    amount: Amount
    vendor: str = Field(..., min_length=1, max_length=160, examples=["Sobeys"])
    categoryId: str | None = Field(default=None, examples=["cat_groceries"])
    date: dt.datetime | None = Field(default=None, examples=["2026-06-09"])
    paymentMethod: PaymentMethod = Field(default="OTHER", examples=["DEBIT_CARD"])
    note: str | None = Field(default=None, max_length=500)
    isShared: bool = False


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TxnType | None = None
    amount: Amount | None = None
    vendor: str | None = Field(default=None, min_length=1, max_length=160)
    categoryId: str | None = None
    date: dt.datetime | None = None
    paymentMethod: PaymentMethod | None = None
    note: str | None = Field(default=None, max_length=500)
    isShared: bool | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: TxnType
    amount: Decimal
    vendor: str
    categoryId: str | None = None
    category: CategoryBrief | None = None
    date: dt.datetime
    paymentMethod: PaymentMethod
    note: str | None = None
    isShared: bool
    createdAt: dt.datetime
    updatedAt: dt.datetime

    @field_serializer("amount")
    def _ser_amount(self, v: Decimal) -> float:
        return float(v)


class TransactionListSummary(BaseModel):
    count: int
    totalIncome: float
    totalExpense: float
    net: float


class TransactionListOut(BaseModel):
    data: list[TransactionOut]
    pagination: PaginationMeta
    summary: TransactionListSummary

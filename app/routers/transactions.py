"""Personal Ledger — Transaction endpoints (the two graded endpoints).

* POST /api/v1/transactions  — create a transaction
* GET  /api/v1/transactions  — list / filter / search / paginate

Both are JWT-protected and strictly scoped to the authenticated user, so a
user can never read or write another user's data (broken-access-control
mitigation). All queries go through Prisma, which parameterises every value
(SQL-injection mitigation).
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from prisma.models import User

from app.core.db import db
from app.core.deps import get_current_user
from app.core.errors import APIError
from app.schemas.common import ErrorResponse, PaginationMeta
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListOut,
    TransactionListSummary,
    TransactionOut,
)

router = APIRouter(prefix="/transactions", tags=["Personal Ledger — Transactions"])

_UTC = dt.timezone.utc
_SORT_FIELDS = {"date", "amount", "createdAt"}


async def _assert_category_owned(category_id: str, user_id: str) -> None:
    """A user may only attach their own category to a transaction."""
    category = await db.category.find_first(where={"id": category_id, "userId": user_id})
    if category is None:
        raise APIError(404, "CATEGORY_NOT_FOUND", "Category not found.")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionOut,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Create a transaction",
)
async def create_transaction(
    body: TransactionCreate, user: User = Depends(get_current_user)
) -> TransactionOut:
    if body.categoryId is not None:
        await _assert_category_owned(body.categoryId, user.id)

    when = body.date or dt.datetime.now(_UTC)

    txn = await db.transaction.create(
        data={
            "userId": user.id,
            "type": body.type,
            "amount": body.amount,
            "vendor": body.vendor,
            "categoryId": body.categoryId,
            "date": when,
            "paymentMethod": body.paymentMethod,
            "note": body.note,
            "isShared": body.isShared,
        },
        include={"category": True},
    )
    return TransactionOut.model_validate(txn)


@router.get(
    "",
    response_model=TransactionListOut,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="List, filter, search and paginate transactions",
)
async def list_transactions(
    user: User = Depends(get_current_user),
    type: str | None = Query(default=None, pattern="^(INCOME|EXPENSE)$"),
    categoryId: str | None = Query(default=None),
    date_from: dt.date | None = Query(default=None, alias="from"),
    date_to: dt.date | None = Query(default=None, alias="to"),
    q: str | None = Query(default=None, max_length=160, description="Search vendor / note."),
    isShared: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="-date", description="One of date|amount|createdAt, optional '-' prefix."),
) -> TransactionListOut:
    # ---- Build a user-scoped filter (ownership is never client-controlled) ----
    where: dict = {"userId": user.id}
    if type is not None:
        where["type"] = type
    if categoryId is not None:
        where["categoryId"] = categoryId
    if isShared is not None:
        where["isShared"] = isShared
    if date_from is not None or date_to is not None:
        date_filter: dict = {}
        if date_from is not None:
            date_filter["gte"] = dt.datetime.combine(date_from, dt.time.min, tzinfo=_UTC)
        if date_to is not None:
            date_filter["lte"] = dt.datetime.combine(date_to, dt.time.max, tzinfo=_UTC)
        where["date"] = date_filter
    if q:
        where["OR"] = [
            {"vendor": {"contains": q, "mode": "insensitive"}},
            {"note": {"contains": q, "mode": "insensitive"}},
        ]

    # ---- Sorting ----
    field = sort[1:] if sort.startswith("-") else sort
    if field not in _SORT_FIELDS:
        raise APIError(422, "VALIDATION_ERROR", f"Cannot sort by '{field}'.")
    direction = "desc" if sort.startswith("-") else "asc"
    order = [{field: direction}, {"id": "desc"}]  # tiebreak for stable pagination

    # ---- Page of rows + total count ----
    total = await db.transaction.count(where=where)
    rows = await db.transaction.find_many(
        where=where,
        include={"category": True},
        order=order,
        skip=(page - 1) * limit,
        take=limit,
    )

    # ---- Summary across the full filtered set (not just this page) ----
    grouped = await db.transaction.group_by(
        by=["type"], where=where, sum={"amount": True}
    )
    income = expense = Decimal(0)
    for g in grouped:
        raw = (g.get("_sum") or {}).get("amount")
        total_amount = Decimal(str(raw)) if raw is not None else Decimal(0)
        if g["type"] == "INCOME":
            income = total_amount
        else:
            expense = total_amount

    total_pages = (total + limit - 1) // limit if total else 0
    return TransactionListOut(
        data=[TransactionOut.model_validate(r) for r in rows],
        pagination=PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages),
        summary=TransactionListSummary(
            count=total,
            totalIncome=float(income),
            totalExpense=float(expense),
            net=float(income - expense),
        ),
    )

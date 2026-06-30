"""Category endpoints (supporting the Personal Ledger workflow)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from prisma.models import User

from app.core.db import db
from app.core.deps import get_current_user
from app.schemas.category import CategoryListOut, CategoryOut
from app.schemas.common import ErrorResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/categories", tags=["Categories"])


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    color: str = Field(default="#6366F1", max_length=9)
    icon: str | None = Field(default=None, max_length=40)
    parentId: str | None = None


@router.get(
    "",
    response_model=CategoryListOut,
    responses={401: {"model": ErrorResponse}},
    summary="List the current user's categories",
)
async def list_categories(
    user: User = Depends(get_current_user),
    parentId: str | None = Query(default=None, description="Filter to subcategories of a parent."),
) -> CategoryListOut:
    where: dict = {"userId": user.id}
    if parentId is not None:
        where["parentId"] = parentId
    rows = await db.category.find_many(where=where, order={"name": "asc"})
    return CategoryListOut(data=[CategoryOut.model_validate(r) for r in rows])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryOut,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Create a custom category",
)
async def create_category(
    body: CategoryCreate, user: User = Depends(get_current_user)
) -> CategoryOut:
    row = await db.category.create(
        data={
            "userId": user.id,
            "name": body.name,
            "color": body.color,
            "icon": body.icon,
            "parentId": body.parentId,
        }
    )
    return CategoryOut.model_validate(row)

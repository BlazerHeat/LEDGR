"""Shared response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: int = Field(..., examples=[1])
    limit: int = Field(..., examples=[20])
    total: int = Field(..., examples=[42])
    totalPages: int = Field(..., examples=[3])


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    type: str | None = None


class ErrorBody(BaseModel):
    code: str = Field(..., examples=["VALIDATION_ERROR"])
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    """Standard error envelope returned by every failing endpoint."""

    error: ErrorBody

"""Category schemas."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    color: str
    icon: str | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    color: str
    icon: str | None = None
    parentId: str | None = None
    isDefault: bool
    createdAt: dt.datetime


class CategoryListOut(BaseModel):
    data: list[CategoryOut]

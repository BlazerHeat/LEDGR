"""Auth request/response schemas."""
from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    email: str = Field(..., max_length=254, examples=["vatsal.ghoghari@dal.ca"])
    password: str = Field(..., min_length=8, max_length=128, examples=["S3cur3pass!"])
    name: str = Field(..., min_length=1, max_length=120, examples=["Vatsal Ghoghari"])

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Must be a valid email address.")
        return v


class LoginIn(BaseModel):
    email: str = Field(..., examples=["vatsal.ghoghari@dal.ca"])
    password: str = Field(..., examples=["S3cur3pass!"])

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: str
    avatarColor: str | None = None
    createdAt: dt.datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access-token lifetime in seconds.")
    user: UserOut

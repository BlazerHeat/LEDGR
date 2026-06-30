"""Authentication endpoints: register, login, me, refresh, logout."""
from __future__ import annotations

import datetime as dt

import jwt
from fastapi import APIRouter, Depends, status
from prisma.models import User

from app.core.config import settings
from app.core.db import db
from app.core.defaults import DEFAULT_CATEGORIES
from app.core.deps import get_current_user
from app.core.errors import APIError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    sha256,
    verify_password,
)
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

_ERRORS = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


async def _issue_tokens(user: User) -> TokenOut:
    access = create_access_token(user_id=user.id, role=user.role)
    refresh, expires_at = create_refresh_token(user_id=user.id)
    await db.refreshtoken.create(
        data={"userId": user.id, "tokenHash": sha256(refresh), "expiresAt": expires_at}
    )
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenOut,
    responses=_ERRORS,
    summary="Register a new user",
)
async def register(body: RegisterIn) -> TokenOut:
    existing = await db.user.find_unique(where={"email": body.email})
    if existing is not None:
        raise APIError(409, "EMAIL_TAKEN", "An account with this email already exists.")

    user = await db.user.create(
        data={
            "email": body.email,
            "passwordHash": hash_password(body.password),
            "name": body.name,
        }
    )
    # Give the new user a sensible starting set of categories.
    await db.category.create_many(
        data=[
            {
                "userId": user.id,
                "name": c["name"],
                "color": c["color"],
                "icon": c["icon"],
                "isDefault": True,
            }
            for c in DEFAULT_CATEGORIES
        ]
    )
    return await _issue_tokens(user)


@router.post(
    "/login",
    response_model=TokenOut,
    responses=_ERRORS,
    summary="Log in and receive JWT access + refresh tokens",
)
async def login(body: LoginIn) -> TokenOut:
    user = await db.user.find_unique(where={"email": body.email})
    # Same generic error whether the email is unknown or the password is wrong,
    # so an attacker cannot enumerate which emails are registered.
    if user is None or not verify_password(body.password, user.passwordHash):
        raise APIError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    return await _issue_tokens(user)


@router.get("/me", response_model=UserOut, responses=_ERRORS, summary="Get the current user")
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post(
    "/refresh",
    response_model=TokenOut,
    responses=_ERRORS,
    summary="Rotate a refresh token for a new access token",
)
async def refresh(body: RefreshIn) -> TokenOut:
    try:
        payload = decode_token(body.refresh_token)
    except jwt.PyJWTError:
        raise APIError(401, "INVALID_TOKEN", "Invalid or expired refresh token.")
    if payload.get("type") != "refresh":
        raise APIError(401, "INVALID_TOKEN", "Invalid token type.")

    stored = await db.refreshtoken.find_unique(where={"tokenHash": sha256(body.refresh_token)})
    now = dt.datetime.now(dt.timezone.utc)
    if stored is None or stored.revokedAt is not None or stored.expiresAt < now:
        raise APIError(401, "INVALID_TOKEN", "Refresh token is no longer valid.")

    # Rotate: revoke the presented token, then issue a fresh pair.
    await db.refreshtoken.update(where={"id": stored.id}, data={"revokedAt": now})
    user = await db.user.find_unique(where={"id": payload["sub"]})
    if user is None:
        raise APIError(401, "INVALID_TOKEN", "User no longer exists.")
    return await _issue_tokens(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
    summary="Revoke a refresh token",
)
async def logout(body: RefreshIn) -> None:
    await db.refreshtoken.update_many(
        where={"tokenHash": sha256(body.refresh_token), "revokedAt": None},
        data={"revokedAt": dt.datetime.now(dt.timezone.utc)},
    )
    return None

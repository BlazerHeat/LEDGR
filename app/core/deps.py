"""Auth dependencies: deny-by-default JWT verification and role checks."""
from __future__ import annotations

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prisma.models import User

from app.core.db import db
from app.core.errors import APIError
from app.core.security import decode_token

# auto_error=False so we can return our own JSON envelope instead of FastAPI's default.
_bearer = HTTPBearer(auto_error=False, description="JWT access token")


def _unauthorized(message: str = "Authentication required.") -> APIError:
    return APIError(401, "UNAUTHORIZED", message)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """Resolve the authenticated user from the Bearer token, or raise 401.

    This is the single deny-by-default gate: any route depending on it is
    inaccessible without a valid, unexpired access token for an existing user.
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Access token has expired.")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid access token.")

    if payload.get("type") != "access":
        raise _unauthorized("Invalid token type.")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token payload.")

    user = await db.user.find_unique(where={"id": user_id})
    if user is None:
        raise _unauthorized("User no longer exists.")

    return user


def require_role(*roles: str):
    """Dependency factory enforcing RBAC for the given roles."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise APIError(403, "FORBIDDEN", "You do not have permission to perform this action.")
        return user

    return _checker

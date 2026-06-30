"""Password hashing (bcrypt) and JWT creation/verification."""
from __future__ import annotations

import datetime as dt
import hashlib
import secrets
import uuid

import bcrypt
import jwt

from app.core.config import settings

# bcrypt operates on at most 72 bytes; we cap the input to avoid backend errors.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def create_access_token(*, user_id: str, role: str) -> str:
    now = _now()
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: str) -> tuple[str, dt.datetime]:
    """Return (raw_token, expires_at). Only the SHA-256 hash is stored in the DB."""
    now = _now()
    expires_at = now + dt.timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_hex(16),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt exceptions on invalid/expired tokens."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

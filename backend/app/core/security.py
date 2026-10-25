import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()


class TokenValidationError(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def _encode_token(user_id: uuid.UUID, token_type: Literal["access", "refresh"]) -> tuple[str, uuid.UUID, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    expires_at = now + lifetime
    token_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "jti": str(token_id),
        "type": token_type,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, token_id, expires_at


def create_access_token(user_id: uuid.UUID) -> str:
    return _encode_token(user_id, "access")[0]


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, uuid.UUID, datetime]:
    return _encode_token(user_id, "refresh")


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "jti", "type", "iat", "exp"]},
        )
        uuid.UUID(payload["sub"])
        uuid.UUID(payload["jti"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise TokenValidationError("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise TokenValidationError("Invalid token type")
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)

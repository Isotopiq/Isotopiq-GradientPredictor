"""JWT encode/decode."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings


def _create_token(subject: str, ttl: timedelta, token_type: str, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + ttl,
        "type": token_type,
    }
    if jti is not None:
        payload["jti"] = jti
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, remember_me: bool = False) -> str:
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    if remember_me:
        ttl = timedelta(days=30)
    return _create_token(subject, ttl, "access")


def create_refresh_token(subject: str, remember_me: bool = False, jti: str | None = None) -> str:
    ttl = timedelta(days=settings.refresh_token_ttl_days)
    if remember_me:
        ttl = timedelta(days=90)
    return _create_token(subject, ttl, "refresh", jti=jti)


def refresh_token_ttl(remember_me: bool = False) -> timedelta:
    """TTL applied to refresh tokens — kept in sync with create_refresh_token."""
    return timedelta(days=90 if remember_me else settings.refresh_token_ttl_days)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")
    return payload

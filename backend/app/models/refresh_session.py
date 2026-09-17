"""Refresh-session ORM model — server-side record of issued refresh tokens.

Each issued refresh token carries a unique ``jti`` claim. We store a SHA-256
hash of that jti so a stolen token can be revoked (logout / password reset /
admin deactivation) and so refresh tokens can be rotated on every use.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base, Timestamped


class RefreshSession(Base, UUIDPK, Timestamped):
    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        # SQLite returns naive datetimes; treat naive as UTC
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        return datetime.now(UTC) < exp

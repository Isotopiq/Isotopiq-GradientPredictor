"""Method ORM model."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK
from app.models.jsonb_compat import JSONBCompat


class Method(Base, UUIDPK, Timestamped):
    __tablename__ = "methods"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    column_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    column_dims: Mapped[dict[str, Any] | None] = mapped_column(JSONBCompat, nullable=True)

    mobile_phase_a: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile_phase_b: Mapped[str | None] = mapped_column(String(255), nullable=True)
    additive: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ph: Mapped[float | None] = mapped_column(nullable=True)
    gradient_table: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONBCompat, nullable=True)
    flow_rate_ml_min: Mapped[float | None] = mapped_column(nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(nullable=True)

    # Hash of column+pH+modifier signature used to key ML models
    method_signature: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

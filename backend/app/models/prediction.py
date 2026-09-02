"""Prediction ORM model."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class Prediction(Base, UUIDPK, Timestamped):
    __tablename__ = "predictions"

    compound_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methods.id", ondelete="CASCADE"), nullable=False, index=True
    )

    predicted_rt_s: Mapped[float | None] = mapped_column(nullable=True)
    rt_lower_s: Mapped[float | None] = mapped_column(nullable=True)
    rt_upper_s: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    extrapolating: Mapped[bool] = mapped_column(default=False, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), default="rules-v1", nullable=False)

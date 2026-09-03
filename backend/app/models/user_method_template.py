"""User-created method template ORM model."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class UserMethodTemplate(Base, UUIDPK, Timestamped):
    __tablename__ = "user_method_templates"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="Custom")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mobile_phase_a: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mobile_phase_b: Mapped[str | None] = mapped_column(String(255), nullable=True)
    additive: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    percent_b_start: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    percent_b_end: Mapped[float] = mapped_column(Float, nullable=False, default=95.0)
    gradient_time_min: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    flow_rate_ml_min: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    column_length_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    particle_size_um: Mapped[float] = mapped_column(Float, nullable=False, default=1.8)
    is_shared: Mapped[bool] = mapped_column(default=False, nullable=False)

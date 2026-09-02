"""Run ORM model (observed chromatographic run)."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class Run(Base, UUIDPK, Timestamped):
    __tablename__ = "runs"

    compound_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    observed_rt_s: Mapped[float] = mapped_column(nullable=False)
    peak_width_s: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_date: Mapped[date | None] = mapped_column(Date, nullable=True)

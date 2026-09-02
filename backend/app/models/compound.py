"""Compound ORM model."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK
from app.models.jsonb_compat import JSONBCompat


class Compound(Base, UUIDPK, Timestamped):
    __tablename__ = "compounds"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_shared: Mapped[bool] = mapped_column(default=False, nullable=False)

    name: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchi: Mapped[str | None] = mapped_column(Text, nullable=True)
    inchikey: Mapped[str | None] = mapped_column(String(27), nullable=True, index=True)
    molfile: Mapped[str | None] = mapped_column(Text, nullable=True)
    cas: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Cached descriptors
    mw: Mapped[float | None] = mapped_column(nullable=True)
    logp: Mapped[float | None] = mapped_column(nullable=True)
    logd_at_ph: Mapped[float | None] = mapped_column(nullable=True)
    pka_values: Mapped[list[Any] | None] = mapped_column(JSONBCompat, nullable=True)
    tpsa: Mapped[float | None] = mapped_column(nullable=True)
    hbd: Mapped[int | None] = mapped_column(nullable=True)
    hba: Mapped[int | None] = mapped_column(nullable=True)
    rotatable_bonds: Mapped[int | None] = mapped_column(nullable=True)
    aromatic_rings: Mapped[int | None] = mapped_column(nullable=True)

    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)

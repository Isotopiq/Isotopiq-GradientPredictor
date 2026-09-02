"""CompoundList ORM model — a named, reusable list of compounds for a user."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK
from app.models.jsonb_compat import JSONBCompat


class CompoundList(Base, UUIDPK, Timestamped):
    __tablename__ = "compound_lists"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB array of compound IDs (UUID strings) in order
    compound_ids: Mapped[list[Any]] = mapped_column(JSONBCompat, nullable=False, default=list)

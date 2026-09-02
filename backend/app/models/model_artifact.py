"""ModelArtifact ORM model (trained ML model metadata)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPK
from app.models.jsonb_compat import JSONBCompat


class ModelArtifact(Base, UUIDPK):
    __tablename__ = "model_artifacts"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    column_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    method_signature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)

    train_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONBCompat, nullable=True)
    feature_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONBCompat, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(nullable=False)
    n_samples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

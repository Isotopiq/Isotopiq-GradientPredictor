"""CompoundList schemas."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompoundListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = None
    compound_ids: list[uuid.UUID] = Field(default_factory=list)


class CompoundListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    compound_ids: list[uuid.UUID] | None = None


class CompoundListOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    compound_ids: list[Any]

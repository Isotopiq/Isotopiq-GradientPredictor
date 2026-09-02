"""Run schemas."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.schemas.common import ORMModel


class RunCreate(BaseModel):
    compound_id: uuid.UUID
    method_id: uuid.UUID
    observed_rt_s: float
    peak_width_s: float | None = None
    notes: str | None = None
    run_date: date | None = None


class RunOut(ORMModel):
    id: uuid.UUID
    compound_id: uuid.UUID
    method_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    observed_rt_s: float
    peak_width_s: float | None = None
    notes: str | None = None
    run_date: date | None = None

"""Prediction schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PredictionRequest(BaseModel):
    compound_id: uuid.UUID
    method_id: uuid.UUID


class PredictionOut(ORMModel):
    id: uuid.UUID
    compound_id: uuid.UUID
    method_id: uuid.UUID
    predicted_rt_s: float | None = None
    rt_lower_s: float | None = None
    rt_upper_s: float | None = None
    confidence: float
    extrapolating: bool
    model_version: str

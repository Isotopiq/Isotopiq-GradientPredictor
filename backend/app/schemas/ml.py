"""ML schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TrainRequest(BaseModel):
    column_type: str
    method_signature: str | None = None
    model_type: str = "xgboost"  # xgboost | lightgbm | sklearn | ensemble
    use_stored_runs: bool = True


class TrainResponse(BaseModel):
    artifact_id: uuid.UUID
    column_type: str
    model_type: str
    version: int
    n_samples: int
    metrics: dict[str, Any]
    trained_at: datetime


class ModelArtifactOut(ORMModel):
    id: uuid.UUID
    column_type: str
    method_signature: str
    model_type: str
    version: int
    artifact_path: str
    train_metrics: dict[str, Any] | None = None
    feature_schema: dict[str, Any] | None = None
    trained_at: datetime
    n_samples: int


class ApplicabilityRequest(BaseModel):
    artifact_id: uuid.UUID
    features: dict[str, Any]


class ApplicabilityOut(BaseModel):
    extrapolating: bool
    distance: float
    threshold: float

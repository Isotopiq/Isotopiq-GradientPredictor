"""Model registry: per-column model versioning + artifact storage."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ml.base import RetentionModel
from app.core.ml.ensemble import EnsembleModel
from app.core.ml.lightgbm_model import LightGBMModel
from app.core.ml.sklearn_gbm import SklearnGBMModel
from app.core.ml.xgboost_model import XGBoostModel
from app.models.model_artifact import ModelArtifact

MODEL_CLASSES: dict[str, type[RetentionModel]] = {
    "xgboost": XGBoostModel,
    "lightgbm": LightGBMModel,
    "sklearn": SklearnGBMModel,
    "ensemble": EnsembleModel,
}


def get_model_class(model_type: str) -> type[RetentionModel]:
    cls = MODEL_CLASSES.get(model_type)
    if cls is None:
        raise ValueError(f"Unknown model type: {model_type}")
    return cls


def create_model(model_type: str) -> RetentionModel:
    return get_model_class(model_type)()


async def save_artifact(
    db: AsyncSession,
    owner_id: uuid.UUID | None,
    column_type: str,
    method_signature: str,
    model_type: str,
    model: RetentionModel,
    metrics: dict[str, Any],
    n_samples: int,
    feature_schema: dict[str, Any] | None = None,
) -> ModelArtifact:
    """Persist a trained model and create a ModelArtifact row."""
    # Determine next version
    stmt = (
        select(ModelArtifact)
        .where(
            (ModelArtifact.column_type == column_type)
            & (ModelArtifact.method_signature == method_signature)
        )
        .order_by(desc(ModelArtifact.version))
        .limit(1)
    )
    result = await db.execute(stmt)
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    storage_path = Path(settings.model_storage_path)
    artifact_filename = f"{column_type}_{method_signature}_v{version}.pkl"
    artifact_path = storage_path / artifact_filename
    model.save(artifact_path)

    artifact = ModelArtifact(
        owner_id=owner_id,
        column_type=column_type,
        method_signature=method_signature,
        model_type=model_type,
        version=version,
        artifact_path=str(artifact_path),
        train_metrics=metrics,  # type: ignore[arg-type]
        feature_schema=feature_schema,  # type: ignore[arg-type]
        trained_at=datetime.now(timezone.utc),
        n_samples=n_samples,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def get_latest_artifact(
    db: AsyncSession, column_type: str, method_signature: str
) -> ModelArtifact | None:
    stmt = (
        select(ModelArtifact)
        .where(
            (ModelArtifact.column_type == column_type)
            & (ModelArtifact.method_signature == method_signature)
        )
        .order_by(desc(ModelArtifact.version))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_artifacts(
    db: AsyncSession, column_type: str | None = None, limit: int = 50
) -> list[ModelArtifact]:
    stmt = select(ModelArtifact).order_by(desc(ModelArtifact.trained_at))
    if column_type:
        stmt = stmt.where(ModelArtifact.column_type == column_type)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> ModelArtifact | None:
    return await db.get(ModelArtifact, artifact_id)


async def delete_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> bool:
    artifact = await db.get(ModelArtifact, artifact_id)
    if artifact is None:
        return False
    # Delete file
    try:
        Path(artifact.artifact_path).unlink(missing_ok=True)
    except Exception:
        pass
    await db.delete(artifact)
    await db.commit()
    return True


# In-memory model cache (LRU-like)
_model_cache: dict[uuid.UUID, RetentionModel] = {}
_cache_limit = 10


def load_model_from_artifact(artifact: ModelArtifact) -> RetentionModel:
    """Load a model from an artifact, with caching."""
    if artifact.id in _model_cache:
        return _model_cache[artifact.id]

    model = create_model(artifact.model_type)
    model.load(Path(artifact.artifact_path))

    # Evict if cache full
    if len(_model_cache) >= _cache_limit:
        _model_cache.pop(next(iter(_model_cache)))
    _model_cache[artifact.id] = model
    return model


def clear_cache() -> None:
    _model_cache.clear()

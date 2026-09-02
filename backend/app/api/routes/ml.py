"""ML routes: train, list models, applicability check."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.core.ml.registry import (
    delete_artifact,
    get_artifact,
    list_artifacts,
)
from app.schemas.ml import ModelArtifactOut, TrainRequest, TrainResponse
from app.services import ml_service

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/train", response_model=TrainResponse, status_code=status.HTTP_201_CREATED)
async def train_model(
    data: TrainRequest,
    db: DBSession,
    current: CurrentUser,
) -> TrainResponse:
    """Train a model from stored runs or uploaded CSV."""
    try:
        if data.use_stored_runs:
            artifact = await ml_service.train_from_stored_runs(
                db=db,
                owner_id=current.id,
                column_type=data.column_type,
                model_type=data.model_type,
                method_signature=data.method_signature,
            )
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "use_stored_runs=false requires a CSV upload via /ml/train/csv",
            )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return TrainResponse(
        artifact_id=artifact.id,
        column_type=artifact.column_type,
        model_type=artifact.model_type,
        version=artifact.version,
        n_samples=artifact.n_samples,
        metrics=artifact.train_metrics or {},
        trained_at=artifact.trained_at,
    )


@router.post("/train/csv", response_model=TrainResponse, status_code=status.HTTP_201_CREATED)
async def train_from_csv(
    db: DBSession,
    current: CurrentUser,
    file: UploadFile = File(...),
    column_type: str = Query(...),
    model_type: str = Query("xgboost"),
) -> TrainResponse:
    """Train a model from an uploaded CSV file."""
    content = await file.read()
    try:
        artifact = await ml_service.train_from_csv(
            db=db,
            owner_id=current.id if current else None,
            column_type=column_type,
            model_type=model_type,
            csv_content=content,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return TrainResponse(
        artifact_id=artifact.id,
        column_type=artifact.column_type,
        model_type=artifact.model_type,
        version=artifact.version,
        n_samples=artifact.n_samples,
        metrics=artifact.train_metrics or {},
        trained_at=artifact.trained_at,
    )


@router.get("/models", response_model=list[ModelArtifactOut])
async def list_models(
    db: DBSession,
    current: CurrentUser,
    column_type: str | None = Query(None),
) -> list[ModelArtifactOut]:
    artifacts = await list_artifacts(db, column_type)
    return [ModelArtifactOut.model_validate(a) for a in artifacts]


@router.get("/models/{artifact_id}", response_model=ModelArtifactOut)
async def get_model(artifact_id: uuid.UUID, db: DBSession, current: CurrentUser) -> ModelArtifactOut:
    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    return ModelArtifactOut.model_validate(artifact)


@router.delete("/models/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(artifact_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    ok = await delete_artifact(db, artifact_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")


@router.get("/stats")
async def model_stats(db: DBSession, current: CurrentUser) -> dict:
    """Get aggregate model statistics for the dashboard."""
    from sqlalchemy import func, select
    from app.models.model_artifact import ModelArtifact
    from app.models.compound import Compound
    from app.models.method import Method
    from app.models.run import Run
    from app.models.prediction import Prediction

    # Count models by type
    model_count_result = await db.execute(
        select(ModelArtifact.model_type, func.count(ModelArtifact.id))
        .group_by(ModelArtifact.model_type)
    )
    models_by_type = {row[0]: row[1] for row in model_count_result.all()}

    # Count models by column type
    col_count_result = await db.execute(
        select(ModelArtifact.column_type, func.count(ModelArtifact.id))
        .group_by(ModelArtifact.column_type)
    )
    models_by_column = {row[0]: row[1] for row in col_count_result.all()}

    # Total counts
    total_models = await db.scalar(select(func.count(ModelArtifact.id)))
    total_compounds = await db.scalar(select(func.count(Compound.id)))
    total_methods = await db.scalar(select(func.count(Method.id)))
    total_runs = await db.scalar(select(func.count(Run.id)))
    total_predictions = await db.scalar(select(func.count(Prediction.id)))

    # Average confidence across predictions
    avg_confidence = await db.scalar(select(func.avg(Prediction.confidence)))

    # Latest models with metrics
    recent_result = await db.execute(
        select(ModelArtifact).order_by(ModelArtifact.trained_at.desc()).limit(10)
    )
    recent_models = []
    for a in recent_result.scalars().all():
        metrics = a.train_metrics or {}
        recent_models.append({
            "id": str(a.id),
            "column_type": a.column_type,
            "model_type": a.model_type,
            "version": a.version,
            "n_samples": a.n_samples,
            "r2": metrics.get("r2"),
            "rmse": metrics.get("rmse"),
            "residual_std": metrics.get("residual_std"),
            "trained_at": a.trained_at.isoformat() if a.trained_at else None,
        })

    # Best performing model per column type
    best_by_column: dict[str, dict] = {}
    all_result = await db.execute(select(ModelArtifact))
    for a in all_result.scalars().all():
        metrics = a.train_metrics or {}
        r2 = metrics.get("r2", 0)
        if r2 is None:
            r2 = 0
        if a.column_type not in best_by_column or r2 > best_by_column[a.column_type].get("r2", 0):
            best_by_column[a.column_type] = {
                "model_type": a.model_type,
                "version": a.version,
                "r2": r2,
                "rmse": metrics.get("rmse"),
                "n_samples": a.n_samples,
            }

    return {
        "totals": {
            "models": total_models or 0,
            "compounds": total_compounds or 0,
            "methods": total_methods or 0,
            "runs": total_runs or 0,
            "predictions": total_predictions or 0,
        },
        "avg_confidence": float(avg_confidence) if avg_confidence else 0.0,
        "models_by_type": models_by_type,
        "models_by_column": models_by_column,
        "best_by_column": best_by_column,
        "recent_models": recent_models,
    }

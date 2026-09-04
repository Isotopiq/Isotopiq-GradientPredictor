"""ML routes: train, list models, applicability check, analytics."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.core.ml.registry import (
    delete_artifact,
    get_artifact,
    list_artifacts,
    load_model_from_artifact,
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

    # Build owner filter for non-admin users
    uid = None if current.is_admin else current.id

    # Count models by type
    model_type_q = select(ModelArtifact.model_type, func.count(ModelArtifact.id)).group_by(ModelArtifact.model_type)
    if uid is not None:
        model_type_q = model_type_q.where(ModelArtifact.owner_id == uid)
    model_count_result = await db.execute(model_type_q)
    models_by_type = {row[0]: row[1] for row in model_count_result.all()}

    # Count models by column type
    model_col_q = select(ModelArtifact.column_type, func.count(ModelArtifact.id)).group_by(ModelArtifact.column_type)
    if uid is not None:
        model_col_q = model_col_q.where(ModelArtifact.owner_id == uid)
    col_count_result = await db.execute(model_col_q)
    models_by_column = {row[0]: row[1] for row in col_count_result.all()}

    # Total counts — scoped to the current user (admin sees global counts)
    if uid is None:
        total_models = await db.scalar(select(func.count(ModelArtifact.id)))
        total_compounds = await db.scalar(select(func.count(Compound.id)))
        total_methods = await db.scalar(select(func.count(Method.id)))
        total_runs = await db.scalar(select(func.count(Run.id)))
        total_predictions = await db.scalar(select(func.count(Prediction.id)))
    else:
        total_models = await db.scalar(
            select(func.count(ModelArtifact.id)).where(ModelArtifact.owner_id == uid)
        )
        total_compounds = await db.scalar(
            select(func.count(Compound.id)).where(Compound.owner_id == uid)
        )
        total_methods = await db.scalar(
            select(func.count(Method.id)).where(Method.owner_id == uid)
        )
        total_runs = await db.scalar(
            select(func.count(Run.id)).where(Run.owner_id == uid)
        )
        # Predictions don't have owner_id — join through method
        total_predictions = await db.scalar(
            select(func.count(Prediction.id))
            .join(Method, Prediction.method_id == Method.id)
            .where(Method.owner_id == uid)
        )

    # Average confidence across predictions (scoped)
    avg_q = select(func.avg(Prediction.confidence))
    if uid is not None:
        avg_q = avg_q.join(Method, Prediction.method_id == Method.id).where(Method.owner_id == uid)
    avg_confidence = await db.scalar(avg_q)

    # Latest models with metrics (scoped)
    recent_q = select(ModelArtifact).order_by(ModelArtifact.trained_at.desc()).limit(10)
    if uid is not None:
        recent_q = recent_q.where(ModelArtifact.owner_id == uid)
    recent_result = await db.execute(recent_q)
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

    # Best performing model per column type (scoped)
    best_by_column: dict[str, dict] = {}
    all_q = select(ModelArtifact)
    if uid is not None:
        all_q = all_q.where(ModelArtifact.owner_id == uid)
    all_result = await db.execute(all_q)
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


@router.get("/models/{artifact_id}/feature-importance")
async def get_feature_importance(
    artifact_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> dict[str, Any]:
    """Get feature importances for a trained model."""
    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    try:
        model = load_model_from_artifact(artifact)
        importances = model.feature_importances
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to load model: {exc}") from exc

    # Sort by importance descending
    sorted_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    return {
        "model_id": str(artifact.id),
        "model_type": artifact.model_type,
        "column_type": artifact.column_type,
        "version": artifact.version,
        "features": [{"name": k, "importance": v} for k, v in sorted_features],
    }


@router.get("/models/{artifact_id}/history")
async def get_model_history(
    artifact_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> dict[str, Any]:
    """Get version history for a model (all versions with same column_type + method_signature)."""
    from sqlalchemy import select
    from app.models.model_artifact import ModelArtifact

    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")

    stmt = (
        select(ModelArtifact)
        .where(
            (ModelArtifact.column_type == artifact.column_type)
            & (ModelArtifact.method_signature == artifact.method_signature)
        )
        .order_by(ModelArtifact.version)
    )
    result = await db.execute(stmt)
    versions = []
    for a in result.scalars().all():
        metrics = a.train_metrics or {}
        versions.append({
            "id": str(a.id),
            "version": a.version,
            "model_type": a.model_type,
            "n_samples": a.n_samples,
            "r2": metrics.get("r2"),
            "rmse": metrics.get("rmse"),
            "residual_std": metrics.get("residual_std"),
            "trained_at": a.trained_at.isoformat() if a.trained_at else None,
        })

    return {
        "column_type": artifact.column_type,
        "method_signature": artifact.method_signature,
        "versions": versions,
    }


@router.get("/performance-trends")
async def performance_trends(db: DBSession, current: CurrentUser) -> dict[str, Any]:
    """Get aggregate performance trends over time."""
    from sqlalchemy import select
    from app.models.model_artifact import ModelArtifact

    result = await db.execute(
        select(ModelArtifact).order_by(ModelArtifact.trained_at)
    )
    trends: list[dict[str, Any]] = []
    for a in result.scalars().all():
        metrics = a.train_metrics or {}
        trends.append({
            "date": a.trained_at.isoformat() if a.trained_at else None,
            "model_id": str(a.id),
            "column_type": a.column_type,
            "model_type": a.model_type,
            "version": a.version,
            "r2": metrics.get("r2"),
            "rmse": metrics.get("rmse"),
            "n_samples": a.n_samples,
        })

    return {"trends": trends}


@router.get("/calibration")
async def calibration_data(db: DBSession, current: CurrentUser) -> dict[str, Any]:
    """Get predicted vs observed RT pairs for calibration plotting."""
    from sqlalchemy import select
    from app.models.run import Run
    from app.models.prediction import Prediction
    from app.models.compound import Compound
    from app.models.method import Method

    # Join predictions with runs (observed) on compound + method
    stmt = (
        select(Prediction, Run, Compound)
        .join(Run, (Prediction.compound_id == Run.compound_id) & (Prediction.method_id == Run.method_id))
        .join(Compound, Prediction.compound_id == Compound.id)
    )
    result = await db.execute(stmt)
    points: list[dict[str, Any]] = []
    for pred, run, compound in result.all():
        points.append({
            "compound_smiles": compound.smiles,
            "compound_name": compound.name,
            "predicted_rt_s": pred.predicted_rt_s,
            "observed_rt_s": run.observed_rt_s,
            "residual": pred.predicted_rt_s - run.observed_rt_s,
            "model_version": pred.model_version,
            "confidence": pred.confidence,
        })

    # Compute simple regression stats
    import numpy as np
    if len(points) >= 2:
        observed = np.array([p["observed_rt_s"] for p in points])
        predicted = np.array([p["predicted_rt_s"] for p in points])
        slope, intercept = np.polyfit(observed, predicted, 1)
        residuals = predicted - (slope * observed + intercept)
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((predicted - predicted.mean()) ** 2))
        r2 = 1 - ss_res / max(ss_tot, 1e-8)
        rmse = float(np.sqrt(np.mean((predicted - observed) ** 2)))
    else:
        slope, intercept, r2, rmse = 1.0, 0.0, 0.0, 0.0

    return {
        "points": points,
        "n_points": len(points),
        "regression": {
            "slope": float(slope),
            "intercept": float(intercept),
            "r2": float(r2),
            "rmse": rmse,
        },
    }

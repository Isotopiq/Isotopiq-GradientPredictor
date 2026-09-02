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

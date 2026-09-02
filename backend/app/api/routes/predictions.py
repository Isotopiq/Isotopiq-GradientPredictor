"""Prediction routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.schemas.prediction import PredictionOut, PredictionRequest
from app.services import prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("", response_model=PredictionOut, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    data: PredictionRequest, db: DBSession, current: CurrentUser
) -> PredictionOut:
    try:
        prediction = await prediction_service.predict(db, data.compound_id, data.method_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return PredictionOut.model_validate(prediction)

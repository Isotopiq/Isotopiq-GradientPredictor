"""Method routes: suggest, CRUD, gradient simulation, chromatogram."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.schemas.method import (
    ChromatogramOut,
    ChromatogramRequest,
    GradientSimulateOut,
    GradientSimulateRequest,
    MethodCreate,
    MethodOut,
    MethodSuggestionOut,
    MethodSuggestionRequest,
    MultiCompoundSuggestionRequest,
    MultiCompoundSuggestionOut,
)
from app.services import method_service

router = APIRouter(prefix="/methods", tags=["methods"])


@router.post("/suggest", response_model=MethodSuggestionOut)
async def suggest_method(data: MethodSuggestionRequest) -> MethodSuggestionOut:
    try:
        result = method_service.suggest(data)
    except method_service.MethodServiceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MethodSuggestionOut.model_validate(result)


@router.post("/gradient/simulate", response_model=GradientSimulateOut)
async def simulate_gradient(data: GradientSimulateRequest) -> GradientSimulateOut:
    result = method_service.simulate_gradient(data)
    return GradientSimulateOut.model_validate(result)


@router.post("/chromatogram", response_model=ChromatogramOut)
async def simulate_chromatogram(data: ChromatogramRequest) -> ChromatogramOut:
    result = method_service.simulate_chromatogram_from_request(data)
    return ChromatogramOut.model_validate(result)


@router.post("/suggest-multi", response_model=MultiCompoundSuggestionOut)
async def suggest_multi_method(data: MultiCompoundSuggestionRequest) -> MultiCompoundSuggestionOut:
    result = method_service.suggest_multi(
        smiles_list=data.smiles_list,
        ionization_mode=data.ionization_mode,
        retention_goal=data.retention_goal,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
    )
    return MultiCompoundSuggestionOut.model_validate(result)


@router.post("", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def create_method(data: MethodCreate, db: DBSession, current: CurrentUser) -> MethodOut:
    method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(method)


@router.get("", response_model=list[MethodOut])
async def list_methods(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[MethodOut]:
    items = await method_service.list_methods(db, current.id, limit, offset)
    return [MethodOut.model_validate(m) for m in items]


@router.get("/{method_id}", response_model=MethodOut)
async def get_method(method_id: uuid.UUID, db: DBSession, current: CurrentUser) -> MethodOut:
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id is not None and method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return MethodOut.model_validate(method)


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_method(method_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    await method_service.delete_method(db, method_id)

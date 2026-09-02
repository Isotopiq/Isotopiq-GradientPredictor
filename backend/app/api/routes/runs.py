"""Run routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.schemas.run import RunCreate, RunOut
from app.services import run_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(data: RunCreate, db: DBSession, current: CurrentUser) -> RunOut:
    run = await run_service.create_run(db, current.id, data)
    return RunOut.model_validate(run)


@router.get("", response_model=list[RunOut])
async def list_runs(
    db: DBSession,
    current: CurrentUser,
    compound_id: uuid.UUID | None = Query(None),
    method_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[RunOut]:
    items = await run_service.list_runs(db, compound_id, method_id, limit, offset)
    return [RunOut.model_validate(r) for r in items]


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(run_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    ok = await run_service.delete_run(db, run_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")

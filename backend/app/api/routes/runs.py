"""Run routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DBSession
from app.schemas.run import RunCreate, RunOut
from app.services import run_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(data: RunCreate, db: DBSession, current: CurrentUser) -> RunOut:
    try:
        run = await run_service.create_run(db, current.id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
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
    owner_id = None if current.is_admin else current.id
    items = await run_service.list_runs(
        db, compound_id, method_id, limit, offset, owner_id
    )
    return [RunOut.model_validate(r) for r in items]


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(run_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    owner_id = None if current.is_admin else current.id
    ok = await run_service.delete_run(db, run_id, owner_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")

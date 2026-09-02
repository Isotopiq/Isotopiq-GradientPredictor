"""Compound list routes: CRUD for named compound lists."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.schemas.compound_list import CompoundListCreate, CompoundListOut, CompoundListUpdate
from app.services import compound_list_service

router = APIRouter(prefix="/compound-lists", tags=["compound-lists"])


@router.post("", response_model=CompoundListOut, status_code=status.HTTP_201_CREATED)
async def create_compound_list(
    data: CompoundListCreate,
    db: DBSession,
    current: CurrentUser,
) -> CompoundListOut:
    cl = await compound_list_service.create_list(db, current.id, data)
    return CompoundListOut.model_validate(cl)


@router.get("", response_model=list[CompoundListOut])
async def list_compound_lists(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[CompoundListOut]:
    items = await compound_list_service.list_lists(db, current.id, limit, offset)
    return [CompoundListOut.model_validate(cl) for cl in items]


@router.get("/{list_id}", response_model=CompoundListOut)
async def get_compound_list(
    list_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
) -> CompoundListOut:
    cl = await compound_list_service.get_list(db, list_id)
    if cl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound list not found")
    if cl.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return CompoundListOut.model_validate(cl)


@router.put("/{list_id}", response_model=CompoundListOut)
async def update_compound_list(
    list_id: uuid.UUID,
    data: CompoundListUpdate,
    db: DBSession,
    current: CurrentUser,
) -> CompoundListOut:
    cl = await compound_list_service.update_list(db, list_id, current.id, data)
    if cl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound list not found")
    return CompoundListOut.model_validate(cl)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compound_list(
    list_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
) -> None:
    deleted = await compound_list_service.delete_list(db, list_id, current.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound list not found")

"""CompoundList service: CRUD for named compound lists."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compound_list import CompoundList
from app.schemas.compound_list import CompoundListCreate, CompoundListUpdate


async def create_list(
    db: AsyncSession, owner_id: uuid.UUID, data: CompoundListCreate
) -> CompoundList:
    cl = CompoundList(
        owner_id=owner_id,
        name=data.name,
        description=data.description,
        compound_ids=[str(cid) for cid in data.compound_ids],
    )
    db.add(cl)
    await db.commit()
    await db.refresh(cl)
    return cl


async def list_lists(
    db: AsyncSession, owner_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[CompoundList]:
    stmt = (
        select(CompoundList)
        .where(CompoundList.owner_id == owner_id)
        .order_by(CompoundList.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_list(db: AsyncSession, list_id: uuid.UUID) -> CompoundList | None:
    stmt = select(CompoundList).where(CompoundList.id == list_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_list(
    db: AsyncSession, list_id: uuid.UUID, owner_id: uuid.UUID, data: CompoundListUpdate
) -> CompoundList | None:
    cl = await get_list(db, list_id)
    if cl is None or cl.owner_id != owner_id:
        return None
    if data.name is not None:
        cl.name = data.name
    if data.description is not None:
        cl.description = data.description
    if data.compound_ids is not None:
        cl.compound_ids = [str(cid) for cid in data.compound_ids]
    await db.commit()
    await db.refresh(cl)
    return cl


async def delete_list(db: AsyncSession, list_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
    cl = await get_list(db, list_id)
    if cl is None or cl.owner_id != owner_id:
        return False
    await db.delete(cl)
    await db.commit()
    return True

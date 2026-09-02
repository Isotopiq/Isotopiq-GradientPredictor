"""Column database routes."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.chem.columns_db import (
    column_to_dict,
    get_brands,
    get_column,
    get_chemistries,
    list_columns,
)

router = APIRouter(prefix="/columns", tags=["columns"])


@router.get("")
async def list_all_columns(
    chemistry: str | None = Query(None),
    brand: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    columns = list_columns(chemistry, brand, limit)
    return [column_to_dict(c) for c in columns]


@router.get("/{column_id}")
async def get_single_column(column_id: str) -> dict:
    col = get_column(column_id)
    if col is None:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
    return column_to_dict(col)


@router.get("/meta/brands")
async def list_brands() -> list[str]:
    return get_brands()


@router.get("/meta/chemistries")
async def list_chemistries() -> list[str]:
    return get_chemistries()

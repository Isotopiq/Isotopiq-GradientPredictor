"""Column database routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.chem.columns_db import (
    column_to_dict,
    get_brands,
    get_column,
    get_column_count,
    get_chemistries,
    list_columns,
)
from app.core.ml.pirm_model import predict_retention

router = APIRouter(prefix="/columns", tags=["columns"])


# ---------------------------------------------------------------------------
# Meta endpoints (must come before /{column_id} to avoid path conflicts)
# ---------------------------------------------------------------------------

@router.get("/meta/brands")
async def list_brands() -> list[str]:
    return get_brands()


@router.get("/meta/chemistries")
async def list_chemistries() -> list[str]:
    return get_chemistries()


@router.get("/count")
async def count_columns() -> dict:
    """Return total column count."""
    return {"total": get_column_count()}


# ---------------------------------------------------------------------------
# PIRM retention prediction
# ---------------------------------------------------------------------------

class PIRMPredictionRequest(BaseModel):
    column_id: str = Field(..., description="Column ID from the database")
    logp: float = Field(..., description="Analyte octanol-water partition coefficient")
    mw: float = Field(..., description="Analyte molecular weight (Da)")
    tpsa: float = Field(0.0, description="Analyte topological polar surface area (Å²)")
    gradient_table: list[dict] = Field(
        ..., description="Multi-segment gradient [{time_s, percent_b}, ...]"
    )
    flow_rate_ml_min: float = Field(0.4, description="Flow rate (mL/min)")


@router.post("/predict-retention")
async def predict_column_retention(req: PIRMPredictionRequest) -> dict:
    """Predict retention time using the Physics-Informed Retention Model (PIRM).

    Uses stationary phase composition (carbon load, bonding density, ligand
    hydrophobicity, surface area, pore size, endcapping) combined with analyte
    descriptors (logP, MW, TPSA) and gradient conditions to predict retention
    time via an extended Snyder LSS model with numerical gradient integration.
    """
    col = get_column(req.column_id)
    if col is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
    if col.phase is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Column has no stationary phase data",
        )

    result = predict_retention(
        column=col,
        logp=req.logp,
        mw=req.mw,
        tpsa=req.tpsa,
        gradient_table=req.gradient_table,
        flow_rate_ml_min=req.flow_rate_ml_min,
    )
    return result


# ---------------------------------------------------------------------------
# Column listing and detail
# ---------------------------------------------------------------------------

@router.get("")
async def list_all_columns(
    chemistry: str | None = Query(None),
    brand: str | None = Query(None),
    search: str | None = Query(None),
    particle_size: float | None = Query(None, description="Filter by particle size in µm"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """List columns with pagination, filtering, and search."""
    columns, total = list_columns(chemistry, brand, search, particle_size, limit, offset)
    return {
        "columns": [column_to_dict(c) for c in columns],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{column_id}")
async def get_single_column(column_id: str) -> dict:
    col = get_column(column_id)
    if col is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
    return column_to_dict(col)

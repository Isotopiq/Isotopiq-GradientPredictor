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
# F3: Tanaka Column Comparison
# ---------------------------------------------------------------------------


class TanakaParamsSchema(BaseModel):
    column_name: str = ""
    column_type: str = "C18"
    k_pb: float = 0.0
    alpha_ch2: float = 0.0
    alpha_t_o: float = 0.0
    alpha_c_p: float = 0.0
    alpha_b_a_76: float = 0.0
    alpha_b_a_27: float = 0.0


class ColumnCompareRequest(BaseModel):
    column_a: TanakaParamsSchema
    column_b: TanakaParamsSchema


class ColumnCompareAllRequest(BaseModel):
    columns: list[TanakaParamsSchema]
    reference: TanakaParamsSchema | None = None


@router.get("/tanaka/reference")
async def list_tanaka_reference() -> dict:
    """List reference Tanaka parameters for common column types."""
    from app.core.chem.column_comparison import REFERENCE_COLUMNS
    return {
        "reference_columns": {k: v.to_dict() for k, v in REFERENCE_COLUMNS.items()}
    }


@router.get("/tanaka/column/{column_id}")
async def get_tanaka_for_column(column_id: str) -> dict:
    """Get estimated Tanaka parameters for a commercial column from the database."""
    col = get_column(column_id)
    if col is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Column '{column_id}' not found")
    from app.core.chem.column_comparison import estimate_tanaka_from_phase
    if col.phase is not None:
        params = estimate_tanaka_from_phase(
            column_name=f"{col.brand} {col.name}",
            column_type=col.chemistry,
            carbon_load_pct=col.phase.carbon_load_pct,
            ligand_length=col.phase.ligand_length,
            bonding_density_umol_m2=col.phase.bonding_density_umol_m2,
            surface_area_m2_g=col.phase.surface_area_m2_g,
            pore_size_a=col.phase.pore_size_a,
            endcapped=col.phase.endcapped,
            polar_embedded=col.phase.polar_embedded,
            particle_type=col.phase.particle_type,
            base_material=col.phase.base_material,
            hydrophobicity_index=col.phase.hydrophobicity_index,
        )
    else:
        # No phase data — use reference columns as fallback
        from app.core.chem.column_comparison import REFERENCE_COLUMNS
        chem = col.chemistry.lower()
        ref_key = "C18_endcapped"
        for key, ref in REFERENCE_COLUMNS.items():
            if chem in ref.column_type.lower():
                ref_key = key
                break
        ref = REFERENCE_COLUMNS[ref_key]
        params = estimate_tanaka_from_phase(
            column_name=f"{col.brand} {col.name}",
            column_type=col.chemistry,
            carbon_load_pct=18.0, ligand_length=18, bonding_density_umol_m2=3.0,
            surface_area_m2_g=180.0, pore_size_a=120.0, endcapped=True,
            polar_embedded=False, hydrophobicity_index=1.0,
        )
    return params.to_dict()


@router.post("/tanaka/compare")
async def compare_two_columns(data: ColumnCompareRequest) -> dict:
    """Compare two columns using Tanaka parameters."""
    from app.core.chem.column_comparison import TanakaParameters, compare_columns

    a = TanakaParameters(**data.column_a.model_dump())
    b = TanakaParameters(**data.column_b.model_dump())
    result = compare_columns(a, b)
    return result.to_dict()


@router.post("/tanaka/compare-all")
async def compare_all_columns(data: ColumnCompareAllRequest) -> dict:
    """Compare all columns against a reference or pairwise."""
    from app.core.chem.column_comparison import TanakaParameters, compare_all, cluster_columns

    columns = [TanakaParameters(**c.model_dump()) for c in data.columns]
    reference = TanakaParameters(**data.reference.model_dump()) if data.reference else None

    comparisons = compare_all(columns, reference)
    clusters = cluster_columns(columns)

    return {
        "comparisons": comparisons,
        "clusters": clusters,
    }


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

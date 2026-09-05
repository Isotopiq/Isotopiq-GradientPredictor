"""Export routes: PDF, CSV, and instrument-format method export.

All PDF exports are section-driven — the user selects which sections to include
via a sections dict in the request body or query params.
"""
from __future__ import annotations

import io
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.export.csv import export_method_csv
from app.core.export.instrument import (
    export_agilent_m,
    export_thermo_xml,
    export_waters_mth,
)
from app.core.export.pdf import (
    BatchAnalysisSections,
    ColumnComparisonSections,
    PDFSectionOptions,
    export_batch_analysis_pdf,
    export_column_comparison_pdf,
    export_method_pdf,
    export_preview_pdf,
)
from app.deps import CurrentUser, DBSession
from app.services import compound_service, method_service

router = APIRouter(prefix="/export", tags=["export"])


def _method_to_dict(method) -> dict:
    return {
        "column_type": method.column_type,
        "temperature_c": method.temperature_c,
        "mobile_phase_a": method.mobile_phase_a,
        "mobile_phase_b": method.mobile_phase_b,
        "additive": method.additive,
        "ph": method.ph,
        "flow_rate_ml_min": method.flow_rate_ml_min,
        "gradient_table": method.gradient_table,
    }


def _compound_to_dict(compound) -> dict | None:
    if compound is None:
        return None
    return {
        "name": compound.name,
        "smiles": compound.smiles,
        "mw": compound.mw,
    }


async def _load_settings_dict(db) -> dict[str, Any]:
    """Load admin settings for PDF branding."""
    from sqlalchemy import select as sa_select

    from app.models.app_settings import AppSettings
    result = await db.execute(sa_select(AppSettings).limit(1))
    s = result.scalar_one_or_none()
    if s is None:
        return {}
    return {
        "lab_name": s.lab_name,
        "lab_subtitle": s.lab_subtitle,
        "report_footer": s.report_footer,
        "logo_bytes": s.logo_bytes,
        "report_title_prefix": s.report_title_prefix,
        "cover_page_text": s.cover_page_text,
        "report_theme": s.report_theme,
        "include_cover_page_default": s.include_cover_page_default,
    }


def _parse_sections_query(sections_str: str | None) -> PDFSectionOptions:
    """Parse a comma-separated sections query param into PDFSectionOptions."""
    if not sections_str:
        return PDFSectionOptions()
    requested = set(s.strip() for s in sections_str.split(","))
    return PDFSectionOptions(
        method_parameters="method_parameters" in requested,
        gradient_program="gradient_program" in requested,
        compound_info="compound_info" in requested,
        chromatogram="chromatogram" in requested,
        resolution_matrix="resolution_matrix" in requested,
        robustness="robustness" in requested,
        optimization="optimization" in requested,
        method_transfer="method_transfer" in requested,
        cover_page="cover_page" in requested,
        disclaimer="disclaimer" in requested,
    )


# ---------------------------------------------------------------------------
# Method export (existing, updated for sections)
# ---------------------------------------------------------------------------

@router.get("/method/{method_id}")
async def export_method(
    method_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
    format: str = Query("pdf", pattern="^(pdf|csv|agilent|waters|thermo)$"),
    compound_id: uuid.UUID | None = Query(None),
    sections: str | None = Query(None, description="Comma-separated section names for PDF"),
):
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id is not None and method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    compound = None
    if compound_id:
        compound = await compound_service.get_compound(db, compound_id)

    method_dict = _method_to_dict(method)
    compound_dict = _compound_to_dict(compound)

    if format == "csv":
        csv_str = export_method_csv(method, compound)
        return StreamingResponse(
            io.BytesIO(csv_str.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.csv"},
        )
    elif format == "pdf":
        settings_dict = await _load_settings_dict(db)
        section_opts = _parse_sections_query(sections)
        pdf_bytes = export_method_pdf(
            method, compound, None, settings_dict,
            sections=section_opts,
        )
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.pdf"},
        )
    elif format == "agilent":
        content = export_agilent_m(method_dict, compound_dict)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.m"},
        )
    elif format == "waters":
        content = export_waters_mth(method_dict, compound_dict)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.mth"},
        )
    elif format == "thermo":
        content = export_thermo_xml(method_dict, compound_dict)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.xml"},
        )


# ---------------------------------------------------------------------------
# Predictor export (unsaved method)
# ---------------------------------------------------------------------------

class PredictorExportRequest(BaseModel):
    name: str | None = None
    column_type: str = "C18"
    ph: float | None = 2.7
    flow_rate_ml_min: float | None = 0.4
    temperature_c: float | None = 30.0
    mobile_phase_a: str | None = None
    mobile_phase_b: str | None = None
    additive: str | None = None
    gradient_table: list[dict[str, Any]] = []
    compounds_smiles: list[str] = []
    compound_names: list[str] | None = None
    dwell_volume_ml: float | None = None
    dead_volume_ml: float | None = None
    sections: dict[str, bool] | None = None


class _MockMethod:
    """Lightweight stand-in for Method ORM object (not persisted)."""
    def __init__(self, data: PredictorExportRequest):
        self.name = data.name
        self.column_type = data.column_type
        self.ph = data.ph
        self.flow_rate_ml_min = data.flow_rate_ml_min
        self.temperature_c = data.temperature_c
        self.mobile_phase_a = data.mobile_phase_a
        self.mobile_phase_b = data.mobile_phase_b
        self.additive = data.additive
        self.gradient_table = data.gradient_table
        self.compounds_smiles = data.compounds_smiles
        self.dwell_volume_ml = data.dwell_volume_ml
        self.dead_volume_ml = data.dead_volume_ml
        self.column_dims = None
        self.owner_id = None


@router.post("/predictor")
async def export_predictor(
    data: PredictorExportRequest,
    db: DBSession,
    current: CurrentUser,
):
    """Export a PDF from the current predictor state (no save required)."""
    settings_dict = await _load_settings_dict(db)
    method = _MockMethod(data)
    section_opts = PDFSectionOptions.from_dict(data.sections)
    pdf_bytes = export_method_pdf(
        method, None, None, settings_dict,
        sections=section_opts,
        compound_names=data.compound_names,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=predictor_report.pdf"},
    )


# ---------------------------------------------------------------------------
# Shared method export (public, no auth)
# ---------------------------------------------------------------------------

@router.get("/shared/{token}")
async def export_shared_method(
    token: str,
    db: DBSession,
    sections: str | None = Query(None),
):
    """Export a shared method as PDF. No auth required."""
    from sqlalchemy import select as sa_select

    from app.models.method import Method

    result = await db.execute(
        sa_select(Method).where(
            Method.share_token == token,
            Method.is_shared.is_(True),
        )
    )
    method = result.scalar_one_or_none()
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared method not found or no longer available")

    settings_dict = await _load_settings_dict(db)
    section_opts = _parse_sections_query(sections)
    # Shared reports: no robustness/optimization (require heavy computation)
    section_opts.robustness = False
    section_opts.optimization = False
    section_opts.method_transfer = False

    pdf_bytes = export_method_pdf(method, None, None, settings_dict, sections=section_opts)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=shared_method_{token}.pdf"},
    )


# ---------------------------------------------------------------------------
# Column comparison export
# ---------------------------------------------------------------------------

class ColumnComparisonExportRequest(BaseModel):
    columns: list[dict[str, Any]] = []
    sections: dict[str, bool] | None = None


@router.post("/column-comparison")
async def export_column_comparison(
    data: ColumnComparisonExportRequest,
    db: DBSession,
    current: CurrentUser,
):
    """Export a column comparison PDF report."""
    if not data.columns:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No columns provided")
    if len(data.columns) > 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Maximum 4 columns allowed")

    settings_dict = await _load_settings_dict(db)
    section_opts = ColumnComparisonSections.from_dict(data.sections)
    pdf_bytes = export_column_comparison_pdf(data.columns, settings_dict, sections=section_opts)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=column_comparison.pdf"},
    )


# ---------------------------------------------------------------------------
# Batch analysis export
# ---------------------------------------------------------------------------

class BatchAnalysisExportRequest(BaseModel):
    method_params: dict[str, Any] = {}
    compounds: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    sections: dict[str, bool] | None = None


@router.post("/batch-analysis")
async def export_batch_analysis(
    data: BatchAnalysisExportRequest,
    db: DBSession,
    current: CurrentUser,
):
    """Export a batch analysis PDF report."""
    settings_dict = await _load_settings_dict(db)
    section_opts = BatchAnalysisSections.from_dict(data.sections)
    batch_data = {
        "method_params": data.method_params,
        "compounds": data.compounds,
        "results": data.results,
    }
    pdf_bytes = export_batch_analysis_pdf(batch_data, settings_dict, sections=section_opts)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=batch_analysis.pdf"},
    )


@router.get("/preview")
async def get_report_preview(
    db: DBSession,
    current: CurrentUser,
):
    """Generate a preview PDF report with sample data using current admin settings.

    Admin only — used by the admin settings page to preview the report template
    design (theme, branding, logo, cover page, etc.).
    """
    if not current.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    settings_dict = await _load_settings_dict(db)
    pdf_bytes = export_preview_pdf(settings_dict)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=report_preview.pdf"},
    )

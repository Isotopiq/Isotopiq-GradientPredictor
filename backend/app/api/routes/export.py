"""Export routes: PDF, CSV, and instrument-format method export."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import io

from app.deps import CurrentUser, DBSession
from app.core.export.csv import export_method_csv
from app.core.export.pdf import export_method_pdf
from app.core.export.instrument import (
    export_agilent_m,
    export_thermo_xml,
    export_waters_mth,
)
from app.services import method_service, compound_service

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


@router.get("/method/{method_id}")
async def export_method(
    method_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
    format: str = Query("pdf", pattern="^(pdf|csv|agilent|waters|thermo)$"),
    compound_id: uuid.UUID | None = Query(None),
    include_chromatogram: bool = Query(False),
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
        # Load app settings for branding
        from sqlalchemy import select as sa_select
        from app.models.app_settings import AppSettings
        settings_result = await db.execute(sa_select(AppSettings).limit(1))
        app_settings = settings_result.scalar_one_or_none()
        settings_dict = None
        if app_settings:
            settings_dict = {
                "lab_name": app_settings.lab_name,
                "lab_subtitle": app_settings.lab_subtitle,
                "report_footer": app_settings.report_footer,
                "logo_bytes": app_settings.logo_bytes,
            }
        pdf_bytes = export_method_pdf(
            method, compound, None, settings_dict,
            include_chromatogram=include_chromatogram,
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

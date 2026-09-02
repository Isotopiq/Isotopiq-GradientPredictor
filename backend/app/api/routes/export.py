"""Export routes: PDF and CSV method export."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import io

from app.deps import CurrentUser, DBSession
from app.core.export.csv import export_method_csv
from app.core.export.pdf import export_method_pdf
from app.services import method_service, compound_service

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/method/{method_id}")
async def export_method(
    method_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    compound_id: uuid.UUID | None = Query(None),
):
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id is not None and method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    compound = None
    if compound_id:
        compound = await compound_service.get_compound(db, compound_id)

    if format == "csv":
        csv_str = export_method_csv(method, compound)
        return StreamingResponse(
            io.BytesIO(csv_str.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.csv"},
        )
    else:
        pdf_bytes = export_method_pdf(method, compound)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=method_{method_id}.pdf"},
        )

"""Health check."""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.database import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(response: Response) -> dict[str, str]:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}
    return {"status": "ok"}

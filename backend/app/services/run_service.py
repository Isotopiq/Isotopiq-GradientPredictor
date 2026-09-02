"""Run service."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.method import Method
from app.models.run import Run
from app.schemas.run import RunCreate

logger = logging.getLogger(__name__)

# Drift detection: retrain when new runs >= this fraction of training set
DRIFT_FRACTION = 0.05
MIN_NEW_RUNS_FOR_RETRAIN = 3


async def create_run(db: AsyncSession, owner_id: uuid.UUID | None, data: RunCreate) -> Run:
    run = Run(
        compound_id=data.compound_id,
        method_id=data.method_id,
        owner_id=owner_id,
        observed_rt_s=data.observed_rt_s,
        peak_width_s=data.peak_width_s,
        notes=data.notes,
        run_date=data.run_date,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Check for drift and trigger retrain if needed
    await _check_drift_and_retrain(db, data.method_id, owner_id)

    return run


async def _check_drift_and_retrain(
    db: AsyncSession, method_id: uuid.UUID, owner_id: uuid.UUID | None
) -> None:
    """Check if enough new runs have accumulated to trigger a model retrain."""
    try:
        method = await db.get(Method, method_id)
        if method is None:
            return

        # Count runs for this method
        from app.models.run import Run as RunModel

        stmt = select(RunModel).where(RunModel.method_id == method_id)
        result = await db.execute(stmt)
        runs = list(result.scalars().all())

        if len(runs) < MIN_NEW_RUNS_FOR_RETRAIN:
            return

        # Check if a model exists for this column type
        from app.core.ml.registry import get_latest_artifact
        from app.services.method_service import compute_method_signature

        sig = method.method_signature or compute_method_signature(
            method.column_type, method.ph, method.mobile_phase_b
        )
        artifact = await get_latest_artifact(db, method.column_type, sig)
        if artifact is None:
            return  # No model to retrain

        # Check if new runs exceed drift fraction of training samples
        if len(runs) >= artifact.n_samples * DRIFT_FRACTION:
            logger.info(
                "Drift detected: %d new runs vs %d training samples for %s. Retraining...",
                len(runs),
                artifact.n_samples,
                method.column_type,
            )
            from app.services.ml_service import train_from_stored_runs

            await train_from_stored_runs(
                db=db,
                owner_id=owner_id,
                column_type=method.column_type,
                model_type=artifact.model_type,
                method_signature=sig,
            )
    except Exception as exc:
        logger.warning("Drift check/retrain failed: %s", exc)


async def list_runs(
    db: AsyncSession,
    compound_id: uuid.UUID | None = None,
    method_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Run]:
    stmt = select(Run).order_by(Run.run_date.desc().nullslast(), Run.created_at.desc())
    if compound_id:
        stmt = stmt.where(Run.compound_id == compound_id)
    if method_id:
        stmt = stmt.where(Run.method_id == method_id)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_run(db: AsyncSession, run_id: uuid.UUID) -> bool:
    run = await db.get(Run, run_id)
    if run is None:
        return False
    await db.delete(run)
    await db.commit()
    return True

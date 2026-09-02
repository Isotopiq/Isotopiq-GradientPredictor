"""Notification routes — retraining recommendations and system alerts."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.deps import CurrentUser, DBSession
from app.models.model_artifact import ModelArtifact
from app.models.run import Run
from app.models.method import Method

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(db: DBSession, current: CurrentUser) -> list[dict]:
    """Get notifications for the current user.

    Checks for:
    - New experimental runs since last model training (retrain recommendation)
    """
    notifications: list[dict] = []

    # Find column types that have runs but no recent model
    # or have new runs since last model training
    run_counts = await db.execute(
        select(
            Method.column_type,
            func.count(Run.id).label("run_count"),
        )
        .join(Method, Run.method_id == Method.id)
        .group_by(Method.column_type)
    )

    for column_type, total_runs in run_counts.all():
        # Find latest model for this column type
        latest_model = await db.execute(
            select(ModelArtifact)
            .where(ModelArtifact.column_type == column_type)
            .order_by(ModelArtifact.trained_at.desc())
            .limit(1)
        )
        model = latest_model.scalar_one_or_none()

        if model is None:
            # No model trained but runs exist
            if total_runs >= 5:
                notifications.append({
                    "id": f"retrain-{column_type}-no-model",
                    "type": "retrain_recommended",
                    "column_type": column_type,
                    "new_run_count": total_runs,
                    "last_trained_at": None,
                    "message": f"{total_runs} runs logged for {column_type} but no model trained yet. Train a model to enable ML predictions.",
                    "severity": "info",
                })
        else:
            # Count runs since last model training
            new_runs = await db.execute(
                select(func.count(Run.id))
                .join(Method, Run.method_id == Method.id)
                .where(
                    (Method.column_type == column_type)
                    & (Run.created_at > model.trained_at)
                )
            )
            new_count = new_runs.scalar() or 0
            if new_count >= 3:
                notifications.append({
                    "id": f"retrain-{column_type}-{model.id}",
                    "type": "retrain_recommended",
                    "column_type": column_type,
                    "new_run_count": new_count,
                    "last_trained_at": model.trained_at.isoformat(),
                    "message": f"{new_count} new runs since last model training ({column_type}). Retrain to improve accuracy.",
                    "severity": "warning",
                })

    return notifications


@router.post("/dismiss")
async def dismiss_notification(
    current: CurrentUser,
    notification_id: str = "",
) -> dict:
    """Dismiss a notification (stored in client-side for now)."""
    return {"dismissed": True, "id": notification_id, "at": datetime.now(timezone.utc).isoformat()}

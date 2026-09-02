"""ML service: orchestrate training and prediction."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ml.applicability import check_applicability
from app.core.ml.features import MethodConditions, build_features_from_descriptors
from app.core.ml.registry import (
    get_latest_artifact,
    load_model_from_artifact,
)
from app.core.ml.trainer import (
    TrainingSample,
    load_stored_runs,
    parse_training_csv,
    train_model,
)
from app.models.compound import Compound
from app.models.method import Method
from app.services.method_service import compute_method_signature


async def train_from_csv(
    db: AsyncSession,
    owner_id: uuid.UUID | None,
    column_type: str,
    model_type: str,
    csv_content: bytes,
    method_signature: str | None = None,
):
    samples = parse_training_csv(csv_content)
    # Filter to requested column type
    if column_type:
        samples = [s for s in samples if s.column_type == column_type]
    if not samples:
        raise ValueError(f"No samples for column type '{column_type}' in CSV")
    return await train_model(db, owner_id, column_type, model_type, samples, method_signature)


async def train_from_stored_runs(
    db: AsyncSession,
    owner_id: uuid.UUID | None,
    column_type: str,
    model_type: str,
    method_signature: str | None = None,
):
    samples = await load_stored_runs(db, column_type)
    if not samples:
        raise ValueError(f"No stored runs for column type '{column_type}'")
    return await train_model(db, owner_id, column_type, model_type, samples, method_signature)


async def predict_with_ml(
    db: AsyncSession, compound: Compound, method: Method
) -> dict[str, Any] | None:
    """Predict RT using a trained ML model if available. Returns None if no model."""
    sig = method.method_signature or compute_method_signature(
        method.column_type, method.ph, method.mobile_phase_b
    )
    artifact = await get_latest_artifact(db, method.column_type, sig)
    if artifact is None:
        return None

    # Build features from stored compound + method
    gt = method.gradient_table or []
    b_start = gt[0]["percent_b"] if gt else 5.0
    b_end = gt[-1]["percent_b"] if gt else 95.0
    t_total = (gt[-1]["time_s"] - gt[0]["time_s"]) / 60.0 if len(gt) >= 2 else 20.0

    conditions = MethodConditions(
        column_type=method.column_type,
        ph=method.ph or 2.7,
        percent_b_start=b_start,
        percent_b_end=b_end,
        gradient_time_min=t_total,
        flow_rate_ml_min=method.flow_rate_ml_min or 0.4,
        temperature_c=method.temperature_c or 30.0,
    )

    descriptors = {
        "mw": compound.mw or 0.0,
        "logp": compound.logp or 0.0,
        "tpsa": compound.tpsa or 0.0,
        "hbd": compound.hbd or 0,
        "hba": compound.hba or 0,
        "rotatable_bonds": compound.rotatable_bonds or 0,
        "aromatic_rings": compound.aromatic_rings or 0,
        "num_rings": 0,
        "num_heavy_atoms": 0,
        "num_heteroatoms": 0,
        "fraction_csp3": 0.0,
    }
    pka_values = compound.pka_values or []
    features = build_features_from_descriptors(descriptors, pka_values, conditions)

    model = load_model_from_artifact(artifact)
    result = model.predict(features)
    is_extrap, distance = model.is_extrapolating(features)

    return {
        "predicted_rt_s": result.mean,
        "rt_lower_s": result.lower,
        "rt_upper_s": result.upper,
        "confidence": result.confidence,
        "extrapolating": is_extrap,
        "applicability_distance": distance,
        "model_version": f"{artifact.model_type}-v{artifact.version}",
    }

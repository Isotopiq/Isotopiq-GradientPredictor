"""Prediction service.

Uses ML model when available for (column_type, method_signature),
falls back to rules-based LSS heuristic estimate.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.lss.gradient_sim import heuristic_lss_params, predict_rt_from_gradient
from app.models.compound import Compound
from app.models.method import Method
from app.models.prediction import Prediction
from app.services.ml_service import predict_with_ml


async def predict(
    db: AsyncSession, compound_id: uuid.UUID, method_id: uuid.UUID
) -> Prediction:
    """Predict retention time for a compound on a method.

    Tries ML model first; falls back to heuristic LSS estimate from logP.
    """
    compound = await db.get(Compound, compound_id)
    method = await db.get(Method, method_id)
    if compound is None:
        raise ValueError("Compound not found")
    if method is None:
        raise ValueError("Method not found")

    # Try ML prediction first
    ml_result = await predict_with_ml(db, compound, method)

    if ml_result is not None:
        prediction = Prediction(
            compound_id=compound_id,
            method_id=method_id,
            predicted_rt_s=ml_result["predicted_rt_s"],
            rt_lower_s=ml_result["rt_lower_s"],
            rt_upper_s=ml_result["rt_upper_s"],
            confidence=ml_result["confidence"],
            extrapolating=ml_result["extrapolating"],
            model_version=ml_result["model_version"],
        )
    else:
        # Fallback: rules-based heuristic
        logp = compound.logp or 0.0
        gradient_table = method.gradient_table or []
        flow = method.flow_rate_ml_min or 0.4

        params = heuristic_lss_params(logp)
        rt = predict_rt_from_gradient(params, gradient_table, flow_rate_ml_min=flow)

        prediction = Prediction(
            compound_id=compound_id,
            method_id=method_id,
            predicted_rt_s=rt,
            confidence=0.3,
            extrapolating=False,
            model_version="rules-v1",
        )

    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)
    return prediction

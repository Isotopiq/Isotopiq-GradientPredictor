"""Prediction service.

Uses ML model when available for (column_type, method_signature),
falls back to Physics-Informed Retention Model (PIRM) using stationary
phase composition, then to rules-based LSS heuristic.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.columns_db import get_column
from app.core.lss.gradient_sim import heuristic_lss_params, predict_rt_from_gradient
from app.core.ml.pirm_model import predict_retention
from app.models.compound import Compound
from app.models.method import Method
from app.models.prediction import Prediction
from app.services.ml_service import predict_with_ml


async def predict(
    db: AsyncSession, compound_id: uuid.UUID, method_id: uuid.UUID
) -> Prediction:
    """Predict retention time for a compound on a method.

    Priority:
      1. Trained ML model (highest confidence)
      2. PIRM physics-informed model (uses stationary phase composition)
      3. Rules-based LSS heuristic from logP (lowest confidence)
    """
    compound = await db.get(Compound, compound_id)
    method = await db.get(Method, method_id)
    if compound is None:
        raise ValueError("Compound not found")
    if method is None:
        raise ValueError("Method not found")

    # 1. Try trained ML model first
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
        # 2. Try PIRM if the method references a real column from the database
        pirm_result = _try_pirm(compound, method)

        if pirm_result is not None:
            prediction = Prediction(
                compound_id=compound_id,
                method_id=method_id,
                predicted_rt_s=pirm_result["predicted_rt_s"],
                rt_lower_s=pirm_result["rt_lower_s"],
                rt_upper_s=pirm_result["rt_upper_s"],
                confidence=pirm_result["confidence"],
                extrapolating=pirm_result["extrapolating"],
                model_version=pirm_result["model_version"],
            )
        else:
            # 3. Fallback: rules-based heuristic
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


def _try_pirm(compound: Compound, method: Method) -> dict | None:
    """Attempt PIRM prediction if the method references a real column.

    The method's column_dims may contain a 'column_id' field linking to
    the commercial column database. If so, use the full stationary phase
    composition for a physics-informed prediction.
    """
    col_dims = method.column_dims or {}
    col_id = col_dims.get("column_id")
    if not col_id:
        return None

    col = get_column(col_id)
    if col is None or col.phase is None:
        return None

    logp = compound.logp or 0.0
    mw = compound.mw or 0.0
    tpsa = compound.tpsa or 0.0
    gradient_table = method.gradient_table or []
    flow = method.flow_rate_ml_min or 0.4

    if not gradient_table:
        return None

    return predict_retention(
        column=col,
        logp=logp,
        mw=mw,
        tpsa=tpsa,
        gradient_table=gradient_table,
        flow_rate_ml_min=flow,
    )

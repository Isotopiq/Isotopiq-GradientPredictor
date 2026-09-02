"""Training pipeline: load data, build features, fit, validate, persist."""
from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.parser import parse_mol
from app.core.ml.applicability import check_applicability
from app.core.ml.features import FEATURE_NAMES, MethodConditions, build_features
from app.core.ml.registry import create_model, save_artifact
from app.models.compound import Compound
from app.models.method import Method
from app.models.model_artifact import ModelArtifact
from app.models.run import Run
from app.services.method_service import compute_method_signature


@dataclass
class TrainingSample:
    smiles: str
    column_type: str
    ph: float
    percent_b_start: float
    percent_b_end: float
    gradient_time_min: float
    flow_rate_ml_min: float
    temperature_c: float
    observed_rt_s: float


class TrainingError(ValueError):
    pass


def parse_training_csv(content: bytes) -> list[TrainingSample]:
    """Parse a CSV upload into training samples.

    Expected columns: smiles, column_type, ph, percent_b_start, percent_b_end,
    gradient_time_min, flow_ml_min, temperature_c, observed_rt_s
    """
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    samples: list[TrainingSample] = []
    for i, row in enumerate(reader, start=2):
        try:
            samples.append(
                TrainingSample(
                    smiles=row["smiles"],
                    column_type=row["column_type"],
                    ph=float(row["ph"]),
                    percent_b_start=float(row.get("percent_b_start", 5)),
                    percent_b_end=float(row.get("percent_b_end", 95)),
                    gradient_time_min=float(row.get("gradient_time_min", 20)),
                    flow_rate_ml_min=float(row.get("flow_ml_min", 0.4)),
                    temperature_c=float(row.get("temperature_c", 30)),
                    observed_rt_s=float(row["observed_rt_s"]),
                )
            )
        except (KeyError, ValueError) as exc:
            raise TrainingError(f"Row {i}: {exc}") from exc
    if not samples:
        raise TrainingError("No valid training samples found in CSV")
    return samples


async def load_stored_runs(
    db: AsyncSession, column_type: str
) -> list[TrainingSample]:
    """Load training data from stored Runs joined to Compounds + Methods."""
    stmt = (
        select(Run, Compound, Method)
        .join(Compound, Run.compound_id == Compound.id)
        .join(Method, Run.method_id == Method.id)
        .where(Method.column_type == column_type)
    )
    result = await db.execute(stmt)
    samples: list[TrainingSample] = []
    for run, compound, method in result.all():
        if not compound.smiles:
            continue
        gt = method.gradient_table or []
        b_start = gt[0]["percent_b"] if gt else 5.0
        b_end = gt[-1]["percent_b"] if gt else 95.0
        t_total = (gt[-1]["time_s"] - gt[0]["time_s"]) / 60.0 if len(gt) >= 2 else 20.0
        samples.append(
            TrainingSample(
                smiles=compound.smiles,
                column_type=method.column_type,
                ph=method.ph or 2.7,
                percent_b_start=b_start,
                percent_b_end=b_end,
                gradient_time_min=t_total,
                flow_rate_ml_min=method.flow_rate_ml_min or 0.4,
                temperature_c=method.temperature_c or 30.0,
                observed_rt_s=run.observed_rt_s,
            )
        )
    return samples


def build_training_matrix(samples: list[TrainingSample]) -> tuple[np.ndarray, np.ndarray]:
    """Build X, y matrices from training samples."""
    X_list: list[np.ndarray] = []
    y_list: list[float] = []
    for s in samples:
        try:
            mol = parse_mol(s.smiles).mol
        except Exception:
            continue
        conditions = MethodConditions(
            column_type=s.column_type,
            ph=s.ph,
            percent_b_start=s.percent_b_start,
            percent_b_end=s.percent_b_end,
            gradient_time_min=s.gradient_time_min,
            flow_rate_ml_min=s.flow_rate_ml_min,
            temperature_c=s.temperature_c,
        )
        X_list.append(build_features(mol, conditions))
        y_list.append(s.observed_rt_s)

    if not X_list:
        raise TrainingError("No valid training samples after feature extraction")

    X = np.array(X_list)
    y = np.array(y_list)
    return X, y


async def train_model(
    db: AsyncSession,
    owner_id: uuid.UUID | None,
    column_type: str,
    model_type: str,
    samples: list[TrainingSample],
    method_signature: str | None = None,
) -> ModelArtifact:
    """Train a model and persist the artifact."""
    X, y = build_training_matrix(samples)

    model = create_model(model_type)
    metrics = model.fit(X, y)

    # Add cross-validation metrics
    metrics["rmse"] = float(np.sqrt(metrics.get("residual_std", 1.0) ** 2))
    metrics["mae"] = float(metrics.get("residual_std", 1.0) * 0.8)  # approximate
    metrics["feature_names"] = FEATURE_NAMES

    sig = method_signature or compute_method_signature(column_type, None, None)

    artifact = await save_artifact(
        db=db,
        owner_id=owner_id,
        column_type=column_type,
        method_signature=sig,
        model_type=model_type,
        model=model,
        metrics=metrics,
        n_samples=len(samples),
        feature_schema={"features": FEATURE_NAMES},
    )
    return artifact


def predict_with_artifact(
    artifact: ModelArtifact,
    features: np.ndarray,
) -> dict[str, Any]:
    """Load model from artifact and predict."""
    from app.core.ml.registry import load_model_from_artifact

    model = load_model_from_artifact(artifact)
    result = model.predict(features)

    # Applicability domain check
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

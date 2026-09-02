"""Ensemble model: weighted average of XGBoost + LightGBM."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from app.core.ml.base import PredictionResult, RetentionModel
from app.core.ml.features import FEATURE_NAMES
from app.core.ml.lightgbm_model import LightGBMModel
from app.core.ml.xgboost_model import XGBoostModel


class EnsembleModel(RetentionModel):
    model_type = "ensemble"

    def __init__(self, xgb_weight: float = 0.5, lgbm_weight: float = 0.5) -> None:
        self._xgb = XGBoostModel()
        self._lgbm = LightGBMModel()
        self._xgb_weight = xgb_weight
        self._lgbm_weight = lgbm_weight
        self._train_X: np.ndarray | None = None
        self._residual_std: float = 1.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        self._train_X = X
        xgb_metrics = self._xgb.fit(X, y)
        lgbm_metrics = self._lgbm.fit(X, y)

        # Ensemble residual: average of both
        self._residual_std = (xgb_metrics["residual_std"] + lgbm_metrics["residual_std"]) / 2.0

        return {
            "residual_std": self._residual_std,
            "r2": (xgb_metrics.get("r2", 0) + lgbm_metrics.get("r2", 0)) / 2.0,
            "n_samples": len(y),
            "xgb_r2": xgb_metrics.get("r2"),
            "lgbm_r2": lgbm_metrics.get("r2"),
        }

    def predict(self, X: np.ndarray) -> PredictionResult:
        if X.ndim == 1:
            X = X.reshape(1, -1)
        xgb_pred = self._xgb.predict(X)
        lgbm_pred = self._lgbm.predict(X)

        mean = self._xgb_weight * xgb_pred.mean + self._lgbm_weight * lgbm_pred.mean
        # Confidence from agreement between models
        agreement = 1.0 - min(1.0, abs(xgb_pred.mean - lgbm_pred.mean) / max(abs(mean), 1.0))
        lower = mean - 1.645 * self._residual_std
        upper = mean + 1.645 * self._residual_std
        confidence = max(0.0, min(1.0, agreement * (1.0 - self._residual_std / max(abs(mean), 1.0))))
        return PredictionResult(mean=float(mean), lower=lower, upper=upper, confidence=confidence)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        xgb_path = path.with_suffix(".xgb.pkl")
        lgbm_path = path.with_suffix(".lgbm.pkl")
        self._xgb.save(xgb_path)
        self._lgbm.save(lgbm_path)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "xgb_weight": self._xgb_weight,
                    "lgbm_weight": self._lgbm_weight,
                    "residual_std": self._residual_std,
                    "train_X": self._train_X,
                },
                f,
            )

    def load(self, path: Path) -> None:
        xgb_path = path.with_suffix(".xgb.pkl")
        lgbm_path = path.with_suffix(".lgbm.pkl")
        self._xgb.load(xgb_path)
        self._lgbm.load(lgbm_path)
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._xgb_weight = data["xgb_weight"]
        self._lgbm_weight = data["lgbm_weight"]
        self._residual_std = data["residual_std"]
        self._train_X = data.get("train_X")

    @property
    def feature_importances(self) -> dict[str, float]:
        xgb_imp = self._xgb.feature_importances
        lgbm_imp = self._lgbm.feature_importances
        result: dict[str, float] = {}
        for name in FEATURE_NAMES:
            result[name] = (
                self._xgb_weight * xgb_imp.get(name, 0.0)
                + self._lgbm_weight * lgbm_imp.get(name, 0.0)
            )
        return result

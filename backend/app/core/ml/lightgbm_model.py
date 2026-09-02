"""LightGBM retention model."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import lightgbm as lgb
from sklearn.model_selection import cross_val_predict

from app.core.ml.base import PredictionResult, RetentionModel
from app.core.ml.features import FEATURE_NAMES


class LightGBMModel(RetentionModel):
    model_type = "lightgbm"

    def __init__(self, n_estimators: int = 300, max_depth: int = -1, learning_rate: float = 0.1) -> None:
        self._params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "objective": "regression",
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        self._model: lgb.LGBMRegressor | None = None
        self._train_X: np.ndarray | None = None
        self._residual_std: float = 1.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        self._train_X = X
        self._model = lgb.LGBMRegressor(**self._params)
        self._model.fit(X, y)

        if len(X) >= 5:
            preds = cross_val_predict(self._model, X, y, cv=min(5, len(X)))
            self._residual_std = float(np.std(y - preds))
        else:
            train_preds = self._model.predict(X)
            self._residual_std = float(np.std(y - train_preds))

        r2 = 1.0 - self._residual_std**2 / max(np.var(y), 1e-8)
        return {
            "residual_std": self._residual_std,
            "r2": float(r2),
            "n_samples": len(y),
        }

    def predict(self, X: np.ndarray) -> PredictionResult:
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if self._model is None:
            raise RuntimeError("Model not fitted")
        means = self._model.predict(X)
        mean = float(means[0])
        lower = mean - 1.645 * self._residual_std
        upper = mean + 1.645 * self._residual_std
        confidence = max(0.0, min(1.0, 1.0 - self._residual_std / max(abs(mean), 1.0)))
        return PredictionResult(mean=mean, lower=lower, upper=upper, confidence=confidence)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "params": self._params,
                    "model_string": self._model.booster_.model_to_string() if self._model else None,
                    "residual_std": self._residual_std,
                    "train_X": self._train_X,
                },
                f,
            )

    def load(self, path: Path) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._params = data["params"]
        self._residual_std = data["residual_std"]
        self._train_X = data.get("train_X")
        if data.get("model_string"):
            self._model = lgb.LGBMRegressor(**self._params)
            self._model._Booster = lgb.Booster(model_str=data["model_string"])  # type: ignore[attr-defined]

    @property
    def feature_importances(self) -> dict[str, float]:
        if self._model is None:
            return {}
        importances = self._model.feature_importances_
        return dict(zip(FEATURE_NAMES, importances.tolist()))

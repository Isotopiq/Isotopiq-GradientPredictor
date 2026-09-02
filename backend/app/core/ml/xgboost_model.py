"""XGBoost retention model with quantile regression for uncertainty."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.model_selection import cross_val_predict

from app.core.ml.base import PredictionResult, RetentionModel
from app.core.ml.features import FEATURE_NAMES


class XGBoostModel(RetentionModel):
    model_type = "xgboost"

    def __init__(self, n_estimators: int = 300, max_depth: int = 5, learning_rate: float = 0.1) -> None:
        self._params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "objective": "reg:squarederror",
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0,
        }
        self._model: xgb.XGBRegressor | None = None
        self._train_X: np.ndarray | None = None
        self._residual_std: float = 1.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        self._train_X = X
        self._model = xgb.XGBRegressor(**self._params)
        self._model.fit(X, y)

        # Estimate uncertainty via CV
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
        lower = mean - 1.645 * self._residual_std  # 90% CI
        upper = mean + 1.645 * self._residual_std
        confidence = max(0.0, min(1.0, 1.0 - self._residual_std / max(abs(mean), 1.0)))
        return PredictionResult(mean=mean, lower=lower, upper=upper, confidence=confidence)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "params": self._params,
                    "model_data": self._model.get_booster().save_raw() if self._model else None,
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
        if data.get("model_data"):
            booster = xgb.Booster()
            booster.load_model(bytearray(data["model_data"]))
            self._model = xgb.XGBRegressor(**self._params)
            self._model._Booster = booster  # type: ignore[attr-defined]

    @property
    def feature_importances(self) -> dict[str, float]:
        if self._model is None:
            return {}
        importances = self._model.feature_importances_
        return dict(zip(FEATURE_NAMES, importances.tolist()))

"""sklearn GradientBoostingRegressor baseline model."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_predict

from app.core.ml.base import PredictionResult, RetentionModel
from app.core.ml.features import FEATURE_NAMES


class SklearnGBMModel(RetentionModel):
    model_type = "sklearn"

    def __init__(self, n_estimators: int = 200, max_depth: int = 4) -> None:
        self._model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            loss="squared_error",
            random_state=42,
        )
        self._train_X: np.ndarray | None = None
        self._residual_std: float = 1.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        self._train_X = X
        self._model.fit(X, y)
        # Estimate residual std via cross-validation
        if len(X) >= 5:
            preds = cross_val_predict(self._model, X, y, cv=min(5, len(X)))
            self._residual_std = float(np.std(y - preds))
        else:
            train_preds = self._model.predict(X)
            self._residual_std = float(np.std(y - train_preds))
        return {
            "residual_std": self._residual_std,
            "n_samples": len(y),
        }

    def predict(self, X: np.ndarray) -> PredictionResult:
        if X.ndim == 1:
            X = X.reshape(1, -1)
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
                {"model": self._model, "residual_std": self._residual_std, "train_X": self._train_X},
                f,
            )

    def load(self, path: Path) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._model = data["model"]
        self._residual_std = data["residual_std"]
        self._train_X = data.get("train_X")

    @property
    def feature_importances(self) -> dict[str, float]:
        importances = self._model.feature_importances_
        return dict(zip(FEATURE_NAMES, importances.tolist()))

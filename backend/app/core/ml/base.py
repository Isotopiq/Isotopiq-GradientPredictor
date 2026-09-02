"""RetentionModel abstract base class.

All retention prediction models implement this interface so that the
underlying estimator (sklearn GBM, XGBoost, LightGBM, ensemble) can be
swapped without changing call sites.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class PredictionResult:
    mean: float
    lower: float
    upper: float
    confidence: float


class RetentionModel(abc.ABC):
    """Abstract retention prediction model."""

    model_type: str = "base"

    @abc.abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Fit the model. Return training metrics dict."""
        raise NotImplementedError

    @abc.abstractmethod
    def predict(self, X: np.ndarray) -> PredictionResult:
        """Predict retention time(s) with uncertainty."""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, path: Path) -> None:
        """Persist model artifact to path."""
        raise NotImplementedError

    @abc.abstractmethod
    def load(self, path: Path) -> None:
        """Load model artifact from path."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def feature_importances(self) -> dict[str, float]:
        """Return feature name -> importance."""
        raise NotImplementedError

    def is_extrapolating(self, X: np.ndarray, threshold: float = 2.0) -> tuple[bool, float]:
        """Check if a sample is outside the applicability domain.

        Default: Euclidean distance to training centroid, normalized by
        the mean pairwise distance in training. Override for model-specific logic.
        Returns (is_extrapolating, distance).
        """
        if not hasattr(self, "_train_X") or self._train_X is None:
            return False, 0.0
        centroid = self._train_X.mean(axis=0)
        dist = np.linalg.norm(X.flatten() - centroid)
        train_dists = np.linalg.norm(self._train_X - centroid, axis=1)
        mean_dist = train_dists.mean() if len(train_dists) > 0 else 1.0
        normalized = dist / max(mean_dist, 1e-8)
        return normalized > threshold, float(normalized)

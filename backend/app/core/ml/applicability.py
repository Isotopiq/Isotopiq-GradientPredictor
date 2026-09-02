"""Applicability domain check."""
from __future__ import annotations

import numpy as np


def check_applicability(
    sample: np.ndarray, train_X: np.ndarray, threshold: float = 2.0
) -> tuple[bool, float]:
    """Check if a sample is within the applicability domain.

    Uses normalized Euclidean distance to the training centroid.
    Returns (is_extrapolating, distance_score).
    """
    if train_X is None or len(train_X) == 0:
        return False, 0.0

    centroid = train_X.mean(axis=0)
    sample_flat = sample.flatten()[: len(centroid)]

    dist = float(np.linalg.norm(sample_flat - centroid))
    train_dists = np.linalg.norm(train_X - centroid, axis=1)
    mean_dist = float(train_dists.mean()) if len(train_dists) > 0 else 1.0
    normalized = dist / max(mean_dist, 1e-8)

    return normalized > threshold, normalized

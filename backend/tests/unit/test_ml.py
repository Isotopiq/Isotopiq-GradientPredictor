"""Unit tests for ML models."""
from __future__ import annotations

import numpy as np
import pytest

from app.core.ml.applicability import check_applicability
from app.core.ml.features import FEATURE_NAMES, MethodConditions, build_features
from app.core.chem.parser import parse_mol


def _make_synthetic_data(n: int = 20, n_features: int = len(FEATURE_NAMES)):
    """Generate synthetic training data."""
    rng = np.random.RandomState(42)
    X = rng.randn(n, n_features)
    # Simple linear relationship + noise
    true_w = rng.randn(n_features)
    y = X @ true_w + rng.randn(n) * 0.1
    return X, y


class TestSklearnModel:
    def test_fit_predict(self):
        from app.core.ml.sklearn_gbm import SklearnGBMModel

        model = SklearnGBMModel()
        X, y = _make_synthetic_data()
        metrics = model.fit(X, y)
        assert "residual_std" in metrics
        assert metrics["n_samples"] == 20

        result = model.predict(X[0])
        assert isinstance(result.mean, float)
        assert result.lower < result.mean < result.upper

    def test_feature_importances(self):
        from app.core.ml.sklearn_gbm import SklearnGBMModel

        model = SklearnGBMModel()
        X, y = _make_synthetic_data()
        model.fit(X, y)
        imp = model.feature_importances
        assert len(imp) == len(FEATURE_NAMES)


class TestXGBoostModel:
    def test_fit_predict(self):
        from app.core.ml.xgboost_model import XGBoostModel

        model = XGBoostModel()
        X, y = _make_synthetic_data()
        metrics = model.fit(X, y)
        assert "r2" in metrics
        assert metrics["n_samples"] == 20

        result = model.predict(X[0])
        assert isinstance(result.mean, float)
        assert result.lower < result.mean < result.upper


class TestLightGBMModel:
    def test_fit_predict(self):
        from app.core.ml.lightgbm_model import LightGBMModel

        model = LightGBMModel()
        X, y = _make_synthetic_data()
        metrics = model.fit(X, y)
        assert "r2" in metrics

        result = model.predict(X[0])
        assert isinstance(result.mean, float)


class TestEnsembleModel:
    def test_fit_predict(self):
        from app.core.ml.ensemble import EnsembleModel

        model = EnsembleModel()
        X, y = _make_synthetic_data()
        metrics = model.fit(X, y)
        assert "xgb_r2" in metrics and "lgbm_r2" in metrics

        result = model.predict(X[0])
        assert isinstance(result.mean, float)
        assert result.lower < result.mean < result.upper


class TestFeatures:
    def test_build_features(self):
        mol = parse_mol("CCO").mol
        conditions = MethodConditions(
            column_type="C18",
            ph=2.7,
            percent_b_start=5.0,
            percent_b_end=95.0,
            gradient_time_min=20.0,
            flow_rate_ml_min=0.4,
            temperature_c=30.0,
        )
        features = build_features(mol, conditions)
        assert features.shape == (len(FEATURE_NAMES),)
        assert features[0] > 0  # MW
        assert features[-5] == 1.0  # col_C18 one-hot


class TestApplicability:
    def test_in_domain(self):
        rng = np.random.RandomState(42)
        train = rng.randn(20, 5)
        sample = train[0]
        is_extrap, dist = check_applicability(sample, train, threshold=2.0)
        assert is_extrap is False
        assert dist < 2.0

    def test_out_of_domain(self):
        rng = np.random.RandomState(42)
        train = rng.randn(20, 5)
        sample = np.array([100, 100, 100, 100, 100])
        is_extrap, dist = check_applicability(sample, train, threshold=2.0)
        assert is_extrap is True
        assert dist > 2.0

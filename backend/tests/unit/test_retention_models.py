"""Tests for retention model registry, auto-selection, and new model equations."""
from __future__ import annotations

import math

from app.core.lss.retention_models import (
    RETENTION_MECHANISMS,
    RETENTION_MODELS,
    auto_select_model,
    get_mechanism_for_column,
    get_models_for_mechanism,
    heuristic_jandera_params,
    heuristic_polarity_params,
    heuristic_quadratic_params,
    infer_mechanism_from_column,
    predict_rt_jandera,
    predict_rt_polarity,
    predict_rt_quadratic,
)


class TestRetentionMechanisms:
    def test_all_mechanisms_defined(self):
        expected = {
            "reversed_phase", "normal_phase", "hilic", "ion_exchange",
            "ion_pair", "size_exclusion", "mixed_mode",
        }
        assert set(RETENTION_MECHANISMS.keys()) == expected

    def test_infer_mechanism_c18(self):
        assert infer_mechanism_from_column("C18") == "reversed_phase"

    def test_infer_mechanism_hilic(self):
        assert infer_mechanism_from_column("HILIC") == "hilic"

    def test_infer_mechanism_nh2(self):
        assert infer_mechanism_from_column("NH2") == "hilic"

    def test_infer_mechanism_silica(self):
        assert infer_mechanism_from_column("silica") == "normal_phase"

    def test_infer_mechanism_scx(self):
        assert infer_mechanism_from_column("SCX") == "ion_exchange"

    def test_infer_mechanism_sec(self):
        assert infer_mechanism_from_column("SEC") == "size_exclusion"

    def test_infer_mechanism_unknown_defaults_rp(self):
        assert infer_mechanism_from_column("unknown_type") == "reversed_phase"

    def test_infer_mechanism_none(self):
        assert infer_mechanism_from_column(None) == "reversed_phase"

    def test_get_mechanism_for_column(self):
        m = get_mechanism_for_column("C18")
        assert m.key == "reversed_phase"
        assert "C18" in m.column_types


class TestRetentionModels:
    def test_all_models_defined(self):
        expected = {
            "lss", "quadratic", "jandera", "polarity", "pirm",
            "ml_trained", "empirical", "lss_fit", "iex_retention", "sec_no_retention",
        }
        assert set(RETENTION_MODELS.keys()) == expected

    def test_lss_equation(self):
        assert "log k" in RETENTION_MODELS["lss"].equation

    def test_quadratic_equation(self):
        assert "a·φ²" in RETENTION_MODELS["quadratic"].equation

    def test_jandera_equation(self):
        assert "(1 + b·φ)^n" in RETENTION_MODELS["jandera"].equation

    def test_polarity_equation(self):
        assert "2.068" in RETENTION_MODELS["polarity"].equation

    def test_models_for_rp(self):
        models = get_models_for_mechanism("reversed_phase")
        assert "lss" in models
        assert "quadratic" in models
        assert "pirm" in models

    def test_sec_has_no_retention_model(self):
        models = get_models_for_mechanism("size_exclusion")
        assert "sec_no_retention" in models
        assert "lss" not in models

    def test_iex_has_own_model(self):
        models = get_models_for_mechanism("ion_exchange")
        assert "iex_retention" in models
        assert "lss" not in models


class TestAutoSelection:
    def test_pirm_when_column_id(self):
        model = auto_select_model(
            column_type="C18", column_id="some_col_id",
            has_calibration=False, has_known_compounds=False,
            has_ml_model=False, percent_b_range=90,
        )
        assert model == "pirm"

    def test_ml_when_model_exists(self):
        model = auto_select_model(
            column_type="C18", column_id=None,
            has_calibration=True, has_known_compounds=False,
            has_ml_model=True, percent_b_range=90,
        )
        assert model == "ml_trained"

    def test_lss_fit_with_calibration(self):
        model = auto_select_model(
            column_type="C18", column_id=None,
            has_calibration=True, has_known_compounds=False,
            has_ml_model=False, percent_b_range=30,
        )
        assert model == "lss_fit"

    def test_quadratic_for_wide_range_with_calibration(self):
        model = auto_select_model(
            column_type="C18", column_id=None,
            has_calibration=True, has_known_compounds=False,
            has_ml_model=False, percent_b_range=50,
        )
        assert model == "quadratic"

    def test_empirical_with_known_compounds(self):
        model = auto_select_model(
            column_type="C18", column_id=None,
            has_calibration=False, has_known_compounds=True,
            has_ml_model=False, percent_b_range=30,
        )
        assert model == "empirical"

    def test_polarity_for_wide_range_no_calibration(self):
        model = auto_select_model(
            column_type="C18", column_id=None,
            has_calibration=False, has_known_compounds=False,
            has_ml_model=False, percent_b_range=50,
        )
        assert model == "polarity"

    def test_default_lss(self):
        model = auto_select_model(
            column_type="C18", column_id=None,
            has_calibration=False, has_known_compounds=False,
            has_ml_model=False, percent_b_range=30,
        )
        assert model == "lss"

    def test_sec_mechanism(self):
        model = auto_select_model(
            column_type="SEC", column_id=None,
            has_calibration=False, has_known_compounds=False,
            has_ml_model=False, percent_b_range=0,
        )
        assert model == "sec_no_retention"

    def test_iex_mechanism(self):
        model = auto_select_model(
            column_type="SCX", column_id=None,
            has_calibration=False, has_known_compounds=False,
            has_ml_model=False, percent_b_range=0,
        )
        assert model == "iex_retention"

    def test_hilic_pirm(self):
        model = auto_select_model(
            column_type="HILIC", column_id="hilic_col",
            has_calibration=False, has_known_compounds=False,
            has_ml_model=False, percent_b_range=90,
        )
        assert model == "pirm"


class TestQuadraticModel:
    def test_predict_rt_basic(self):
        params = heuristic_quadratic_params(logp=2.0, mw=200, t0=60)
        table = [
            {"time_s": 0, "percent_b": 5},
            {"time_s": 60, "percent_b": 5},
            {"time_s": 1200, "percent_b": 95},
            {"time_s": 1320, "percent_b": 95},
        ]
        rt = predict_rt_quadratic(params, table, flow_rate_ml_min=0.4)
        assert rt > 60
        assert rt < 1400

    def test_predict_rt_with_dwell(self):
        params = heuristic_quadratic_params(logp=2.0, mw=200, t0=60)
        table = [
            {"time_s": 0, "percent_b": 5},
            {"time_s": 1200, "percent_b": 95},
        ]
        rt_no_dwell = predict_rt_quadratic(params, table, flow_rate_ml_min=0.4)
        rt_with_dwell = predict_rt_quadratic(
            params, table, flow_rate_ml_min=0.4, dwell_volume_ml=0.5,
        )
        # With dwell volume, RT should be later (gradient arrives later)
        assert rt_with_dwell >= rt_no_dwell

    def test_heuristic_params_reasonable(self):
        params = heuristic_quadratic_params(logp=3.0, mw=300, t0=60)
        assert params.s > 0
        assert params.log_kw > 0
        assert abs(params.a_quad) < 1.0  # quadratic term should be small


class TestJanderaModel:
    def test_predict_rt_basic(self):
        params = heuristic_jandera_params(logp=2.0, mw=200, t0=60)
        table = [
            {"time_s": 0, "percent_b": 5},
            {"time_s": 60, "percent_b": 5},
            {"time_s": 1200, "percent_b": 95},
            {"time_s": 1320, "percent_b": 95},
        ]
        rt = predict_rt_jandera(params, table, flow_rate_ml_min=0.4)
        assert rt > 60
        assert rt < 1400

    def test_heuristic_params_reasonable(self):
        params = heuristic_jandera_params(logp=3.0, mw=300, t0=60)
        assert params.a_jan > 0
        assert params.b_jan > 0
        assert params.n_jan > 0


class TestPolarityModel:
    def test_predict_rt_basic(self):
        params = heuristic_polarity_params(logp=2.0, t0=60)
        table = [
            {"time_s": 0, "percent_b": 5},
            {"time_s": 60, "percent_b": 5},
            {"time_s": 1200, "percent_b": 95},
            {"time_s": 1320, "percent_b": 95},
        ]
        rt = predict_rt_polarity(params, table, flow_rate_ml_min=0.4)
        assert rt > 60
        assert rt < 1400

    def test_polarity_uses_ln_convention(self):
        """The polarity model uses ln, not log10 (Eq 6.31)."""
        params = heuristic_polarity_params(logp=0.0, t0=60)
        # ln_k0 should be in natural log units
        assert params.ln_k0 > 0

    def test_heuristic_params_convert_logp_to_ln(self):
        """logP is log10; ln_k0 should be in ln units."""
        params = heuristic_polarity_params(logp=2.0, t0=60)
        # ln(10) * 2 * 0.5 + 1 = 1.1513 + 1 = 2.1513
        assert abs(params.ln_k0 - (math.log(10) * 2 * 0.5 + 1.0)) < 0.01

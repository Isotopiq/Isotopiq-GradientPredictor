"""Unit tests for LSS gradient simulation."""
from __future__ import annotations

import pytest

from app.core.lss.chromatogram import (
    Peak,
    default_peak_width,
    gaussian,
    resolution,
    simulate_chromatogram,
)
from app.core.lss.gradient_sim import (
    CalibrationRun,
    fit_lss,
    heuristic_lss_params,
    predict_rt_from_gradient,
    predict_rt_lss,
)


class TestLSS:
    def test_heuristic_params(self):
        params = heuristic_lss_params(logp=3.0)
        assert params.s > 0
        assert params.log_k0 > 0
        assert params.t0 > 0

    def test_predict_rt_isocratic(self):
        params = heuristic_lss_params(logp=2.0, t0=60.0)
        run = CalibrationRun(gradient_time_s=0, phi_start=0.3, phi_end=0.3, observed_rt_s=0)
        rt = predict_rt_lss(params, run)
        assert rt > 60.0  # must elute after void

    def test_predict_rt_gradient(self):
        params = heuristic_lss_params(logp=2.0, t0=60.0)
        run = CalibrationRun(gradient_time_s=1200, phi_start=0.05, phi_end=0.95, observed_rt_s=0)
        rt = predict_rt_lss(params, run)
        assert rt > 60.0
        assert rt < 1260.0  # should elute during or near end of gradient

    def test_fit_lss_with_two_runs(self):
        params_true = heuristic_lss_params(logp=3.0, t0=60.0)
        run1 = CalibrationRun(gradient_time_s=600, phi_start=0.05, phi_end=0.95, observed_rt_s=0)
        run2 = CalibrationRun(gradient_time_s=1200, phi_start=0.05, phi_end=0.95, observed_rt_s=0)
        rt1 = predict_rt_lss(params_true, run1)
        rt2 = predict_rt_lss(params_true, run2)
        run1.observed_rt_s = rt1
        run2.observed_rt_s = rt2
        fitted = fit_lss([run1, run2], t0=60.0)
        # Fitted should predict close to observed
        pred1 = predict_rt_lss(fitted, run1)
        pred2 = predict_rt_lss(fitted, run2)
        assert abs(pred1 - rt1) < 30.0
        assert abs(pred2 - rt2) < 30.0

    def test_fit_lss_needs_two_runs(self):
        with pytest.raises(ValueError):
            fit_lss([CalibrationRun(600, 0.05, 0.95, 300)], t0=60.0)

    def test_predict_from_gradient_table(self):
        params = heuristic_lss_params(logp=2.0)
        table = [
            {"time_s": 0.0, "percent_b": 5.0},
            {"time_s": 60.0, "percent_b": 5.0},
            {"time_s": 1200.0, "percent_b": 95.0},
            {"time_s": 1320.0, "percent_b": 95.0},
        ]
        rt = predict_rt_from_gradient(params, table, flow_rate_ml_min=0.4)
        assert rt > 0


class TestChromatogram:
    def test_gaussian(self):
        val = gaussian(5.0, center=5.0, width=4.0, height=1.0)
        assert val == pytest.approx(1.0, abs=0.01)

    def test_gaussian_off_center(self):
        val = gaussian(100.0, center=5.0, width=4.0, height=1.0)
        assert val < 0.001

    def test_simulate_chromatogram(self):
        peaks = [Peak(rt_s=300, width_s=10, height=1.0, label="A")]
        result = simulate_chromatogram(peaks, total_time_s=600, n_points=100)
        assert len(result["times"]) == 100
        assert len(result["intensities"]) == 100
        assert max(result["intensities"]) > 0.5  # peak should be visible

    def test_default_peak_width(self):
        w = default_peak_width(300.0)
        assert w > 0

    def test_resolution(self):
        rs = resolution(300, 10, 320, 10)
        assert rs > 1.0  # well separated

    def test_resolution_overlapping(self):
        rs = resolution(300, 10, 302, 10)
        assert rs < 0.5

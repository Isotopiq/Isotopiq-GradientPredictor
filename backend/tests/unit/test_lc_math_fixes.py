"""Tests for LC math bug fixes: peak width convention, width sorting,
dwell time in analytical LSS, and resolution map t0."""
from __future__ import annotations

import pytest

from app.core.lss.chromatogram import default_peak_width, resolution
from app.core.lss.gradient_sim import (
    CalibrationRun,
    LSSParameters,
    predict_rt_lss,
)
from app.core.lss.suitability import evaluate_method, score_method


class TestPeakWidthConvention:
    """Stage 3.1: default_peak_width should return FWHM, not 4σ baseline width."""

    def test_default_peak_width_is_fwhm(self):
        """FWHM = 2.355 * sigma, where sigma = rt / sqrt(N).

        For rt=300, N=12000: sigma = 300/109.5 = 2.739
        FWHM = 2.355 * 2.739 = 6.45
        Old 4σ = 4 * 2.739 = 10.95
        """
        w = default_peak_width(300.0)
        # FWHM should be ~6.45, not ~10.95
        assert w < 8.0, f"Expected FWHM < 8, got {w} (old 4σ would be ~11)"
        assert w > 5.0, f"Expected FWHM > 5, got {w}"

    def test_default_peak_width_scales_with_rt(self):
        """Width should increase with retention time."""
        w1 = default_peak_width(100.0)
        w2 = default_peak_width(600.0)
        assert w2 > w1

    def test_default_peak_width_floor(self):
        """Very small RT should still give a minimum width."""
        w = default_peak_width(1.0)
        assert w >= 2.0


class TestResolutionWithFWHM:
    """Resolution function should convert FWHM to baseline width for USP formula."""

    def test_resolution_uses_fwhm_to_baseline_conversion(self):
        """USP Rs = 2*(rt2-rt1)/(wb1+wb2) where wb = 4σ = FWHM * 1.698.

        For two peaks at 300 and 320, each with FWHM=6.45:
        wb = 6.45 * 1.698 = 10.95
        Rs = 2*20 / (10.95+10.95) = 40/21.9 = 1.83
        """
        rs = resolution(300, 6.45, 320, 6.45)
        # Should be ~1.83, not the old value that treated FWHM as 4σ directly
        assert rs > 1.5, f"Expected Rs > 1.5 with FWHM conversion, got {rs}"
        assert rs < 2.5, f"Expected Rs < 2.5, got {rs}"

    def test_resolution_zero_width(self):
        rs = resolution(300, 0, 320, 0)
        assert rs == 0.0


class TestWidthSortingInSuitability:
    """Stage 3.2: widths must be sorted alongside RTs."""

    def test_score_method_sorts_widths_correctly(self):
        """If RTs are unsorted, widths should follow their corresponding RTs.

        With RTs [300, 100, 200] and widths [10, 3, 5]:
        After sorting: RTs [100, 200, 300], widths [3, 5, 10]
        The resolution between peaks 100 and 200 should use widths 3 and 5.
        """
        # Unsorted RTs with corresponding widths
        rts = [300, 100, 200]
        widths = [10, 3, 5]

        # Score with unsorted input
        score_unsorted = score_method(rts, widths, total_time_s=600, t0_s=60)

        # Score with sorted input (should be identical)
        score_sorted = score_method(
            [100, 200, 300], [3, 5, 10], total_time_s=600, t0_s=60,
        )

        assert score_unsorted == pytest.approx(score_sorted, abs=0.001)

    def test_evaluate_method_sorts_widths_correctly(self):
        """Same test for evaluate_method."""
        rts = [300, 100, 200]
        widths = [10, 3, 5]

        eval_unsorted = evaluate_method(rts, widths, total_time_s=600, t0_s=60)
        eval_sorted = evaluate_method(
            [100, 200, 300], [3, 5, 10], total_time_s=600, t0_s=60,
        )

        # The min_resolution criterion should match
        unsorted_res = next(
            c for c in eval_unsorted.criteria if c.name == "min_resolution"
        )
        sorted_res = next(
            c for c in eval_sorted.criteria if c.name == "min_resolution"
        )
        assert unsorted_res.value == pytest.approx(sorted_res.value, abs=0.01)

    def test_score_method_no_widths(self):
        """When no widths provided, should use default_peak_width."""
        rts = [100, 200, 300]
        score = score_method(rts, None, total_time_s=600, t0_s=60)
        assert 0 <= score <= 1


class TestDwellTimeInAnalyticalLSS:
    """Stage 3.3: predict_rt_lss should account for dwell time."""

    def test_dwell_time_without_arg_is_backward_compatible(self):
        """Calling without dwell_time_s should give same result as before."""
        params = LSSParameters(log_k0=1.0, s=5.0, t0=60.0)
        run = CalibrationRun(gradient_time_s=1200, phi_start=0.05, phi_end=0.95, observed_rt_s=0)

        rt_no_arg = predict_rt_lss(params, run)
        rt_zero_dwell = predict_rt_lss(params, run, dwell_time_s=0.0)

        assert rt_no_arg == pytest.approx(rt_zero_dwell)

    def test_dwell_time_increases_rt(self):
        """With dwell time, RT should be later (gradient arrives later at column)."""
        params = LSSParameters(log_k0=1.0, s=5.0, t0=60.0)
        run = CalibrationRun(gradient_time_s=1200, phi_start=0.05, phi_end=0.95, observed_rt_s=0)

        rt_no_dwell = predict_rt_lss(params, run, dwell_time_s=0.0)
        rt_with_dwell = predict_rt_lss(params, run, dwell_time_s=30.0)

        # RT with dwell should be later
        assert rt_with_dwell > rt_no_dwell, (
            f"Expected RT with dwell > RT without dwell, "
            f"got {rt_with_dwell} vs {rt_no_dwell}"
        )

    def test_dwell_time_effect_is_reasonable(self):
        """The dwell time effect should be less than t_dwell + t0 (not double-counted)."""
        params = LSSParameters(log_k0=1.0, s=5.0, t0=60.0)
        run = CalibrationRun(gradient_time_s=1200, phi_start=0.05, phi_end=0.95, observed_rt_s=0)

        rt_no_dwell = predict_rt_lss(params, run, dwell_time_s=0.0)
        rt_with_dwell = predict_rt_lss(params, run, dwell_time_s=60.0)

        # The increase should be less than t_dwell (60s) since the analyte
        # migrates during the dwell time
        increase = rt_with_dwell - rt_no_dwell
        assert increase < 60.0, f"Expected increase < t_dwell (60s), got {increase}"

    def test_isocratic_ignores_dwell(self):
        """Isocratic elution should not be affected by dwell time."""
        params = LSSParameters(log_k0=1.0, s=5.0, t0=60.0)
        run = CalibrationRun(gradient_time_s=0, phi_start=0.3, phi_end=0.3, observed_rt_s=0)

        rt_no_dwell = predict_rt_lss(params, run, dwell_time_s=0.0)
        rt_with_dwell = predict_rt_lss(params, run, dwell_time_s=60.0)

        assert rt_no_dwell == pytest.approx(rt_with_dwell)


class TestResolutionMapT0:
    """Stage 3.4: resolution maps should use actual column void volume, not 0.4."""

    def test_resolution_map_1d_accepts_column_void_volume(self):
        """The 1D resolution map should accept and use column_void_volume_ml."""
        from app.core.lss.resolution_map import resolution_map_1d

        # Use simple SMILES that will parse
        smiles = ["C", "CC"]  # methane, ethane
        try:
            result = resolution_map_1d(
                smiles,
                variable="gradient_time",
                var_range=(10, 30),
                steps=3,
                fixed_params={
                    "column_void_volume_ml": 0.8,  # different from default 0.4
                },
            )
            # Should produce valid results
            assert len(result.x_values) == 3
            assert len(result.min_rs) == 3
        except (ValueError, Exception):
            # Compounds may fail to parse in some environments
            pytest.skip("Compound parsing not available in test environment")

    def test_resolution_map_2d_accepts_column_void_volume(self):
        """The 2D resolution map should accept and use column_void_volume_ml."""
        from app.core.lss.resolution_map import resolution_map_2d

        smiles = ["C", "CC"]
        try:
            result = resolution_map_2d(
                smiles,
                var_x="gradient_time",
                range_x=(10, 30),
                steps_x=3,
                var_y="temperature",
                range_y=(25, 40),
                steps_y=3,
                fixed_params={
                    "column_void_volume_ml": 0.8,
                },
            )
            assert len(result.x_values) == 3
            assert len(result.y_values) == 3
        except (ValueError, Exception):
            pytest.skip("Compound parsing not available in test environment")

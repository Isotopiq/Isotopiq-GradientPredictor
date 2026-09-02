"""Linear Solvent Strength (LSS) gradient simulation.

LSS model (Snyder): log k = log k0 - S * phi
where phi is the fraction of strong solvent (%B/100), k0 is the retention
factor at phi=0, and S is the solvent strength parameter.

For a linear gradient from phi0 to phi1 over time tG, the retention factor
at elution k_e and retention time tR can be approximated by:

  tR = t0 * (1 + (1/B) * log(1 + B * k0_eff))   ... (gradient elution)

where B = S * delta_phi * t0 / tG and k0_eff = k at gradient start.

With 2+ calibration runs at different gradient times, S and k0 can be
estimated. Without calibration, we fall back to a heuristic from logP.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LSSParameters:
    """LSS model parameters for a compound on a given column/method."""

    log_k0: float  # log10(k) at phi=0
    s: float  # solvent strength slope
    t0: float  # column dead time (s), = column_volume / flow


@dataclass
class CalibrationRun:
    gradient_time_s: float
    phi_start: float  # fraction (0-1)
    phi_end: float  # fraction (0-1)
    observed_rt_s: float


def fit_lss(
    runs: list[CalibrationRun], t0: float = 60.0
) -> LSSParameters:
    """Estimate LSS S and log k0 from >=2 calibration runs at different gradient times.

    Uses a simple grid/analytic approach: for a linear gradient,
    tR ≈ t0 + (tG / (S * dphi)) * log10(1 + k0 * S * dphi * t0 / tG * 10^(-S*phi0))
    We solve for (log_k0, S) by least-squares over the runs.
    """
    if len(runs) < 2:
        raise ValueError("Need at least 2 calibration runs to fit LSS parameters")

    # Simple 2D grid search (good enough for a starting estimate)
    best_err = float("inf")
    best = LSSParameters(log_k0=1.0, s=5.0, t0=t0)

    log_k0_grid = [x * 0.25 for x in range(-20, 61)]  # -5 .. 15
    s_grid = [x * 0.5 for x in range(2, 41)]  # 1 .. 20

    for log_k0 in log_k0_grid:
        for s in s_grid:
            err = 0.0
            for r in runs:
                pred = predict_rt_lss(LSSParameters(log_k0=log_k0, s=s, t0=t0), r)
                err += (pred - r.observed_rt_s) ** 2
            if err < best_err:
                best_err = err
                best = LSSParameters(log_k0=log_k0, s=s, t0=t0)

    return best


def predict_rt_lss(params: LSSParameters, run: CalibrationRun) -> float:
    """Predict retention time for a given gradient run using LSS."""
    dphi = run.phi_end - run.phi_start
    if dphi <= 0:
        # Isocratic
        k = 10 ** (params.log_k0 - params.s * run.phi_start)
        return params.t0 * (1 + k)

    tG = run.gradient_time_s
    b = params.s * dphi * params.t0 / tG
    k0_eff = 10 ** (params.log_k0 - params.s * run.phi_start)
    # Gradient elution equation (Snyder)
    tR = params.t0 * (1 + (1.0 / b) * math.log10(1 + b * k0_eff))
    return tR


def heuristic_lss_params(logp: float, t0: float = 60.0) -> LSSParameters:
    """Heuristic LSS parameters from logP (no calibration data).

    S typically 4-10 for small molecules; log_k0 correlates loosely with logP.
    """
    s = 4.0 + max(0.0, logp) * 0.8
    log_k0 = 0.5 + max(0.0, logp) * 0.6
    return LSSParameters(log_k0=log_k0, s=min(s, 15.0), t0=t0)


def predict_rt_from_gradient(
    params: LSSParameters,
    gradient_table: list[dict],
    flow_rate_ml_min: float = 0.4,
    column_void_volume_ml: float = 0.4,
) -> float:
    """Predict RT for an arbitrary (possibly multi-segment) gradient.

    gradient_table: list of {time_s, percent_b} points (piecewise linear).
    """
    t0 = 60.0 * column_void_volume_ml / max(flow_rate_ml_min, 0.01)
    params_t0 = LSSParameters(log_k0=params.log_k0, s=params.s, t0=t0)

    # Convert to a single linear-gradient approximation using the steepest segment
    if not gradient_table:
        return t0

    # Find the main ramp segment (largest %B change)
    best_seg = None
    best_dphi = -1.0
    for i in range(len(gradient_table) - 1):
        p0 = gradient_table[i]
        p1 = gradient_table[i + 1]
        dphi = abs(p1["percent_b"] - p0["percent_b"]) / 100.0
        if dphi > best_dphi:
            best_dphi = dphi
            best_seg = (p0, p1)

    if best_seg is None or best_dphi <= 0:
        # Isocratic at the first point
        phi = gradient_table[0]["percent_b"] / 100.0
        k = 10 ** (params_t0.log_k0 - params_t0.s * phi)
        return t0 * (1 + k)

    p0, p1 = best_seg
    run = CalibrationRun(
        gradient_time_s=p1["time_s"] - p0["time_s"],
        phi_start=p0["percent_b"] / 100.0,
        phi_end=p1["percent_b"] / 100.0,
        observed_rt_s=0.0,
    )
    return p0["time_s"] + predict_rt_lss(params_t0, run)

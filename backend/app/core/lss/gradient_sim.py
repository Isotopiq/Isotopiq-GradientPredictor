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


def heuristic_lss_params(
    logp: float,
    t0: float = 60.0,
    mw: float = 200.0,
    tpsa: float = 0.0,
    hbd: int = 0,
    hba: int = 0,
    column_type: str = "C18",
) -> LSSParameters:
    """Heuristic LSS parameters from molecular descriptors (no calibration data).

    LSS model: log k = log_k0 - S * phi
    where phi = fraction of strong solvent (%B/100).

    Parameters are estimated from multiple physicochemical descriptors:
    - logP: primary driver of hydrophobic retention (higher → more retention)
    - MW: larger molecules have higher S (solvent strength slope)
    - TPSA: polar surface area reduces retention (HILIC exception)
    - HBD/HBA: H-bonding reduces RP retention via water interaction

    Column type modulates the model:
    - C18: standard RP, strongest hydrophobic retention
    - C8: less retentive RP (shorter chain → lower log_k0)
    - C4: weak RP (short chain → much lower log_k0)
    - phenyl: RP with π-π selectivity (aromatic compounds retained more)
    - PFP: RP with dipole/π selectivity (polarizable compounds retained more)
    - HILIC: opposite mechanism — polar compounds retained more
    - ion_pair: charged compounds retained via ion pairing
    """
    # S (solvent strength slope): typically 4-10 for small molecules.
    # S increases with molecular size (larger molecules are more sensitive
    # to changes in mobile phase composition).
    s = 4.0 + (mw / 200.0) * 1.5 + max(0.0, logp) * 0.5
    s = min(s, 15.0)

    # log_k0 (retention at phi=0, i.e. 100% water):
    # Base from logP, reduced by polarity (TPSA, H-bond donors/acceptors).
    tpsa_penalty = (tpsa / 50.0) * 0.3
    hbd_penalty = hbd * 0.15
    hba_penalty = hba * 0.08

    log_k0 = 0.5 + max(0.0, logp) * 0.6 - tpsa_penalty - hbd_penalty - hba_penalty

    # --- Column-type-specific modulation ---
    col = column_type.lower().strip()

    if col == "hilic":
        # HILIC: opposite retention — polar compounds retained MORE.
        # Invert the polarity penalties into bonuses, and reduce logP contribution.
        log_k0 = 0.3 + (tpsa / 50.0) * 0.4 + hbd * 0.2 + hba * 0.1 + max(0.0, logp) * 0.1
        s = 3.0 + (mw / 200.0) * 1.0  # HILIC gradients are gentler
    elif col in ("c4", "butyl"):
        # Short-chain RP: much less retentive than C18
        log_k0 *= 0.5
        s *= 0.8
    elif col in ("c8", "octyl"):
        # Medium-chain RP: less retentive than C18
        log_k0 *= 0.7
        s *= 0.9
    elif col in ("phenyl", "phenylhexyl"):
        # Phenyl: π-π interactions increase retention of aromatic compounds.
        # We approximate "aromaticity" via logP contribution (aromatic compounds
        # tend to have higher logP). Add a bonus for moderate-to-high logP.
        log_k0 += max(0.0, logp) * 0.15
    elif col in ("pfp", "pentafluorophenyl"):
        # PFP: dipole/π selectivity — retains polarizable and halogenated compounds.
        # Add bonus for H-bond acceptors (dipole interaction) and moderate polarity.
        log_k0 += hba * 0.12 + (tpsa / 100.0) * 0.2
    elif col in ("ion_pair", "ionpair"):
        # Ion-pairing: charged compounds (ionized at method pH) are retained.
        # We approximate via HBD/HBA (ionizable groups tend to have these).
        log_k0 += hbd * 0.3 + hba * 0.15
        s += 1.0
    elif col in ("c18", "ods", "octadecyl"):
        # Standard C18 — base model, no modulation needed
        pass

    # Floor log_k0 so very polar compounds still have some retention
    log_k0 = max(-1.0, log_k0)

    return LSSParameters(log_k0=log_k0, s=s, t0=t0)


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

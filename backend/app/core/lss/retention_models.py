"""Retention mechanism and model registry.

Defines all supported retention mechanisms (RP, NP, HILIC, IEX, ion-pair, SEC,
mixed-mode) and retention models (LSS, Quadratic, Jandera, Polarity, PIRM, ML,
Empirical, LSS Fit) with auto-selection logic based on available parameters.

Equations verified against the Gradient LC Math Reference PDF
(García-Álvarez-Coque, HPLC 2013 Amsterdam):
  - LSS model:        Eq 6.4   log k = log k_w - S·φ
  - Quadratic model:  Eq 6.198 log k = log k_w - S·φ + a·φ²
  - Jandera model:    Eq 6.20  k = a / (1 + b·φ)^n
  - Polarity model:   Eq 6.31  ln k = ln k_0 - 2.068·φ + 1.341·φ²
  - Gradient eq:      Eq 6.13  t_g = t_0 + ∫₀^(t_g-t_0) [1/k(φ(t_c))] dt_c
  - LSS analytical:   Eq 6.17  t_g = (1/(m·S))·log(b+1) + t_0
  - LSS + dwell:      Eq 6.19  t_g = (1/(m·S))·log(k_0·b·10^(-b·t_d/t_0)+1) + t_0 + t_d
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Retention Mechanisms
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetentionMechanism:
    """A chromatographic retention mechanism."""
    key: str
    label: str
    description: str
    column_types: tuple[str, ...]
    solvent_model: str  # "organic_modifier" | "aqueous_fraction" | "salt_gradient" | "isocratic"


RETENTION_MECHANISMS: dict[str, RetentionMechanism] = {
    "reversed_phase": RetentionMechanism(
        key="reversed_phase",
        label="Reversed-Phase (RP)",
        description="Hydrophobic interaction — nonpolar stationary phase, polar mobile phase. "
                    "Most common LC mechanism. Retention increases with analyte hydrophobicity.",
        column_types=("C18", "C8", "C4", "phenyl", "PFP", "CN"),
        solvent_model="organic_modifier",
    ),
    "normal_phase": RetentionMechanism(
        key="normal_phase",
        label="Normal-Phase (NP)",
        description="Polar stationary phase, nonpolar mobile phase. Retention increases "
                    "with analyte polarity. Used for lipids, fat-soluble vitamins.",
        column_types=("silica", "alumina", "NH2_NP", "CN_NP", "diol"),
        solvent_model="organic_modifier",
    ),
    "hilic": RetentionMechanism(
        key="hilic",
        label="HILIC",
        description="Hydrophilic interaction chromatography — polar analytes retained on "
                    "polar stationary phase via water-rich layer. Good for sugars, "
                    "nucleotides, polar metabolites.",
        column_types=("HILIC", "NH2", "amide", "zic_hilic"),
        solvent_model="aqueous_fraction",
    ),
    "ion_exchange": RetentionMechanism(
        key="ion_exchange",
        label="Ion-Exchange (IEX)",
        description="Retention by electrostatic interaction between charged analytes and "
                    "oppositely charged stationary phase. Elution by salt gradient.",
        column_types=("SCX", "SAX", "WCX", "WAX"),
        solvent_model="salt_gradient",
    ),
    "ion_pair": RetentionMechanism(
        key="ion_pair",
        label="Ion-Pair Chromatography",
        description="RP with ion-pair reagent (e.g. TFA, HFBA) for charged analytes. "
                    "Combines RP separation with ionic retention.",
        column_types=("ion_pair",),
        solvent_model="organic_modifier",
    ),
    "size_exclusion": RetentionMechanism(
        key="size_exclusion",
        label="Size-Exclusion (SEC)",
        description="Separation by molecular size — no retention model. Large molecules "
                    "elute first (less access to pores). Used for polymers, proteins.",
        column_types=("SEC", "gel_filtration"),
        solvent_model="isocratic",
    ),
    "mixed_mode": RetentionMechanism(
        key="mixed_mode",
        label="Mixed-Mode",
        description="Combined RP + IEX selectivity on a single column. Useful for "
                    "charged and neutral compounds in one run.",
        column_types=("mixed_mode", "MM_RP_IEX"),
        solvent_model="organic_modifier",
    ),
}


# ---------------------------------------------------------------------------
# Retention Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetentionModel:
    """A mathematical retention model."""
    key: str
    label: str
    equation: str
    applicable_mechanisms: tuple[str, ...]
    requires: str
    reference: str
    # Whether this model is fully implemented (vs. "coming soon")
    implemented: bool = True


RETENTION_MODELS: dict[str, RetentionModel] = {
    "lss": RetentionModel(
        key="lss",
        label="Linear Solvent Strength (LSS / Snyder)",
        equation="log k = log k_w - S·φ",
        applicable_mechanisms=("reversed_phase", "normal_phase", "hilic", "ion_pair"),
        requires="logP + MW (heuristic) or calibration runs (fit)",
        reference="Snyder & Dolan, 2007. Eq 6.4 in reference PDF",
    ),
    "quadratic": RetentionModel(
        key="quadratic",
        label="Quadratic log k model",
        equation="log k = log k_w - S·φ + a·φ²",
        applicable_mechanisms=("reversed_phase", "normal_phase"),
        requires="≥3 calibration runs across wide %B range",
        reference="Eq 6.198 in reference PDF — better for wide %B ranges",
    ),
    "jandera": RetentionModel(
        key="jandera",
        label="Jandera model",
        equation="k = a / (1 + b·φ)^n",
        applicable_mechanisms=("normal_phase", "reversed_phase"),
        requires="≥3 calibration runs",
        reference="Eq 6.20 in reference PDF — originally for NPLC",
    ),
    "polarity": RetentionModel(
        key="polarity",
        label="Polarity model",
        equation="ln k = ln k_0 - 2.068·φ + 1.341·φ²",
        applicable_mechanisms=("reversed_phase",),
        requires="No calibration — uses universal coefficients",
        reference="Eq 6.31 in reference PDF — empirical universal model",
    ),
    "pirm": RetentionModel(
        key="pirm",
        label="Physics-Informed Retention Model (PIRM)",
        equation="LSS with stationary-phase composition terms",
        applicable_mechanisms=("reversed_phase", "hilic"),
        requires="Commercial column ID (stationary phase data)",
        reference="Snyder, Dolan, Carr, Neue regression",
    ),
    "ml_trained": RetentionModel(
        key="ml_trained",
        label="ML-Trained Model",
        equation="Learned model (column_type + method_signature)",
        applicable_mechanisms=("reversed_phase", "hilic", "ion_pair"),
        requires="Trained model exists for this column type",
        reference="Custom ML model trained on historical data",
    ),
    "empirical": RetentionModel(
        key="empirical",
        label="Empirical Equation (from known compounds)",
        equation="RT = a + b·logP + c·TPSA + ... (MLR)",
        applicable_mechanisms=("reversed_phase", "hilic", "ion_pair"),
        requires="≥5 compounds with known RT",
        reference="Multiple linear regression on molecular descriptors",
    ),
    "lss_fit": RetentionModel(
        key="lss_fit",
        label="LSS Fit (from calibration runs)",
        equation="log k = log k_w - S·φ (fitted S, k_w)",
        applicable_mechanisms=("reversed_phase", "normal_phase", "hilic", "ion_pair"),
        requires="≥2 gradient calibration runs",
        reference="Snyder & Dolan, 2007. Eq 6.4 fitted to calibration data",
    ),
    # IEX and SEC don't use solvent-strength models
    "iex_retention": RetentionModel(
        key="iex_retention",
        label="Ion-Exchange Retention",
        equation="log k = a - z·log[I] (linear salt gradient)",
        applicable_mechanisms=("ion_exchange",),
        requires="Salt concentration and analyte charge",
        reference="Standard IEX model — retention decreases with ionic strength",
    ),
    "sec_no_retention": RetentionModel(
        key="sec_no_retention",
        label="Size-Exclusion (no retention model)",
        equation="RT = t_0 (size-based separation, no k)",
        applicable_mechanisms=("size_exclusion",),
        requires="Column void volume only",
        reference="SEC separates by size, not retention factor",
    ),
}


# ---------------------------------------------------------------------------
# Column type → mechanism mapping
# ---------------------------------------------------------------------------

_COLUMN_MECHANISM_MAP: dict[str, str] = {
    # RP
    "c18": "reversed_phase",
    "ods": "reversed_phase",
    "octadecyl": "reversed_phase",
    "c8": "reversed_phase",
    "octyl": "reversed_phase",
    "c4": "reversed_phase",
    "butyl": "reversed_phase",
    "phenyl": "reversed_phase",
    "phenylhexyl": "reversed_phase",
    "pfp": "reversed_phase",
    "pentafluorophenyl": "reversed_phase",
    "cn": "reversed_phase",  # CN can be RP or NP
    # NP
    "silica": "normal_phase",
    "alumina": "normal_phase",
    "nh2_np": "normal_phase",
    "cn_np": "normal_phase",
    "diol": "normal_phase",
    # HILIC
    "hilic": "hilic",
    "nh2": "hilic",
    "amide": "hilic",
    "zic_hilic": "hilic",
    # IEX
    "scx": "ion_exchange",
    "sax": "ion_exchange",
    "wcx": "ion_exchange",
    "wax": "ion_exchange",
    # Ion-pair
    "ion_pair": "ion_pair",
    "ionpair": "ion_pair",
    # SEC
    "sec": "size_exclusion",
    "gel_filtration": "size_exclusion",
    # Mixed-mode
    "mixed_mode": "mixed_mode",
    "mm_rp_iex": "mixed_mode",
}


def infer_mechanism_from_column(column_type: str | None) -> str:
    """Infer the retention mechanism from the column type.

    Returns the mechanism key (e.g. "reversed_phase") or "reversed_phase"
    as default if the column type is unknown.
    """
    if not column_type:
        return "reversed_phase"
    key = column_type.lower().strip()
    return _COLUMN_MECHANISM_MAP.get(key, "reversed_phase")


# ---------------------------------------------------------------------------
# Auto-selection
# ---------------------------------------------------------------------------

def auto_select_model(
    column_type: str | None,
    column_id: str | None,
    has_calibration: bool,
    has_known_compounds: bool,
    has_ml_model: bool,
    percent_b_range: float,
    mechanism: str | None = None,
) -> str:
    """Auto-select the best retention model based on available parameters.

    Args:
        column_type: The column type string (e.g. "C18", "HILIC").
        column_id: Commercial column ID if a commercial column is selected.
        has_calibration: Whether calibration runs are available.
        has_known_compounds: Whether ≥5 known compounds with RT are available.
        has_ml_model: Whether a trained ML model exists for this column type.
        percent_b_range: The %B range (end - start) of the gradient.
        mechanism: Override mechanism; if None, inferred from column_type.

    Returns:
        The model key (e.g. "pirm", "lss", "quadratic").
    """
    # 1. Determine mechanism from column type
    if mechanism is None:
        mechanism = infer_mechanism_from_column(column_type)

    # SEC and IEX have their own models
    if mechanism == "size_exclusion":
        return "sec_no_retention"
    if mechanism == "ion_exchange":
        return "iex_retention"

    # 2. If ML model exists for this column type → use it (highest confidence)
    if has_ml_model:
        return "ml_trained"

    # 3. If commercial column selected → PIRM
    if column_id and mechanism in ("reversed_phase", "hilic"):
        return "pirm"

    # 4. If calibration runs provided → LSS fit or quadratic
    if has_calibration:
        if percent_b_range > 40 and mechanism == "reversed_phase":
            return "quadratic"  # wide range needs quadratic
        return "lss_fit"

    # 5. If known compounds provided → empirical
    if has_known_compounds:
        return "empirical"

    # 6. If wide %B range and no calibration → polarity model (universal)
    if percent_b_range > 40 and mechanism == "reversed_phase":
        return "polarity"

    # 7. Default: heuristic LSS
    return "lss"


def get_models_for_mechanism(mechanism: str) -> list[str]:
    """Get the list of applicable model keys for a given mechanism."""
    return [
        key for key, model in RETENTION_MODELS.items()
        if mechanism in model.applicable_mechanisms
    ]


def get_mechanism_for_column(column_type: str | None) -> RetentionMechanism:
    """Get the RetentionMechanism object for a column type."""
    key = infer_mechanism_from_column(column_type)
    return RETENTION_MECHANISMS.get(key, RETENTION_MECHANISMS["reversed_phase"])


# ---------------------------------------------------------------------------
# Quadratic model implementation (Eq 6.198)
# ---------------------------------------------------------------------------

@dataclass
class QuadraticParams:
    """Parameters for the quadratic retention model: log k = log k_w - S·φ + a·φ²."""

    log_kw: float  # log10(k) at φ=0
    s: float       # linear solvent strength term
    a_quad: float  # quadratic term
    t0: float      # column dead time (s)


def predict_rt_quadratic(
    params: QuadraticParams,
    gradient_table: list[dict],
    flow_rate_ml_min: float = 0.4,
    dwell_volume_ml: float | None = None,
    dead_volume_ml: float | None = None,
) -> float:
    """Predict RT using the quadratic retention model via numerical integration.

    log k = log k_w - S·φ + a·φ²
    k = 10^(log_kw - S·φ + a·φ²)

    Uses the same numerical integration approach as the LSS model:
        tR = t0 + ∫ [1 / (1 + k(φ(t)))] dt

    Reference: Eq 6.198 in the Gradient LC Math Reference PDF.
    """
    if not gradient_table:
        return params.t0

    if dead_volume_ml is not None and dead_volume_ml > 0:
        t0 = 60.0 * dead_volume_ml / max(flow_rate_ml_min, 0.01)
    else:
        t0 = params.t0

    t_dwell = 0.0
    if dwell_volume_ml is not None and dwell_volume_ml > 0:
        t_dwell = 60.0 * dwell_volume_ml / max(flow_rate_ml_min, 0.01)

    total_time = gradient_table[-1]["time_s"]

    def phi_at(t: float) -> float:
        effective_t = t - t_dwell
        if effective_t <= gradient_table[0]["time_s"]:
            return gradient_table[0]["percent_b"] / 100.0
        for i in range(len(gradient_table) - 1):
            t0_i = gradient_table[i]["time_s"]
            t1_i = gradient_table[i + 1]["time_s"]
            if t0_i <= effective_t <= t1_i:
                p0 = gradient_table[i]["percent_b"] / 100.0
                p1 = gradient_table[i + 1]["percent_b"] / 100.0
                if t1_i == t0_i:
                    return p1
                frac = (effective_t - t0_i) / (t1_i - t0_i)
                return p0 + frac * (p1 - p0)
        return gradient_table[-1]["percent_b"] / 100.0

    dt = 0.5
    migration = 0.0
    t = 0.0

    while t < total_time + t0 * 2 + t_dwell:
        phi = phi_at(min(t, total_time + t_dwell))
        log_k = params.log_kw - params.s * phi + params.a_quad * phi * phi
        k = 10.0 ** log_k
        if k < 0.01:
            k = 0.01
        velocity = 1.0 / (t0 * (1.0 + k))
        migration += velocity * dt
        t += dt
        if migration >= 1.0:
            break

    if migration < 1.0:
        return total_time + t0 + t_dwell

    return round(t, 2)


# ---------------------------------------------------------------------------
# Jandera model implementation (Eq 6.20)
# ---------------------------------------------------------------------------

@dataclass
class JanderaParams:
    """Parameters for the Jandera retention model: k = a / (1 + b·φ)^n."""

    a_jan: float   # pre-factor
    b_jan: float   # solvent strength
    n_jan: float   # exponent
    t0: float      # column dead time (s)


def predict_rt_jandera(
    params: JanderaParams,
    gradient_table: list[dict],
    flow_rate_ml_min: float = 0.4,
    dwell_volume_ml: float | None = None,
    dead_volume_ml: float | None = None,
) -> float:
    """Predict RT using the Jandera retention model via numerical integration.

    k = a / (1 + b·φ)^n

    Uses numerical integration of the fundamental gradient equation.
    Reference: Eq 6.20 in the Gradient LC Math Reference PDF.
    """
    if not gradient_table:
        return params.t0

    if dead_volume_ml is not None and dead_volume_ml > 0:
        t0 = 60.0 * dead_volume_ml / max(flow_rate_ml_min, 0.01)
    else:
        t0 = params.t0

    t_dwell = 0.0
    if dwell_volume_ml is not None and dwell_volume_ml > 0:
        t_dwell = 60.0 * dwell_volume_ml / max(flow_rate_ml_min, 0.01)

    total_time = gradient_table[-1]["time_s"]

    def phi_at(t: float) -> float:
        effective_t = t - t_dwell
        if effective_t <= gradient_table[0]["time_s"]:
            return gradient_table[0]["percent_b"] / 100.0
        for i in range(len(gradient_table) - 1):
            t0_i = gradient_table[i]["time_s"]
            t1_i = gradient_table[i + 1]["time_s"]
            if t0_i <= effective_t <= t1_i:
                p0 = gradient_table[i]["percent_b"] / 100.0
                p1 = gradient_table[i + 1]["percent_b"] / 100.0
                if t1_i == t0_i:
                    return p1
                frac = (effective_t - t0_i) / (t1_i - t0_i)
                return p0 + frac * (p1 - p0)
        return gradient_table[-1]["percent_b"] / 100.0

    dt = 0.5
    migration = 0.0
    t = 0.0

    while t < total_time + t0 * 2 + t_dwell:
        phi = phi_at(min(t, total_time + t_dwell))
        denom = (1.0 + params.b_jan * phi) ** params.n_jan
        if denom < 0.01:
            denom = 0.01
        k = params.a_jan / denom
        if k < 0.01:
            k = 0.01
        velocity = 1.0 / (t0 * (1.0 + k))
        migration += velocity * dt
        t += dt
        if migration >= 1.0:
            break

    if migration < 1.0:
        return total_time + t0 + t_dwell

    return round(t, 2)


# ---------------------------------------------------------------------------
# Polarity model implementation (Eq 6.31)
# ---------------------------------------------------------------------------

# Universal coefficients from the reference PDF (Eq 6.31)
_POLARITY_COEF_LINEAR = -2.068
_POLARITY_COEF_QUAD = 1.341


@dataclass
class PolarityParams:
    """Parameters for the polarity model: ln k = ln k_0 - 2.068·φ + 1.341·φ²."""

    ln_k0: float  # ln(k) at φ=0
    t0: float     # column dead time (s)


def predict_rt_polarity(
    params: PolarityParams,
    gradient_table: list[dict],
    flow_rate_ml_min: float = 0.4,
    dwell_volume_ml: float | None = None,
    dead_volume_ml: float | None = None,
) -> float:
    """Predict RT using the polarity model via numerical integration.

    ln k = ln k_0 - 2.068·φ + 1.341·φ²
    k = exp(ln_k_0 - 2.068·φ + 1.341·φ²)

    Uses universal coefficients from the reference PDF (Eq 6.31).
    """
    if not gradient_table:
        return params.t0

    if dead_volume_ml is not None and dead_volume_ml > 0:
        t0 = 60.0 * dead_volume_ml / max(flow_rate_ml_min, 0.01)
    else:
        t0 = params.t0

    t_dwell = 0.0
    if dwell_volume_ml is not None and dwell_volume_ml > 0:
        t_dwell = 60.0 * dwell_volume_ml / max(flow_rate_ml_min, 0.01)

    total_time = gradient_table[-1]["time_s"]

    def phi_at(t: float) -> float:
        effective_t = t - t_dwell
        if effective_t <= gradient_table[0]["time_s"]:
            return gradient_table[0]["percent_b"] / 100.0
        for i in range(len(gradient_table) - 1):
            t0_i = gradient_table[i]["time_s"]
            t1_i = gradient_table[i + 1]["time_s"]
            if t0_i <= effective_t <= t1_i:
                p0 = gradient_table[i]["percent_b"] / 100.0
                p1 = gradient_table[i + 1]["percent_b"] / 100.0
                if t1_i == t0_i:
                    return p1
                frac = (effective_t - t0_i) / (t1_i - t0_i)
                return p0 + frac * (p1 - p0)
        return gradient_table[-1]["percent_b"] / 100.0

    dt = 0.5
    migration = 0.0
    t = 0.0

    while t < total_time + t0 * 2 + t_dwell:
        phi = phi_at(min(t, total_time + t_dwell))
        ln_k = params.ln_k0 + _POLARITY_COEF_LINEAR * phi + _POLARITY_COEF_QUAD * phi * phi
        k = math.exp(ln_k)
        if k < 0.01:
            k = 0.01
        velocity = 1.0 / (t0 * (1.0 + k))
        migration += velocity * dt
        t += dt
        if migration >= 1.0:
            break

    if migration < 1.0:
        return total_time + t0 + t_dwell

    return round(t, 2)


def heuristic_polarity_params(logp: float, t0: float = 60.0) -> PolarityParams:
    """Estimate polarity model parameters from logP (heuristic, no calibration).

    The polarity model uses ln convention. We convert from logP (log10) to ln:
        ln k_0 ≈ ln(10) * logP * 0.5 + 1.0
    (rough heuristic — k at φ=0 scales with hydrophobicity)
    """
    ln_k0 = math.log(10.0) * max(0.0, logp) * 0.5 + 1.0
    return PolarityParams(ln_k0=ln_k0, t0=t0)


def heuristic_quadratic_params(
    logp: float, mw: float = 200.0, t0: float = 60.0
) -> QuadraticParams:
    """Estimate quadratic model parameters from descriptors (heuristic).

    The quadratic term a is typically small (0.1-0.5) and accounts for
    curvature in log k vs φ at wide %B ranges.
    """
    s = 4.0 + (mw / 200.0) * 1.5 + max(0.0, logp) * 0.5
    s = min(s, 15.0)
    log_kw = 0.5 + max(0.0, logp) * 0.6
    a_quad = 0.3  # typical curvature term
    return QuadraticParams(log_kw=log_kw, s=s, a_quad=a_quad, t0=t0)


def heuristic_jandera_params(
    logp: float, mw: float = 200.0, t0: float = 60.0
) -> JanderaParams:
    """Estimate Jandera model parameters from descriptors (heuristic).

    The Jandera model k = a/(1 + b·φ)^n is primarily for NPLC.
    For RP, we use approximate values: a ~ k_w, b ~ S/4, n ~ 1-2.
    """
    kw = 10.0 ** (0.5 + max(0.0, logp) * 0.6)
    s = 4.0 + (mw / 200.0) * 1.5 + max(0.0, logp) * 0.5
    s = min(s, 15.0)
    a_jan = kw
    b_jan = s / 4.0
    n_jan = 1.5
    return JanderaParams(a_jan=a_jan, b_jan=b_jan, n_jan=n_jan, t0=t0)

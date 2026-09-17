"""Van Deemter efficiency analysis and flow-rate optimization.

Physics implemented here (all standard, literature-based):

1. Linear velocity <-> volumetric flow

   Chromatographic linear velocity u = L / t0 relates to flow through the
   total (accessible) porosity of the packed bed:

       u [mm/s] = F [mL/min] * 1000 / (60 * A_geo * eps_T)
       F [mL/min] = u * A_geo * eps_T * 60 / 1000

   with A_geo = pi*(dc/2)^2 the geometric cross-section in mm^2.
   eps_T ~ 0.68 fully porous, ~0.62 core-shell (less intraparticle volume).

   The *superficial* velocity u_sup = F / A_geo (no porosity) is the Darcy
   flux used for the pressure-drop equation: u_sup = u * eps_T.

2. Van Deemter in reduced (Knox) coordinates

       h = a + b/nu + c*nu        h = H/dp     nu = u*dp/Dm

   Literature-typical reduced coefficients for well-packed RP beds:
   - fully porous : a=1.0, b=2.0, c=0.05  -> h_min ~ 1.6
   - core-shell   : a=0.8, b=2.0, c=0.04  -> h_min ~ 1.4
     (narrower PSD lowers a; short diffusion path lowers c)

   Closed-form optimum:  nu_opt = sqrt(b/c),  h_min = a + 2*sqrt(b*c).

3. Solute diffusion coefficient — Wilke-Chang

       Dm [cm^2/s] = 7.4e-8 * T * sqrt(phi*M_s) / (eta * V_A^0.6)

   Association factors phi: water 2.26, methanol 1.9, acetonitrile ~1.0.
   Mixture phi and M_s approximated by volume-fraction weighting.
   Solute molar volume V_A defaults to 0.9*MW (typical organic density
   ~1.1 g/cm3); Dm may be supplied directly to override.

4. Mobile-phase viscosity — Snyder & Dolan, "Introduction to Modern
   Liquid Chromatography", 3rd ed., Appendix IV Table IV.1(b):
   measured eta(cP) for MeOH-water and ACN-water on a grid of
   temperature (15-60 C) x water content (0-100 %v/v). Bilinear
   interpolation; Arrhenius extrapolation eta ~ exp(B(1/T-1/T0)),
   B=1800 K, outside the tabulated range. These mixtures are strongly
   non-ideal (MeOH-water peaks ~1.8 cP near 50 %v) so a log-mixing rule
   is deliberately NOT used.

5. Backpressure — Darcy / Kozeny-Carman

       dP [Pa] = phi * eta * u_sup * L / dp^2,
       phi = 180*(1-eps_e)^2 / eps_e^3   (Kozeny constant, eps_e ~ 0.40)

   Sanity: dp=1.7 um, L=100 mm, dc=2.1 mm, F=0.6 mL/min, eta=0.9 cP
   -> ~910 bar, consistent with ACQUITY-class practice.

6. Optimizer modes

   - "efficiency": fixed column (L, dc, dp given). u_opt = sqrt(b/c)*Dm/dp.
     If dP(u_opt) > P_max the recommendation is pressure-capped to
     u_c = P_max*dp^2/(phi*eta*eps_T*L) and flagged.
   - "speed": fixed target plate count N and P_max (Desmet kinetic
     optimum). Minimize t0 = N*H(u)/u s.t. dP <= P_max with L free.
     t0 decreases monotonically in u, so the pressure constraint binds:

         u*H(u) = P_max*dp^2 / (phi*eta*eps_T*N)
         (c*dp^2/Dm)*u^2 + a*dp*u + (b*Dm - K) = 0   (quadratic)

     Feasibility requires K > b*Dm (the B-term floor on dP for N plates).
     Optimal length L* = N*H(u*) falls out of the solution.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Van Deemter coefficients (reduced Knox parameters), literature-typical
# ---------------------------------------------------------------------------

VD_COEFFICIENTS: dict[str, tuple[float, float, float]] = {
    # particle_type -> (a, b, c)
    "fully_porous": (1.0, 2.0, 0.05),
    "hybrid": (1.0, 2.0, 0.05),      # BEH-type: hybrid base, still fully porous
    "core_shell": (0.8, 2.0, 0.04),  # narrower PSD, shorter diffusion path
    "graphitic": (1.5, 2.0, 0.08),   # PGC: poorly characterised, conservative
}

# Total (accessible) bed porosity by particle type
TOTAL_POROSITY: dict[str, float] = {
    "fully_porous": 0.68,
    "hybrid": 0.68,
    "core_shell": 0.62,
    "graphitic": 0.65,
}

DEFAULT_INTERSTITIAL_POROSITY = 0.40  # eps_e, external/interparticle void

# Standard analytical IDs for the diameter mapping table
STANDARD_IDS_MM = (1.0, 1.5, 2.1, 3.0, 4.6)

# Analyte-size defaults: MW only enters through Dm (~MW^-0.6), so a
# "typical small molecule" default is a reasonable, forgiving choice.
DEFAULT_ANALYTE_MW = 300.0
PROTON_MASS_DA = 1.007276  # proton mass for [M+zH]^z+ / [M-zH]^z- adducts


def mz_to_neutral_mw(mz: float, charge: int) -> float:
    """Neutral mass from an m/z and signed charge (proton adducts).

        MW = |z| * m/z - z * proton_mass

    z=+1 ([M+H]+)  -> MW = m/z - 1.0073
    z=-1 ([M-H]-)  -> MW = m/z + 1.0073
    z=+2           -> MW = 2*m/z - 2.0146
    """
    if charge == 0:
        raise ValueError("charge must be non-zero")
    mw = abs(charge) * mz - charge * PROTON_MASS_DA
    if mw <= 0:
        raise ValueError(f"m/z {mz} at charge {charge} gives non-positive mass")
    return mw


# ---------------------------------------------------------------------------
# Mobile-phase viscosity — Snyder & Dolan App. IV Table IV.1(b)
# eta in cP; index = water content 0,10,...,100 %v/v; rows by temperature C.
# Upper figure MeOH-water, lower figure ACN-water in the source table.
# ---------------------------------------------------------------------------

_VISC_TEMPS_C = (15, 20, 25, 30, 35, 40, 45, 50, 55, 60)
_VISC_WATER_PCT = tuple(range(0, 101, 10))

_VISC_MEOH: dict[int, list[float]] = {
    15: [0.63, 1.05, 1.40, 1.69, 1.91, 2.02, 2.00, 1.92, 1.72, 1.43, 1.10],
    20: [0.60, 0.93, 1.25, 1.52, 1.72, 1.83, 1.83, 1.75, 1.57, 1.32, 1.00],
    25: [0.56, 0.84, 1.12, 1.36, 1.54, 1.62, 1.62, 1.56, 1.40, 1.18, 0.89],
    30: [0.51, 0.76, 1.01, 1.21, 1.36, 1.43, 1.43, 1.36, 1.23, 1.04, 0.79],
    35: [0.46, 0.69, 0.91, 1.09, 1.21, 1.26, 1.24, 1.19, 1.07, 0.92, 0.70],
    40: [0.42, 0.64, 0.83, 0.98, 1.08, 1.12, 1.11, 1.05, 0.96, 0.82, 0.64],
    45: [0.39, 0.58, 0.76, 0.89, 0.98, 1.02, 1.00, 0.96, 0.87, 0.75, 0.58],
    50: [0.37, 0.54, 0.70, 0.82, 0.90, 0.94, 0.93, 0.89, 0.82, 0.71, 0.54],
    55: [0.36, 0.50, 0.65, 0.76, 0.84, 0.88, 0.88, 0.84, 0.77, 0.67, 0.51],
    60: [0.33, 0.47, 0.61, 0.72, 0.79, 0.81, 0.81, 0.77, 0.70, 0.61, 0.47],
}

_VISC_ACN: dict[int, list[float]] = {
    15: [0.40, 0.54, 0.70, 0.81, 0.89, 0.98, 1.09, 1.30, 1.23, 1.18, 1.10],
    20: [0.37, 0.50, 0.56, 0.69, 0.81, 0.90, 0.99, 1.13, 1.10, 1.14, 1.00],
    25: [0.35, 0.46, 0.52, 0.59, 0.72, 0.82, 0.89, 0.98, 0.98, 1.01, 0.89],
    30: [0.32, 0.43, 0.45, 0.52, 0.65, 0.74, 0.80, 0.86, 0.87, 0.90, 0.79],
    35: [0.30, 0.39, 0.43, 0.47, 0.59, 0.68, 0.72, 0.76, 0.78, 0.73, 0.70],
    40: [0.27, 0.36, 0.41, 0.44, 0.54, 0.62, 0.65, 0.68, 0.70, 0.72, 0.64],
    45: [0.25, 0.33, 0.38, 0.43, 0.50, 0.58, 0.59, 0.61, 0.64, 0.61, 0.58],
    50: [0.24, 0.31, 0.36, 0.41, 0.46, 0.53, 0.55, 0.57, 0.60, 0.60, 0.54],
    55: [0.23, 0.29, 0.34, 0.38, 0.43, 0.49, 0.51, 0.53, 0.56, 0.53, 0.51],
    60: [0.22, 0.27, 0.31, 0.35, 0.41, 0.46, 0.49, 0.50, 0.53, 0.52, 0.47],
}

_VISC_TABLES = {"meoh": _VISC_MEOH, "methanol": _VISC_MEOH,
                "acn": _VISC_ACN, "acetonitrile": _VISC_ACN}

_ARRHENIUS_B_K = 1800.0  # for extrapolation beyond tabulated range


def _interp_grid(row: list[float], water_pct: float) -> float:
    """Linear interpolation over the water-% axis (10 %v steps)."""
    x = min(max(water_pct, 0.0), 100.0) / 10.0
    i = int(x)
    if i >= 10:
        return row[10]
    f = x - i
    return row[i] + f * (row[i + 1] - row[i])


def mobile_phase_viscosity_cp(
    solvent_b: str,
    fraction_b: float,
    temperature_c: float,
) -> float:
    """Viscosity (cP) of a water/organic mixture.

    Bilinear interpolation of the Snyder & Dolan App. IV Table IV.1(b)
    grid (water %v/v x temperature). Outside 15-60 C the nearest boundary
    row is Arrhenius-scaled: eta(T) = eta(T0)*exp(B*(1/T - 1/T0)).
    """
    table = _VISC_TABLES.get(solvent_b.lower())
    if table is None:
        raise ValueError(
            f"Unsupported organic solvent '{solvent_b}' "
            f"(supported: acetonitrile, methanol)"
        )
    water_pct = min(max(1.0 - fraction_b, 0.0), 1.0) * 100.0

    temps = sorted(table)
    t_lo, t_hi = temps[0], temps[-1]

    def row_at(t: int) -> float:
        return _interp_grid(table[t], water_pct)

    if temperature_c <= t_lo:
        base = row_at(t_lo)
        return base * math.exp(_ARRHENIUS_B_K * (1.0 / (temperature_c + 273.15)
                                                - 1.0 / (t_lo + 273.15)))
    if temperature_c >= t_hi:
        base = row_at(t_hi)
        return base * math.exp(_ARRHENIUS_B_K * (1.0 / (temperature_c + 273.15)
                                                - 1.0 / (t_hi + 273.15)))
    for i in range(len(temps) - 1):
        a, b = temps[i], temps[i + 1]
        if a <= temperature_c <= b:
            f = (temperature_c - a) / (b - a)
            return row_at(a) + f * (row_at(b) - row_at(a))
    return row_at(t_hi)


# ---------------------------------------------------------------------------
# Diffusion coefficient — Wilke-Chang
# ---------------------------------------------------------------------------

# Association factor phi and molar mass (g/mol) for the solvent entering
# the Wilke-Chang sqrt(phi*M_s) term.
_SOLVENT_PHI_MW = {
    "water": (2.26, 18.02),
    "acn": (1.0, 41.05),
    "acetonitrile": (1.0, 41.05),
    "meoh": (1.9, 32.04),
    "methanol": (1.9, 32.04),
}


def wilke_chang_dm_m2_s(
    analyte_mw: float,
    solvent_b: str,
    fraction_b: float,
    temperature_c: float,
    eta_cp: float,
    molar_volume_cm3: float | None = None,
) -> float:
    """Wilke-Chang diffusion coefficient in m^2/s.

    Dm[cm^2/s] = 7.4e-8 * T * sqrt(phi*M_s) / (eta * V_A^0.6)
    Mixture phi and M_s approximated by volume-fraction weighting of the
    water and organic values (documented approximation).
    """
    phi_w, m_w = _SOLVENT_PHI_MW["water"]
    phi_b, m_b = _SOLVENT_PHI_MW.get(solvent_b.lower(), (1.0, 41.05))
    x_b = min(max(fraction_b, 0.0), 1.0)
    phi_mix = (1 - x_b) * phi_w + x_b * phi_b
    m_mix = (1 - x_b) * m_w + x_b * m_b

    v_a = molar_volume_cm3 if molar_volume_cm3 else 0.9 * analyte_mw
    dm_cm2_s = (7.4e-8 * (temperature_c + 273.15) * math.sqrt(phi_mix * m_mix)
                / (eta_cp * v_a ** 0.6))
    return dm_cm2_s * 1e-4  # cm^2/s -> m^2/s


# ---------------------------------------------------------------------------
# Velocity <-> flow conversions
# ---------------------------------------------------------------------------

def geometric_area_mm2(inner_diameter_mm: float) -> float:
    return math.pi * (inner_diameter_mm / 2.0) ** 2


def flow_to_linear_velocity(flow_ml_min: float, inner_diameter_mm: float,
                            porosity_total: float) -> float:
    """Chromatographic linear velocity u = L/t0 in mm/s."""
    a_mm2 = geometric_area_mm2(inner_diameter_mm)
    return flow_ml_min * 1000.0 / (60.0 * a_mm2 * porosity_total)


def linear_velocity_to_flow(u_mm_s: float, inner_diameter_mm: float,
                            porosity_total: float) -> float:
    a_mm2 = geometric_area_mm2(inner_diameter_mm)
    return u_mm_s * a_mm2 * porosity_total * 60.0 / 1000.0


def superficial_velocity_mm_s(flow_ml_min: float, inner_diameter_mm: float) -> float:
    """Darcy (superficial) velocity F/A_geo in mm/s — used for pressure."""
    return flow_ml_min * 1000.0 / (60.0 * geometric_area_mm2(inner_diameter_mm))


def holdup_time_s(length_mm: float, u_mm_s: float) -> float:
    """t0 = L/u."""
    return length_mm / u_mm_s


def holdup_volume_ml(inner_diameter_mm: float, length_mm: float,
                     porosity_total: float) -> float:
    return geometric_area_mm2(inner_diameter_mm) * length_mm * porosity_total / 1000.0


# ---------------------------------------------------------------------------
# Van Deemter / efficiency / pressure
# ---------------------------------------------------------------------------

def kozeny_phi(porosity_interstitial: float = DEFAULT_INTERSTITIAL_POROSITY) -> float:
    """Kozeny-Carman flow-resistance factor 180(1-e)^2/e^3."""
    e = porosity_interstitial
    return 180.0 * (1.0 - e) ** 2 / e ** 3


def reduced_velocity(u_mm_s: float, dp_um: float, dm_m2_s: float) -> float:
    """nu = u*dp/Dm (dimensionless)."""
    return u_mm_s * (dp_um * 1e-3) / (dm_m2_s * 1e6)


def plate_height_um(u_mm_s: float, dp_um: float, dm_m2_s: float,
                    a: float, b: float, c: float) -> float:
    """H [um] = dp * (a + b/nu + c*nu)."""
    nu = reduced_velocity(u_mm_s, dp_um, dm_m2_s)
    if nu <= 0:
        return float("inf")
    return dp_um * (a + b / nu + c * nu)


def plate_count(length_mm: float, h_um: float) -> float:
    if h_um <= 0 or math.isinf(h_um):
        return 0.0
    return length_mm * 1000.0 / h_um


def backpressure_bar(flow_ml_min: float, inner_diameter_mm: float,
                     length_mm: float, dp_um: float, eta_cp: float,
                     porosity_interstitial: float = DEFAULT_INTERSTITIAL_POROSITY
                     ) -> float:
    """Darcy/Kozeny-Carman pressure drop in bar."""
    u_sup_m_s = superficial_velocity_mm_s(flow_ml_min, inner_diameter_mm) * 1e-3
    dp_m = dp_um * 1e-6
    eta_pa_s = eta_cp * 1e-3
    l_m = length_mm * 1e-3
    dp_pa = kozeny_phi(porosity_interstitial) * eta_pa_s * u_sup_m_s * l_m / dp_m ** 2
    return dp_pa / 1e5


def optimal_velocity_mm_s(dp_um: float, dm_m2_s: float,
                          a: float, b: float, c: float) -> float:
    """Van Deemter optimum: nu_opt = sqrt(b/c) -> u = nu_opt*Dm/dp."""
    nu_opt = math.sqrt(b / c)
    return nu_opt * dm_m2_s * 1e6 / (dp_um * 1e-3)


# ---------------------------------------------------------------------------
# Column context and results
# ---------------------------------------------------------------------------

@dataclass
class ColumnGeometry:
    length_mm: float
    inner_diameter_mm: float
    particle_size_um: float
    particle_type: str = "fully_porous"
    porosity_total: float | None = None
    porosity_interstitial: float = DEFAULT_INTERSTITIAL_POROSITY

    def resolved_eps_t(self) -> float:
        if self.porosity_total is not None:
            return self.porosity_total
        return TOTAL_POROSITY.get(self.particle_type, 0.68)

    def coeffs(self) -> tuple[float, float, float]:
        return VD_COEFFICIENTS.get(self.particle_type,
                                   VD_COEFFICIENTS["fully_porous"])


@dataclass
class CurvePoint:
    flow_ml_min: float
    u_mm_s: float
    h_um: float
    n: float
    pressure_bar: float
    # Optional band bounds when multiple analyte Dm values were evaluated
    # (the extreme-Dm curves cross at nu_opt, so the band envelopes them).
    h_low_um: float | None = None
    h_high_um: float | None = None

    def to_dict(self) -> dict[str, float]:
        d = {
            "flow_ml_min": round(self.flow_ml_min, 4),
            "u_mm_s": round(self.u_mm_s, 3),
            "h_um": round(self.h_um, 3),
            "n": round(self.n),
            "pressure_bar": round(self.pressure_bar, 1),
        }
        if self.h_low_um is not None:
            d["h_low_um"] = round(self.h_low_um, 3)
        if self.h_high_um is not None:
            d["h_high_um"] = round(self.h_high_um, 3)
        return d


@dataclass
class OptimumResult:
    mode: str                    # "efficiency" | "speed_at_plates"
    u_mm_s: float
    flow_ml_min: float
    h_um: float
    n: float
    t0_s: float
    pressure_bar: float
    required_length_mm: float | None  # set for speed mode (L is solved)
    pressure_limited: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "u_mm_s": round(self.u_mm_s, 3),
            "flow_ml_min": round(self.flow_ml_min, 4),
            "h_um": round(self.h_um, 3),
            "n": round(self.n),
            "t0_s": round(self.t0_s, 1),
            "pressure_bar": round(self.pressure_bar, 1),
            "required_length_mm": (
                round(self.required_length_mm, 1)
                if self.required_length_mm is not None else None
            ),
            "pressure_limited": self.pressure_limited,
            "notes": self.notes,
        }


@dataclass
class DiameterMapRow:
    inner_diameter_mm: float
    optimal_flow_ml_min: float
    u_mm_s: float
    pressure_bar: float
    n: float
    scaled_flow_ml_min: float | None  # user flow geometrically scaled to this ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "inner_diameter_mm": self.inner_diameter_mm,
            "optimal_flow_ml_min": round(self.optimal_flow_ml_min, 4),
            "u_mm_s": round(self.u_mm_s, 3),
            "pressure_bar": round(self.pressure_bar, 1),
            "n": round(self.n),
            "scaled_flow_ml_min": (
                round(self.scaled_flow_ml_min, 4)
                if self.scaled_flow_ml_min is not None else None
            ),
        }


# ---------------------------------------------------------------------------
# Analysis entry points
# ---------------------------------------------------------------------------

def van_deemter_curve(
    col: ColumnGeometry,
    dm_m2_s: float,
    eta_cp: float,
    flow_min_ml_min: float,
    flow_max_ml_min: float,
    points: int = 60,
    band_dm: tuple[float, float] | None = None,
) -> list[CurvePoint]:
    """Plate-height curve over a flow range.

    ``band_dm`` optionally provides the extreme (lowest, highest) analyte
    diffusion coefficients; each point then also carries h_low/h_high —
    the envelope of the curves at those Dm values (they cross at nu_opt).
    """
    a, b, c = col.coeffs()
    eps_t = col.resolved_eps_t()
    out: list[CurvePoint] = []
    n_pts = max(10, min(points, 300))
    for i in range(n_pts):
        f = flow_min_ml_min + (flow_max_ml_min - flow_min_ml_min) * i / (n_pts - 1)
        u = flow_to_linear_velocity(f, col.inner_diameter_mm, eps_t)
        h = plate_height_um(u, col.particle_size_um, dm_m2_s, a, b, c)
        h_low = h_high = None
        if band_dm is not None:
            h1 = plate_height_um(u, col.particle_size_um, band_dm[0], a, b, c)
            h2 = plate_height_um(u, col.particle_size_um, band_dm[1], a, b, c)
            # Envelope of all evaluated curves — the extreme-Dm curves cross
            # at nu_opt, where the mid curve can dip below both, so include h.
            h_low, h_high = min(h, h1, h2), max(h, h1, h2)
        out.append(CurvePoint(
            flow_ml_min=f,
            u_mm_s=u,
            h_um=h,
            n=plate_count(col.length_mm, h),
            pressure_bar=backpressure_bar(
                f, col.inner_diameter_mm, col.length_mm,
                col.particle_size_um, eta_cp, col.porosity_interstitial),
            h_low_um=h_low,
            h_high_um=h_high,
        ))
    return out


def optimize_efficiency(
    col: ColumnGeometry,
    dm_m2_s: float,
    eta_cp: float,
    max_pressure_bar: float,
) -> OptimumResult:
    """Max-efficiency optimum for the given column (closed form), with a
    pressure-capped fallback if the optimum exceeds max_pressure_bar."""
    a, b, c = col.coeffs()
    eps_t = col.resolved_eps_t()
    notes: list[str] = []

    u_opt = optimal_velocity_mm_s(col.particle_size_um, dm_m2_s, a, b, c)
    f_opt = linear_velocity_to_flow(u_opt, col.inner_diameter_mm, eps_t)
    p_opt = backpressure_bar(
        f_opt, col.inner_diameter_mm, col.length_mm,
        col.particle_size_um, eta_cp, col.porosity_interstitial)

    pressure_limited = False
    if p_opt > max_pressure_bar:
        # dP ∝ F at fixed column -> cap velocity at the pressure limit
        pressure_limited = True
        u_cap = u_opt * max_pressure_bar / p_opt
        f_cap = linear_velocity_to_flow(u_cap, col.inner_diameter_mm, eps_t)
        notes.append(
            f"Van Deemter optimum needs {p_opt:.0f} bar > limit "
            f"{max_pressure_bar:.0f} bar — flow capped at pressure limit"
        )
        u_opt, f_opt, p_opt = u_cap, f_cap, max_pressure_bar

    h = plate_height_um(u_opt, col.particle_size_um, dm_m2_s, a, b, c)
    n = plate_count(col.length_mm, h)
    return OptimumResult(
        mode="efficiency",
        u_mm_s=u_opt,
        flow_ml_min=f_opt,
        h_um=h,
        n=n,
        t0_s=holdup_time_s(col.length_mm, u_opt),
        pressure_bar=p_opt,
        required_length_mm=None,
        pressure_limited=pressure_limited,
        notes=notes,
    )


def optimize_speed(
    col: ColumnGeometry,
    dm_m2_s: float,
    eta_cp: float,
    target_plates: float,
    max_pressure_bar: float,
) -> OptimumResult:
    """Kinetic (Desmet) optimum: minimum t0 for target N at P_max, column
    length free. Solves (c*dp^2/Dm)u^2 + a*dp*u + (b*Dm - K) = 0 with
    K = P_max*dp^2/(phi*eta*eps_T*N)."""
    a, b, c = col.coeffs()
    eps_t = col.resolved_eps_t()
    phi = kozeny_phi(col.porosity_interstitial)
    notes: list[str] = []

    dp_m = col.particle_size_um * 1e-6
    eta_pa_s = eta_cp * 1e-3
    p_pa = max_pressure_bar * 1e5
    n = target_plates

    k_val = p_pa * dp_m ** 2 / (phi * eta_pa_s * eps_t * n)  # u*H target [m^2/s]
    floor = b * dm_m2_s                                     # min of u*H as u->0

    if k_val <= floor:
        n_max = p_pa * dp_m ** 2 / (phi * eta_pa_s * eps_t * floor)
        return OptimumResult(
            mode="speed_at_plates",
            u_mm_s=0.0, flow_ml_min=0.0, h_um=0.0, n=0.0, t0_s=0.0,
            pressure_bar=0.0, required_length_mm=None,
            pressure_limited=True,
            notes=[
                f"Target N={n:.0f} infeasible at {max_pressure_bar:.0f} bar "
                f"with dp={col.particle_size_um}um — the B-term alone needs "
                f"more pressure. Max achievable N ~ {n_max:.0f}; reduce the "
                f"plate target or raise the pressure limit.",
            ],
        )

    # Quadratic in u (SI): (c*dp^2/Dm)u^2 + a*dp*u + (b*Dm - K) = 0
    qa = c * dp_m ** 2 / dm_m2_s
    qb = a * dp_m
    qc = floor - k_val
    disc = qb * qb - 4.0 * qa * qc
    u_star = (-qb + math.sqrt(disc)) / (2.0 * qa)  # m/s, positive root

    u_mm_s = u_star * 1e3
    h_um = plate_height_um(u_mm_s, col.particle_size_um, dm_m2_s, a, b, c)
    l_star_mm = n * h_um / 1000.0
    f_star = linear_velocity_to_flow(u_mm_s, col.inner_diameter_mm, eps_t)
    t0 = l_star_mm / u_mm_s

    if l_star_mm < 20:
        notes.append(
            f"Optimal length {l_star_mm:.0f} mm is very short — "
            f"consider a shorter column format")
    if l_star_mm > 500:
        notes.append(
            f"Optimal length {l_star_mm:.0f} mm exceeds practical columns — "
            f"coupled columns or lower N required")

    return OptimumResult(
        mode="speed_at_plates",
        u_mm_s=u_mm_s,
        flow_ml_min=f_star,
        h_um=h_um,
        n=n,
        t0_s=t0,
        pressure_bar=max_pressure_bar,
        required_length_mm=l_star_mm,
        pressure_limited=True,  # constraint binds by construction
        notes=notes,
    )


def diameter_map(
    col: ColumnGeometry,
    dm_m2_s: float,
    eta_cp: float,
    current_flow_ml_min: float | None = None,
    ids_mm: tuple[float, ...] = STANDARD_IDS_MM,
) -> list[DiameterMapRow]:
    """Optimal flow and pressure mapped across standard column IDs at the
    same linear velocity; also the user's current flow geometrically
    rescaled (F ∝ dc^2) to each ID."""
    a, b, c = col.coeffs()
    eps_t = col.resolved_eps_t()
    u_opt = optimal_velocity_mm_s(col.particle_size_um, dm_m2_s, a, b, c)
    h = plate_height_um(u_opt, col.particle_size_um, dm_m2_s, a, b, c)
    n = plate_count(col.length_mm, h)

    rows: list[DiameterMapRow] = []
    for id_mm in ids_mm:
        f_opt = linear_velocity_to_flow(u_opt, id_mm, eps_t)
        p = backpressure_bar(f_opt, id_mm, col.length_mm,
                             col.particle_size_um, eta_cp,
                             col.porosity_interstitial)
        scaled = (current_flow_ml_min
                  * (id_mm / col.inner_diameter_mm) ** 2
                  if current_flow_ml_min else None)
        rows.append(DiameterMapRow(
            inner_diameter_mm=id_mm,
            optimal_flow_ml_min=f_opt,
            u_mm_s=u_opt,
            pressure_bar=p,
            n=n,
            scaled_flow_ml_min=scaled,
        ))
    return rows


def assess_flow(
    col: ColumnGeometry,
    dm_m2_s: float,
    eta_cp: float,
    flow_ml_min: float,
) -> dict[str, Any]:
    """Evaluate a user flow rate against the Van Deemter optimum."""
    a, b, c = col.coeffs()
    eps_t = col.resolved_eps_t()
    u = flow_to_linear_velocity(flow_ml_min, col.inner_diameter_mm, eps_t)
    h = plate_height_um(u, col.particle_size_um, dm_m2_s, a, b, c)
    u_opt = optimal_velocity_mm_s(col.particle_size_um, dm_m2_s, a, b, c)
    h_min = plate_height_um(u_opt, col.particle_size_um, dm_m2_s, a, b, c)
    p = backpressure_bar(flow_ml_min, col.inner_diameter_mm, col.length_mm,
                         col.particle_size_um, eta_cp, col.porosity_interstitial)

    ratio = u / u_opt if u_opt > 0 else 0.0
    if 0.7 <= ratio <= 1.4:
        verdict = "optimal"
    elif ratio < 0.7:
        verdict = "below optimum (B-term dominated — longitudinal diffusion)"
    else:
        verdict = "above optimum (C-term dominated — mass transfer resistance)"

    return {
        "flow_ml_min": round(flow_ml_min, 4),
        "u_mm_s": round(u, 3),
        "h_um": round(h, 3),
        "n": round(plate_count(col.length_mm, h)),
        "pressure_bar": round(p, 1),
        "t0_s": round(holdup_time_s(col.length_mm, u), 1),
        "efficiency_vs_optimum_pct": round(100.0 * h_min / h, 1)
        if math.isfinite(h) and h > 0 else 0.0,
        "velocity_ratio": round(ratio, 2),
        "verdict": verdict,
    }

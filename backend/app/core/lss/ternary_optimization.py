"""Ternary solvent optimization.

Optimizes three-solvent ratios using a grid search over the
composition triangle, similar to ACD/Labs ternary solvent
optimization.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.core.lss.chromatogram import default_peak_width, resolution
from app.core.lss.gradient_sim import heuristic_lss_params, predict_rt_from_gradient

# Solvent strength parameters relative to ACN
# S_ratio = S_solvent / S_acn
SOLVENT_STRENGTH = {
    "acn": 1.0,      # acetonitrile (reference)
    "meoh": 0.85,    # methanol (slightly weaker than ACN in RP)
    "ipa": 1.15,     # isopropanol (stronger than ACN)
    "water": 0.0,    # weak solvent
    "acetone": 1.1,
    "thf": 1.2,      # tetrahydrofuran
}


@dataclass
class TernaryPoint:
    """A point in the ternary composition space."""
    frac_a: float  # fraction of solvent A (water)
    frac_b: float  # fraction of solvent B (e.g. ACN)
    frac_c: float  # fraction of solvent C (e.g. MeOH)
    min_rs: float = 0.0
    rts: list[float] = field(default_factory=list)


@dataclass
class TernaryOptResult:
    """Ternary optimization result."""
    solvent_a: str
    solvent_b: str
    solvent_c: str
    points: list[TernaryPoint]
    optimal: TernaryPoint | None
    mode: str  # "binary" or "ternary"

    def to_dict(self) -> dict[str, Any]:
        return {
            "solvent_a": self.solvent_a,
            "solvent_b": self.solvent_b,
            "solvent_c": self.solvent_c,
            "mode": self.mode,
            "optimal": {
                "frac_a": round(self.optimal.frac_a, 4),
                "frac_b": round(self.optimal.frac_b, 4),
                "frac_c": round(self.optimal.frac_c, 4),
                "min_rs": round(self.optimal.min_rs, 4),
                "rts": [round(rt, 2) for rt in self.optimal.rts],
            } if self.optimal else None,
            "points": [
                {
                    "frac_a": round(p.frac_a, 4),
                    "frac_b": round(p.frac_b, 4),
                    "frac_c": round(p.frac_c, 4),
                    "min_rs": round(p.min_rs, 4),
                }
                for p in self.points
            ],
        }


def ternary_optimize(
    smiles_list: list[str],
    solvent_a: str = "water",
    solvent_b: str = "acn",
    solvent_c: str = "meoh",
    gradient_time_min: float = 20.0,
    flow_rate_ml_min: float = 0.4,
    ph: float = 2.7,
    temperature_c: float = 30.0,
    column_type: str = "C18",
    mode: str = "ternary",
    grid_resolution: int = 5,
) -> TernaryOptResult:
    """Optimize ternary solvent ratios.

    mode: "binary" searches only the perimeter (binary mixtures),
          "ternary" searches the interior of the triangle.
    """
    from app.core.chem.logd import logd_at_ph
    from app.core.chem.parser import parse_mol
    from app.core.rules.engine import suggest_method

    # Prepare compounds
    compounds: list[dict[str, Any]] = []
    for i, smi in enumerate(smiles_list):
        try:
            parsed = parse_mol(smi)
            sugg = suggest_method(parsed.mol, ionization_mode="ESI+",
                                  retention_goal="neutral", gradient_time_min=gradient_time_min,
                                  flow_rate_ml_min=flow_rate_ml_min)
            logd = logd_at_ph(parsed.mol, ph, sugg.descriptors.logp)
            compounds.append({
                "index": i,
                "smiles": smi,
                "effective_logp": logd,
                "mw": sugg.descriptors.mw,
                "tpsa": sugg.descriptors.tpsa,
                "hbd": sugg.descriptors.hbd,
                "hba": sugg.descriptors.hba,
            })
        except Exception:
            continue

    if len(compounds) < 2:
        raise ValueError("Need at least 2 valid compounds for ternary optimization")

    # Get solvent strength ratios
    s_b = SOLVENT_STRENGTH.get(solvent_b.lower(), 1.0)
    s_c = SOLVENT_STRENGTH.get(solvent_c.lower(), 0.85)

    # Temperature factor (negative: RP-LC retention is exothermic, higher T → lower k)
    delta_h_over_r = -5000.0
    t1 = 303.15
    t2 = temperature_c + 273.15
    temp_factor = math.exp(delta_h_over_r * (1.0 / t1 - 1.0 / t2))
    temp_factor = max(0.5, min(2.0, temp_factor))

    # Generate grid points in the ternary space
    # frac_a + frac_b + frac_c = 1.0
    # We search over organic fraction: frac_b + frac_c = organic_fraction
    # And the ratio of B to C within the organic fraction
    points: list[TernaryPoint] = []

    n = grid_resolution
    for i in range(n + 1):
        for j in range(n + 1 - i):
            # i = fraction of A, j = fraction of B, rest = C
            frac_a = i / n
            frac_b = j / n
            frac_c = 1.0 - frac_a - frac_b

            if frac_c < -0.001:
                continue
            frac_c = max(0.0, frac_c)

            # In binary mode, skip interior points (where all three > 0)
            if mode == "binary" and frac_a > 0.01 and frac_b > 0.01 and frac_c > 0.01:
                continue

            # Compute effective solvent strength
            # phi_effective = frac_b * s_b + frac_c * s_c (organic fraction weighted)
            organic_frac = frac_b + frac_c
            if organic_frac < 0.01:
                continue  # pure water, skip

            # Effective phi for LSS: weighted by solvent strength
            phi_eff = frac_b * s_b + frac_c * s_c

            # Build gradient: 5% to 95% effective organic over gradient_time
            # We represent this as %B in the gradient table, but adjust S parameter
            t_total = gradient_time_min * 60
            # Use effective percent_b = phi_eff * 100 at the end
            # Start at 5% organic, end at phi_eff*100
            start_pct = 5.0
            end_pct = min(95.0, phi_eff * 100)

            grad_table = [
                {"time_s": 0, "percent_b": start_pct},
                {"time_s": 60, "percent_b": start_pct},
                {"time_s": t_total - 120, "percent_b": end_pct},
                {"time_s": t_total, "percent_b": end_pct},
            ]

            # Predict RTs with adjusted S parameter
            rts: list[float] = []
            for c in compounds:
                params = heuristic_lss_params(
                    c["effective_logp"],
                    mw=c.get("mw", 200.0),
                    tpsa=c.get("tpsa", 0.0),
                    hbd=c.get("hbd", 0),
                    hba=c.get("hba", 0),
                    column_type=column_type,
                )
                # Adjust S for mixed solvent
                # S_eff = S * (weighted average of solvent strength)
                s_eff = params.s * (s_b * frac_b + s_c * frac_c) / max(organic_frac, 0.01)
                params_adjusted = type(params)(log_k0=params.log_k0, s=s_eff, t0=params.t0)

                rt = predict_rt_from_gradient(params_adjusted, grad_table, flow_rate_ml_min)
                rt *= temp_factor
                rts.append(rt)

            # Compute min resolution
            sorted_rts = sorted(
                zip(rts, [default_peak_width(rt) for rt in rts], strict=False)
            )
            min_rs = float("inf")
            for k in range(len(sorted_rts) - 1):
                rt_a, w_a = sorted_rts[k]
                rt_b, w_b = sorted_rts[k + 1]
                rs = resolution(rt_a, w_a, rt_b, w_b)
                if rs < min_rs:
                    min_rs = rs
            if min_rs == float("inf"):
                min_rs = 0.0

            points.append(TernaryPoint(
                frac_a=frac_a, frac_b=frac_b, frac_c=frac_c,
                min_rs=min_rs, rts=rts,
            ))

    # Find optimal
    optimal = max(points, key=lambda p: p.min_rs) if points else None

    return TernaryOptResult(
        solvent_a=solvent_a,
        solvent_b=solvent_b,
        solvent_c=solvent_c,
        points=points,
        optimal=optimal,
        mode=mode,
    )

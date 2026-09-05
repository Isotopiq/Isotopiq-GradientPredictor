"""Resolution maps for 1D and 2D optimization.

Computes resolution across a range of one or two variables
(gradient time, pH, temperature, flow rate, %B start/end) to
visualize the resolution landscape, similar to ACD/Labs LC
Simulator resolution maps.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.core.lss.chromatogram import default_peak_width, resolution
from app.core.lss.gradient_sim import heuristic_lss_params, predict_rt_from_gradient
from app.core.lss.suitability import SuitabilityCriteria, score_method

VALID_VARIABLES = {
    "gradient_time", "ph", "temperature", "flow_rate",
    "percent_b_start", "percent_b_end",
}


@dataclass
class ResolutionMap1D:
    """1D resolution map."""
    variable: str
    x_values: list[float]
    min_rs: list[float]
    per_compound_rts: list[list[float]]  # [compound_index][x_index]
    co_elution_points: list[dict[str, Any]]
    suitability_scores: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "x_values": [round(v, 4) for v in self.x_values],
            "min_rs": [round(r, 4) for r in self.min_rs],
            "per_compound_rts": [[round(rt, 2) for rt in rts] for rts in self.per_compound_rts],
            "co_elution_points": self.co_elution_points,
            "suitability_scores": [round(s, 4) for s in self.suitability_scores],
        }


@dataclass
class ResolutionMap2D:
    """2D resolution map (heatmap)."""
    var_x: str
    var_y: str
    x_values: list[float]
    y_values: list[float]
    rs_grid: list[list[float]]  # [y_index][x_index]
    optimal_point: dict[str, float]
    suitability_grid: list[list[float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "var_x": self.var_x,
            "var_y": self.var_y,
            "x_values": [round(v, 4) for v in self.x_values],
            "y_values": [round(v, 4) for v in self.y_values],
            "rs_grid": [[round(r, 4) for r in row] for row in self.rs_grid],
            "optimal_point": {k: round(v, 4) for k, v in self.optimal_point.items()},
            "suitability_grid": [[round(s, 4) for s in row] for row in self.suitability_grid],
        }


def _compute_rts_for_compounds(
    compounds: list[dict[str, Any]],
    gradient_table: list[dict],
    flow_rate: float,
    temperature: float,
    column_type: str,
) -> list[tuple[float, float]]:
    """Compute RTs for all compounds at given conditions. Returns [(rt, width), ...]."""
    # Temperature factor (negative: RP-LC retention is exothermic, higher T → lower k)
    delta_h_over_r = -5000.0
    t1 = 303.15
    t2 = temperature + 273.15
    temp_factor = math.exp(delta_h_over_r * (1.0 / t1 - 1.0 / t2))
    temp_factor = max(0.5, min(2.0, temp_factor))

    rts: list[tuple[float, float]] = []
    for c in compounds:
        params = heuristic_lss_params(
            c["effective_logp"],
            mw=c.get("mw", 200.0),
            tpsa=c.get("tpsa", 0.0),
            hbd=c.get("hbd", 0),
            hba=c.get("hba", 0),
            column_type=column_type,
        )
        rt = predict_rt_from_gradient(params, gradient_table, flow_rate)
        rt *= temp_factor
        w = default_peak_width(rt)
        rts.append((rt, w))
    return rts


def _compute_min_rs(rts: list[tuple[float, float]]) -> float:
    """Compute minimum pairwise resolution from RTs and widths."""
    if len(rts) < 2:
        return float("inf")
    sorted_rts = sorted(rts, key=lambda x: x[0])
    min_rs = float("inf")
    for i in range(len(sorted_rts) - 1):
        rt_a, w_a = sorted_rts[i]
        rt_b, w_b = sorted_rts[i + 1]
        rs = resolution(rt_a, w_a, rt_b, w_b)
        if rs < min_rs:
            min_rs = rs
    return min_rs if min_rs != float("inf") else 0.0


def _prepare_compounds(
    smiles_list: list[str],
    ph: float,
) -> list[dict[str, Any]]:
    """Parse compounds and compute descriptors + logD."""
    from app.core.chem.logd import logd_at_ph
    from app.core.chem.parser import parse_mol
    from app.core.rules.engine import suggest_method

    compounds: list[dict[str, Any]] = []
    for i, smi in enumerate(smiles_list):
        try:
            parsed = parse_mol(smi)
        except Exception:
            continue
        sugg = suggest_method(parsed.mol, ionization_mode="ESI+",
                              retention_goal="neutral", gradient_time_min=20,
                              flow_rate_ml_min=0.4)
        logd = logd_at_ph(parsed.mol, ph, sugg.descriptors.logp)
        compounds.append({
            "index": i,
            "smiles": smi,
            "logp": sugg.descriptors.logp,
            "effective_logp": logd,
            "mw": sugg.descriptors.mw,
            "tpsa": sugg.descriptors.tpsa,
            "hbd": sugg.descriptors.hbd,
            "hba": sugg.descriptors.hba,
        })
    return compounds


def _build_gradient_table(
    gradient_time_min: float,
    percent_b_start: float,
    percent_b_end: float,
) -> list[dict]:
    """Build a standard gradient table."""
    t_total = gradient_time_min * 60
    return [
        {"time_s": 0, "percent_b": percent_b_start},
        {"time_s": 60, "percent_b": percent_b_start},
        {"time_s": t_total - 120, "percent_b": percent_b_end},
        {"time_s": t_total, "percent_b": percent_b_end},
    ]


def resolution_map_1d(
    smiles_list: list[str],
    variable: str,
    var_range: tuple[float, float],
    steps: int = 20,
    fixed_params: dict[str, Any] | None = None,
) -> ResolutionMap1D:
    """Compute 1D resolution map across a variable range."""
    if variable not in VALID_VARIABLES:
        raise ValueError(f"Invalid variable: {variable}. Must be one of {VALID_VARIABLES}")

    fp = fixed_params or {}
    ph = fp.get("ph", 2.7)
    temperature = fp.get("temperature", 30.0)
    flow_rate = fp.get("flow_rate", 0.4)
    gradient_time = fp.get("gradient_time", 20.0)
    percent_b_start = fp.get("percent_b_start", 5.0)
    percent_b_end = fp.get("percent_b_end", 95.0)
    column_type = fp.get("column_type", "C18")
    criteria = fp.get("suitability")

    compounds = _prepare_compounds(smiles_list, ph)
    if len(compounds) < 2:
        raise ValueError("Need at least 2 valid compounds for resolution map")

    x_values = [var_range[0] + (var_range[1] - var_range[0]) * i / (steps - 1) for i in range(steps)]
    min_rs_list: list[float] = []
    per_compound_rts: list[list[float]] = [[] for _ in compounds]
    co_elution_points: list[dict[str, Any]] = []
    suitability_scores: list[float] = []

    suit_criteria = None
    if criteria:
        suit_criteria = SuitabilityCriteria(
            min_resolution=criteria.get("min_resolution", 1.5),
            max_run_time_min=criteria.get("max_run_time_min", 60.0),
            min_k=criteria.get("min_k", 0.5),
            max_k=criteria.get("max_k", 20.0),
        )

    for x in x_values:
        # Set the variable
        gt = gradient_time
        fr = flow_rate
        temp = temperature
        p = ph
        bs = percent_b_start
        be = percent_b_end

        if variable == "gradient_time":
            gt = x
        elif variable == "ph":
            p = x
            # Recompute logD at new pH
            compounds = _prepare_compounds(smiles_list, p)
        elif variable == "temperature":
            temp = x
        elif variable == "flow_rate":
            fr = x
        elif variable == "percent_b_start":
            bs = x
        elif variable == "percent_b_end":
            be = x

        grad_table = _build_gradient_table(gt, bs, be)
        rts = _compute_rts_for_compounds(compounds, grad_table, fr, temp, column_type)

        min_rs = _compute_min_rs(rts)
        min_rs_list.append(min_rs)

        for i, (rt, _) in enumerate(rts):
            if i < len(per_compound_rts):
                per_compound_rts[i].append(rt)

        # Co-elution check
        if min_rs < 0.8:
            co_elution_points.append({
                "x": round(x, 4),
                "min_rs": round(min_rs, 4),
            })

        # Suitability score
        if suit_criteria:
            t0 = 60.0 * 0.4 / max(fr, 0.01)
            score = score_method([r[0] for r in rts], [r[1] for r in rts], gt * 60, t0, suit_criteria)
            suitability_scores.append(score)
        else:
            suitability_scores.append(0.0)

    return ResolutionMap1D(
        variable=variable,
        x_values=x_values,
        min_rs=min_rs_list,
        per_compound_rts=per_compound_rts,
        co_elution_points=co_elution_points,
        suitability_scores=suitability_scores,
    )


def resolution_map_2d(
    smiles_list: list[str],
    var_x: str,
    range_x: tuple[float, float],
    steps_x: int,
    var_y: str,
    range_y: tuple[float, float],
    steps_y: int,
    fixed_params: dict[str, Any] | None = None,
) -> ResolutionMap2D:
    """Compute 2D resolution map (heatmap)."""
    if var_x not in VALID_VARIABLES or var_y not in VALID_VARIABLES:
        raise ValueError(f"Invalid variable. Must be one of {VALID_VARIABLES}")

    fp = fixed_params or {}
    ph = fp.get("ph", 2.7)
    temperature = fp.get("temperature", 30.0)
    flow_rate = fp.get("flow_rate", 0.4)
    gradient_time = fp.get("gradient_time", 20.0)
    percent_b_start = fp.get("percent_b_start", 5.0)
    percent_b_end = fp.get("percent_b_end", 95.0)
    column_type = fp.get("column_type", "C18")
    criteria = fp.get("suitability")

    compounds = _prepare_compounds(smiles_list, ph)
    if len(compounds) < 2:
        raise ValueError("Need at least 2 valid compounds for resolution map")

    x_values = [range_x[0] + (range_x[1] - range_x[0]) * i / max(steps_x - 1, 1) for i in range(steps_x)]
    y_values = [range_y[0] + (range_y[1] - range_y[0]) * i / max(steps_y - 1, 1) for i in range(steps_y)]

    rs_grid: list[list[float]] = []
    suitability_grid: list[list[float]] = []
    optimal = {"x": x_values[0], "y": y_values[0], "rs": 0.0}

    suit_criteria = None
    if criteria:
        suit_criteria = SuitabilityCriteria(
            min_resolution=criteria.get("min_resolution", 1.5),
            max_run_time_min=criteria.get("max_run_time_min", 60.0),
            min_k=criteria.get("min_k", 0.5),
            max_k=criteria.get("max_k", 20.0),
        )

    for y in y_values:
        rs_row: list[float] = []
        suit_row: list[float] = []
        for x in x_values:
            # Set variables
            gt, fr, temp, p, bs, be = gradient_time, flow_rate, temperature, ph, percent_b_start, percent_b_end
            comps = compounds

            if var_x == "gradient_time":
                gt = x
            elif var_x == "ph":
                p = x
                comps = _prepare_compounds(smiles_list, p)
            elif var_x == "temperature":
                temp = x
            elif var_x == "flow_rate":
                fr = x
            elif var_x == "percent_b_start":
                bs = x
            elif var_x == "percent_b_end":
                be = x

            if var_y == "gradient_time":
                gt = y
            elif var_y == "ph":
                p = y
                comps = _prepare_compounds(smiles_list, p)
            elif var_y == "temperature":
                temp = y
            elif var_y == "flow_rate":
                fr = y
            elif var_y == "percent_b_start":
                bs = y
            elif var_y == "percent_b_end":
                be = y

            grad_table = _build_gradient_table(gt, bs, be)
            rts = _compute_rts_for_compounds(comps, grad_table, fr, temp, column_type)
            min_rs = _compute_min_rs(rts)
            rs_row.append(min_rs)

            if suit_criteria:
                t0 = 60.0 * 0.4 / max(fr, 0.01)
                score = score_method(
                    [r[0] for r in rts], [r[1] for r in rts], gt * 60, t0, suit_criteria
                )
                suit_row.append(score)
            else:
                suit_row.append(0.0)

            if min_rs > optimal["rs"]:
                optimal = {"x": x, "y": y, "rs": min_rs}

        rs_grid.append(rs_row)
        suitability_grid.append(suit_row)

    return ResolutionMap2D(
        var_x=var_x,
        var_y=var_y,
        x_values=x_values,
        y_values=y_values,
        rs_grid=rs_grid,
        optimal_point=optimal,
        suitability_grid=suitability_grid,
    )

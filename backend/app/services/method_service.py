"""Method service: rules-based suggestion + persistence + gradient simulation."""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.parser import ChemParseError, parse_mol
from app.core.lss.chromatogram import (
    Peak,
    default_peak_width,
    simulate_chromatogram,
)
from app.core.lss.gradient_sim import (
    CalibrationRun,
    heuristic_lss_params,
    predict_rt_from_gradient,
    predict_rt_lss,
    fit_lss,
)
from app.core.rules.engine import suggest_method
from app.models.method import Method
from app.schemas.method import (
    ChromatogramRequest,
    GradientSimulateRequest,
    MethodCreate,
    MethodSuggestionRequest,
)


class MethodServiceError(ValueError):
    pass


def suggest(data: MethodSuggestionRequest) -> dict[str, Any]:
    """Run the rules engine on the input molecule and return a suggestion dict."""
    raw = data.smiles or data.inchi or data.molfile
    if not raw:
        raise MethodServiceError("Provide smiles, inchi, or molfile")
    try:
        parsed = parse_mol(raw)
    except ChemParseError as exc:
        raise MethodServiceError(str(exc)) from exc

    suggestion = suggest_method(
        parsed.mol,
        ionization_mode=data.ionization_mode,
        retention_goal=data.retention_goal,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
        column_type_override=data.column_type,
    )

    return {
        "column": {
            "column_type": suggestion.column.column_type,
            "rationale": suggestion.column.rationale,
            "alternatives": suggestion.column.alternatives,
        },
        "ph": {
            "recommended_ph": suggestion.ph.recommended_ph,
            "rationale": suggestion.ph.rationale,
            "warning_zones": suggestion.ph.warning_zones,
        },
        "additive": {
            "additive": suggestion.additive.additive,
            "rationale": suggestion.additive.rationale,
            "alternatives": suggestion.additive.alternatives,
        },
        "gradient": suggestion.gradient,
        "pka_values": suggestion.pka_values,
        "logd_at_recommended_ph": suggestion.logd_at_recommended_ph,
        "ionizable": suggestion.ionizable,
        "permanently_charged": suggestion.permanently_charged,
        "descriptors": {
            "mw": suggestion.descriptors.mw,
            "logp": suggestion.descriptors.logp,
            "tpsa": suggestion.descriptors.tpsa,
            "hbd": suggestion.descriptors.hbd,
            "hba": suggestion.descriptors.hba,
            "rotatable_bonds": suggestion.descriptors.rotatable_bonds,
            "aromatic_rings": suggestion.descriptors.aromatic_rings,
            "num_rings": suggestion.descriptors.num_rings,
            "num_heavy_atoms": suggestion.descriptors.num_heavy_atoms,
            "num_heteroatoms": suggestion.descriptors.num_heteroatoms,
            "fraction_csp3": suggestion.descriptors.fraction_csp3,
        },
    }


def compute_method_signature(column_type: str, ph: float | None, modifier: str | None) -> str:
    """Stable hash signature for ML model keying."""
    raw = f"{column_type}|{ph or ''}|{modifier or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def create_method(
    db: AsyncSession, owner_id: uuid.UUID | None, data: MethodCreate
) -> Method:
    signature = data.method_signature or compute_method_signature(
        data.column_type, data.ph, data.mobile_phase_b
    )
    method = Method(
        owner_id=owner_id,
        name=data.name,
        column_type=data.column_type,
        column_dims=data.column_dims,
        mobile_phase_a=data.mobile_phase_a,
        mobile_phase_b=data.mobile_phase_b,
        additive=data.additive,
        ph=data.ph,
        gradient_table=data.gradient_table,  # type: ignore[arg-type]
        flow_rate_ml_min=data.flow_rate_ml_min,
        temperature_c=data.temperature_c,
        method_signature=signature,
        compounds_smiles=data.compounds_smiles,  # type: ignore[arg-type]
    )
    db.add(method)
    await db.commit()
    await db.refresh(method)
    return method


async def get_method(db: AsyncSession, method_id: uuid.UUID) -> Method | None:
    return await db.get(Method, method_id)


async def list_methods(
    db: AsyncSession, owner_id: uuid.UUID | None, limit: int = 50, offset: int = 0
) -> list[Method]:
    stmt = select(Method).order_by(Method.created_at.desc())
    if owner_id is not None:
        stmt = stmt.where(Method.owner_id == owner_id)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_method(db: AsyncSession, method_id: uuid.UUID) -> bool:
    method = await db.get(Method, method_id)
    if method is None:
        return False
    await db.delete(method)
    await db.commit()
    return True


def simulate_gradient(data: GradientSimulateRequest) -> dict[str, Any]:
    """Predict RT for a gradient, using calibration runs if provided, else heuristic."""
    if data.calibration_runs and len(data.calibration_runs) >= 2:
        runs = [
            CalibrationRun(
                gradient_time_s=r["gradient_time_s"],
                phi_start=r["phi_start"],
                phi_end=r["phi_end"],
                observed_rt_s=r["observed_rt_s"],
            )
            for r in data.calibration_runs
        ]
        params = fit_lss(runs)
        method = "lss_fit"
    else:
        params = heuristic_lss_params(
            data.logp,
            mw=data.mw,
            tpsa=data.tpsa,
            hbd=data.hbd,
            hba=data.hba,
            column_type=data.column_type,
        )
        method = "heuristic"

    rt = predict_rt_from_gradient(
        params,
        data.gradient_table,
        flow_rate_ml_min=data.flow_rate_ml_min,
        column_void_volume_ml=data.column_void_volume_ml,
    )
    return {
        "predicted_rt_s": rt,
        "gradient_table": data.gradient_table,
        "method": method,
    }


def simulate_chromatogram_from_request(data: ChromatogramRequest) -> dict[str, Any]:
    peaks = [
        Peak(
            rt_s=p["rt_s"],
            width_s=p.get("width_s") or default_peak_width(p["rt_s"]),
            height=p.get("height", 1.0),
            label=p.get("label", ""),
            color=p.get("color", ""),
        )
        for p in data.peaks
    ]
    return simulate_chromatogram(peaks, total_time_s=data.total_time_s, n_points=data.n_points)


# --- Multi-compound method optimization ---

def suggest_multi(
    smiles_list: list[str],
    ionization_mode: str = "ESI+",
    retention_goal: str = "neutral",
    gradient_time_min: float = 25.0,
    flow_rate_ml_min: float = 0.4,
    column_type: str | None = None,
) -> dict[str, Any]:
    """Suggest a method that resolves a mixture of compounds.

    Returns per-compound suggestions, a merged gradient, predicted RTs,
    and pairwise resolution matrix with co-elution flags.
    """
    from app.core.chem.parser import ChemParseError, parse_mol
    from app.core.rules.engine import suggest_method
    from app.core.rules.gradient import heuristic_gradient
    from app.core.lss.gradient_sim import (
        heuristic_lss_params,
        predict_rt_from_gradient,
    )
    from app.core.lss.chromatogram import default_peak_width, resolution

    per_compound: list[dict[str, Any]] = []
    for i, smi in enumerate(smiles_list):
        try:
            parsed = parse_mol(smi)
        except ChemParseError:
            per_compound.append({"index": i, "error": "invalid SMILES", "smiles": smi})
            continue

        sugg = suggest_method(
            parsed.mol,
            ionization_mode=ionization_mode,
            retention_goal=retention_goal,
            gradient_time_min=gradient_time_min,
            flow_rate_ml_min=flow_rate_ml_min,
            column_type_override=column_type,
        )
        per_compound.append(
            {
                "index": i,
                "smiles": smi,
                "column": {
                    "column_type": sugg.column.column_type,
                    "rationale": sugg.column.rationale,
                },
                "pka_values": sugg.pka_values,
                "logp": sugg.descriptors.logp,
                "logd": sugg.logd_at_recommended_ph,
                "mw": sugg.descriptors.mw,
                "tpsa": sugg.descriptors.tpsa,
                "hbd": sugg.descriptors.hbd,
                "hba": sugg.descriptors.hba,
                "rotatable_bonds": sugg.descriptors.rotatable_bonds,
                "aromatic_rings": sugg.descriptors.aromatic_rings,
                "num_rings": sugg.descriptors.num_rings,
            }
        )

    # Merge: use widest gradient range
    valid = [c for c in per_compound if "error" not in c]
    if not valid:
        return {"per_compound": per_compound, "gradient": {}, "resolution_matrix": []}

    b_starts = [c.get("logp", 2.0) for c in valid]
    # Use the most hydrophobic compound's gradient as base, extend to cover all
    max_logp = max(b_starts) if b_starts else 2.0
    merged_gradient = heuristic_gradient(max_logp, gradient_time_min, flow_rate_ml_min)

    # Determine effective column type (override or from per-compound suggestion)
    effective_column = column_type or valid[0].get("column", {}).get("column_type", "C18")

    # Predict RT for each compound on the merged gradient
    rts: list[tuple[int, float, float]] = []  # (index, rt, width)
    for c in valid:
        params = heuristic_lss_params(
            c.get("logp", 2.0),
            mw=c.get("mw", 200.0),
            tpsa=c.get("tpsa", 0.0),
            hbd=c.get("hbd", 0),
            hba=c.get("hba", 0),
            column_type=effective_column,
        )
        rt = predict_rt_from_gradient(
            params, merged_gradient["gradient_table"], flow_rate_ml_min
        )
        w = default_peak_width(rt)
        c["predicted_rt_s"] = rt
        c["peak_width_s"] = w
        rts.append((c["index"], rt, w))

    # Pairwise resolution
    resolution_matrix: list[dict[str, Any]] = []
    for i in range(len(rts)):
        for j in range(i + 1, len(rts)):
            idx_i, rt_i, w_i = rts[i]
            idx_j, rt_j, w_j = rts[j]
            rs = resolution(rt_i, w_i, rt_j, w_j)
            resolution_matrix.append(
                {
                    "compound_a": idx_i,
                    "compound_b": idx_j,
                    "rt_a": rt_i,
                    "rt_b": rt_j,
                    "resolution": rs,
                    "co_elution_risk": rs < 1.5,
                }
            )

    return {
        "per_compound": per_compound,
        "gradient": merged_gradient,
        "resolution_matrix": resolution_matrix,
        "co_elution_count": sum(1 for r in resolution_matrix if r["co_elution_risk"]),
    }


def optimize_gradient_separation(
    smiles_list: list[str],
    flow_rate_ml_min: float = 0.4,
    gradient_time_min: float = 20.0,
    column_type: str | None = None,
    ph: float = 2.7,
    temperature_c: float = 30.0,
) -> dict[str, Any]:
    """Search for the gradient (%B start/end/time) that maximizes separation.

    Uses a grid search over %B start (2-20), %B end (60-98), and gradient time
    (10-60 min). For each candidate, predicts RTs via LSS (with pH-adjusted
    logP and temperature factors) and scores the configuration using:
    - Minimum pairwise resolution (primary)
    - Separation space utilization (peaks spread across gradient window)
    - Penalties for void-volume elution or post-gradient elution

    Returns the best configuration with predicted RTs and resolution matrix.
    """
    import math
    from app.core.chem.parser import ChemParseError, parse_mol
    from app.core.rules.engine import suggest_method
    from app.core.lss.gradient_sim import (
        heuristic_lss_params,
        predict_rt_from_gradient,
    )
    from app.core.lss.chromatogram import default_peak_width, resolution

    # Parse all compounds and collect descriptors
    compounds: list[dict[str, Any]] = []
    for i, smi in enumerate(smiles_list):
        try:
            parsed = parse_mol(smi)
        except ChemParseError:
            continue
        sugg = suggest_method(
            parsed.mol,
            ionization_mode="ESI+",
            retention_goal="neutral",
            gradient_time_min=gradient_time_min,
            flow_rate_ml_min=flow_rate_ml_min,
            column_type_override=column_type,
        )
        compounds.append({
            "index": i,
            "smiles": smi,
            "logp": sugg.descriptors.logp,
            "mw": sugg.descriptors.mw,
            "tpsa": sugg.descriptors.tpsa,
            "hbd": sugg.descriptors.hbd,
            "hba": sugg.descriptors.hba,
            "pka_values": sugg.pka_values,
            "name": None,
        })

    if len(compounds) < 2:
        return suggest_multi(
            smiles_list,
            flow_rate_ml_min=flow_rate_ml_min,
            gradient_time_min=gradient_time_min,
            column_type=column_type,
        )

    # pH-adjusted logP (same model as frontend)
    def adjust_logp_for_ph(logp: float, pka_values: list[float] | None) -> float:
        if not pka_values:
            return logp
        pka = pka_values[0]
        is_acidic = pka < 7
        delta = ph - pka if is_acidic else pka - ph
        if delta <= 0:
            return logp
        penalty = min(3.0, math.log10(1 + 10 ** delta))
        return max(-2.0, logp - penalty)

    # Temperature factors (same model as frontend)
    temp_rt_factor = max(0.7, 1.0 - (temperature_c - 30) * 0.015)

    # Pre-compute effective logP for each compound
    for c in compounds:
        c["effective_logp"] = adjust_logp_for_ph(c["logp"], c.get("pka_values"))

    # Grid search parameters
    b_start_candidates = [2, 5, 8, 10, 15, 20, 25, 30]
    b_end_candidates = [50, 60, 70, 80, 90, 95, 98]
    time_candidates = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]

    best_config = None
    best_score = -1e9
    best_min_res = 0.0
    best_rts: list[tuple[int, float, float]] = []
    best_gradient: dict[str, Any] = {}

    effective_column = column_type or "C18"

    for b_start in b_start_candidates:
        for b_end in b_end_candidates:
            if b_end - b_start < 20:
                continue
            for g_time in time_candidates:
                t_total = g_time * 60
                grad_table = [
                    {"time_s": 0, "percent_b": b_start},
                    {"time_s": 60, "percent_b": b_start},
                    {"time_s": t_total - 120, "percent_b": b_end},
                    {"time_s": t_total, "percent_b": b_end},
                ]

                # Predict RT for each compound using pH-adjusted logP
                rts: list[tuple[int, float, float]] = []
                for c in compounds:
                    params = heuristic_lss_params(
                        c["effective_logp"],
                        mw=c.get("mw", 200.0),
                        tpsa=c.get("tpsa", 0.0),
                        hbd=c.get("hbd", 0),
                        hba=c.get("hba", 0),
                        column_type=effective_column,
                    )
                    rt = predict_rt_from_gradient(
                        params, grad_table, flow_rate_ml_min
                    )
                    rt *= temp_rt_factor
                    w = default_peak_width(rt)
                    rts.append((c["index"], rt, w))

                # Sort by RT
                rts_sorted = sorted(rts, key=lambda x: x[1])

                # Compute minimum adjacent resolution
                min_res = float("inf")
                for j in range(len(rts_sorted) - 1):
                    _, rt_a, w_a = rts_sorted[j]
                    _, rt_b, w_b = rts_sorted[j + 1]
                    rs = resolution(rt_a, w_a, rt_b, w_b)
                    if rs < min_res:
                        min_res = rs

                # Compute separation space utilization:
                # what fraction of the gradient window is used by the peaks?
                first_rt = rts_sorted[0][1]
                last_rt = rts_sorted[-1][1]
                useful_window = t_total - 60  # exclude initial hold
                spread = last_rt - first_rt
                utilization = spread / max(useful_window, 1.0)
                utilization = min(1.0, utilization)

                # Penalties
                penalty = 0.0
                for _, rt, _ in rts_sorted:
                    if rt < 60:  # void volume elution
                        penalty += 10.0
                    if rt > t_total:  # post-gradient elution
                        penalty += 5.0
                    if rt < 90:  # near-void (poor retention)
                        penalty += 2.0

                # Score: weighted combination of resolution + utilization - penalties
                # Resolution is primary (weight 3.0), utilization secondary (weight 1.0)
                # Prefer longer gradients slightly less (avoid always picking 60 min)
                time_penalty = (g_time - 20) * 0.02  # mild preference for shorter gradients
                score = min_res * 3.0 + utilization * 2.0 - penalty - time_penalty

                if score > best_score:
                    best_score = score
                    best_min_res = min_res
                    best_config = {
                        "percent_b_start": b_start,
                        "percent_b_end": b_end,
                        "gradient_time_min": g_time,
                    }
                    best_rts = rts
                    best_gradient = {
                        "gradient_table": grad_table,
                        "flow_rate_ml_min": flow_rate_ml_min,
                        "gradient_time_min": g_time,
                        "percent_b_start": b_start,
                        "percent_b_end": b_end,
                        "column_length_mm": 100,
                    }

    # Build the result using the best configuration
    per_compound: list[dict[str, Any]] = []
    for c in compounds:
        # Find the RT for this compound
        rt_entry = next((r for r in best_rts if r[0] == c["index"]), None)
        if rt_entry:
            _, rt, w = rt_entry
            per_compound.append({
                "index": c["index"],
                "smiles": c["smiles"],
                "logp": c["logp"],
                "predicted_rt_s": rt,
                "peak_width_s": w,
                "column": {"column_type": column_type or "C18", "rationale": "Optimized"},
            })

    # Build resolution matrix
    resolution_matrix: list[dict[str, Any]] = []
    for i in range(len(best_rts)):
        for j in range(i + 1, len(best_rts)):
            idx_i, rt_i, w_i = best_rts[i]
            idx_j, rt_j, w_j = best_rts[j]
            rs = resolution(rt_i, w_i, rt_j, w_j)
            resolution_matrix.append({
                "compound_a": idx_i,
                "compound_b": idx_j,
                "rt_a": rt_i,
                "rt_b": rt_j,
                "resolution": rs,
                "co_elution_risk": rs < 1.5,
            })

    return {
        "per_compound": per_compound,
        "gradient": best_gradient,
        "resolution_matrix": resolution_matrix,
        "co_elution_count": sum(1 for r in resolution_matrix if r["co_elution_risk"]),
        "optimization": {
            "percent_b_start": best_config["percent_b_start"],
            "percent_b_end": best_config["percent_b_end"],
            "gradient_time_min": best_config["gradient_time_min"],
            "min_resolution": best_min_res,
            "configurations_tested": len(b_start_candidates)
            * len(b_end_candidates)
            * len(time_candidates),
        },
    }

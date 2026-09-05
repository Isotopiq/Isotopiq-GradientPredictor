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
        dwell_volume_ml=data.dwell_volume_ml,
        dead_volume_ml=data.dead_volume_ml,
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
    """Predict RT for a gradient.

    Priority:
      1. PIRM (if column_id references a commercial column with phase data)
      2. LSS fit (if calibration runs provided)
      3. Heuristic LSS (fallback)

    If smiles + pH are provided, logD is computed server-side using
    multi-site Henderson-Hasselbalch (more accurate than the frontend
    single-pKa approximation).
    """
    # Compute logD from SMILES + pH if provided
    effective_logp = data.logp
    if data.smiles and data.ph is not None:
        try:
            from app.core.chem.parser import parse_mol
            from app.core.chem.logd import logd_at_ph

            mol = parse_mol(data.smiles).mol
            effective_logp = logd_at_ph(mol, data.ph, data.logp)
        except Exception:
            pass  # fall back to raw logP

    # 1. Try PIRM if a commercial column ID is provided
    if data.column_id:
        from app.core.chem.columns_db import get_column
        from app.core.ml.pirm_model import predict_retention as pirm_predict

        col = get_column(data.column_id)
        if col is not None and col.phase is not None:
            # Compute 3D descriptors if SMILES is available
            asph = 0.0
            rgyr = 0.0
            pmi_ratio = 0.0
            if data.smiles:
                try:
                    from app.core.chem.parser import parse_mol
                    from app.core.chem.descriptors import compute_descriptors
                    mol = parse_mol(data.smiles).mol
                    desc = compute_descriptors(mol)
                    if desc.descriptors_3d:
                        asph = desc.descriptors_3d.asphericity
                        rgyr = desc.descriptors_3d.radius_of_gyration
                        pmi_ratio = desc.descriptors_3d.pmi_ratio_13
                except Exception:
                    pass

            result = pirm_predict(
                column=col,
                logp=effective_logp,
                mw=data.mw,
                tpsa=data.tpsa,
                gradient_table=data.gradient_table,
                flow_rate_ml_min=data.flow_rate_ml_min,
                asphericity=asph,
                radius_of_gyration=rgyr,
                pmi_ratio_13=pmi_ratio,
                dwell_volume_ml=data.dwell_volume_ml,
                dead_volume_ml=data.dead_volume_ml,
            )
            return {
                "predicted_rt_s": result["predicted_rt_s"],
                "gradient_table": data.gradient_table,
                "method": "pirm",
                "confidence": result["confidence"],
                "extrapolating": result["extrapolating"],
                "rt_lower_s": result["rt_lower_s"],
                "rt_upper_s": result["rt_upper_s"],
            }

    # 2. LSS fit from calibration runs
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
        # 3. Heuristic LSS
        params = heuristic_lss_params(
            effective_logp,
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
        dwell_volume_ml=data.dwell_volume_ml,
        dead_volume_ml=data.dead_volume_ml,
    )
    return {
        "predicted_rt_s": rt,
        "gradient_table": data.gradient_table,
        "method": method,
    }


def simulate_chromatogram_from_request(data: ChromatogramRequest) -> dict[str, Any]:
    from app.core.lss.chromatogram import default_tailing
    peaks = [
        Peak(
            rt_s=p["rt_s"],
            width_s=p.get("width_s") or default_peak_width(p["rt_s"]),
            height=p.get("height", 1.0),
            label=p.get("label", ""),
            color=p.get("color", ""),
            tailing=p.get("tailing", default_tailing(p["rt_s"])),
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
    suitability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search for the gradient (%B start/end/time) that maximizes separation.

    Uses a grid search over %B start (2-20), %B end (60-98), and gradient time
    (10-60 min). For each candidate, predicts RTs via LSS (with pH-adjusted
    logP and temperature factors) and scores the configuration using:
    - Minimum pairwise resolution (primary)
    - Separation space utilization (peaks spread across gradient window)
    - Penalties for void-volume elution or post-gradient elution
    - F7: Suitability criteria (if provided)

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
        # Compute logD using multi-site Henderson-Hasselbalch
        from app.core.chem.logd import logd_at_ph
        logd = logd_at_ph(parsed.mol, ph, sugg.descriptors.logp)
        compounds.append({
            "index": i,
            "smiles": smi,
            "logp": sugg.descriptors.logp,
            "logd": logd,
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

    # Temperature factor using van 't Hoff (see F8)
    # ΔH/R ≈ -5000K for RP-LC (retention is exothermic: higher T → lower k → lower RT)
    # k(T2)/k(T1) = exp(ΔH/R * (1/T1 - 1/T2))
    delta_h_over_r = -5000.0  # K
    t1 = 303.15  # 30°C reference
    t2 = temperature_c + 273.15
    temp_rt_factor = math.exp(delta_h_over_r * (1.0 / t1 - 1.0 / t2))
    temp_rt_factor = max(0.5, min(2.0, temp_rt_factor))

    # Pre-compute effective logD for each compound (already done above)
    for c in compounds:
        c["effective_logp"] = c["logd"]

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

                # F7: Apply suitability criteria bonus/penalty
                if suitability:
                    from app.core.lss.suitability import SuitabilityCriteria, score_method
                    crit = SuitabilityCriteria(
                        min_resolution=suitability.get("min_resolution", 1.5),
                        max_run_time_min=suitability.get("max_run_time_min", 60.0),
                        min_k=suitability.get("min_k", 0.5),
                        max_k=suitability.get("max_k", 20.0),
                    )
                    t0_calc = 60.0 * 0.4 / max(flow_rate_ml_min, 0.01)  # approximate t0
                    suit_score = score_method(
                        [r[1] for r in rts_sorted],
                        [r[2] for r in rts_sorted],
                        t_total,
                        t0_calc,
                        crit,
                    )
                    # Bonus for high suitability, penalty for low
                    score += suit_score * 5.0
                    # Hard penalty if run time exceeds max
                    if g_time > crit.max_run_time_min:
                        score -= 20.0

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

    # F7: Evaluate suitability of the best method
    suitability_eval = None
    if suitability:
        from app.core.lss.suitability import SuitabilityCriteria, evaluate_method
        crit = SuitabilityCriteria(
            min_resolution=suitability.get("min_resolution", 1.5),
            max_run_time_min=suitability.get("max_run_time_min", 60.0),
            min_k=suitability.get("min_k", 0.5),
            max_k=suitability.get("max_k", 20.0),
        )
        t0_calc = 60.0 * 0.4 / max(flow_rate_ml_min, 0.01)
        best_rts_sorted = sorted(best_rts, key=lambda x: x[1])
        eval_result = evaluate_method(
            [r[1] for r in best_rts_sorted],
            [r[2] for r in best_rts_sorted],
            best_gradient.get("gradient_table", [{}])[-1].get("time_s", t_total) if best_gradient else t_total,
            t0_calc,
            crit,
        )
        suitability_eval = eval_result.to_dict()

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
        "suitability": suitability_eval,
    }


def analyze_robustness(
    smiles_list: list[str],
    gradient_table: list[dict],
    flow_rate_ml_min: float = 0.4,
    ph: float = 2.7,
    temperature_c: float = 30.0,
    column_type: str = "C18",
) -> dict[str, Any]:
    """Analyze method robustness by perturbing pH, temperature, and flow.

    For each perturbation (±5%), predicts RTs for all compounds and computes
    the change in minimum pairwise resolution. Identifies which parameters
    and compounds are most sensitive.
    """
    import math
    from app.core.chem.parser import ChemParseError, parse_mol
    from app.core.chem.logd import logd_at_ph
    from app.core.rules.engine import suggest_method
    from app.core.lss.gradient_sim import (
        heuristic_lss_params,
        predict_rt_from_gradient,
    )
    from app.core.lss.chromatogram import default_peak_width, resolution

    # Parse compounds
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
            gradient_time_min=20.0,
            flow_rate_ml_min=flow_rate_ml_min,
            column_type_override=column_type,
        )
        compounds.append({
            "index": i,
            "smiles": smi,
            "mol": parsed.mol,
            "logp": sugg.descriptors.logp,
            "mw": sugg.descriptors.mw,
            "tpsa": sugg.descriptors.tpsa,
            "hbd": sugg.descriptors.hbd,
            "hba": sugg.descriptors.hba,
        })

    if len(compounds) < 2:
        return {
            "perturbations": [],
            "sensitivity_score": 0.0,
            "most_sensitive_compound": -1,
            "message": "Need at least 2 compounds for robustness analysis",
        }

    # van 't Hoff temperature factor (negative: RP-LC retention is exothermic)
    delta_h_over_r = -5000.0
    t1 = 303.15

    def predict_rts(perturbed_ph: float, perturbed_temp: float, perturbed_flow: float) -> list[float]:
        rts = []
        for c in compounds:
            logd = logd_at_ph(c["mol"], perturbed_ph, c["logp"])
            params = heuristic_lss_params(
                logd,
                mw=c["mw"],
                tpsa=c["tpsa"],
                hbd=c["hbd"],
                hba=c["hba"],
                column_type=column_type,
            )
            rt = predict_rt_from_gradient(params, gradient_table, flow_rate_ml_min=perturbed_flow)
            # Temperature correction
            t2 = perturbed_temp + 273.15
            temp_factor = math.exp(delta_h_over_r * (1.0 / t1 - 1.0 / t2))
            temp_factor = max(0.5, min(2.0, temp_factor))
            rts.append(rt * temp_factor)
        return rts

    def min_resolution(rts: list[float]) -> float:
        sorted_rts = sorted(rts)
        min_rs = float("inf")
        for j in range(len(sorted_rts) - 1):
            w1 = default_peak_width(sorted_rts[j])
            w2 = default_peak_width(sorted_rts[j + 1])
            rs = resolution(sorted_rts[j], w1, sorted_rts[j + 1], w2)
            if rs < min_rs:
                min_rs = rs
        return min_rs if min_rs != float("inf") else 0.0

    # Baseline
    baseline_rts = predict_rts(ph, temperature_c, flow_rate_ml_min)
    baseline_min_res = min_resolution(baseline_rts)

    # Perturbations: ±5% for each parameter
    perturbations = []
    perturbation_specs = [
        ("pH", "+0.2", ph + 0.2, temperature_c, flow_rate_ml_min),
        ("pH", "-0.2", ph - 0.2, temperature_c, flow_rate_ml_min),
        ("Temperature", "+3°C", ph, temperature_c + 3, flow_rate_ml_min),
        ("Temperature", "-3°C", ph, temperature_c - 3, flow_rate_ml_min),
        ("Flow Rate", "+5%", ph, temperature_c, flow_rate_ml_min * 1.05),
        ("Flow Rate", "-5%", ph, temperature_c, flow_rate_ml_min * 0.95),
    ]

    for param, delta, p_ph, p_temp, p_flow in perturbation_specs:
        rts = predict_rts(p_ph, p_temp, p_flow)
        min_res = min_resolution(rts)
        change = min_res - baseline_min_res
        perturbations.append({
            "parameter": param,
            "delta": delta,
            "rts": [round(r, 2) for r in rts],
            "min_resolution": round(min_res, 3),
            "resolution_change": round(change, 3),
        })

    # Overall sensitivity score: average absolute resolution change
    avg_change = sum(abs(p["resolution_change"]) for p in perturbations) / len(perturbations)
    sensitivity_score = round(avg_change, 3)

    # Find most sensitive compound: the one with largest RT variance across perturbations
    rt_variances = []
    for i in range(len(compounds)):
        rts_for_compound = [p["rts"][i] for p in perturbations if i < len(p["rts"])]
        if rts_for_compound:
            mean_rt = sum(rts_for_compound) / len(rts_for_compound)
            variance = sum((r - mean_rt) ** 2 for r in rts_for_compound) / len(rts_for_compound)
            rt_variances.append((i, variance))
    most_sensitive = max(rt_variances, key=lambda x: x[1])[0] if rt_variances else -1

    return {
        "perturbations": perturbations,
        "sensitivity_score": sensitivity_score,
        "most_sensitive_compound": most_sensitive,
        "baseline_min_resolution": round(baseline_min_res, 3),
        "baseline_rts": [round(r, 2) for r in baseline_rts],
    }

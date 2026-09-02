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
        params = heuristic_lss_params(data.logp)
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

    # Predict RT for each compound on the merged gradient
    rts: list[tuple[int, float, float]] = []  # (index, rt, width)
    for c in valid:
        params = heuristic_lss_params(c.get("logp", 2.0))
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

"""Rules engine orchestrator: compound descriptors -> full method suggestion."""
from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem

from app.core.chem.descriptors import DescriptorResult, compute_descriptors
from app.core.chem.logd import logd_at_ph
from app.core.chem.pka import estimate_pka_sites, estimate_pka_values
from app.core.rules.additive import AdditiveSuggestion, suggest_additive
from app.core.rules.column import ColumnSuggestion, suggest_column
from app.core.rules.gradient import heuristic_gradient
from app.core.rules.ph import PhSuggestion, suggest_ph


@dataclass(frozen=True)
class MethodSuggestion:
    column: ColumnSuggestion
    ph: PhSuggestion
    additive: AdditiveSuggestion
    gradient: dict
    descriptors: DescriptorResult
    pka_values: list[float]
    logd_at_recommended_ph: float
    ionizable: bool
    permanently_charged: bool


def suggest_method(
    mol: Chem.Mol,
    ionization_mode: str = "ESI+",
    retention_goal: str = "neutral",
    gradient_time_min: float = 20.0,
    flow_rate_ml_min: float = 0.4,
    column_type_override: str | None = None,
) -> MethodSuggestion:
    """Produce a full rules-based method suggestion for a single compound.

    If *column_type_override* is provided, the rules engine will use that
    column type instead of the heuristic recommendation, while still
    computing all other parameters (pH, additive, gradient) normally.
    """
    descriptors = compute_descriptors(mol)
    pka_sites = estimate_pka_sites(mol)
    pka_values = estimate_pka_values(mol)
    ionizable = bool(pka_sites)

    # Permanently charged heuristic: quaternary ammonium / sulfonate
    permanently_charged = _is_permanently_charged(mol)

    ph_suggestion = suggest_ph(pka_values, retention_goal=retention_goal)
    logd = logd_at_ph(mol, ph_suggestion.recommended_ph, descriptors.logp)

    if column_type_override:
        column = ColumnSuggestion(
            column_type=column_type_override,
            rationale=f"User-selected column: {column_type_override}. "
            "Other parameters computed from molecular properties.",
            alternatives=[],
        )
    else:
        column = suggest_column(
            logp=descriptors.logp,
            logd=logd,
            tpsa=descriptors.tpsa,
            ionizable=ionizable,
            max_pka_gap=max(pka_values) - min(pka_values) if pka_values else 0.0,
        )

    additive = suggest_additive(
        ph=ph_suggestion.recommended_ph,
        ionization_mode=ionization_mode,
        ionizable=ionizable,
        permanently_charged=permanently_charged,
    )

    gradient = heuristic_gradient(
        logp=descriptors.logp,
        gradient_time_min=gradient_time_min,
        flow_rate_ml_min=flow_rate_ml_min,
    )

    return MethodSuggestion(
        column=column,
        ph=ph_suggestion,
        additive=additive,
        gradient=gradient,
        descriptors=descriptors,
        pka_values=pka_values,
        logd_at_recommended_ph=logd,
        ionizable=ionizable,
        permanently_charged=permanently_charged,
    )


def _is_permanently_charged(mol: Chem.Mol) -> bool:
    """Heuristic: quaternary ammonium or sulfonate present."""
    patterns = [
        Chem.MolFromSmarts("[NX4+]"),
        Chem.MolFromSmarts("[SX4](=O)(=O)[O-]"),
        Chem.MolFromSmarts("[PX4+]"),
    ]
    return any(p is not None and mol.HasSubstructMatch(p) for p in patterns)

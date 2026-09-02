"""Mobile phase additive suggestion rules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdditiveSuggestion:
    additive: str
    rationale: str
    alternatives: list[str]


def suggest_additive(
    ph: float, ionization_mode: str, ionizable: bool, permanently_charged: bool
) -> AdditiveSuggestion:
    """Suggest a mobile phase additive.

    ionization_mode: "ESI+" | "ESI-" | "APCI" | "any"
    """
    if permanently_charged:
        return AdditiveSuggestion(
            additive="TFA 0.1% (ion-pair)",
            rationale=(
                "Permanently charged species need ion-pairing for RP retention. "
                "TFA is common but suppresses ESI; consider HFIP or perfluoropentanoic acid for MS."
            ),
            alternatives=["HFIP 0.1%", "perfluoropentanoic acid 5mM"],
        )

    if ionization_mode == "ESI+":
        return AdditiveSuggestion(
            additive="formic acid 0.1%",
            rationale=(
                f"pH {ph:.1f} with 0.1% formic acid is the standard ESI+ compatible volatile additive. "
                "Promotes protonation of basic analytes."
            ),
            alternatives=["acetic acid 0.1%", "ammonium formate 5mM"],
        )

    if ionization_mode == "ESI-":
        if ph > 7.0:
            return AdditiveSuggestion(
                additive="ammonium bicarbonate 10mM",
                rationale=(
                    f"pH {ph:.1f} (basic) with ammonium bicarbonate suits ESI- for deprotonated acids. "
                    "Volatile, MS-compatible."
                ),
                alternatives=["ammonium acetate 10mM", "NH4OH 0.1%"],
            )
        return AdditiveSuggestion(
            additive="ammonium acetate 10mM",
            rationale=(
                f"pH {ph:.1f} with ammonium acetate is a volatile ESI- compatible buffer. "
                "Useful for acidic analytes near neutral pH."
            ),
            alternatives=["ammonium formate 10mM", "acetic acid 0.1%"],
        )

    # Default / APCI / any
    if ionizable:
        return AdditiveSuggestion(
            additive="ammonium formate 10mM",
            rationale=(
                "Generic volatile buffer compatible with both ESI polarities and APCI. "
                "Adjust pH with formic acid or ammonia."
            ),
            alternatives=["ammonium acetate 10mM", "formic acid 0.1%"],
        )

    return AdditiveSuggestion(
        additive="formic acid 0.1%",
        rationale="Low-background volatile additive, standard default for non-ionizable analytes.",
        alternatives=["acetic acid 0.1%", "none"],
    )

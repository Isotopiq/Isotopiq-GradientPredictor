"""Column chemistry suggestion rules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnSuggestion:
    column_type: str  # C18 | phenyl | HILIC | ion_pair | other
    rationale: str
    alternatives: list[str]


def suggest_column(logp: float, logd: float, tpsa: float, ionizable: bool, max_pka_gap: float) -> ColumnSuggestion:
    """Suggest a starting column based on lipophilicity and ionizability.

    Heuristics (documented, conservative):
      - logD < -1 or TPSA > 120  -> HILIC (very polar)
      - permanently charged / large ionization gap -> ion_pair
      - logP 2-5, moderate polarity -> C18 (default workhorse)
      - logP > 5 -> C18 (retentive, may need high %B)
      - aromatic-rich (caller may pass logp as proxy) -> phenyl as alternative
    """
    if logd < -1.0 or tpsa > 120.0:
        return ColumnSuggestion(
            column_type="HILIC",
            rationale=(
                f"Very polar (logD={logd:.1f}, TPSA={tpsa:.0f}). "
                "HILIC retains polar/ionized analytes that elute in void on RP."
            ),
            alternatives=["ion_pair", "C18"],
        )

    if ionizable and max_pka_gap > 4.0:
        return ColumnSuggestion(
            column_type="ion_pair",
            rationale=(
                "Permanently / strongly ionized species. "
                "Ion-pairing improves retention on RP without HILIC's MS-friendliness issues."
            ),
            alternatives=["HILIC", "C18"],
        )

    # Default
    return ColumnSuggestion(
        column_type="C18",
        rationale=(
            f"Moderate lipophilicity (logP={logp:.1f}, logD={logd:.1f}). "
            "C18 is the standard reversed-phase workhorse with broad retention."
        ),
        alternatives=["phenyl", "C8"],
    )

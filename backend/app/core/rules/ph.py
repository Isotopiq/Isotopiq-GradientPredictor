"""Mobile phase pH recommendation rules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhSuggestion:
    recommended_ph: float
    rationale: str
    warning_zones: list[tuple[float, float]]
    """pKa ± 1.5 ranges where peak shape is typically poor."""


def suggest_ph(pka_values: list[float], retention_goal: str = "neutral") -> PhSuggestion:
    """Recommend a mobile phase pH based on pKa(s).

    retention_goal:
      - "neutral": keep analyte neutral (better peak shape on RP)
      - "ionized": keep analyte ionized (for MS sensitivity / HILIC)

    Heuristic: pick a pH at least 2 units away from the nearest pKa in the
    desired direction. If no pKa, default to pH 2.5 (acidic, MS-friendly).
    """
    warning_zones = [(p - 1.5, p + 1.5) for p in pka_values]

    if not pka_values:
        return PhSuggestion(
            recommended_ph=2.5,
            rationale="No ionizable groups detected. pH 2.5 (acidic, MS-friendly) is a safe default.",
            warning_zones=warning_zones,
        )

    nearest = min(pka_values, key=lambda p: abs(p - 7.0))

    if retention_goal == "ionized":
        # For acids: pH > pKa + 2 (deprotonated). For bases: pH < pKa - 2 (protonated).
        # Without acid/base classification here, pick the side that ionizes the most sites.
        # Simplified: choose pH 2 units below the lowest pKa (bases ionized) or
        # 2 units above the highest (acids ionized). Default to low pH for ESI+ compatibility.
        candidate_low = nearest - 2.0
        candidate_high = max(pka_values) + 2.0
        # Prefer low pH for ESI+ unless that lands in a warning zone
        if not _in_any_zone(candidate_low, warning_zones):
            return PhSuggestion(
                recommended_ph=round(max(2.0, candidate_low), 1),
                rationale=(
                    f"Ionization goal: pH set ~2 units below nearest pKa ({nearest}). "
                    "Bases protonated (ESI+ friendly)."
                ),
                warning_zones=warning_zones,
            )
        return PhSuggestion(
            recommended_ph=round(min(11.0, candidate_high), 1),
            rationale=(
                f"Ionization goal: pH set ~2 units above highest pKa ({max(pka_values)}). "
                "Acids deprotonated (ESI- friendly)."
            ),
            warning_zones=warning_zones,
        )

    # neutral goal: pick pH 2 units away from nearest pKa, preferring acidic side
    candidate_low = nearest - 2.0
    candidate_high = nearest + 2.0
    if 2.0 <= candidate_low <= 10.0 and not _in_any_zone(candidate_low, warning_zones):
        return PhSuggestion(
            recommended_ph=round(candidate_low, 1),
            rationale=(
                f"Neutral goal: pH ~2 units below nearest pKa ({nearest}) keeps acids protonated. "
                "Better peak shape on RP."
            ),
            warning_zones=warning_zones,
        )
    if 2.0 <= candidate_high <= 10.0 and not _in_any_zone(candidate_high, warning_zones):
        return PhSuggestion(
            recommended_ph=round(candidate_high, 1),
            rationale=(
                f"Neutral goal: pH ~2 units above nearest pKa ({nearest}) keeps bases deprotonated. "
                "Better peak shape on RP."
            ),
            warning_zones=warning_zones,
        )

    # Fallback
    return PhSuggestion(
        recommended_ph=2.5,
        rationale="Could not place pH safely away from all pKa values. Defaulting to pH 2.5.",
        warning_zones=warning_zones,
    )


def _in_any_zone(ph: float, zones: list[tuple[float, float]]) -> bool:
    return any(lo <= ph <= hi for lo, hi in zones)

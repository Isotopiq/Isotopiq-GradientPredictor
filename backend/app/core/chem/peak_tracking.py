"""Peak tracking / matching between chromatograms.

Matches peaks across multiple chromatograms using:
- Retention time proximity
- Peak area ratios
- UV/spectral similarity (where available)
- Solvent front filtering
- Concentration/quality thresholds

Returns match confidence and unmatched peaks.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class TrackPeak:
    """A peak for tracking."""
    rt_min: float
    area: float = 0.0
    height: float = 0.0
    width_min: float = 0.0
    uv_spectrum: list[float] | None = None  # absorbance at multiple wavelengths
    compound_name: str = ""
    chromatogram_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rt_min": round(self.rt_min, 4),
            "area": round(self.area, 2),
            "height": round(self.height, 2),
            "width_min": round(self.width_min, 4),
            "compound_name": self.compound_name,
            "chromatogram_id": self.chromatogram_id,
        }


@dataclass
class PeakMatch:
    """A matched peak across chromatograms."""
    peaks: list[TrackPeak]
    confidence: float  # 0..1
    mean_rt: float
    rt_std: float
    mean_area: float
    area_cv: float  # coefficient of variation
    matched: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "peaks": [p.to_dict() for p in self.peaks],
            "confidence": round(self.confidence, 4),
            "mean_rt": round(self.mean_rt, 4),
            "rt_std": round(self.rt_std, 4),
            "mean_area": round(self.mean_area, 2),
            "area_cv": round(self.area_cv, 4),
            "matched": self.matched,
        }


@dataclass
class PeakTrackingResult:
    """Result of peak tracking across chromatograms."""
    matches: list[PeakMatch]
    unmatched: list[TrackPeak]
    n_chromatograms: int
    n_matched_groups: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "unmatched": [p.to_dict() for p in self.unmatched],
            "n_chromatograms": self.n_chromatograms,
            "n_matched_groups": self.n_matched_groups,
        }


def track_peaks(
    chromatograms: dict[str, list[TrackPeak]],
    rt_tolerance_min: float = 0.15,
    area_tolerance_pct: float = 50.0,
    min_confidence: float = 0.3,
    solvent_front_rt_min: float = 0.5,
    min_area: float = 1000.0,
) -> PeakTrackingResult:
    """Track peaks across multiple chromatograms.

    chromatograms: {chromatogram_id: [peaks, ...]}

    Matching algorithm:
    1. Filter out solvent front peaks and low-area noise
    2. Sort all peaks by RT
    3. Group peaks within rt_tolerance across chromatograms
    4. Score each group by RT consistency and area consistency
    5. Apply UV spectral matching if available
    """
    all_peaks: list[TrackPeak] = []
    for chrom_id, peaks in chromatograms.items():
        for p in peaks:
            # Filter: skip solvent front and very small peaks
            if p.rt_min < solvent_front_rt_min:
                continue
            if p.area > 0 and p.area < min_area:
                continue
            p.chromatogram_id = chrom_id
            all_peaks.append(p)

    if not all_peaks:
        return PeakTrackingResult(
            matches=[], unmatched=[], n_chromatograms=len(chromatograms), n_matched_groups=0,
        )

    # Sort by RT
    all_peaks.sort(key=lambda p: p.rt_min)

    # Group peaks by RT proximity
    groups: list[list[TrackPeak]] = []
    current_group: list[TrackPeak] = [all_peaks[0]]

    for i in range(1, len(all_peaks)):
        if all_peaks[i].rt_min - current_group[-1].rt_min <= rt_tolerance_min:
            current_group.append(all_peaks[i])
        else:
            groups.append(current_group)
            current_group = [all_peaks[i]]
    groups.append(current_group)

    # Score each group
    matches: list[PeakMatch] = []
    unmatched: list[TrackPeak] = []

    for group in groups:
        if len(group) < 2:
            unmatched.extend(group)
            continue

        # Check that peaks are from different chromatograms
        chrom_ids = set(p.chromatogram_id for p in group)
        if len(chrom_ids) < 2:
            # Same chromatogram — not a match
            unmatched.extend(group)
            continue

        # Compute RT statistics
        rts = [p.rt_min for p in group]
        mean_rt = sum(rts) / len(rts)
        if len(rts) > 1:
            rt_std = math.sqrt(sum((rt - mean_rt) ** 2 for rt in rts) / len(rts))
        else:
            rt_std = 0.0

        # RT confidence: 1.0 if all at same RT, 0 if at tolerance limit
        rt_confidence = max(0.0, 1.0 - rt_std / rt_tolerance_min)

        # Area consistency (if areas available)
        areas = [p.area for p in group if p.area > 0]
        area_confidence = 1.0
        area_cv = 0.0
        mean_area = 0.0
        if len(areas) >= 2:
            mean_area = sum(areas) / len(areas)
            if mean_area > 0:
                area_cv = math.sqrt(sum((a - mean_area) ** 2 for a in areas) / len(areas)) / mean_area
                # Area confidence: 1.0 if CV=0, 0 if CV > area_tolerance/100
                area_tol = area_tolerance_pct / 100.0
                area_confidence = max(0.0, 1.0 - area_cv / area_tol)

        # UV spectral matching (if available)
        uv_confidence = 1.0
        uv_spectra = [p.uv_spectrum for p in group if p.uv_spectrum]
        if len(uv_spectra) >= 2:
            # Compute pairwise cosine similarity
            similarities = []
            for i in range(len(uv_spectra)):
                for j in range(i + 1, len(uv_spectra)):
                    sim = _cosine_similarity(uv_spectra[i], uv_spectra[j])
                    similarities.append(sim)
            uv_confidence = sum(similarities) / len(similarities) if similarities else 1.0

        # Overall confidence: weighted combination
        # RT is primary (weight 0.5), area secondary (0.3), UV (0.2)
        overall = rt_confidence * 0.5 + area_confidence * 0.3 + uv_confidence * 0.2

        if overall >= min_confidence:
            matches.append(PeakMatch(
                peaks=group,
                confidence=overall,
                mean_rt=mean_rt,
                rt_std=rt_std,
                mean_area=mean_area,
                area_cv=area_cv,
                matched=True,
            ))
        else:
            unmatched.extend(group)

    # Sort matches by confidence descending
    matches.sort(key=lambda m: m.confidence, reverse=True)

    return PeakTrackingResult(
        matches=matches,
        unmatched=unmatched,
        n_chromatograms=len(chromatograms),
        n_matched_groups=len(matches),
    )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(a[i] * b[i] for i in range(len(a)))
    norm_a = math.sqrt(sum(v ** 2 for v in a))
    norm_b = math.sqrt(sum(v ** 2 for v in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))

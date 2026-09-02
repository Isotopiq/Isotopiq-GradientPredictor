"""Simulated chromatogram (Gaussian peaks) for preview."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Peak:
    rt_s: float
    width_s: float
    height: float
    label: str = ""
    color: str = ""


def gaussian(x: float, center: float, width: float, height: float) -> float:
    """Gaussian peak value at x."""
    sigma = width / (2.0 * math.sqrt(2.0 * math.log(2.0)))  # FWHM -> sigma
    if sigma <= 0:
        return 0.0
    return height * math.exp(-((x - center) ** 2) / (2.0 * sigma**2))


def simulate_chromatogram(
    peaks: list[Peak],
    total_time_s: float,
    n_points: int = 500,
) -> dict:
    """Return {times: [...], intensities: [...], peaks: [...]} for charting."""
    times = [i * total_time_s / (n_points - 1) for i in range(n_points)]
    intensities = [0.0] * n_points
    for peak in peaks:
        for i, t in enumerate(times):
            intensities[i] += gaussian(t, peak.rt_s, peak.width_s, peak.height)
    return {
        "times": times,
        "intensities": intensities,
        "peaks": [
            {
                "rt_s": p.rt_s,
                "width_s": p.width_s,
                "height": p.height,
                "label": p.label,
                "color": p.color,
            }
            for p in peaks
        ],
    }


def default_peak_width(rt_s: float) -> float:
    """Heuristic peak width (FWHM) from retention time.

    Typical plate count ~10000-20000; width grows with sqrt(rt).
    """
    n_plates = 12000.0
    if rt_s <= 0:
        return 2.0
    return max(2.0, rt_s / math.sqrt(n_plates) * 4.0)


def resolution(rt1: float, w1: float, rt2: float, w2: float) -> float:
    """Chromatographic resolution Rs between two peaks."""
    if w1 + w2 <= 0:
        return 0.0
    return 2.0 * abs(rt2 - rt1) / (w1 + w2)

"""Simulated chromatogram (EMG peaks) for preview."""
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
    tailing: float = 1.5  # EMG tau/sigma ratio (1.0=symmetric, >1=tailing)


def gaussian(x: float, center: float, width: float, height: float) -> float:
    """Gaussian peak value at x (kept for backward compatibility)."""
    sigma = width / (2.0 * math.sqrt(2.0 * math.log(2.0)))  # FWHM -> sigma
    if sigma <= 0:
        return 0.0
    return height * math.exp(-((x - center) ** 2) / (2.0 * sigma**2))


def emg(x: float, center: float, width: float, height: float, tau_ratio: float = 1.5) -> float:
    """Exponentially Modified Gaussian peak value at x.

    The EMG is the standard model for chromatographic peaks with tailing.
    It is the convolution of a Gaussian with an exponential decay function.

    Args:
        x: Time point.
        center: Peak center (retention time).
        width: FWHM of the Gaussian component.
        height: Peak height.
        tau_ratio: tau/sigma ratio (1.0 = symmetric Gaussian, >1 = tailing).

    Returns:
        Peak intensity at x.
    """
    sigma = width / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    if sigma <= 0:
        return 0.0

    # tau controls the exponential tail
    tau = sigma * max(0.01, tau_ratio - 1.0)

    # EMG via the error function approximation
    # h(x) = (height/2) * exp((sigma^2/(2*tau) + (center-x)/tau)) * erfc((center + sigma^2/tau - x) / (sigma*sqrt(2)))
    z = (center + sigma * sigma / tau - x) / (sigma * math.sqrt(2.0))
    arg = sigma * sigma / (2.0 * tau) + (center - x) / tau

    # Prevent overflow
    if arg > 50:
        return 0.0
    if arg < -50:
        return 0.0

    try:
        erfc_val = math.erfc(z)
    except (OverflowError, ValueError):
        return 0.0

    return (height / 2.0) * math.exp(arg) * erfc_val


def simulate_chromatogram(
    peaks: list[Peak],
    total_time_s: float,
    n_points: int = 500,
) -> dict:
    """Return {times: [...], intensities: [...], peaks: [...]} for charting.

    Uses EMG peak shape for realistic chromatographic tailing.
    """
    times = [i * total_time_s / (n_points - 1) for i in range(n_points)]
    intensities = [0.0] * n_points
    for peak in peaks:
        for i, t in enumerate(times):
            intensities[i] += emg(t, peak.rt_s, peak.width_s, peak.height, peak.tailing)
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
                "tailing": p.tailing,
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


def default_tailing(rt_s: float) -> float:
    """Heuristic tailing factor (USP) from retention time.

    Early-eluting peaks tend to be more symmetric; later peaks show
    more tailing due to secondary interactions with silanols.
    """
    if rt_s <= 0:
        return 1.0
    # Base tailing of 1.2, increasing slightly with retention
    return min(2.5, 1.2 + rt_s / 600.0)


def resolution(rt1: float, w1: float, rt2: float, w2: float) -> float:
    """Chromatographic resolution Rs between two peaks."""
    if w1 + w2 <= 0:
        return 0.0
    return 2.0 * abs(rt2 - rt1) / (w1 + w2)

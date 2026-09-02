"""Heuristic starting gradient from logP."""
from __future__ import annotations


def heuristic_gradient(
    logp: float,
    gradient_time_min: float = 20.0,
    flow_rate_ml_min: float = 0.4,
    column_length_mm: int = 100,
) -> dict:
    """Return a starting gradient table + conditions based on logP.

    Returns dict with: gradient_table [{time_s, percent_b}], flow_rate_ml_min, gradient_time_min
    """
    # %B start/end heuristics from logP
    if logp < 1.0:
        b_start, b_end = 2.0, 60.0
    elif logp < 3.0:
        b_start, b_end = 5.0, 80.0
    elif logp < 5.0:
        b_start, b_end = 10.0, 95.0
    else:
        b_start, b_end = 20.0, 98.0

    t_total = gradient_time_min * 60.0
    # 1 min hold at start, linear ramp, 2 min hold at end
    t0 = 60.0
    t1 = t_total - 120.0
    t2 = t_total

    gradient_table = [
        {"time_s": 0.0, "percent_b": b_start},
        {"time_s": t0, "percent_b": b_start},
        {"time_s": t1, "percent_b": b_end},
        {"time_s": t2, "percent_b": b_end},
    ]

    return {
        "gradient_table": gradient_table,
        "flow_rate_ml_min": flow_rate_ml_min,
        "gradient_time_min": gradient_time_min,
        "percent_b_start": b_start,
        "percent_b_end": b_end,
        "column_length_mm": column_length_mm,
    }

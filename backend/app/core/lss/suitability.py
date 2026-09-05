"""Suitability criteria engine for method optimization.

Provides configurable criteria (min resolution, max run time, retention
factor limits) that drive method scoring and optimization, similar to
ACD/Labs LC Simulator suitability criteria.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.lss.chromatogram import default_peak_width, resolution


@dataclass
class SuitabilityCriteria:
    """User-configurable suitability criteria for method evaluation.

    Defaults match common LC-MS method development targets.
    """
    min_resolution: float = 1.5
    max_run_time_min: float = 60.0
    min_k: float = 0.5
    max_k: float = 20.0
    # Optional: minimum peak height ratio (tallest/smallest)
    min_peak_height_ratio: float | None = None

    def to_dict(self) -> dict:
        return {
            "min_resolution": self.min_resolution,
            "max_run_time_min": self.max_run_time_min,
            "min_k": self.min_k,
            "max_k": self.max_k,
            "min_peak_height_ratio": self.min_peak_height_ratio,
        }


@dataclass
class CriterionResult:
    """Result of evaluating a single criterion."""
    name: str
    passed: bool
    value: float
    target: str
    detail: str


@dataclass
class SuitabilityEvaluation:
    """Detailed suitability evaluation for a method."""
    overall_score: float  # 0..1
    criteria: list[CriterionResult] = field(default_factory=list)
    all_passed: bool = False

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 4),
            "all_passed": self.all_passed,
            "criteria": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "value": round(c.value, 4) if isinstance(c.value, float) else c.value,
                    "target": c.target,
                    "detail": c.detail,
                }
                for c in self.criteria
            ],
        }


def score_method(
    rts_s: list[float],
    widths_s: list[float] | None,
    total_time_s: float,
    t0_s: float,
    criteria: SuitabilityCriteria | None = None,
) -> float:
    """Compute a 0..1 suitability score for a method.

    Penalizes:
    - Resolution below min_resolution
    - Run time exceeding max_run_time_min
    - Retention factor (k) outside [min_k, max_k]

    Returns a score in [0, 1] where 1.0 means all criteria are satisfied.
    """
    if criteria is None:
        criteria = SuitabilityCriteria()

    if not rts_s:
        return 0.0

    score = 1.0

    # 1. Resolution penalty
    if len(rts_s) >= 2:
        # Sort (rt, width) pairs together to avoid mismatched widths
        if widths_s:
            pairs = sorted(zip(rts_s, widths_s, strict=False), key=lambda p: p[0])
            sorted_rts = [p[0] for p in pairs]
            sorted_widths = [p[1] for p in pairs]
        else:
            sorted_rts = sorted(rts_s)
            sorted_widths = None
        min_rs = float("inf")
        for i in range(len(sorted_rts) - 1):
            w = (
                sorted_widths[i]
                if sorted_widths and i < len(sorted_widths)
                else default_peak_width(sorted_rts[i])
            )
            w_next = (
                sorted_widths[i + 1]
                if sorted_widths and i + 1 < len(sorted_widths)
                else default_peak_width(sorted_rts[i + 1])
            )
            rs = resolution(sorted_rts[i], sorted_rts[i + 1], w, w_next)
            if rs < min_rs:
                min_rs = rs
        if min_rs == float("inf"):
            min_rs = 0.0
        if min_rs < criteria.min_resolution:
            # Linear penalty: 0 at Rs=0, full at Rs=min_resolution
            score *= min(1.0, min_rs / criteria.min_resolution)

    # 2. Run time penalty
    run_time_min = total_time_s / 60.0
    if run_time_min > criteria.max_run_time_min:
        # Penalize proportionally to overshoot
        overshoot = (run_time_min - criteria.max_run_time_min) / criteria.max_run_time_min
        score *= max(0.0, 1.0 - overshoot)

    # 3. Retention factor penalty
    if t0_s > 0:
        for rt in rts_s:
            k = (rt - t0_s) / t0_s
            if k < criteria.min_k:
                score *= 0.8  # too little retention
            elif k > criteria.max_k:
                score *= 0.8  # too much retention

    return max(0.0, min(1.0, score))


def evaluate_method(
    rts_s: list[float],
    widths_s: list[float] | None,
    total_time_s: float,
    t0_s: float,
    criteria: SuitabilityCriteria | None = None,
) -> SuitabilityEvaluation:
    """Evaluate a method against suitability criteria with detailed breakdown."""
    if criteria is None:
        criteria = SuitabilityCriteria()

    results: list[CriterionResult] = []

    # 1. Resolution
    if len(rts_s) >= 2:
        # Sort (rt, width) pairs together to avoid mismatched widths
        if widths_s:
            pairs = sorted(zip(rts_s, widths_s, strict=False), key=lambda p: p[0])
            sorted_rts = [p[0] for p in pairs]
            sorted_widths = [p[1] for p in pairs]
        else:
            sorted_rts = sorted(rts_s)
            sorted_widths = None
        min_rs = float("inf")
        for i in range(len(sorted_rts) - 1):
            w = (
                sorted_widths[i]
                if sorted_widths and i < len(sorted_widths)
                else default_peak_width(sorted_rts[i])
            )
            w_next = (
                sorted_widths[i + 1]
                if sorted_widths and i + 1 < len(sorted_widths)
                else default_peak_width(sorted_rts[i + 1])
            )
            rs = resolution(sorted_rts[i], sorted_rts[i + 1], w, w_next)
            if rs < min_rs:
                min_rs = rs
        if min_rs == float("inf"):
            min_rs = 0.0
        results.append(CriterionResult(
            name="min_resolution",
            passed=min_rs >= criteria.min_resolution,
            value=min_rs,
            target=f"≥ {criteria.min_resolution}",
            detail=f"Minimum pairwise resolution = {min_rs:.2f}",
        ))
    else:
        results.append(CriterionResult(
            name="min_resolution",
            passed=True,
            value=float("inf"),
            target=f"≥ {criteria.min_resolution}",
            detail="Single compound — no resolution requirement",
        ))

    # 2. Run time
    run_time_min = total_time_s / 60.0
    results.append(CriterionResult(
        name="max_run_time",
        passed=run_time_min <= criteria.max_run_time_min,
        value=run_time_min,
        target=f"≤ {criteria.max_run_time_min} min",
        detail=f"Total run time = {run_time_min:.1f} min",
    ))

    # 3. Retention factor
    if t0_s > 0:
        k_values = [(rt - t0_s) / t0_s for rt in rts_s]
        min_k = min(k_values) if k_values else 0.0
        max_k = max(k_values) if k_values else 0.0
        k_pass = all(criteria.min_k <= k <= criteria.max_k for k in k_values)
        results.append(CriterionResult(
            name="retention_factor",
            passed=k_pass,
            value=min_k,
            target=f"{criteria.min_k} ≤ k ≤ {criteria.max_k}",
            detail=f"k range: {min_k:.2f} – {max_k:.2f}",
        ))

    overall = score_method(rts_s, widths_s, total_time_s, t0_s, criteria)
    all_passed = all(r.passed for r in results)

    return SuitabilityEvaluation(
        overall_score=overall,
        criteria=results,
        all_passed=all_passed,
    )

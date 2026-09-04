"""Model selection for gradient retention prediction.

Supports linear, quadratic, and log-log models for fitting
calibration data, with fit quality metrics and bad-peak thresholding,
similar to ACD/Labs LC Simulator model selection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GradientModel(str, Enum):
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    LOG_LOG = "log_log"


@dataclass
class CalibrationPoint:
    """A single calibration data point."""
    gradient_time_min: float
    observed_rt_min: float
    # Optional: compound identifier for multi-compound calibration
    compound_id: str | None = None


@dataclass
class ModelFit:
    """Fitted model parameters."""
    model_type: GradientModel
    coefficients: list[float]  # varies by model type
    r_squared: float
    rmse: float
    max_residual: float
    n_points: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type.value,
            "coefficients": [round(c, 6) for c in self.coefficients],
            "r_squared": round(self.r_squared, 6),
            "rmse": round(self.rmse, 6),
            "max_residual": round(self.max_residual, 6),
            "n_points": self.n_points,
        }


@dataclass
class FitQuality:
    """Quality metrics for a model fit."""
    r_squared: float
    rmse: float
    max_residual: float
    bad_peaks_count: int
    bad_peaks_threshold: float
    residuals: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "r_squared": round(self.r_squared, 6),
            "rmse": round(self.rmse, 6),
            "max_residual": round(self.max_residual, 6),
            "bad_peaks_count": self.bad_peaks_count,
            "bad_peaks_threshold": round(self.bad_peaks_threshold, 4),
            "residuals": [round(r, 4) for r in self.residuals],
        }


def fit_model(
    model_type: GradientModel,
    points: list[CalibrationPoint],
) -> ModelFit:
    """Fit a gradient retention model to calibration data.

    Models:
    - LINEAR: RT = a + b * tG
    - QUADRATIC: RT = a + b * tG + c * tG²
    - LOG_LOG: log(RT) = a + b * log(tG)
    """
    if len(points) < 2:
        raise ValueError("Need at least 2 calibration points")

    x = [p.gradient_time_min for p in points]
    y = [p.observed_rt_min for p in points]
    n = len(points)

    if model_type == GradientModel.LINEAR:
        # y = a + b*x
        coeffs = _fit_linear(x, y)

        def predict_fn(tg: float) -> float:
            return coeffs[0] + coeffs[1] * tg
    elif model_type == GradientModel.QUADRATIC:
        # y = a + b*x + c*x²
        if n < 3:
            # Fall back to linear if not enough points
            coeffs = _fit_linear(x, y) + [0.0]
        else:
            coeffs = _fit_quadratic(x, y)

        def predict_fn(tg: float) -> float:  # noqa: F811
            return coeffs[0] + coeffs[1] * tg + coeffs[2] * tg ** 2
    elif model_type == GradientModel.LOG_LOG:
        # log(y) = a + b * log(x)
        log_x = [math.log(max(xi, 0.01)) for xi in x]
        log_y = [math.log(max(yi, 0.01)) for yi in y]
        log_coeffs = _fit_linear(log_x, log_y)
        coeffs = log_coeffs

        def predict_fn(tg: float) -> float:  # noqa: F811
            return math.exp(log_coeffs[0] + log_coeffs[1] * math.log(max(tg, 0.01)))
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    # Compute fit quality
    y_pred = [predict_fn(xi) for xi in x]
    residuals = [y[i] - y_pred[i] for i in range(n)]

    y_mean = sum(y) / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum(r ** 2 for r in residuals)

    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = math.sqrt(ss_res / n) if n > 0 else 0.0
    max_residual = max(abs(r) for r in residuals) if residuals else 0.0

    return ModelFit(
        model_type=model_type,
        coefficients=coeffs,
        r_squared=r_squared,
        rmse=rmse,
        max_residual=max_residual,
        n_points=n,
    )


def predict_rt(model_fit: ModelFit, gradient_time_min: float) -> float:
    """Predict RT using a fitted model."""
    c = model_fit.coefficients
    if model_fit.model_type == GradientModel.LINEAR:
        return c[0] + c[1] * gradient_time_min
    elif model_fit.model_type == GradientModel.QUADRATIC:
        return c[0] + c[1] * gradient_time_min + c[2] * gradient_time_min ** 2
    elif model_fit.model_type == GradientModel.LOG_LOG:
        return math.exp(c[0] + c[1] * math.log(max(gradient_time_min, 0.01)))
    raise ValueError(f"Unknown model type: {model_fit.model_type}")


def evaluate_fit(
    model_fit: ModelFit,
    points: list[CalibrationPoint],
    bad_peaks_threshold: float = 0.75,
) -> FitQuality:
    """Evaluate fit quality with bad-peak detection."""
    residuals = []
    bad_count = 0

    for p in points:
        pred = predict_rt(model_fit, p.gradient_time_min)
        residual = p.observed_rt_min - pred
        residuals.append(residual)
        if abs(residual) > bad_peaks_threshold:
            bad_count += 1

    return FitQuality(
        r_squared=model_fit.r_squared,
        rmse=model_fit.rmse,
        max_residual=model_fit.max_residual,
        bad_peaks_count=bad_count,
        bad_peaks_threshold=bad_peaks_threshold,
        residuals=residuals,
    )


def suggest_best_model(
    points: list[CalibrationPoint],
    bad_peaks_threshold: float = 0.75,
) -> tuple[GradientModel, ModelFit, FitQuality]:
    """Try all models and return the best one by R²."""
    results: list[tuple[GradientModel, ModelFit, FitQuality]] = []

    for model_type in GradientModel:
        try:
            fit = fit_model(model_type, points)
            quality = evaluate_fit(fit, points, bad_peaks_threshold)
            results.append((model_type, fit, quality))
        except Exception:
            continue

    if not results:
        raise ValueError("Could not fit any model to the data")

    # Sort by R² descending
    results.sort(key=lambda r: r[1].r_squared, reverse=True)
    return results[0]


def _fit_linear(x: list[float], y: list[float]) -> list[float]:
    """Fit y = a + b*x using OLS. Returns [a, b]."""
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_x2 = sum(xi ** 2 for xi in x)

    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-12:
        return [sum_y / n, 0.0]

    b = (n * sum_xy - sum_x * sum_y) / denom
    a = (sum_y - b * sum_x) / n
    return [a, b]


def _fit_quadratic(x: list[float], y: list[float]) -> list[float]:
    """Fit y = a + b*x + c*x² using OLS. Returns [a, b, c]."""
    n = len(x)
    # Normal equations for quadratic
    sx = sum(x)
    sx2 = sum(xi ** 2 for xi in x)
    sx3 = sum(xi ** 3 for xi in x)
    sx4 = sum(xi ** 4 for xi in x)
    sy = sum(y)
    sxy = sum(x[i] * y[i] for i in range(n))
    sx2y = sum(x[i] ** 2 * y[i] for i in range(n))

    # Solve 3x3 system: [[n, sx, sx2], [sx, sx2, sx3], [sx2, sx3, sx4]]
    # * [a, b, c] = [sy, sxy, sx2y]
    A = [[float(n), sx, sx2], [sx, sx2, sx3], [sx2, sx3, sx4]]
    b_vec = [sy, sxy, sx2y]

    return _solve_3x3(A, b_vec)


def _solve_3x3(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve a 3x3 linear system using Cramer's rule."""
    det = _det3(A)
    if abs(det) < 1e-12:
        # Fall back to linear
        linear = _fit_linear(
            [A[1][0] for _ in range(len(b))],  # dummy
            b,
        )
        return linear + [0.0]

    # Cramer's rule
    A0 = [[b[0], A[0][1], A[0][2]], [b[1], A[1][1], A[1][2]], [b[2], A[2][1], A[2][2]]]
    A1 = [[A[0][0], b[0], A[0][2]], [A[1][0], b[1], A[1][2]], [A[2][0], b[2], A[2][2]]]
    A2 = [[A[0][0], A[0][1], b[0]], [A[1][0], A[1][1], b[1]], [A[2][0], A[2][1], b[2]]]

    a = _det3(A0) / det
    b_val = _det3(A1) / det
    c = _det3(A2) / det
    return [a, b_val, c]


def _det3(m: list[list[float]]) -> float:
    """3x3 determinant."""
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )

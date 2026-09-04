"""Prediction equation mode: structure-property-RT regression.

Builds a retention prediction equation from >=5 known structures+RTs
using linear regression on molecular descriptors (logD, MW, MR, TPSA,
HBD, HBA), similar to ACD/Labs Prediction Mode.

Reports:
- Coefficients for each descriptor
- R (correlation coefficient), R², standard deviation (StD)
- Applicability domain flags
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnownCompoundRT:
    """A known compound with measured retention time."""
    smiles: str
    rt_min: float
    # Method conditions (for context — all compounds should use same conditions)
    column_type: str = "C18"
    ph: float = 2.7
    gradient_time_min: float = 20.0
    flow_rate_ml_min: float = 0.4
    temperature_c: float = 30.0


@dataclass
class PredictionEquation:
    """Fitted prediction equation."""
    coefficients: dict[str, float]  # descriptor name -> coefficient
    intercept: float
    r: float  # correlation coefficient
    r_squared: float
    std_dev: float  # standard deviation of residuals (min)
    n: int  # number of compounds used
    descriptor_names: list[str]
    descriptor_means: dict[str, float]  # for applicability domain
    descriptor_stds: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "coefficients": {k: round(v, 6) for k, v in self.coefficients.items()},
            "intercept": round(self.intercept, 6),
            "r": round(self.r, 4),
            "r_squared": round(self.r_squared, 4),
            "std_dev": round(self.std_dev, 4),
            "n": self.n,
            "descriptor_names": self.descriptor_names,
            "descriptor_means": {k: round(v, 4) for k, v in self.descriptor_means.items()},
            "descriptor_stds": {k: round(v, 4) for k, v in self.descriptor_stds.items()},
        }


@dataclass
class PredictionResult:
    """Prediction result for a new compound."""
    predicted_rt_min: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    in_applicability_domain: bool
    extrapolation_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_rt_min": round(self.predicted_rt_min, 4),
            "confidence_interval_lower": round(self.confidence_interval_lower, 4),
            "confidence_interval_upper": round(self.confidence_interval_upper, 4),
            "in_applicability_domain": self.in_applicability_domain,
            "extrapolation_warnings": self.extrapolation_warnings,
        }


def _compute_descriptors(smiles: str, ph: float) -> dict[str, float]:
    """Compute molecular descriptors for a SMILES at a given pH."""
    from rdkit.Chem import Crippen

    from app.core.chem.descriptors import compute_descriptors
    from app.core.chem.logd import logd_at_ph
    from app.core.chem.parser import parse_mol

    mol = parse_mol(smiles).mol
    desc = compute_descriptors(mol)

    # logD at method pH
    logd = logd_at_ph(mol, ph, desc.logp)

    # Molar refractivity (MR)
    mr = Crippen.MolMR(mol)

    return {
        "logD": logd,
        "MW": desc.mw,
        "MR": mr,
        "TPSA": desc.tpsa,
        "HBD": float(desc.hbd),
        "HBA": float(desc.hba),
        "logP": desc.logp,
        "rotatable_bonds": float(desc.rotatable_bonds),
        "aromatic_rings": float(desc.aromatic_rings),
    }


# Descriptors used in the regression equation
DESCRIPTOR_NAMES = ["logD", "MW", "MR", "TPSA", "HBD", "HBA"]


def build_prediction_equation(
    compounds: list[KnownCompoundRT],
    descriptor_names: list[str] | None = None,
) -> PredictionEquation:
    """Build a retention prediction equation from known compounds.

    Requires at least 5 compounds (like ACD/Labs).
    Uses ordinary least squares (OLS) linear regression.
    """
    if len(compounds) < 5:
        raise ValueError(
            f"Need at least 5 compounds to build prediction equation, got {len(compounds)}"
        )

    desc_names = descriptor_names or DESCRIPTOR_NAMES

    # Compute descriptor matrix
    X: list[list[float]] = []
    y: list[float] = []
    for c in compounds:
        try:
            desc = _compute_descriptors(c.smiles, c.ph)
            row = [desc.get(name, 0.0) for name in desc_names]
            X.append(row)
            y.append(c.rt_min)
        except Exception as e:
            raise ValueError(f"Failed to compute descriptors for {c.smiles}: {e}") from e

    n = len(y)
    k = len(desc_names)

    # OLS regression using normal equations: beta = (X'X)^-1 X'y
    # Add intercept column
    X_aug = [[1.0] + row for row in X]

    # Compute X'X (k+1 x k+1)
    xtx = [[0.0] * (k + 1) for _ in range(k + 1)]
    for i in range(k + 1):
        for j in range(k + 1):
            xtx[i][j] = sum(X_aug[row][i] * X_aug[row][j] for row in range(n))

    # Compute X'y (k+1 vector)
    xty = [sum(X_aug[row][i] * y[row] for row in range(n)) for i in range(k + 1)]

    # Solve using Gaussian elimination
    beta = _solve_linear_system(xtx, xty)

    intercept = beta[0]
    coefficients = {desc_names[i]: beta[i + 1] for i in range(k)}

    # Compute predicted values and residuals
    y_pred = []
    for row in X_aug:
        pred = sum(beta[i] * row[i] for i in range(k + 1))
        y_pred.append(pred)

    residuals = [y[i] - y_pred[i] for i in range(n)]

    # R (correlation coefficient) and R²
    y_mean = sum(y) / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum(r ** 2 for r in residuals)

    if ss_tot == 0:
        r_squared = 0.0
    else:
        r_squared = 1.0 - ss_res / ss_tot

    r = math.sqrt(max(0.0, r_squared))

    # Standard deviation of residuals
    if n - k - 1 > 0:
        std_dev = math.sqrt(ss_res / (n - k - 1))
    else:
        std_dev = math.sqrt(ss_res / max(n, 1))

    # Descriptor means and stds for applicability domain
    desc_means = {}
    desc_stds = {}
    for idx, name in enumerate(desc_names):
        vals = [X[row][idx] for row in range(n)]
        mean = sum(vals) / n
        desc_means[name] = mean
        if n > 1:
            desc_stds[name] = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1))
        else:
            desc_stds[name] = 0.0

    return PredictionEquation(
        coefficients=coefficients,
        intercept=intercept,
        r=r,
        r_squared=r_squared,
        std_dev=std_dev,
        n=n,
        descriptor_names=desc_names,
        descriptor_means=desc_means,
        descriptor_stds=desc_stds,
    )


def predict_rt(
    equation: PredictionEquation,
    smiles: str,
    ph: float = 2.7,
) -> PredictionResult:
    """Predict retention time for a new compound using the equation."""
    desc = _compute_descriptors(smiles, ph)

    # Apply equation
    rt = equation.intercept
    for name in equation.descriptor_names:
        rt += equation.coefficients.get(name, 0.0) * desc.get(name, 0.0)

    # Confidence interval: ±2 * StD
    ci_lower = rt - 2 * equation.std_dev
    ci_upper = rt + 2 * equation.std_dev

    # Applicability domain check: is the new compound within the
    # descriptor range of the training set?
    warnings: list[str] = []
    in_domain = True
    for name in equation.descriptor_names:
        val = desc.get(name, 0.0)
        mean = equation.descriptor_means.get(name, 0.0)
        std = equation.descriptor_stds.get(name, 0.0)
        if std > 0:
            z_score = abs(val - mean) / std
            if z_score > 3.0:
                in_domain = False
                warnings.append(
                    f"{name}={val:.2f} is {z_score:.1f}σ from training mean (extrapolation)"
                )

    if equation.r < 0.8:
        warnings.append(
            f"Low correlation (R={equation.r:.3f}) — predictions may be unreliable"
        )
    if equation.std_dev > 2.0:
        warnings.append(
            f"High standard deviation (StD={equation.std_dev:.2f} min) — wide confidence interval"
        )

    return PredictionResult(
        predicted_rt_min=max(0.0, rt),
        confidence_interval_lower=max(0.0, ci_lower),
        confidence_interval_upper=ci_upper,
        in_applicability_domain=in_domain,
        extrapolation_warnings=warnings,
    )


def _solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve Ax = b using Gaussian elimination with partial pivoting."""
    n = len(b)
    # Augmented matrix
    aug = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        # Partial pivoting
        max_row = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[max_row][col]):
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]

        if abs(aug[col][col]) < 1e-12:
            # Singular — use ridge regression fallback
            return _solve_ridge(A, b, ridge=1e-6)

        # Eliminate
        for row in range(col + 1, n):
            factor = aug[row][col] / aug[col][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = aug[i][n]
        for j in range(i + 1, n):
            x[i] -= aug[i][j] * x[j]
        x[i] /= aug[i][i]

    return x


def _solve_ridge(A: list[list[float]], b: list[float], ridge: float = 1e-3) -> list[float]:
    """Ridge regression fallback for singular matrices."""
    n = len(b)
    # Add ridge penalty to diagonal
    A_reg = [A[i][:] for i in range(n)]
    for i in range(n):
        A_reg[i][i] += ridge

    return _solve_linear_system_no_pivot(A_reg, b)


def _solve_linear_system_no_pivot(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination without pivoting (for ridge fallback)."""
    n = len(b)
    aug = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        if abs(aug[col][col]) < 1e-15:
            aug[col][col] = 1e-15
        for row in range(col + 1, n):
            factor = aug[row][col] / aug[col][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = aug[i][n]
        for j in range(i + 1, n):
            x[i] -= aug[i][j] * x[j]
        x[i] /= aug[i][i]

    return x

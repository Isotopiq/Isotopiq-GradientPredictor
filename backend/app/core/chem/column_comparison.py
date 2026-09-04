"""Tanaka column comparison using six characterization parameters.

Implements the Tanaka column characterization protocol:
- k(PB) — hydrophobicity (pentylbenzene retention)
- α(CH2) — methylene selectivity
- α(T/O) — shape selectivity (triphenylene/o-terphenyl)
- α(C/P) — hydrogen bonding capacity (caffeine/phenol)
- α(B/A) — ion-exchange capacity at pH 7.6 (benzylamine/phenol)
- α(B/A)2 — ion-exchange capacity at pH 2.7

Computes Column Distance Factor (CDF) for similarity comparison.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class TanakaParameters:
    """Six Tanaka column characterization parameters."""
    k_pb: float          # hydrophobicity (k pentylbenzene)
    alpha_ch2: float     # methylene selectivity
    alpha_t_o: float     # shape selectivity (triphenylene/o-terphenyl)
    alpha_c_p: float     # hydrogen bonding (caffeine/phenol)
    alpha_b_a_76: float  # ion-exchange at pH 7.6
    alpha_b_a_27: float  # ion-exchange at pH 2.7
    column_name: str = ""
    column_type: str = "C18"

    def as_vector(self) -> list[float]:
        return [self.k_pb, self.alpha_ch2, self.alpha_t_o, self.alpha_c_p, self.alpha_b_a_76, self.alpha_b_a_27]

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_name": self.column_name,
            "column_type": self.column_type,
            "k_pb": round(self.k_pb, 4),
            "alpha_ch2": round(self.alpha_ch2, 4),
            "alpha_t_o": round(self.alpha_t_o, 4),
            "alpha_c_p": round(self.alpha_c_p, 4),
            "alpha_b_a_76": round(self.alpha_b_a_76, 4),
            "alpha_b_a_27": round(self.alpha_b_a_27, 4),
        }


# Reference Tanaka parameters for common column types
# Based on published Tanaka characterization data
REFERENCE_COLUMNS: dict[str, TanakaParameters] = {
    "C18_symmetric": TanakaParameters(
        k_pb=7.0, alpha_ch2=1.5, alpha_t_o=1.5, alpha_c_p=0.5,
        alpha_b_a_76=0.1, alpha_b_a_27=0.0, column_name="C18 (symmetric)", column_type="C18",
    ),
    "C18_endcapped": TanakaParameters(
        k_pb=8.0, alpha_ch2=1.6, alpha_t_o=1.7, alpha_c_p=0.4,
        alpha_b_a_76=0.05, alpha_b_a_27=0.0, column_name="C18 (endcapped)", column_type="C18",
    ),
    "C8": TanakaParameters(
        k_pb=4.5, alpha_ch2=1.4, alpha_t_o=1.3, alpha_c_p=0.45,
        alpha_b_a_76=0.1, alpha_b_a_27=0.0, column_name="C8", column_type="C8",
    ),
    "C18_polar_embedded": TanakaParameters(
        k_pb=6.0, alpha_ch2=1.4, alpha_t_o=1.4, alpha_c_p=0.6,
        alpha_b_a_76=0.2, alpha_b_a_27=0.05, column_name="C18 polar embedded", column_type="C18",
    ),
    "phenyl": TanakaParameters(
        k_pb=5.5, alpha_ch2=1.3, alpha_t_o=2.5, alpha_c_p=0.5,
        alpha_b_a_76=0.1, alpha_b_a_27=0.0, column_name="Phenyl", column_type="Phenyl",
    ),
    "hilic": TanakaParameters(
        k_pb=0.5, alpha_ch2=0.3, alpha_t_o=0.8, alpha_c_p=1.5,
        alpha_b_a_76=0.5, alpha_b_a_27=0.3, column_name="HILIC", column_type="HILIC",
    ),
    "pentafluorophenyl": TanakaParameters(
        k_pb=4.0, alpha_ch2=1.2, alpha_t_o=3.0, alpha_c_p=0.8,
        alpha_b_a_76=0.15, alpha_b_a_27=0.05, column_name="PFP", column_type="PFP",
    ),
}


@dataclass
class ColumnComparison:
    """Comparison result between two columns."""
    column_a: TanakaParameters
    column_b: TanakaParameters
    cdf: float  # Column Distance Factor (0=identical, higher=more different)
    parameter_differences: dict[str, float]
    similarity: float  # 0..1 (1=identical)
    orthogonality: float  # 0..1 (1=orthogonal/complementary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_a": self.column_a.to_dict(),
            "column_b": self.column_b.to_dict(),
            "cdf": round(self.cdf, 4),
            "parameter_differences": {k: round(v, 4) for k, v in self.parameter_differences.items()},
            "similarity": round(self.similarity, 4),
            "orthogonality": round(self.orthogonality, 4),
        }


def column_distance_factor(a: TanakaParameters, b: TanakaParameters) -> float:
    """Compute Column Distance Factor (CDF) between two columns.

    CDF = Euclidean distance in normalized Tanaka parameter space.
    """
    vec_a = a.as_vector()
    vec_b = b.as_vector()

    # Normalize each parameter by its typical range
    ranges = [10.0, 2.0, 3.0, 1.5, 1.0, 0.5]  # typical ranges for each parameter

    squared_sum = 0.0
    for i in range(len(vec_a)):
        diff = (vec_a[i] - vec_b[i]) / ranges[i]
        squared_sum += diff ** 2

    return math.sqrt(squared_sum)


def compare_columns(a: TanakaParameters, b: TanakaParameters) -> ColumnComparison:
    """Compare two columns using Tanaka parameters."""
    cdf = column_distance_factor(a, b)

    # Similarity: 1 / (1 + CDF)
    similarity = 1.0 / (1.0 + cdf)

    # Orthogonality: how complementary are the selectivities?
    # High orthogonality = different selectivity patterns
    # Use the angle between the parameter vectors
    vec_a = a.as_vector()
    vec_b = b.as_vector()

    dot = sum(vec_a[i] * vec_b[i] for i in range(len(vec_a)))
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b))

    if norm_a > 0 and norm_b > 0:
        cos_angle = max(-1.0, min(1.0, dot / (norm_a * norm_b)))
        angle = math.acos(cos_angle)
        orthogonality = angle / (math.pi / 2)  # normalize to 0..1
    else:
        orthogonality = 0.0

    param_diffs = {
        "k_pb": abs(a.k_pb - b.k_pb),
        "alpha_ch2": abs(a.alpha_ch2 - b.alpha_ch2),
        "alpha_t_o": abs(a.alpha_t_o - b.alpha_t_o),
        "alpha_c_p": abs(a.alpha_c_p - b.alpha_c_p),
        "alpha_b_a_76": abs(a.alpha_b_a_76 - b.alpha_b_a_76),
        "alpha_b_a_27": abs(a.alpha_b_a_27 - b.alpha_b_a_27),
    }

    return ColumnComparison(
        column_a=a,
        column_b=b,
        cdf=cdf,
        parameter_differences=param_diffs,
        similarity=similarity,
        orthogonality=orthogonality,
    )


def compare_all(
    columns: list[TanakaParameters],
    reference: TanakaParameters | None = None,
) -> list[dict[str, Any]]:
    """Compare all columns against a reference (or pairwise matrix)."""
    results: list[dict[str, Any]] = []

    if reference:
        for col in columns:
            comp = compare_columns(reference, col)
            results.append(comp.to_dict())
    else:
        # Pairwise
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                comp = compare_columns(columns[i], columns[j])
                results.append(comp.to_dict())

    return results


def cluster_columns(
    columns: list[TanakaParameters],
    n_clusters: int = 3,
) -> dict[str, list[str]]:
    """Simple k-means-like clustering of columns by Tanaka parameters.

    Returns a mapping of cluster_id -> list of column names.
    """
    if not columns:
        return {}

    if len(columns) <= n_clusters:
        return {f"cluster_{i}": [col.column_name] for i, col in enumerate(columns)}

    # Initialize cluster centers using first n_clusters columns
    centers = [columns[i].as_vector() for i in range(n_clusters)]
    assignments = [0] * len(columns)

    for _ in range(10):  # max iterations
        changed = False
        for idx, col in enumerate(columns):
            vec = col.as_vector()
            best_cluster = 0
            best_dist = float("inf")
            for ci, center in enumerate(centers):
                dist = math.sqrt(sum((vec[i] - center[i]) ** 2 for i in range(len(vec))))
                if dist < best_dist:
                    best_dist = dist
                    best_cluster = ci
            if assignments[idx] != best_cluster:
                assignments[idx] = best_cluster
                changed = True

        # Update centers
        for ci in range(n_clusters):
            members = [columns[i].as_vector() for i in range(len(columns)) if assignments[i] == ci]
            if members:
                centers[ci] = [sum(m[d] for m in members) / len(members) for d in range(len(members[0]))]

        if not changed:
            break

    clusters: dict[str, list[str]] = {}
    for ci in range(n_clusters):
        clusters[f"cluster_{ci}"] = [
            columns[i].column_name for i in range(len(columns)) if assignments[i] == ci
        ]

    return clusters

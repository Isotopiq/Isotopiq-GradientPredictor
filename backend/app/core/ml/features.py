"""Feature vector builder: descriptors + method conditions -> numpy array."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from rdkit import Chem

from app.core.chem.descriptors import compute_descriptors
from app.core.chem.pka import estimate_pka_values

# Fixed feature schema (order matters for model persistence)
FEATURE_NAMES = [
    "mw",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
    "aromatic_rings",
    "num_rings",
    "num_heavy_atoms",
    "num_heteroatoms",
    "fraction_csp3",
    "n_pka_sites",
    "min_pka",
    "max_pka",
    # Method conditions
    "ph",
    "percent_b_start",
    "percent_b_end",
    "gradient_time_min",
    "flow_rate_ml_min",
    "temperature_c",
    # Column one-hot
    "col_C18",
    "col_phenyl",
    "col_HILIC",
    "col_ion_pair",
    "col_other",
]

COLUMN_TYPES = ["C18", "phenyl", "HILIC", "ion_pair", "other"]


@dataclass
class MethodConditions:
    column_type: str
    ph: float
    percent_b_start: float
    percent_b_end: float
    gradient_time_min: float
    flow_rate_ml_min: float
    temperature_c: float


def build_features(mol: Chem.Mol, conditions: MethodConditions) -> np.ndarray:
    """Build a feature vector from a molecule + method conditions."""
    d = compute_descriptors(mol)
    pka_values = estimate_pka_values(mol)

    features = [
        d.mw,
        d.logp,
        d.tpsa,
        d.hbd,
        d.hba,
        d.rotatable_bonds,
        d.aromatic_rings,
        d.num_rings,
        d.num_heavy_atoms,
        d.num_heteroatoms,
        d.fraction_csp3,
        float(len(pka_values)),
        min(pka_values) if pka_values else 0.0,
        max(pka_values) if pka_values else 0.0,
        # Method
        conditions.ph,
        conditions.percent_b_start,
        conditions.percent_b_end,
        conditions.gradient_time_min,
        conditions.flow_rate_ml_min,
        conditions.temperature_c,
        # Column one-hot
        float(conditions.column_type == "C18"),
        float(conditions.column_type == "phenyl"),
        float(conditions.column_type == "HILIC"),
        float(conditions.column_type == "ion_pair"),
        float(conditions.column_type == "other"),
    ]
    return np.array(features, dtype=np.float64)


def build_features_from_descriptors(
    descriptors: dict, pka_values: list[float], conditions: MethodConditions
) -> np.ndarray:
    """Build features from pre-computed descriptor dict (avoids re-parsing molecule)."""
    features = [
        descriptors.get("mw", 0.0),
        descriptors.get("logp", 0.0),
        descriptors.get("tpsa", 0.0),
        descriptors.get("hbd", 0),
        descriptors.get("hba", 0),
        descriptors.get("rotatable_bonds", 0),
        descriptors.get("aromatic_rings", 0),
        descriptors.get("num_rings", 0),
        descriptors.get("num_heavy_atoms", 0),
        descriptors.get("num_heteroatoms", 0),
        descriptors.get("fraction_csp3", 0.0),
        float(len(pka_values)),
        min(pka_values) if pka_values else 0.0,
        max(pka_values) if pka_values else 0.0,
        conditions.ph,
        conditions.percent_b_start,
        conditions.percent_b_end,
        conditions.gradient_time_min,
        conditions.flow_rate_ml_min,
        conditions.temperature_c,
        float(conditions.column_type == "C18"),
        float(conditions.column_type == "phenyl"),
        float(conditions.column_type == "HILIC"),
        float(conditions.column_type == "ion_pair"),
        float(conditions.column_type == "other"),
    ]
    return np.array(features, dtype=np.float64)

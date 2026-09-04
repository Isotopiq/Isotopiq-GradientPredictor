"""Buffer calculator and mobile phase editor.

Calculates pH of common LC-MS buffers, checks MS compatibility,
and provides buffer mixing recipes, similar to ACD/Labs mobile phase editor.

Examples:
- 0.1% formic acid → pH ≈ 2.7
- 0.1% acetic acid → pH ≈ 3.0
- 10 mM ammonium formate → pH ≈ 6.5 (adjustable)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# Common LC-MS buffers and acids with their properties
# pKa, density (g/mL), MW (g/mol), MS-compatible
ACID_PROPERTIES = {
    "formic_acid": {
        "pKa": 3.75, "density": 1.22, "mw": 46.03,
        "ms_compatible": True, "name": "Formic acid",
    },
    "acetic_acid": {
        "pKa": 4.76, "density": 1.05, "mw": 60.05,
        "ms_compatible": True, "name": "Acetic acid",
    },
    "trifluoroacetic_acid": {
        "pKa": 0.23, "density": 1.49, "mw": 114.02,
        "ms_compatible": False, "name": "TFA",
    },
    "phosphoric_acid": {
        "pKa1": 2.15, "pKa2": 7.2, "pKa3": 12.3,
        "density": 1.685, "mw": 98.0,
        "ms_compatible": False, "name": "Phosphoric acid",
    },
    "citric_acid": {
        "pKa1": 3.13, "pKa2": 4.76, "pKa3": 6.4,
        "density": 1.665, "mw": 192.12,
        "ms_compatible": False, "name": "Citric acid",
    },
    "carbonic_acid": {
        "pKa1": 6.35, "pKa2": 10.33,
        "ms_compatible": True, "name": "Carbonic acid",
    },
}

BASE_PROPERTIES = {
    "ammonia": {
        "pKa": 9.25, "density": 0.88, "mw": 17.03,
        "ms_compatible": True, "name": "Ammonia",
    },
    "ammonium_hydroxide": {
        "pKa": 9.25, "density": 0.88, "mw": 35.05,
        "ms_compatible": True, "name": "Ammonium hydroxide",
    },
    "triethylamine": {
        "pKa": 10.75, "density": 0.726, "mw": 101.19,
        "ms_compatible": False, "name": "Triethylamine",
    },
}

BUFFER_SALTS = {
    "ammonium_formate": {
        "pKa": 3.75, "mw": 63.06,
        "ms_compatible": True, "name": "Ammonium formate",
    },
    "ammonium_acetate": {
        "pKa": 4.76, "mw": 77.08,
        "ms_compatible": True, "name": "Ammonium acetate",
    },
    "ammonium_bicarbonate": {
        "pKa": 9.25, "mw": 79.06,
        "ms_compatible": True, "name": "Ammonium bicarbonate",
    },
    "ammonium_phosphate": {
        "pKa": 7.2, "mw": 132.06,
        "ms_compatible": False, "name": "Ammonium phosphate",
    },
}


@dataclass
class BufferResult:
    """Calculated buffer properties."""
    estimated_ph: float
    buffer_name: str
    concentration_mM: float
    ms_compatible: bool
    warnings: list[str] = field(default_factory=list)
    recipe: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimated_ph": round(self.estimated_ph, 2),
            "buffer_name": self.buffer_name,
            "concentration_mM": round(self.concentration_mM, 2),
            "ms_compatible": self.ms_compatible,
            "warnings": self.warnings,
            "recipe": self.recipe,
        }


@dataclass
class MobilePhase:
    """Mobile phase composition."""
    solvent_a: str  # e.g. "water"
    solvent_b: str  # e.g. "acetonitrile"
    buffer: str | None = None  # e.g. "formic_acid"
    buffer_percent: float = 0.0  # e.g. 0.1 (% v/v for acids, mM for salts)
    buffer_unit: str = "percent"  # "percent" or "mM"
    ph_target: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "solvent_a": self.solvent_a,
            "solvent_b": self.solvent_b,
            "buffer": self.buffer,
            "buffer_percent": self.buffer_percent,
            "buffer_unit": self.buffer_unit,
            "ph_target": self.ph_target,
        }


def calculate_buffer_ph(
    buffer: str,
    concentration: float,
    unit: str = "percent",
) -> BufferResult:
    """Calculate the pH of a buffer solution.

    For acids (percent v/v): uses Henderson-Hasselbalch with concentration.
    For salts (mM): uses the salt pKa directly.
    """
    warnings: list[str] = []

    # Check if it's an acid
    if buffer in ACID_PROPERTIES:
        props = ACID_PROPERTIES[buffer]
        name = props["name"]
        ms_compat = props["ms_compatible"]

        if unit == "percent":
            # Convert % v/v to molarity
            # % v/v = mL acid per 100 mL solution
            # M = (% * 10 * density) / MW
            density = props.get("density", 1.0)
            mw = props.get("mw", 50.0)
            conc_mM = (concentration * 10 * density / mw) * 1000  # mM

            # For a weak acid: pH = 0.5 * (pKa - log C)
            # where C is the acid concentration in M
            pKa = props.get("pKa", props.get("pKa1", 3.0))
            c_molar = conc_mM / 1000.0
            if c_molar > 0:
                ph = 0.5 * (pKa - math.log10(c_molar))
            else:
                ph = 7.0

            recipe = f"{concentration}% {name} in water ({conc_mM:.1f} mM)"
        else:
            # mM concentration
            conc_mM = concentration
            pKa = props.get("pKa", props.get("pKa1", 3.0))
            c_molar = conc_mM / 1000.0
            if c_molar > 0:
                ph = 0.5 * (pKa - math.log10(c_molar))
            else:
                ph = 7.0
            recipe = f"{conc_mM:.1f} mM {name}"

        if not ms_compat:
            warnings.append(f"{name} is NOT MS-compatible — use volatile buffers for LC-MS")
        if buffer == "trifluoroacetic_acid" and concentration > 0.1:
            warnings.append("TFA at >0.1% causes ion suppression in ESI-MS")

        return BufferResult(
            estimated_ph=ph,
            buffer_name=name,
            concentration_mM=conc_mM if unit == "percent" else concentration,
            ms_compatible=ms_compat,
            warnings=warnings,
            recipe=recipe,
        )

    # Check if it's a buffer salt
    if buffer in BUFFER_SALTS:
        props = BUFFER_SALTS[buffer]
        name = props["name"]
        ms_compat = props["ms_compatible"]
        pKa = props["pKa"]

        # Buffer salts at their pKa give pH ≈ pKa
        # Without titration, the pH is approximately the pKa
        ph = pKa

        if unit == "mM":
            conc_mM = concentration
            recipe = f"{conc_mM:.1f} mM {name}"
        else:
            # Approximate: 0.1% ≈ 10 mM for most salts
            conc_mM = concentration * 100
            recipe = f"{concentration}% {name} (~{conc_mM:.0f} mM)"

        if not ms_compat:
            warnings.append(f"{name} is NOT MS-compatible — non-volatile")

        return BufferResult(
            estimated_ph=ph,
            buffer_name=name,
            concentration_mM=conc_mM,
            ms_compatible=ms_compat,
            warnings=warnings,
            recipe=recipe,
        )

    # Check if it's a base
    if buffer in BASE_PROPERTIES:
        props = BASE_PROPERTIES[buffer]
        name = props["name"]
        ms_compat = props["ms_compatible"]
        pKa = props["pKa"]

        if unit == "percent":
            density = props.get("density", 1.0)
            mw = props.get("mw", 17.0)
            conc_mM = (concentration * 10 * density / mw) * 1000
        else:
            conc_mM = concentration

        # For a weak base: pH = 14 - 0.5*(pKb - log C)
        # pKb = 14 - pKa
        pKb = 14 - pKa
        c_molar = conc_mM / 1000.0
        if c_molar > 0:
            ph = 14 - 0.5 * (pKb - math.log10(c_molar))
        else:
            ph = 7.0

        recipe = f"{conc_mM:.1f} mM {name}"
        if not ms_compat:
            warnings.append(f"{name} is NOT MS-compatible")

        return BufferResult(
            estimated_ph=ph,
            buffer_name=name,
            concentration_mM=conc_mM,
            ms_compatible=ms_compat,
            warnings=warnings,
            recipe=recipe,
        )

    return BufferResult(
        estimated_ph=7.0,
        buffer_name=buffer,
        concentration_mM=concentration,
        ms_compatible=True,
        warnings=["Unknown buffer — cannot calculate pH"],
        recipe=f"{concentration} {unit} {buffer}",
    )


def check_compatibility(
    mobile_phase: MobilePhase,
) -> dict[str, Any]:
    """Check mobile phase compatibility warnings."""
    warnings: list[str] = []
    is_ms_compatible = True

    # Check buffer MS compatibility
    if mobile_phase.buffer:
        if mobile_phase.buffer in ACID_PROPERTIES:
            if not ACID_PROPERTIES[mobile_phase.buffer]["ms_compatible"]:
                is_ms_compatible = False
                warnings.append(f"{ACID_PROPERTIES[mobile_phase.buffer]['name']} is not MS-compatible")
        elif mobile_phase.buffer in BUFFER_SALTS:
            if not BUFFER_SALTS[mobile_phase.buffer]["ms_compatible"]:
                is_ms_compatible = False
                warnings.append(f"{BUFFER_SALTS[mobile_phase.buffer]['name']} is not MS-compatible")

    # Check solvent compatibility
    if mobile_phase.solvent_a == "thf" or mobile_phase.solvent_b == "thf":
        warnings.append("THF can degrade PEEK tubing — use stainless steel")
    if mobile_phase.solvent_a == "dichloromethane" or mobile_phase.solvent_b == "dichloromethane":
        warnings.append("DCM is not compatible with PEEK")

    # Check for precipitation risk
    if mobile_phase.buffer == "ammonium_phosphate" and mobile_phase.solvent_b == "acn":
        if mobile_phase.buffer_percent > 20:
            warnings.append("High phosphate + high ACN risks precipitation")

    return {
        "ms_compatible": is_ms_compatible,
        "warnings": warnings,
    }


def list_buffers() -> dict[str, Any]:
    """List all available buffers with their properties."""
    return {
        "acids": {k: {kk: vv for kk, vv in v.items()} for k, v in ACID_PROPERTIES.items()},
        "bases": {k: {kk: vv for kk, vv in v.items()} for k, v in BASE_PROPERTIES.items()},
        "salts": {k: {kk: vv for kk, vv in v.items()} for k, v in BUFFER_SALTS.items()},
    }

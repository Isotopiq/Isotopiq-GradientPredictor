"""Method Transfer Assistant.

Translates HPLC methods between columns/instruments, accounting for:
- Column dimensions (length, diameter, particle size)
- Dwell volume differences
- Dead volume differences
- Flow rate scaling (to maintain linear velocity)
- Gradient time scaling (to maintain column volumes)
- Injection volume scaling

Based on standard method transfer equations from Snyder & Dolan
and the ACD/Labs Method Transfer tool.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColumnSpec:
    """Column specification for method transfer."""
    length_mm: float
    inner_diameter_mm: float
    particle_size_um: float
    dwell_volume_ml: float = 0.0
    dead_volume_ml: float = 0.0


@dataclass
class SourceMethod:
    """Source method parameters."""
    column: ColumnSpec
    flow_rate_ml_min: float
    gradient_table: list[dict]  # [{time_s, percent_b}, ...]
    injection_volume_ul: float = 5.0
    temperature_c: float = 30.0


@dataclass
class TransferredMethod:
    """Transferred method parameters."""
    column: ColumnSpec
    flow_rate_ml_min: float
    gradient_table: list[dict]
    injection_volume_ul: float
    temperature_c: float
    scaling_factors: dict[str, float]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": {
                "length_mm": self.column.length_mm,
                "inner_diameter_mm": self.column.inner_diameter_mm,
                "particle_size_um": self.column.particle_size_um,
                "dwell_volume_ml": self.column.dwell_volume_ml,
                "dead_volume_ml": self.column.dead_volume_ml,
            },
            "flow_rate_ml_min": round(self.flow_rate_ml_min, 4),
            "gradient_table": [
                {"time_s": round(p["time_s"], 2), "percent_b": round(p["percent_b"], 2)}
                for p in self.gradient_table
            ],
            "injection_volume_ul": round(self.injection_volume_ul, 2),
            "temperature_c": self.temperature_c,
            "scaling_factors": {k: round(v, 4) for k, v in self.scaling_factors.items()},
            "notes": self.notes,
        }


def transfer_method(
    source: SourceMethod,
    target_column: ColumnSpec,
    preserve_resolution: bool = True,
) -> TransferredMethod:
    """Transfer a method from source column to target column.

    Uses standard geometric scaling laws:
    - Flow rate: F2 = F1 * (dc2² / dc1²) * (dp1 / dp2)  [optimal velocity]
    - Gradient time: tG2 = tG1 * (L2/dc2²) / (L1/dc1²)  [column volumes]
    - Injection volume: Vinj2 = Vinj1 * (dc2² * L2) / (dc1² * L1)
    """
    src = source.column
    tgt = target_column

    notes: list[str] = []

    # 1. Flow rate scaling
    # Optimal linear velocity scales as 1/dp, and flow = velocity * cross-section
    # F2 = F1 * (dc2/dc1)² * (dp1/dp2)
    flow_scale = (tgt.inner_diameter_mm / src.inner_diameter_mm) ** 2 * (src.particle_size_um / tgt.particle_size_um)
    new_flow = source.flow_rate_ml_min * flow_scale

    # Practical limits
    if new_flow > 5.0:
        notes.append(f"Flow rate {new_flow:.2f} mL/min is high — check pressure limits")
    if new_flow < 0.05:
        notes.append(f"Flow rate {new_flow:.3f} mL/min is very low — may cause diffusion")

    # 2. Gradient time scaling
    # Column volume = π * (dc/2)² * L
    # tG scales with column volume / flow rate
    # tG2 = tG1 * (Vcol2 / Vcol1) / (F2 / F1)
    # But we already scaled flow, so:
    # tG2 = tG1 * (L2 * dc2²) / (L1 * dc1²) / flow_scale
    vol_ratio = (tgt.length_mm * tgt.inner_diameter_mm ** 2) / (src.length_mm * src.inner_diameter_mm ** 2)
    if preserve_resolution:
        grad_time_scale = vol_ratio / flow_scale
    else:
        grad_time_scale = 1.0  # keep gradient time constant

    # 3. Injection volume scaling
    # Vinj2 = Vinj1 * (Vcol2 / Vcol1) = Vinj1 * vol_ratio
    inj_scale = vol_ratio
    new_inj = source.injection_volume_ul * inj_scale

    # 4. Scale gradient table
    new_gradient: list[dict] = []
    for point in source.gradient_table:
        new_time = point["time_s"] * grad_time_scale
        # Adjust for dwell volume difference
        # The gradient reaches the column after dwell time
        # t_dwell = V_dwell / F
        src_dwell_time = src.dwell_volume_ml / max(source.flow_rate_ml_min, 0.01) * 60  # seconds
        tgt_dwell_time = tgt.dwell_volume_ml / max(new_flow, 0.01) * 60
        dwell_shift = tgt_dwell_time - src_dwell_time
        new_time_adj = max(0, new_time + dwell_shift)
        new_gradient.append({
            "time_s": new_time_adj,
            "percent_b": point["percent_b"],
        })

    # 5. Temperature (usually kept constant, but note pressure changes)
    new_temp = source.temperature_c
    if tgt.particle_size_um < src.particle_size_um:
        notes.append(f"Smaller particles ({tgt.particle_size_um}μm) — pressure will increase ~{(src.particle_size_um/tgt.particle_size_um)**2:.1f}x")

    if tgt.length_mm != src.length_mm:
        notes.append(f"Column length changed {src.length_mm}→{tgt.length_mm}mm — efficiency scales with √L")

    if abs(flow_scale - 1.0) > 0.01:
        notes.append(f"Flow scaled by {flow_scale:.2f}x to maintain optimal linear velocity")

    if abs(grad_time_scale - 1.0) > 0.01:
        notes.append(f"Gradient time scaled by {grad_time_scale:.2f}x to maintain column-volume equivalence")

    # Dwell volume note
    if abs(src.dwell_volume_ml - tgt.dwell_volume_ml) > 0.01:
        notes.append(
            f"Dwell volume changed {src.dwell_volume_ml:.2f}→{tgt.dwell_volume_ml:.2f}mL "
            f"(shift: {dwell_shift:.1f}s)"
        )

    return TransferredMethod(
        column=tgt,
        flow_rate_ml_min=new_flow,
        gradient_table=new_gradient,
        injection_volume_ul=new_inj,
        temperature_c=new_temp,
        scaling_factors={
            "flow_rate": flow_scale,
            "gradient_time": grad_time_scale,
            "injection_volume": inj_scale,
            "column_volume": vol_ratio,
        },
        notes=notes,
    )


# Preset column configurations for common transfers
TRANSFER_PRESETS = {
    "hplc_to_uhplc": {
        "source": {"length_mm": 150, "inner_diameter_mm": 4.6, "particle_size_um": 5.0},
        "target": {"length_mm": 50, "inner_diameter_mm": 2.1, "particle_size_um": 1.7},
        "name": "HPLC → UHPLC",
    },
    "uhplc_to_hplc": {
        "source": {"length_mm": 50, "inner_diameter_mm": 2.1, "particle_size_um": 1.7},
        "target": {"length_mm": 150, "inner_diameter_mm": 4.6, "particle_size_um": 5.0},
        "name": "UHPLC → HPLC",
    },
    "hplc_to_hplc_narrow": {
        "source": {"length_mm": 150, "inner_diameter_mm": 4.6, "particle_size_um": 5.0},
        "target": {"length_mm": 150, "inner_diameter_mm": 2.1, "particle_size_um": 5.0},
        "name": "HPLC 4.6mm → HPLC 2.1mm",
    },
}

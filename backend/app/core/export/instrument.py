"""Instrument format exports for LC methods."""
from __future__ import annotations

from typing import Any


def export_agilent_m(method: dict[str, Any], compound: dict[str, Any] | None = None) -> str:
    """Export method in Agilent .m text format (simplified)."""
    gt = method.get("gradient_table") or []
    lines = [
        "$: Agilent LC Method File (Exported from IsotopiQ LC-MS Suite)",
        "$: Generated automatically — verify before instrument use",
        "",
        f"Method Name: IsotopiQ_{method.get('column_type', 'C18')}",
        "",
        "[Column]",
        f"Column Type: {method.get('column_type', 'C18')}",
        f"Temperature: {method.get('temperature_c', 30)} C",
        "",
        "[Mobile Phase]",
        f"Solvent A: {method.get('mobile_phase_a', 'Water')}",
        f"Solvent B: {method.get('mobile_phase_b', 'ACN')}",
        f"Additive: {method.get('additive', 'None')}",
        f"pH: {method.get('ph', 2.7)}",
        "",
        "[Flow]",
        f"Flow Rate: {method.get('flow_rate_ml_min', 0.4)} mL/min",
        "",
        "[Gradient]",
    ]
    for i, point in enumerate(gt):
        time_min = point.get("time_s", 0) / 60.0
        pct_b = point.get("percent_b", 0)
        lines.append(f"  Step {i + 1}: {time_min:.2f} min, {pct_b:.1f}% B")

    lines.extend([
        "",
        "[Detection]",
        "MS: ESI (auto-polarity)",
        "",
    ])

    if compound:
        lines.extend([
            "[Sample]",
            f"Compound: {compound.get('name', 'Unknown')}",
            f"SMILES: {compound.get('smiles', 'N/A')}",
            f"MW: {compound.get('mw', 'N/A')} g/mol",
            "",
        ])

    lines.append("[End]")
    return "\n".join(lines)


def export_waters_mth(method: dict[str, Any], compound: dict[str, Any] | None = None) -> str:
    """Export method in Waters .mth XML format (simplified)."""
    gt = method.get("gradient_table") or []
    gradient_xml = "\n".join(
        f'      <GradientPoint time="{p.get("time_s", 0) / 60.0:.2f}" percentB="{p.get("percent_b", 0):.1f}" />'
        for p in gt
    )

    compound_xml = ""
    if compound:
        compound_xml = f"""
  <Sample>
    <Compound>{compound.get('name', 'Unknown')}</Compound>
    <SMILES>{compound.get('smiles', 'N/A')}</SMILES>
    <MW>{compound.get('mw', 'N/A')}</MW>
  </Sample>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<WatersMethod version="1.0" generatedBy="IsotopiQ LC-MS Suite">
  <Column type="{method.get('column_type', 'C18')}" temperature="{method.get('temperature_c', 30)}" />
  <MobilePhase>
    <SolventA>{method.get('mobile_phase_a', 'Water')}</SolventA>
    <SolventB>{method.get('mobile_phase_b', 'ACN')}</SolventB>
    <Additive>{method.get('additive', 'None')}</Additive>
    <pH>{method.get('ph', 2.7)}</pH>
  </MobilePhase>
  <Flow rate="{method.get('flow_rate_ml_min', 0.4)}" unit="mL/min" />
  <Gradient>
{gradient_xml}
  </Gradient>
  <Detection>
    <MS mode="ESI" polarity="auto" />
  </Detection>{compound_xml}
</WatersMethod>
"""


def export_thermo_xml(method: dict[str, Any], compound: dict[str, Any] | None = None) -> str:
    """Export method in Thermo .xml format (simplified)."""
    gt = method.get("gradient_table") or []
    gradient_xml = "\n".join(
        f'    <GradientPoint time="{p.get("time_s", 0) / 60.0:.2f}" percentB="{p.get("percent_b", 0):.1f}" />'
        for p in gt
    )

    compound_xml = ""
    if compound:
        compound_xml = f"""
  <SampleInfo>
    <CompoundName>{compound.get('name', 'Unknown')}</CompoundName>
    <SMILES>{compound.get('smiles', 'N/A')}</SMILES>
    <MolecularWeight>{compound.get('mw', 'N/A')}</MolecularWeight>
  </SampleInfo>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ThermoMethod version="1.0" generatedBy="IsotopiQ LC-MS Suite">
  <InstrumentType>Vanquish UHPLC</InstrumentType>
  <Column chemistry="{method.get('column_type', 'C18')}" temperature="{method.get('temperature_c', 30)}C" />
  <Solvents>
    <SolventA composition="{method.get('mobile_phase_a', 'Water')}" />
    <SolventB composition="{method.get('mobile_phase_b', 'ACN')}" />
    <Additive>{method.get('additive', 'None')}</Additive>
  </Solvents>
  <FlowRate value="{method.get('flow_rate_ml_min', 0.4)}" unit="mL/min" />
  <GradientProgram>
{gradient_xml}
  </GradientProgram>
  <MSDetection mode="ESI" polaritySwitching="true" />{compound_xml}
</ThermoMethod>
"""

"""Thermo Chromeleon .meth file parser.

Extracts chromatography conditions from binary .meth files which contain
embedded XML with instrument method data (gradient table, flow rate, column
temperature, solvent composition, etc.).

The .meth file format is a binary container with XML content embedded within.
The gradient is stored as TimeStepNode entries with child PropertyStepNode
entries containing Flow.Nominal, %B.Value, and Curve properties.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GradientStep:
    """A single gradient timetable entry."""
    time_min: float
    flow_rate_ml_min: float | None = None
    percent_b: float | None = None
    curve: int | None = None  # 5 = linear


@dataclass
class ParsedMethod:
    """Parsed chromatography method from a .meth file."""
    instrument: str | None = None
    method_name: str | None = None
    column_temp_c: float | None = None
    flow_rate_ml_min: float | None = None
    gradient_table: list[GradientStep] = field(default_factory=list)
    solvent_a: str | None = None
    solvent_b: str | None = None
    method_end_time_min: float | None = None
    injection_volume_ul: float | None = None
    sampler_temp_c: float | None = None
    # Derived values for training
    percent_b_start: float | None = None
    percent_b_end: float | None = None
    gradient_time_min: float | None = None
    # Raw warnings encountered during parsing
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument,
            "method_name": self.method_name,
            "column_temp_c": self.column_temp_c,
            "flow_rate_ml_min": self.flow_rate_ml_min,
            "solvent_a": self.solvent_a,
            "solvent_b": self.solvent_b,
            "method_end_time_min": self.method_end_time_min,
            "injection_volume_ul": self.injection_volume_ul,
            "sampler_temp_c": self.sampler_temp_c,
            "percent_b_start": self.percent_b_start,
            "percent_b_end": self.percent_b_end,
            "gradient_time_min": self.gradient_time_min,
            "gradient_table": [
                {
                    "time_min": s.time_min,
                    "flow_rate_ml_min": s.flow_rate_ml_min,
                    "percent_b": s.percent_b,
                    "curve": s.curve,
                }
                for s in self.gradient_table
            ],
            "warnings": self.warnings,
        }


class MethParseError(ValueError):
    """Raised when a .meth file cannot be parsed."""


def _extract_text(content: bytes) -> str:
    """Extract readable ASCII text from binary .meth file."""
    # The .meth file is binary but contains large XML sections
    # Try UTF-8 first (some files are valid UTF-8 with BOM)
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return content.decode("latin-1", errors="ignore")


def _find_xml_start(text: str) -> str | None:
    """Find the start of the embedded XML content."""
    idx = text.find("<?xml")
    if idx >= 0:
        return text[idx:]
    idx = text.find("<CmData>")
    if idx >= 0:
        return text[idx:]
    return None


def _parse_float_from_value(val: str) -> float | None:
    """Extract a float from a value string like '0.170 [ml/min]' or '47.0 [%]'."""
    if not val:
        return None
    # Remove HTML entities
    val = val.replace("&quot;", '"').replace("&amp;", "&")
    # Extract the numeric part
    match = re.search(r"[-+]?\d*\.?\d+", val)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _parse_scientific(val: str) -> float | None:
    """Parse a scientific notation string like '1.00000000000000010E-001'."""
    if not val or val == "-Infinity" or val == "Infinity":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def parse_meth_file(content: bytes) -> ParsedMethod:
    """Parse a Thermo Chromeleon .meth file and extract chromatography conditions.

    Args:
        content: Raw bytes of the .meth file

    Returns:
        ParsedMethod with gradient table, flow rate, temperature, and solvents

    Raises:
        MethParseError: If the file cannot be parsed
    """
    if not content:
        raise MethParseError("Empty file content")

    text = _extract_text(content)
    if not text:
        raise MethParseError("No readable text found in file")

    result = ParsedMethod()

    # Find instrument name
    instr_match = re.search(r'<Instrument value="([^"]*)"', text)
    if instr_match:
        result.instrument = instr_match.group(1)

    # Find method name
    name_match = re.search(r'<Name value="([^"]*)"', text)
    if name_match:
        result.method_name = name_match.group(1)

    # Find method end time
    end_match = re.search(r'Name="InstrumentMethodEnd"[^>]*Value="([^"]*)"', text)
    if end_match:
        try:
            result.method_end_time_min = float(end_match.group(1))
        except ValueError:
            pass

    # Find column temperature - look for TCC (Thermostatted Column Compartment)
    # The column temp is in a PropertyStepNode with SymbolPath containing "TCC.*CC.Temperature.Nominal"
    # SymbolPath and Value are separate self-closing tags
    temp_pairs = re.findall(
        r'SymbolPath value="TCC\d*\.TCC\d*_CC\.Temperature\.Nominal"\s*/>\s*<Value value="([^"]*)"',
        text,
    )
    if temp_pairs:
        temp = _parse_float_from_value(temp_pairs[0])
        if temp is not None:
            result.column_temp_c = temp
    else:
        # Fallback: look for the column temp in the device properties
        # Struct Name="Temperature" with child Property Name="Nominal"
        temp_struct_match = re.search(
            r'Struct Name="Temperature".*?</Struct>',
            text, re.DOTALL,
        )
        if temp_struct_match:
            temp_match = re.search(
                r'Name="Nominal"[^>]*Unit="[^"]*C"[^>]*Value="([^"]*)"',
                temp_struct_match.group(),
            )
            if temp_match:
                try:
                    result.column_temp_c = float(temp_match.group(1))
                except ValueError:
                    pass

    # Find sampler temperature
    sampler_temp_match = re.search(
        r'SymbolPath value="SamplerModule\.Temperature\.Nominal"\s*/>\s*<Value value="([^"]*)"',
        text,
    )
    if sampler_temp_match:
        result.sampler_temp_c = _parse_float_from_value(sampler_temp_match.group(1))

    # Find solvent equates (A and B)
    # These are in Struct Name="%A" / Struct Name="%B" with a child Property
    # Name="Equate" Value="..." — the Equate is a separate self-closing tag
    solvent_a_match = re.search(
        r'Struct Name="%A".*?</Struct>',
        text, re.DOTALL,
    )
    if solvent_a_match:
        equate_match = re.search(r'Name="Equate"[^>]*Value="([^"]*)"', solvent_a_match.group())
        if equate_match:
            result.solvent_a = equate_match.group(1).replace("&quot;", "")

    solvent_b_match = re.search(
        r'Struct Name="%B".*?</Struct>',
        text, re.DOTALL,
    )
    if solvent_b_match:
        equate_match = re.search(r'Name="Equate"[^>]*Value="([^"]*)"', solvent_b_match.group())
        if equate_match:
            result.solvent_b = equate_match.group(1).replace("&quot;", "")

    # Parse gradient table from TimeStepNode entries
    # Each TimeStepNode has an InternalValue (time in minutes) and child
    # PropertyStepNode entries with Flow.Nominal, %B.Value, and Curve
    gradient_steps = _parse_gradient_table(text)
    result.gradient_table = gradient_steps

    # Derive summary values from gradient table
    if gradient_steps:
        # Filter to steps that have %B values (the actual gradient)
        b_steps = [s for s in gradient_steps if s.percent_b is not None and s.time_min >= 0]
        if b_steps:
            result.percent_b_start = b_steps[0].percent_b
            result.percent_b_end = max(b_steps, key=lambda s: s.time_min).percent_b
            result.gradient_time_min = max(s.time_min for s in gradient_steps)

        # Use the most common flow rate
        flows = [s.flow_rate_ml_min for s in gradient_steps if s.flow_rate_ml_min is not None and s.flow_rate_ml_min > 0]
        if flows:
            # Use the flow rate from the first non-zero entry (initial gradient flow)
            result.flow_rate_ml_min = flows[0]

    if not result.gradient_table:
        result.warnings.append("No gradient table found — file may use a different format")

    return result


def _parse_gradient_table(text: str) -> list[GradientStep]:
    """Parse the gradient timetable from TimeStepNode entries.

    The gradient is stored as a series of TimeStepNode entries, each containing:
    - InternalValue: time in minutes (scientific notation)
    - Child PropertyStepNode entries with SymbolPath and Value for:
      - *.Flow.Nominal: flow rate in ml/min
      - *.%B.Value: percent of solvent B
      - *.Curve: gradient curve type (5 = linear)
    """
    steps: list[GradientStep] = []

    # Find all TimeStepNode opening positions
    openings = list(re.finditer(r'<Item type="TimeStepNode">', text))
    if not openings:
        return steps

    for i, opening in enumerate(openings):
        start = opening.start()
        end = openings[i + 1].start() if i + 1 < len(openings) else min(start + 5000, len(text))
        chunk = text[start:end]

        # Extract time
        time_match = re.search(r'InternalValue value="([^"]*)"', chunk)
        if not time_match:
            continue
        time_str = time_match.group(1)
        if time_str in ("-Infinity", "Infinity", ""):
            continue
        time_val = _parse_scientific(time_str)
        if time_val is None:
            continue

        # Extract child PropertyStepNode values
        # SymbolPath and Value are separate self-closing XML tags:
        # <SymbolPath value="..." /><Value value="..." />
        flow = None
        percent_b = None
        curve = None

        # Find all SymbolPath+Value pairs in this chunk
        prop_pairs = re.findall(
            r'SymbolPath value="([^"]*)"\s*/>\s*<Value value="([^"]*)"',
            chunk,
        )
        for path, val in prop_pairs:
            if "Flow.Nominal" in path:
                flow = _parse_float_from_value(val)
            elif "%B.Value" in path:
                percent_b = _parse_float_from_value(val)
            elif path.endswith("Curve"):
                try:
                    curve = int(float(val))
                except ValueError:
                    pass

        # Only add if we found at least one relevant property
        if flow is not None or percent_b is not None:
            steps.append(GradientStep(
                time_min=time_val,
                flow_rate_ml_min=flow,
                percent_b=percent_b,
                curve=curve,
            ))

    return steps

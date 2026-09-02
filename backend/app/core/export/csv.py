"""CSV export: instrument-ready method parameters."""
from __future__ import annotations

import csv
import io

from app.models.method import Method
from app.models.compound import Compound


def export_method_csv(method: Method, compound: Compound | None = None) -> str:
    """Export a method as instrument-ready CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["# LC-MS Method Export"])
    if compound:
        writer.writerow(["# Compound", compound.name or compound.smiles or ""])
    writer.writerow(["# Column", method.column_type])
    writer.writerow(["# pH", method.ph or ""])
    writer.writerow(["# Additive", method.additive or ""])
    writer.writerow(["# Flow Rate (mL/min)", method.flow_rate_ml_min or ""])
    writer.writerow(["# Temperature (C)", method.temperature_c or ""])
    writer.writerow([])

    # Gradient table
    writer.writerow(["Time (min)", "%B", "Flow (mL/min)"])
    gt = method.gradient_table or []
    for point in gt:
        writer.writerow([
            f"{point['time_s'] / 60:.2f}",
            f"{point['percent_b']:.1f}",
            f"{method.flow_rate_ml_min or 0.4:.2f}",
        ])

    return output.getvalue()

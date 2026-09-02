"""PDF export: method report with structure, descriptors, gradient chart."""
from __future__ import annotations

import io
from pathlib import Path

from app.models.compound import Compound
from app.models.method import Method
from app.models.prediction import Prediction

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
)


def export_method_pdf(
    method: Method,
    compound: Compound | None = None,
    prediction: Prediction | None = None,
) -> bytes:
    """Generate a PDF method report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Disclaimer", fontSize=8, textColor=colors.grey))

    story: list = []

    # Title
    story.append(Paragraph("LC-MS Method Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Compound info
    if compound:
        story.append(Paragraph(f"<b>Compound:</b> {compound.name or compound.smiles or 'N/A'}", styles["Normal"]))
        story.append(Paragraph(f"<b>SMILES:</b> {compound.smiles or 'N/A'}", styles["Normal"]))
        story.append(Spacer(1, 6))

        # Descriptor table
        desc_data = [
            ["Property", "Value"],
            ["MW (g/mol)", f"{compound.mw:.2f}" if compound.mw else "—"],
            ["logP", f"{compound.logp:.2f}" if compound.logp else "—"],
            ["TPSA (Å²)", f"{compound.tpsa:.1f}" if compound.tpsa else "—"],
            ["HBD", str(compound.hbd or "—")],
            ["HBA", str(compound.hba or "—")],
            ["pKa (est.)", ", ".join(str(p) for p in (compound.pka_values or [])) or "—"],
        ]
        desc_table = Table(desc_data, colWidths=[2 * inch, 2 * inch])
        desc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ]))
        story.append(desc_table)
        story.append(Spacer(1, 12))

    # Method info
    story.append(Paragraph("<b>Method Parameters</b>", styles["Heading2"]))
    method_data = [
        ["Parameter", "Value"],
        ["Column", method.column_type],
        ["Mobile Phase A", method.mobile_phase_a or "—"],
        ["Mobile Phase B", method.mobile_phase_b or "—"],
        ["Additive", method.additive or "—"],
        ["pH", str(method.ph or "—")],
        ["Flow Rate (mL/min)", str(method.flow_rate_ml_min or "—")],
        ["Temperature (°C)", str(method.temperature_c or "—")],
    ]
    method_table = Table(method_data, colWidths=[2.5 * inch, 2.5 * inch])
    method_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
    ]))
    story.append(method_table)
    story.append(Spacer(1, 12))

    # Gradient table
    gt = method.gradient_table or []
    if gt:
        story.append(Paragraph("<b>Gradient Program</b>", styles["Heading2"]))
        grad_data = [["Time (min)", "%B"]]
        for p in gt:
            grad_data.append([f"{p['time_s'] / 60:.2f}", f"{p['percent_b']:.1f}"])
        grad_table = Table(grad_data, colWidths=[2 * inch, 2 * inch])
        grad_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(grad_table)
        story.append(Spacer(1, 12))

    # Prediction
    if prediction:
        story.append(Paragraph("<b>Prediction</b>", styles["Heading2"]))
        pred_data = [
            ["Predicted RT (s)", f"{prediction.predicted_rt_s:.1f}" if prediction.predicted_rt_s else "—"],
            ["Confidence", f"{prediction.confidence:.1%}"],
            ["Model", prediction.model_version],
        ]
        pred_table = Table(pred_data, colWidths=[2.5 * inch, 2.5 * inch])
        pred_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(pred_table)
        story.append(Spacer(1, 12))

    # Disclaimer
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "DISCLAIMER: Predictions are estimates derived from physicochemical heuristics "
        "and statistical models. They require experimental verification before use in "
        "regulated or production analytical work. pKa and logP values from RDKit are approximate.",
        styles["Disclaimer"],
    ))

    doc.build(story)
    return buf.getvalue()

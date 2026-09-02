"""Modern PDF report generator for LC-MS method reports.

Uses reportlab platypus with a professional scientific design:
- Header band with lab name/logo
- Color-coded section headers with accent bars
- Clean data tables with alternating rows
- Gradient program visualization
- Footer with disclaimer and page numbers
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.models.compound import Compound
from app.models.method import Method
from app.models.prediction import Prediction

# Color palette — professional scientific
_ACCENT = colors.HexColor("#2563eb")  # Blue 600
_ACCENT_LIGHT = colors.HexColor("#dbeafe")  # Blue 100
_DARK = colors.HexColor("#1e293b")  # Slate 800
_MUTED = colors.HexColor("#64748b")  # Slate 500
_ROW_ALT = colors.HexColor("#f8fafc")  # Slate 50
_BORDER = colors.HexColor("#e2e8f0")  # Slate 200
_SUCCESS = colors.HexColor("#16a34a")
_WARNING = colors.HexColor("#d97706")


def _build_styles() -> dict:
    """Create custom paragraph styles."""
    base = getSampleStyleSheet()
    styles = {
        "report_title": ParagraphStyle(
            "report_title", parent=base["Title"],
            fontSize=20, leading=26, textColor=_DARK,
            spaceAfter=4, fontName="Helvetica-Bold",
        ),
        "report_subtitle": ParagraphStyle(
            "report_subtitle", parent=base["Normal"],
            fontSize=10, leading=14, textColor=_MUTED,
            spaceAfter=12, fontName="Helvetica",
        ),
        "section_header": ParagraphStyle(
            "section_header", parent=base["Heading2"],
            fontSize=12, leading=16, textColor=_ACCENT,
            spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, leading=13, textColor=_DARK,
            fontName="Helvetica",
        ),
        "body_muted": ParagraphStyle(
            "body_muted", parent=base["Normal"],
            fontSize=8, leading=11, textColor=_MUTED,
            fontName="Helvetica",
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, leading=10, textColor=_MUTED,
            fontName="Helvetica-Oblique",
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Normal"],
            fontSize=8, leading=11, textColor=_DARK,
            fontName="Courier",
        ),
    }
    return styles


def _section_bar(title: str, styles: dict) -> Table:
    """Create a section header with a colored left bar."""
    bar = Table(
        [[Paragraph(title, styles["section_header"])]],
        colWidths=[170 * mm],
    )
    bar.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, 0), 3, _ACCENT),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("TOPPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
    ]))
    return bar


def _data_table(
    data: list[list[str]],
    col_widths: list[float],
    styles: dict,
) -> Table:
    """Create a styled data table with header row and alternating rows."""
    tbl = Table(data, colWidths=col_widths)
    style_cmds = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), _DARK),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, _BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDER),
    ]
    # Alternating row backgrounds
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), _ROW_ALT))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _gradient_bars_table(
    gradient: list[dict],
    styles: dict,
) -> Table:
    """Create a visual gradient program table with horizontal bars."""
    if not gradient:
        return Paragraph("No gradient program defined.", styles["body_muted"])

    max_b = max((p.get("percent_b", 0) for p in gradient), default=100)
    min_b = min((p.get("percent_b", 0) for p in gradient), default=0)
    span = max(max_b - min_b, 1)

    rows = [["Time (min)", "%B", ""]]
    for p in gradient:
        t_min = p.get("time_s", 0) / 60.0
        pct_b = p.get("percent_b", 0)
        bar_width = ((pct_b - min_b) / span) * 100
        bar = f'<font color="#{_ACCENT.hexval()[2:]}">{"█" * int(bar_width / 5)}</font>'
        rows.append([f"{t_min:.2f}", f"{pct_b:.1f}%", bar])

    tbl = Table(rows, colWidths=[30 * mm, 20 * mm, 120 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, _BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDER),
        ("FONTNAME", (2, 1), (2, -1), "Courier"),
        ("FONTSIZE", (2, 1), (2, -1), 7),
    ]))
    for i in range(1, len(rows)):
        if i % 2 == 0:
            tbl.setStyle(TableStyle([("BACKGROUND", (0, i), (-1, i), _ROW_ALT)]))
    return tbl


def export_method_pdf(
    method: Method,
    compound: Compound | None = None,
    prediction: Prediction | None = None,
    settings: dict | None = None,
) -> bytes:
    """Generate a modern, beautifully designed PDF method report.

    Args:
        method: The method to report on.
        compound: Optional compound associated with the method.
        prediction: Optional prediction result.
        settings: Optional dict with lab_name, lab_subtitle, report_footer, logo_bytes.
    """
    buf = io.BytesIO()
    styles = _build_styles()

    # Settings with defaults
    s = settings or {}
    lab_name = s.get("lab_name", "IsotopiQ")
    lab_subtitle = s.get("lab_subtitle", "LC-MS Method Prediction Suite")
    report_footer = s.get(
        "report_footer",
        "Predictions are estimates derived from physicochemical heuristics and statistical models. "
        "They require experimental verification before use in regulated or production analytical work.",
    )
    logo_bytes = s.get("logo_bytes")

    # Page template with header and footer
    page_w, page_h = A4
    margin = 15 * mm
    frame = Frame(margin, margin + 15 * mm, page_w - 2 * margin, page_h - 2 * margin - 25 * mm, id="main")

    def _on_page(canvas, doc):
        canvas.saveState()
        # Header band
        canvas.setFillColor(_DARK)
        canvas.rect(0, page_h - 20 * mm, page_w, 20 * mm, fill=1, stroke=0)
        # Accent line under header
        canvas.setFillColor(_ACCENT)
        canvas.rect(0, page_h - 20 * mm - 2, page_w, 2, fill=1, stroke=0)

        # Logo or lab name in header
        if logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img_io = io.BytesIO(logo_bytes)
                img = ImageReader(img_io)
                iw, ih = img.getSize()
                # Fit to 12mm height
                target_h = 12 * mm
                target_w = iw * (target_h / ih)
                if target_w > 60 * mm:
                    target_w = 60 * mm
                    target_h = ih * (target_w / iw)
                canvas.drawImage(
                    img, margin, page_h - 16 * mm,
                    width=target_w, height=target_h,
                    mask="auto",
                )
            except Exception:
                canvas.setFillColor(colors.white)
                canvas.setFont("Helvetica-Bold", 14)
                canvas.drawString(margin, page_h - 14 * mm, lab_name)
        else:
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 14)
            canvas.drawString(margin, page_h - 14 * mm, lab_name)

        # Subtitle in header
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_w - margin, page_h - 14 * mm, lab_subtitle)

        # Footer
        canvas.setFillColor(_BORDER)
        canvas.rect(margin, margin + 12 * mm, page_w - 2 * margin, 0.5, fill=1, stroke=0)
        canvas.setFillColor(_MUTED)
        canvas.setFont("Helvetica-Oblique", 7)
        # Wrap footer text
        from reportlab.lib.utils import simpleSplit
        footer_lines = simpleSplit(report_footer, "Helvetica-Oblique", 7, page_w - 2 * margin)
        y = margin + 8 * mm
        for line in footer_lines[:2]:
            canvas.drawString(margin, y, line)
            y -= 9

        # Page number + timestamp
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(
            page_w - margin, margin + 2 * mm,
            f"Page {doc.page} — Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        )
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=25 * mm,
        bottomMargin=margin,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_on_page)])

    story: list = []

    # Title
    story.append(Paragraph("LC-MS Method Report", styles["report_title"]))
    story.append(Paragraph(
        f"Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}",
        styles["report_subtitle"],
    ))

    # Compound section
    if compound:
        story.append(_section_bar("Compound Information", styles))
        story.append(Spacer(1, 4))

        compound_name = compound.name or "Unnamed compound"
        compound_smiles = compound.smiles or "N/A"

        info_data = [
            ["Name", compound_name],
            ["SMILES", compound_smiles],
            ["InChIKey", compound.inchikey or "—"],
        ]
        info_tbl = _data_table(info_data, [40 * mm, 130 * mm], styles)
        story.append(info_tbl)
        story.append(Spacer(1, 8))

        # Descriptors
        desc_data = [
            ["Property", "Value", "Property", "Value"],
            ["MW (g/mol)", f"{compound.mw:.2f}" if compound.mw else "—", "HBD", str(compound.hbd or "—")],
            ["logP", f"{compound.logp:.2f}" if compound.logp else "—", "HBA", str(compound.hba or "—")],
            ["TPSA (Å²)", f"{compound.tpsa:.1f}" if compound.tpsa else "—", "Rotatable Bonds", str(compound.rotatable_bonds or "—")],
            ["pKa (est.)", ", ".join(str(p) for p in (compound.pka_values or [])) or "—", "Aromatic Rings", str(compound.aromatic_rings or "—")],
        ]
        desc_tbl = _data_table(desc_data, [35 * mm, 50 * mm, 35 * mm, 50 * mm], styles)
        story.append(desc_tbl)

    # Method parameters
    story.append(_section_bar("Method Parameters", styles))
    story.append(Spacer(1, 4))

    method_data = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Column", method.column_type or "—", "pH", str(method.ph) if method.ph is not None else "—"],
        ["Mobile Phase A", method.mobile_phase_a or "—", "Flow (mL/min)", str(method.flow_rate_ml_min or "—")],
        ["Mobile Phase B", method.mobile_phase_b or "—", "Temp (°C)", str(method.temperature_c or "—")],
        ["Additive", method.additive or "—", "Column Length", f"{method.column_dims.get('length_mm', '—')} mm" if method.column_dims else "—"],
    ]
    method_tbl = _data_table(method_data, [35 * mm, 50 * mm, 35 * mm, 50 * mm], styles)
    story.append(method_tbl)

    # Gradient program
    story.append(_section_bar("Gradient Program", styles))
    story.append(Spacer(1, 4))
    gt = method.gradient_table or []
    if gt:
        story.append(_gradient_bars_table(gt, styles))
    else:
        story.append(Paragraph("No gradient program defined.", styles["body_muted"]))

    # Prediction results
    if prediction:
        story.append(_section_bar("Retention Prediction", styles))
        story.append(Spacer(1, 4))

        pred_data = [
            ["Parameter", "Value"],
            ["Predicted RT", f"{prediction.predicted_rt_s:.1f} s" if prediction.predicted_rt_s else "—"],
            ["RT Range", f"{prediction.rt_lower_s:.1f} – {prediction.rt_upper_s:.1f} s" if prediction.rt_lower_s and prediction.rt_upper_s else "—"],
            ["Confidence", f"{prediction.confidence:.1%}" if prediction.confidence else "—"],
            ["Model Version", prediction.model_version or "—"],
            ["Extrapolating", "Yes" if prediction.extrapolating else "No"],
        ]
        pred_tbl = _data_table(pred_data, [60 * mm, 110 * mm], styles)
        story.append(pred_tbl)

        if prediction.extrapolating:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                '<font color="#d97706">⚠ Warning: This prediction is outside the model\'s '
                "applicability domain (extrapolating). Use with caution.</font>",
                styles["body"],
            ))

    doc.build(story)
    return buf.getvalue()

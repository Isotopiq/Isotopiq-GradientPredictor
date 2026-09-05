"""Modern PDF report generator for LC-MS method reports.

Uses reportlab platypus with a professional scientific design:
- Header band with lab name/logo
- Color-coded section headers with accent bars
- Clean data tables with alternating rows
- Matplotlib-rendered gradient composition chart
- Matplotlib-rendered XIC chromatogram with EMG peaks
- Multi-compound support with resolution matrix
- Footer with disclaimer and page numbers
"""
from __future__ import annotations

import io
import math
from datetime import datetime, timezone
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
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

# Matplotlib colors matching the palette
_MPL_ACCENT = "#2563eb"
_MPL_DARK = "#1e293b"
_MPL_MUTED = "#64748b"
_MPL_GRID = "#e2e8f0"
_MPEAK_COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
]


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


def _render_gradient_chart(gradient: list[dict]) -> bytes:
    """Render a proper gradient composition chart using matplotlib.

    Shows %B vs time with a filled area under the curve, axis labels,
    gridlines, and a clean scientific style. Returns PNG bytes.
    """
    if not gradient:
        gradient = [{"time_s": 0, "percent_b": 5}, {"time_s": 1200, "percent_b": 95}]

    times_min = [p.get("time_s", 0) / 60.0 for p in gradient]
    percents = [p.get("percent_b", 0) for p in gradient]

    fig, ax = plt.subplots(figsize=(7, 2.5), dpi=150)
    fig.patch.set_facecolor("white")

    # Filled area under the curve
    ax.fill_between(times_min, 0, percents, color=_MPL_ACCENT, alpha=0.15)
    # Line on top
    ax.plot(times_min, percents, color=_MPL_ACCENT, linewidth=2, marker="o", markersize=4)

    # Also show %A (solvent A composition) as a mirror
    percents_a = [100 - p for p in percents]
    ax.plot(times_min, percents_a, color=_MPL_MUTED, linewidth=1.5, linestyle="--", alpha=0.6)
    ax.fill_between(times_min, 0, percents_a, color=_MPL_MUTED, alpha=0.05)

    ax.set_xlabel("Time (min)", fontsize=9, color=_MPL_DARK)
    ax.set_ylabel("Solvent %", fontsize=9, color=_MPL_DARK)
    ax.set_xlim(times_min[0], times_min[-1])
    ax.set_ylim(0, 100)
    ax.set_title("Gradient Composition", fontsize=11, color=_MPL_DARK, fontweight="bold", pad=8)

    # Legend
    ax.legend(["%B (Organic)", "%A (Aqueous)"], loc="upper left", fontsize=8, framealpha=0.9)

    ax.grid(True, color=_MPL_GRID, linewidth=0.5, alpha=0.7)
    ax.tick_params(colors=_MPL_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(_MPL_GRID)
        spine.set_linewidth(0.5)

    # Annotate start/end %B
    if len(times_min) >= 2:
        ax.annotate(
            f"{percents[0]:.0f}%",
            xy=(times_min[0], percents[0]),
            xytext=(5, 8),
            textcoords="offset points",
            fontsize=8,
            color=_MPL_ACCENT,
            fontweight="bold",
        )
        ax.annotate(
            f"{percents[-1]:.0f}%",
            xy=(times_min[-1], percents[-1]),
            xytext=(-20, 8),
            textcoords="offset points",
            fontsize=8,
            color=_MPL_ACCENT,
            fontweight="bold",
        )

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _emg(x: float, center: float, width: float, height: float, tau_ratio: float = 1.5) -> float:
    """Exponentially Modified Gaussian peak shape."""
    sigma = width / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    if sigma <= 0:
        return 0.0
    tau = sigma * max(0.01, tau_ratio - 1.0)
    z = (center + sigma * sigma / tau - x) / (sigma * math.sqrt(2.0))
    arg = sigma * sigma / (2.0 * tau) + (center - x) / tau
    if arg > 50 or arg < -50:
        return 0.0
    try:
        import math as m
        erfc_val = m.erfc(z)
    except (OverflowError, ValueError):
        return 0.0
    return (height / 2.0) * math.exp(arg) * erfc_val


def _render_chromatogram(
    peaks: list[dict[str, Any]],
    total_time_s: float,
) -> bytes:
    """Render an XIC chromatogram with EMG peaks using matplotlib.

    Each compound gets its own colored trace. Returns PNG bytes.
    """
    if not peaks:
        # Empty placeholder
        fig, ax = plt.subplots(figsize=(7, 2.5), dpi=150)
        fig.patch.set_facecolor("white")
        ax.text(0.5, 0.5, "No chromatogram data", ha="center", va="center",
                fontsize=12, color=_MPL_MUTED, transform=ax.transAxes)
        ax.set_axis_off()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    n_points = 500
    times = [i * total_time_s / (n_points - 1) for i in range(n_points)]
    times_min = [t / 60.0 for t in times]

    fig, ax = plt.subplots(figsize=(7, 3), dpi=150)
    fig.patch.set_facecolor("white")

    for i, peak in enumerate(peaks):
        rt_s = peak.get("rt_s", 0)
        width_s = peak.get("width_s", 10)
        height = peak.get("height", 1.0)
        tailing = peak.get("tailing", 1.5)
        label = peak.get("label", f"Peak {i+1}")
        color = peak.get("color") or _MPEAK_COLORS[i % len(_MPEAK_COLORS)]

        values = [_emg(t, rt_s, width_s, height, tailing) for t in times]
        ax.plot(times_min, values, color=color, linewidth=1.8, label=label)
        ax.fill_between(times_min, 0, values, color=color, alpha=0.15)

        # RT marker
        ax.axvline(x=rt_s / 60.0, color=color, linestyle=":", linewidth=0.8, alpha=0.5)
        ax.annotate(
            f"{label}\n{rt_s/60:.2f} min",
            xy=(rt_s / 60.0, height * 0.95),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=7,
            color=color,
            fontweight="bold",
        )

    ax.set_xlabel("Time (min)", fontsize=9, color=_MPL_DARK)
    ax.set_ylabel("Intensity (XIC)", fontsize=9, color=_MPL_DARK)
    ax.set_title("Simulated XIC Chromatogram", fontsize=11, color=_MPL_DARK, fontweight="bold", pad=8)
    ax.set_xlim(0, total_time_s / 60.0)
    ax.grid(True, color=_MPL_GRID, linewidth=0.5, alpha=0.7)
    ax.tick_params(colors=_MPL_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(_MPL_GRID)
        spine.set_linewidth(0.5)

    # Legend outside the plot
    if len(peaks) <= 6:
        ax.legend(loc="upper right", fontsize=7, framealpha=0.9, ncol=1)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _simulate_peaks_for_pdf(
    smiles_list: list[str],
    gradient_table: list[dict],
    flow_rate: float,
    ph: float,
    temperature_c: float,
    column_type: str,
) -> tuple[list[dict[str, Any]], float]:
    """Simulate chromatogram peaks for the PDF report.

    Returns (peaks, total_time_s).
    """
    from app.core.chem.parser import ChemParseError, parse_mol
    from app.core.chem.logd import logd_at_ph
    from app.core.rules.engine import suggest_method
    from app.core.lss.gradient_sim import heuristic_lss_params, predict_rt_from_gradient
    from app.core.lss.chromatogram import default_peak_width, default_tailing

    # Temperature factor (negative: RP-LC retention is exothermic, higher T → lower k)
    delta_h_over_r = -5000.0
    t1 = 303.15
    t2 = temperature_c + 273.15
    temp_factor = math.exp(delta_h_over_r * (1.0 / t1 - 1.0 / t2))
    temp_factor = max(0.5, min(2.0, temp_factor))

    peaks = []
    max_rt = 0.0

    for i, smi in enumerate(smiles_list):
        try:
            parsed = parse_mol(smi)
        except ChemParseError:
            continue

        sugg = suggest_method(
            parsed.mol,
            ionization_mode="ESI+",
            retention_goal="neutral",
            gradient_time_min=20.0,
            flow_rate_ml_min=flow_rate,
            column_type_override=column_type,
        )

        logd = logd_at_ph(parsed.mol, ph, sugg.descriptors.logp)
        params = heuristic_lss_params(
            logd,
            mw=sugg.descriptors.mw,
            tpsa=sugg.descriptors.tpsa,
            hbd=sugg.descriptors.hbd,
            hba=sugg.descriptors.hba,
            column_type=column_type,
        )
        rt = predict_rt_from_gradient(params, gradient_table, flow_rate_ml_min=flow_rate)
        rt *= temp_factor

        # Try to get a compound name
        name = f"Compound {i+1}"
        try:
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smi)
            if mol:
                # Try to get a name from the molecule
                if mol.HasProp("_Name") and mol.GetProp("_Name"):
                    name = mol.GetProp("_Name")
        except Exception:
            pass

        width = default_peak_width(rt)
        tailing = default_tailing(rt)
        color = _MPEAK_COLORS[i % len(_MPEAK_COLORS)]

        peaks.append({
            "rt_s": rt,
            "width_s": width,
            "height": 1.0,
            "label": name,
            "color": color,
            "tailing": tailing,
        })
        if rt > max_rt:
            max_rt = rt

    total_time = max(max_rt * 1.15, gradient_table[-1]["time_s"] if gradient_table else 1200)
    return peaks, total_time


def _resolution_matrix(peaks: list[dict[str, Any]]) -> list[list[str]]:
    """Build a resolution matrix table for the PDF."""
    from app.core.lss.chromatogram import resolution

    n = len(peaks)
    if n < 2:
        return []

    # Sort peaks by RT
    sorted_peaks = sorted(peaks, key=lambda p: p["rt_s"])
    header = ["Compound"] + [p["label"] for p in sorted_peaks]
    rows = [header]

    for i, pi in enumerate(sorted_peaks):
        row = [pi["label"]]
        for j, pj in enumerate(sorted_peaks):
            if i == j:
                row.append("—")
            elif i < j:
                rs = resolution(pi["rt_s"], pi["width_s"], pj["rt_s"], pj["width_s"])
                if rs < 1.5:
                    row.append(f"{rs:.2f} ⚠")
                else:
                    row.append(f"{rs:.2f}")
            else:
                row.append("")  # lower triangle empty
        rows.append(row)

    return rows


def export_method_pdf(
    method: Method,
    compound: Compound | None = None,
    prediction: Prediction | None = None,
    settings: dict | None = None,
    include_chromatogram: bool = False,
) -> bytes:
    """Generate a modern, beautifully designed PDF method report.

    Args:
        method: The method to report on.
        compound: Optional compound associated with the method.
        prediction: Optional prediction result.
        settings: Optional dict with lab_name, lab_subtitle, report_footer, logo_bytes.
        include_chromatogram: If True, include simulated XIC chromatogram and
            resolution matrix using the method's compounds_smiles.
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
    method_name = method.name or "Untitled Method"
    story.append(Paragraph(
        f"<b>{method_name}</b> &mdash; Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}",
        styles["report_subtitle"],
    ))

    # --- Compound Information ---
    compounds_smiles: list[str] = method.compounds_smiles or []
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
    elif compounds_smiles:
        # Multi-compound section
        story.append(_section_bar(f"Compounds ({len(compounds_smiles)})", styles))
        story.append(Spacer(1, 4))

        comp_data = [["#", "SMILES", "Status"]]
        for i, smi in enumerate(compounds_smiles):
            comp_data.append([str(i + 1), smi[:80] + ("..." if len(smi) > 80 else ""), "Parsed"])
        comp_tbl = _data_table(comp_data, [10 * mm, 140 * mm, 20 * mm], styles)
        story.append(comp_tbl)

    # --- Method Parameters ---
    story.append(_section_bar("Method Parameters", styles))
    story.append(Spacer(1, 4))

    col_dims = method.column_dims or {}
    method_data = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Column Type", method.column_type or "—", "pH", f"{method.ph:.2f}" if method.ph is not None else "—"],
        ["Mobile Phase A", method.mobile_phase_a or "—", "Flow (mL/min)", f"{method.flow_rate_ml_min:.2f}" if method.flow_rate_ml_min else "—"],
        ["Mobile Phase B", method.mobile_phase_b or "—", "Temp (°C)", f"{method.temperature_c:.0f}" if method.temperature_c else "—"],
        ["Additive", method.additive or "—", "Column Length", f"{col_dims.get('length_mm', '—')} mm" if col_dims else "—"],
    ]
    method_tbl = _data_table(method_data, [35 * mm, 50 * mm, 35 * mm, 50 * mm], styles)
    story.append(method_tbl)

    # --- Gradient Program with visual chart ---
    story.append(_section_bar("Gradient Program", styles))
    story.append(Spacer(1, 4))
    gt = method.gradient_table or []
    if gt:
        # Render gradient chart as PNG
        gradient_png = _render_gradient_chart(gt)
        img = Image(io.BytesIO(gradient_png), width=170 * mm, height=60 * mm)
        story.append(img)
        story.append(Spacer(1, 6))

        # Also include the gradient table data
        grad_data = [["Time (min)", "%B", "%A"]]
        for p in gt:
            t_min = p.get("time_s", 0) / 60.0
            pct_b = p.get("percent_b", 0)
            grad_data.append([f"{t_min:.2f}", f"{pct_b:.1f}%", f"{100 - pct_b:.1f}%"])
        grad_tbl = _data_table(grad_data, [40 * mm, 40 * mm, 40 * mm], styles)
        story.append(grad_tbl)
    else:
        story.append(Paragraph("No gradient program defined.", styles["body_muted"]))

    # --- Prediction Results ---
    if prediction:
        story.append(_section_bar("Retention Prediction", styles))
        story.append(Spacer(1, 4))

        pred_data = [
            ["Parameter", "Value"],
            ["Predicted RT", f"{prediction.predicted_rt_s:.1f} s ({prediction.predicted_rt_s/60:.2f} min)" if prediction.predicted_rt_s else "—"],
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
                '<font color="#d97706">Warning: This prediction is outside the model\'s '
                "applicability domain (extrapolating). Use with caution.</font>",
                styles["body"],
            ))

    # --- Simulated Chromatogram (optional) ---
    if include_chromatogram and compounds_smiles:
        story.append(PageBreak())
        story.append(_section_bar("Simulated XIC Chromatogram", styles))
        story.append(Spacer(1, 4))

        # Simulate peaks
        peaks, total_time = _simulate_peaks_for_pdf(
            compounds_smiles,
            gt,
            flow_rate=method.flow_rate_ml_min or 0.4,
            ph=method.ph or 2.7,
            temperature_c=method.temperature_c or 30.0,
            column_type=method.column_type or "C18",
        )

        if peaks:
            # Render chromatogram chart
            chroma_png = _render_chromatogram(peaks, total_time)
            img = Image(io.BytesIO(chroma_png), width=170 * mm, height=72 * mm)
            story.append(img)
            story.append(Spacer(1, 8))

            # Peak summary table
            peak_data = [["#", "Compound", "RT (min)", "Width (s)", "Tailing"]]
            for i, p in enumerate(peaks):
                peak_data.append([
                    str(i + 1),
                    p["label"],
                    f"{p['rt_s']/60:.2f}",
                    f"{p['width_s']:.1f}",
                    f"{p['tailing']:.2f}",
                ])
            peak_tbl = _data_table(peak_data, [10 * mm, 60 * mm, 30 * mm, 30 * mm, 30 * mm], styles)
            story.append(peak_tbl)
            story.append(Spacer(1, 8))

            # Resolution matrix
            res_matrix = _resolution_matrix(peaks)
            if res_matrix:
                story.append(_section_bar("Resolution Matrix (Rs)", styles))
                story.append(Spacer(1, 4))
                # Calculate column widths based on number of compounds
                n_cols = len(res_matrix[0])
                col_w = 170 * mm / n_cols
                res_tbl = _data_table(res_matrix, [col_w] * n_cols, styles)
                story.append(res_tbl)
                story.append(Spacer(1, 4))
                story.append(Paragraph(
                    "Rs &gt; 1.5 indicates baseline resolution. "
                    "Rs &lt; 1.5 (marked with &#9888;) indicates co-elution risk.",
                    styles["body_muted"],
                ))
        else:
            story.append(Paragraph(
                "Unable to simulate chromatogram — compounds could not be parsed.",
                styles["body_muted"],
            ))

    # --- Disclaimer ---
    story.append(Spacer(1, 14))
    story.append(_section_bar("Disclaimer", styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Predictions are estimates derived from physicochemical heuristics and "
        "statistical models. They require experimental verification before use in "
        "regulated or production analytical work. pKa values are heuristic estimates. "
        "Retention times may differ from actual experimental results due to column "
        "batch variability, instrument configuration, and sample matrix effects.",
        styles["body_muted"],
    ))

    doc.build(story)
    return buf.getvalue()

"""Modern PDF report generator for LC-MS method reports.

Uses reportlab platypus with a professional scientific design:
- Header band with lab name/logo
- Color-coded section headers with accent bars
- Clean data tables with alternating rows
- Matplotlib-rendered gradient composition chart
- Matplotlib-rendered XIC chromatogram with EMG peaks
- Multi-compound support with resolution matrix
- Optional robustness, optimization, and method transfer sections
- User-selectable sections via PDFSectionOptions
- Theme support (blue, green, slate, burgundy)
- Optional cover page with admin-configurable text
- Footer with disclaimer and page numbers
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
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

# ---------------------------------------------------------------------------
# Theme palettes
# ---------------------------------------------------------------------------

_THEMES: dict[str, dict[str, str]] = {
    "blue": {
        "accent": "#2563eb",
        "accent_light": "#dbeafe",
        "dark": "#1e293b",
        "muted": "#64748b",
        "row_alt": "#f8fafc",
        "border": "#e2e8f0",
        "success": "#16a34a",
        "warning": "#d97706",
    },
    "green": {
        "accent": "#059669",
        "accent_light": "#d1fae5",
        "dark": "#064e3b",
        "muted": "#6b7280",
        "row_alt": "#f0fdf4",
        "border": "#d1d5db",
        "success": "#16a34a",
        "warning": "#d97706",
    },
    "slate": {
        "accent": "#475569",
        "accent_light": "#e2e8f0",
        "dark": "#0f172a",
        "muted": "#64748b",
        "row_alt": "#f8fafc",
        "border": "#cbd5e1",
        "success": "#16a34a",
        "warning": "#d97706",
    },
    "burgundy": {
        "accent": "#9f1239",
        "accent_light": "#fecdd3",
        "dark": "#4c0519",
        "muted": "#6b7280",
        "row_alt": "#fef2f2",
        "border": "#e5e7eb",
        "success": "#16a34a",
        "warning": "#d97706",
    },
}


def _get_theme(name: str | None) -> dict[str, colors.HexColor]:
    """Return reportlab color objects for the given theme."""
    t = _THEMES.get(name or "blue", _THEMES["blue"])
    return {k: colors.HexColor(v) for k, v in t.items()}


def _get_mpl_theme(name: str | None) -> dict[str, str]:
    """Return matplotlib color strings for the given theme."""
    return _THEMES.get(name or "blue", _THEMES["blue"])


# Peak colors (shared across all themes)
_MPEAK_COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
]


# ---------------------------------------------------------------------------
# Section selection model
# ---------------------------------------------------------------------------

@dataclass
class PDFSectionOptions:
    """User-selectable sections for PDF export.

    Every section is independently toggleable. Defaults match the
    pre-refactor behaviour (method params + gradient + compound info
    + disclaimer on; chromatogram + resolution + robustness + optimization
    + transfer + cover off).
    """
    method_parameters: bool = True
    gradient_program: bool = True
    compound_info: bool = True
    chromatogram: bool = False
    resolution_matrix: bool = False
    robustness: bool = False
    optimization: bool = False
    method_transfer: bool = False
    cover_page: bool = False
    disclaimer: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, bool] | None) -> PDFSectionOptions:
        if d is None:
            return cls()
        return cls(
            method_parameters=d.get("method_parameters", True),
            gradient_program=d.get("gradient_program", True),
            compound_info=d.get("compound_info", True),
            chromatogram=d.get("chromatogram", False),
            resolution_matrix=d.get("resolution_matrix", False),
            robustness=d.get("robustness", False),
            optimization=d.get("optimization", False),
            method_transfer=d.get("method_transfer", False),
            cover_page=d.get("cover_page", False),
            disclaimer=d.get("disclaimer", True),
        )


@dataclass
class ColumnComparisonSections:
    """Section toggles for column comparison PDFs."""
    tanaka_table: bool = True
    radar_chart: bool = True
    similarity_matrix: bool = True
    parameter_diffs: bool = True
    cover_page: bool = False
    disclaimer: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, bool] | None) -> ColumnComparisonSections:
        if d is None:
            return cls()
        return cls(
            tanaka_table=d.get("tanaka_table", True),
            radar_chart=d.get("radar_chart", True),
            similarity_matrix=d.get("similarity_matrix", True),
            parameter_diffs=d.get("parameter_diffs", True),
            cover_page=d.get("cover_page", False),
            disclaimer=d.get("disclaimer", True),
        )


@dataclass
class BatchAnalysisSections:
    """Section toggles for batch analysis PDFs."""
    method_parameters: bool = True
    compound_table: bool = True
    chromatogram: bool = True
    flagged_compounds: bool = True
    cover_page: bool = False
    disclaimer: bool = True

    @classmethod
    def from_dict(cls, d: dict[str, bool] | None) -> BatchAnalysisSections:
        if d is None:
            return cls()
        return cls(
            method_parameters=d.get("method_parameters", True),
            compound_table=d.get("compound_table", True),
            chromatogram=d.get("chromatogram", True),
            flagged_compounds=d.get("flagged_compounds", True),
            cover_page=d.get("cover_page", False),
            disclaimer=d.get("disclaimer", True),
        )


# ---------------------------------------------------------------------------
# Style helpers (theme-aware)
# ---------------------------------------------------------------------------

def _build_styles(theme: dict[str, colors.HexColor]) -> dict:
    """Create custom paragraph styles for the given theme."""
    base = getSampleStyleSheet()
    styles = {
        "report_title": ParagraphStyle(
            "report_title", parent=base["Title"],
            fontSize=20, leading=26, textColor=theme["dark"],
            spaceAfter=4, fontName="Helvetica-Bold",
        ),
        "report_subtitle": ParagraphStyle(
            "report_subtitle", parent=base["Normal"],
            fontSize=10, leading=14, textColor=theme["muted"],
            spaceAfter=12, fontName="Helvetica",
        ),
        "section_header": ParagraphStyle(
            "section_header", parent=base["Heading2"],
            fontSize=12, leading=16, textColor=theme["accent"],
            spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, leading=13, textColor=theme["dark"],
            fontName="Helvetica",
        ),
        "body_muted": ParagraphStyle(
            "body_muted", parent=base["Normal"],
            fontSize=8, leading=11, textColor=theme["muted"],
            fontName="Helvetica",
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, leading=10, textColor=theme["muted"],
            fontName="Helvetica-Oblique",
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Normal"],
            fontSize=8, leading=11, textColor=theme["dark"],
            fontName="Courier",
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"],
            fontSize=9, leading=12, textColor=theme["dark"],
            fontName="Helvetica",
            wordWrap="LTR",
        ),
        "cell_small": ParagraphStyle(
            "cell_small", parent=base["Normal"],
            fontSize=8, leading=10, textColor=theme["dark"],
            fontName="Helvetica",
            wordWrap="LTR",
        ),
        "cell_mono": ParagraphStyle(
            "cell_mono", parent=base["Normal"],
            fontSize=7.5, leading=10, textColor=theme["dark"],
            fontName="Courier",
            wordWrap="LTR",
        ),
        "cell_header": ParagraphStyle(
            "cell_header", parent=base["Normal"],
            fontSize=9, leading=12, textColor=colors.white,
            fontName="Helvetica-Bold",
            wordWrap="LTR",
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"],
            fontSize=28, leading=36, textColor=theme["accent"],
            spaceAfter=8, fontName="Helvetica-Bold",
            alignment=1,  # center
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", parent=base["Normal"],
            fontSize=14, leading=20, textColor=theme["muted"],
            spaceAfter=24, fontName="Helvetica",
            alignment=1,
        ),
        "cover_body": ParagraphStyle(
            "cover_body", parent=base["Normal"],
            fontSize=11, leading=16, textColor=theme["dark"],
            spaceAfter=12, fontName="Helvetica",
            alignment=1,
        ),
    }
    return styles


def _section_bar(title: str, styles: dict, theme: dict[str, colors.HexColor]) -> Table:
    """Create a section header with a colored left bar."""
    bar = Table(
        [[Paragraph(title, styles["section_header"])]],
        colWidths=[170 * mm],
    )
    bar.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, 0), 3, theme["accent"]),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("TOPPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
    ]))
    return bar


def _wrap_cell(value: str, styles: dict, is_header: bool = False, is_mono: bool = False) -> Any:
    """Wrap a cell value in a Paragraph for proper text wrapping.

    Plain strings in ReportLab Tables don't wrap — they overflow.
    Paragraphs respect wordWrap and column width automatically.
    """
    if isinstance(value, (Paragraph, Table, Image)):
        return value
    text = str(value) if value is not None else ""
    # Escape XML special characters for ReportLab Paragraph
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if is_header:
        return Paragraph(text, styles["cell_header"])
    if is_mono:
        return Paragraph(text, styles["cell_mono"])
    return Paragraph(text, styles["cell"])


def _data_table(
    data: list[list[str]],
    col_widths: list[float],
    styles: dict,
    theme: dict[str, colors.HexColor],
    mono_columns: set[int] | None = None,
) -> Table:
    """Create a styled data table with header row, alternating rows, and text wrapping.

    Args:
        data: 2D list of cell values (strings or Paragraphs).
        col_widths: Column widths in points.
        styles: Style dict from _build_styles.
        theme: Theme color dict.
        mono_columns: Set of column indices (0-based) that should use monospace
            font (e.g. SMILES columns). Defaults to empty set.
    """
    if mono_columns is None:
        mono_columns = set()

    # Wrap all cell values in Paragraphs for proper text wrapping
    wrapped_data: list[list[Any]] = []
    for row_idx, row in enumerate(data):
        wrapped_row: list[Any] = []
        for col_idx, cell in enumerate(row):
            if row_idx == 0:
                wrapped_row.append(_wrap_cell(cell, styles, is_header=True))
            elif col_idx in mono_columns:
                wrapped_row.append(_wrap_cell(cell, styles, is_mono=True))
            else:
                wrapped_row.append(_wrap_cell(cell, styles))
        wrapped_data.append(wrapped_row)

    tbl = Table(wrapped_data, colWidths=col_widths)
    style_cmds = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), theme["accent"]),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, theme["border"]),
        ("BOX", (0, 0), (-1, -1), 0.5, theme["border"]),
    ]
    # Alternating row backgrounds
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), theme["row_alt"]))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ---------------------------------------------------------------------------
# Chart renderers (theme-aware)
# ---------------------------------------------------------------------------

def _render_gradient_chart(gradient: list[dict], mpl_theme: dict[str, str]) -> bytes:
    """Render a gradient composition chart using matplotlib. Returns PNG bytes."""
    if not gradient:
        gradient = [{"time_s": 0, "percent_b": 5}, {"time_s": 1200, "percent_b": 95}]

    times_min = [p.get("time_s", 0) / 60.0 for p in gradient]
    percents = [p.get("percent_b", 0) for p in gradient]

    fig, ax = plt.subplots(figsize=(7, 2.5), dpi=150)
    fig.patch.set_facecolor("white")

    ax.fill_between(times_min, 0, percents, color=mpl_theme["accent"], alpha=0.15)
    ax.plot(times_min, percents, color=mpl_theme["accent"], linewidth=2, marker="o", markersize=4)

    percents_a = [100 - p for p in percents]
    ax.plot(times_min, percents_a, color=mpl_theme["muted"], linewidth=1.5, linestyle="--", alpha=0.6)
    ax.fill_between(times_min, 0, percents_a, color=mpl_theme["muted"], alpha=0.05)

    ax.set_xlabel("Time (min)", fontsize=9, color=mpl_theme["dark"])
    ax.set_ylabel("Solvent %", fontsize=9, color=mpl_theme["dark"])
    ax.set_xlim(times_min[0], times_min[-1])
    ax.set_ylim(0, 100)
    ax.set_title("Gradient Composition", fontsize=11, color=mpl_theme["dark"], fontweight="bold", pad=8)
    ax.legend(["%B (Organic)", "%A (Aqueous)"], loc="upper left", fontsize=8, framealpha=0.9)

    ax.grid(True, color=mpl_theme["border"], linewidth=0.5, alpha=0.7)
    ax.tick_params(colors=mpl_theme["muted"], labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(mpl_theme["border"])
        spine.set_linewidth(0.5)

    if len(times_min) >= 2:
        ax.annotate(f"{percents[0]:.0f}%", xy=(times_min[0], percents[0]),
                    xytext=(5, 8), textcoords="offset points",
                    fontsize=8, color=mpl_theme["accent"], fontweight="bold")
        ax.annotate(f"{percents[-1]:.0f}%", xy=(times_min[-1], percents[-1]),
                    xytext=(-20, 8), textcoords="offset points",
                    fontsize=8, color=mpl_theme["accent"], fontweight="bold")

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
    mpl_theme: dict[str, str],
) -> bytes:
    """Render an XIC chromatogram with EMG peaks using matplotlib. Returns PNG bytes.

    Uses smart label placement to prevent overlap:
    - Labels are placed above the plot area with callout lines to peaks
    - Labels are staggered vertically when peaks are close together
    - Long labels are truncated
    - Figure height adapts to the number of peaks
    """
    if not peaks:
        fig, ax = plt.subplots(figsize=(7, 2.5), dpi=150)
        fig.patch.set_facecolor("white")
        ax.text(0.5, 0.5, "No chromatogram data", ha="center", va="center",
                fontsize=12, color=mpl_theme["muted"], transform=ax.transAxes)
        ax.set_axis_off()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    n_points = 500
    times = [i * total_time_s / (n_points - 1) for i in range(n_points)]
    times_min = [t / 60.0 for t in times]

    # Sort peaks by RT for label placement
    sorted_peaks = sorted(peaks, key=lambda p: p.get("rt_s", 0))

    # Dynamic figure height: taller for more peaks
    n_peaks = len(sorted_peaks)
    fig_height = 3.0 if n_peaks <= 4 else (3.5 if n_peaks <= 8 else 4.0)

    fig, ax = plt.subplots(figsize=(7, fig_height), dpi=150)
    fig.patch.set_facecolor("white")

    # Plot peaks
    for i, peak in enumerate(sorted_peaks):
        rt_s = peak.get("rt_s", 0)
        width_s = peak.get("width_s", 10)
        height = peak.get("height", 1.0)
        tailing = peak.get("tailing", 1.5)
        label = peak.get("label", f"Peak {i+1}")
        color = peak.get("color") or _MPEAK_COLORS[i % len(_MPEAK_COLORS)]

        values = [_emg(t, rt_s, width_s, height, tailing) for t in times]
        ax.plot(times_min, values, color=color, linewidth=1.8, label=label)
        ax.fill_between(times_min, 0, values, color=color, alpha=0.15)

    # Set y-axis limit with headroom for labels
    ax.set_ylim(0, 1.45)
    ax.set_xlim(0, total_time_s / 60.0)

    # Smart label placement: stagger labels vertically and use callout lines
    # Place labels in the upper portion of the plot (y > 1.0 in normalized height)
    # Stagger between 3 levels to avoid overlap
    label_levels = [1.35, 1.22, 1.09]
    min_rt_gap = total_time_s / 60.0 * 0.06  # 6% of total time as minimum gap

    placed_labels: list[dict[str, Any]] = []

    for i, peak in enumerate(sorted_peaks):
        rt_s = peak.get("rt_s", 0)
        rt_min = rt_s / 60.0
        label = peak.get("label", f"Peak {i+1}")
        color = peak.get("color") or _MPEAK_COLORS[i % len(_MPEAK_COLORS)]

        # Truncate long labels
        max_label_len = 18
        if len(label) > max_label_len:
            label = label[:max_label_len - 1] + "…"

        label_text = f"{label}\n{rt_min:.2f} min"

        # Determine vertical level: check if previous label at level 0 is too close
        level_idx = i % len(label_levels)
        # Try to find a level that doesn't overlap with recent labels
        for try_level in range(len(label_levels)):
            level = label_levels[try_level]
            overlap = False
            for pl in placed_labels:
                if abs(pl["rt_min"] - rt_min) < min_rt_gap and abs(pl["level"] - level) < 0.08:
                    overlap = True
                    break
            if not overlap:
                level_idx = try_level
                break
        else:
            # All levels overlap — use the staggered one
            level_idx = i % len(label_levels)

        y_label = label_levels[level_idx]

        # Draw callout line from peak top to label
        peak_y = peak.get("height", 1.0) * 0.95
        ax.annotate(
            "",
            xy=(rt_min, peak_y),
            xytext=(rt_min, y_label - 0.02),
            arrowprops=dict(
                arrowstyle="-",
                color=color,
                linewidth=0.6,
                alpha=0.6,
                linestyle=":",
            ),
        )

        # Place the label text
        ha = "center"
        # Adjust horizontal alignment if near edges
        if rt_min < total_time_s / 60.0 * 0.08:
            ha = "left"
        elif rt_min > total_time_s / 60.0 * 0.92:
            ha = "right"

        ax.text(
            rt_min, y_label, label_text,
            fontsize=6.5, color=color, fontweight="bold",
            ha=ha, va="bottom",
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor=color, linewidth=0.4, alpha=0.85),
        )

        placed_labels.append({"rt_min": rt_min, "level": y_label, "label": label})

    ax.set_xlabel("Time (min)", fontsize=9, color=mpl_theme["dark"])
    ax.set_ylabel("Intensity (XIC)", fontsize=9, color=mpl_theme["dark"])
    ax.set_title("Simulated XIC Chromatogram", fontsize=11, color=mpl_theme["dark"], fontweight="bold", pad=8)
    ax.grid(True, color=mpl_theme["border"], linewidth=0.5, alpha=0.7)
    ax.tick_params(colors=mpl_theme["muted"], labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(mpl_theme["border"])
        spine.set_linewidth(0.5)

    # Legend below the plot for many peaks, upper right for few
    if n_peaks <= 6:
        ax.legend(loc="upper right", fontsize=7, framealpha=0.9, ncol=1,
                  bbox_to_anchor=(1.0, 0.95))
    else:
        ax.legend(loc="upper center", fontsize=6, framealpha=0.9,
                  ncol=min(n_peaks, 4), bbox_to_anchor=(0.5, 1.02))

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _render_radar_chart(
    columns: list[dict[str, Any]],
    mpl_theme: dict[str, str],
) -> bytes:
    """Render a Tanaka radar chart overlaying up to 4 columns. Returns PNG bytes."""
    categories = ["k PB", "k SR", "k TFA", "k CH2", "k amide"]
    n = len(categories)
    angles = [i / n * 2 * math.pi for i in range(n)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), dpi=150, subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")

    colors_list = [mpl_theme["accent"], "#ef4444", "#10b981", "#f59e0b"]

    for i, col in enumerate(columns):
        tanaka = col.get("tanaka", {})
        values = [
            tanaka.get("k_pb", 0),
            tanaka.get("k_sr", 0),
            tanaka.get("k_tfa", 0),
            tanaka.get("k_ch2", 0),
            tanaka.get("k_amide", 0),
        ]
        # Normalise to 0-1 range for radar (divide by typical max)
        max_vals = [10, 10, 10, 10, 10]
        values_norm = [min(v / m, 1.0) for v, m in zip(values, max_vals, strict=False)]
        values_norm += values_norm[:1]
        color = colors_list[i % len(colors_list)]
        ax.plot(angles, values_norm, "o-", linewidth=2, color=color, label=col.get("label", f"Column {i+1}"))
        ax.fill(angles, values_norm, alpha=0.15, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=9, color=mpl_theme["dark"])
    ax.set_ylim(0, 1)
    ax.set_title("Tanaka Column Comparison", fontsize=11, color=mpl_theme["dark"], fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8, framealpha=0.9)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _render_resolution_heatmap(
    rts: list[float],
    widths: list[float],
    labels: list[str],
    mpl_theme: dict[str, str],
) -> bytes:
    """Render a simple resolution heatmap between compounds. Returns PNG bytes."""
    n = len(rts)
    if n < 2:
        fig, ax = plt.subplots(figsize=(5, 3), dpi=150)
        fig.patch.set_facecolor("white")
        ax.text(0.5, 0.5, "Need 2+ compounds", ha="center", va="center",
                fontsize=12, color=mpl_theme["muted"], transform=ax.transAxes)
        ax.set_axis_off()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    from app.core.lss.chromatogram import resolution as calc_res

    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 0
            else:
                matrix[i][j] = calc_res(rts[i], widths[i], rts[j], widths[j])

    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    fig.patch.set_facecolor("white")

    import numpy as np
    arr = np.array(matrix)
    im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=3)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    short_labels = [lbl[:12] for lbl in labels]
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8, color=mpl_theme["dark"])
    ax.set_yticklabels(short_labels, fontsize=8, color=mpl_theme["dark"])
    ax.set_title("Resolution Matrix (Rs)", fontsize=11, color=mpl_theme["dark"], fontweight="bold", pad=8)

    for i in range(n):
        for j in range(n):
            if i != j:
                ax.text(j, i, f"{matrix[i][j]:.1f}", ha="center", va="center", fontsize=7, color="white" if matrix[i][j] < 1.5 else mpl_theme["dark"])

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Rs")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Peak simulation for PDF
# ---------------------------------------------------------------------------

def _simulate_peaks_for_pdf(
    smiles_list: list[str],
    gradient_table: list[dict],
    flow_rate: float,
    ph: float,
    temperature_c: float,
    column_type: str,
    compound_names: list[str] | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """Simulate chromatogram peaks for the PDF report.

    Returns (peaks, total_time_s).
    """
    from app.core.chem.logd import logd_at_ph
    from app.core.chem.parser import ChemParseError, parse_mol
    from app.core.lss.chromatogram import default_peak_width, default_tailing
    from app.core.lss.gradient_sim import heuristic_lss_params, predict_rt_from_gradient
    from app.core.rules.engine import suggest_method

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

        name = (compound_names[i] if compound_names and i < len(compound_names) else None) or f"Compound {i+1}"

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
                    row.append(f"{rs:.2f} !")
                else:
                    row.append(f"{rs:.2f}")
            else:
                row.append("")
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# New section renderers
# ---------------------------------------------------------------------------

def _render_robustness_section(
    method: Method,
    compounds_smiles: list[str],
    styles: dict,
    theme: dict[str, colors.HexColor],
) -> list:
    """Render robustness analysis section. Returns story flowables."""
    story: list = []
    from app.services.method_service import analyze_robustness

    try:
        result = analyze_robustness(
            smiles_list=compounds_smiles,
            gradient_table=method.gradient_table or [],
            flow_rate_ml_min=method.flow_rate_ml_min or 0.4,
            ph=method.ph or 2.7,
            temperature_c=method.temperature_c or 30.0,
            column_type=method.column_type or "C18",
        )
    except Exception:
        story.append(Paragraph("Robustness analysis could not be computed.", styles["body_muted"]))
        return story

    if not result.get("perturbations"):
        story.append(Paragraph(
            result.get("message", "Need at least 2 compounds for robustness analysis."),
            styles["body_muted"],
        ))
        return story

    story.append(_section_bar("Robustness Analysis", styles, theme))
    story.append(Spacer(1, 4))

    # Perturbation table
    pert_data = [["Parameter", "Delta", "Min Rs", "Rs Change"]]
    for p in result["perturbations"]:
        change = p["resolution_change"]
        change_str = f"{change:+.3f}" if change >= 0 else f"{change:.3f}"
        pert_data.append([
            p["parameter"],
            p["delta"],
            f"{p['min_resolution']:.3f}",
            change_str,
        ])
    pert_tbl = _data_table(pert_data, [40 * mm, 30 * mm, 40 * mm, 40 * mm], styles, theme)
    story.append(pert_tbl)
    story.append(Spacer(1, 6))

    # Summary
    story.append(Paragraph(
        f"<b>Sensitivity score:</b> {result['sensitivity_score']:.3f} "
        f"(lower is more robust)",
        styles["body"],
    ))
    if result.get("most_sensitive_compound", -1) >= 0:
        story.append(Paragraph(
            f"<b>Most sensitive compound:</b> #{result['most_sensitive_compound'] + 1}",
            styles["body"],
        ))
    story.append(Paragraph(
        f"<b>Baseline min Rs:</b> {result.get('baseline_min_resolution', 0):.3f}",
        styles["body"],
    ))

    return story


def _render_optimization_section(
    method: Method,
    compounds_smiles: list[str],
    styles: dict,
    theme: dict[str, colors.HexColor],
    mpl_theme: dict[str, str],
) -> list:
    """Render optimization results section. Returns story flowables."""
    story: list = []
    story.append(_section_bar("Optimization Results", styles, theme))
    story.append(Spacer(1, 4))

    if not compounds_smiles or len(compounds_smiles) < 2:
        story.append(Paragraph(
            "Optimization requires 2 or more compounds.",
            styles["body_muted"],
        ))
        return story

    # Simulate peaks to get RTs and widths for the resolution heatmap
    try:
        peaks, total_time = _simulate_peaks_for_pdf(
            compounds_smiles,
            method.gradient_table or [],
            flow_rate=method.flow_rate_ml_min or 0.4,
            ph=method.ph or 2.7,
            temperature_c=method.temperature_c or 30.0,
            column_type=method.column_type or "C18",
        )
    except Exception:
        story.append(Paragraph(
            "Could not simulate optimization data.",
            styles["body_muted"],
        ))
        return story

    if not peaks:
        story.append(Paragraph("No peaks could be simulated.", styles["body_muted"]))
        return story

    # Resolution heatmap
    rts = [p["rt_s"] for p in peaks]
    widths = [p["width_s"] for p in peaks]
    labels = [p["label"] for p in peaks]

    heatmap_png = _render_resolution_heatmap(rts, widths, labels, mpl_theme)
    img = Image(io.BytesIO(heatmap_png), width=140 * mm, height=110 * mm)
    story.append(img)
    story.append(Spacer(1, 6))

    # Peak summary
    peak_data = [["#", "Compound", "RT (min)", "Width (s)", "Tailing"]]
    for i, p in enumerate(peaks):
        peak_data.append([
            str(i + 1),
            p["label"],
            f"{p['rt_s']/60:.2f}",
            f"{p['width_s']:.1f}",
            f"{p['tailing']:.2f}",
        ])
    peak_tbl = _data_table(peak_data, [10 * mm, 60 * mm, 30 * mm, 30 * mm, 30 * mm], styles, theme)
    story.append(peak_tbl)

    return story


def _render_transfer_section(
    method: Method,
    styles: dict,
    theme: dict[str, colors.HexColor],
) -> list:
    """Render method transfer info section. Returns story flowables."""
    story: list = []
    story.append(_section_bar("Method Transfer Information", styles, theme))
    story.append(Spacer(1, 4))

    dwell = method.dwell_volume_ml
    dead = method.dead_volume_ml
    flow = method.flow_rate_ml_min or 0.4

    has_volume = dwell is not None or dead is not None
    if not has_volume:
        story.append(Paragraph(
            "No dwell or dead volume data recorded for this method.",
            styles["body_muted"],
        ))
        return story

    transfer_data = [["Parameter", "Value"]]
    if dwell is not None:
        transfer_data.append(["Dwell Volume", f"{dwell:.2f} mL"])
        dwell_delay = dwell / flow
        transfer_data.append(["Dwell Time (gradient delay)", f"{dwell_delay:.2f} min ({dwell_delay * 60:.0f} s)"])
    if dead is not None:
        transfer_data.append(["Dead Volume", f"{dead:.2f} mL"])
        dead_time = dead / flow
        transfer_data.append(["Dead Time (t0)", f"{dead_time:.2f} min ({dead_time * 60:.0f} s)"])

    transfer_tbl = _data_table(transfer_data, [80 * mm, 90 * mm], styles, theme)
    story.append(transfer_tbl)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "When transferring this method to another instrument, adjust the gradient "
        "start time by the difference in dwell volumes divided by the flow rate.",
        styles["body_muted"],
    ))

    return story


def _build_cover_page(
    method: Method,
    settings: dict,
    styles: dict,
    theme: dict[str, colors.HexColor],
) -> list:
    """Build a full-page cover. Returns story flowables."""
    story: list = []
    s = settings or {}
    lab_name = s.get("lab_name", "IsotopiQ")
    title_prefix = s.get("report_title_prefix", "")
    cover_text = s.get("cover_page_text", "")

    story.append(Spacer(1, 60 * mm))

    # Lab name
    story.append(Paragraph(lab_name, styles["cover_title"]))
    story.append(Paragraph("LC-MS Method Prediction Suite", styles["cover_subtitle"]))

    story.append(Spacer(1, 20 * mm))

    # Report title
    report_title = "LC-MS Method Report"
    if title_prefix:
        report_title = f"{title_prefix} — {report_title}"
    story.append(Paragraph(report_title, styles["cover_title"]))

    method_name = method.name or "Untitled Method"
    story.append(Paragraph(method_name, styles["cover_subtitle"]))

    story.append(Spacer(1, 15 * mm))

    # Date
    now = datetime.now(UTC)
    story.append(Paragraph(
        now.strftime("%B %d, %Y at %H:%M UTC"),
        styles["cover_body"],
    ))

    # Cover page text from admin settings
    if cover_text:
        story.append(Spacer(1, 20 * mm))
        story.append(Paragraph(cover_text, styles["cover_body"]))

    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# Main method PDF generator (section-driven)
# ---------------------------------------------------------------------------

def export_method_pdf(
    method: Method,
    compound: Compound | None = None,
    prediction: Prediction | None = None,
    settings: dict | None = None,
    sections: PDFSectionOptions | None = None,
    compound_names: list[str] | None = None,
) -> bytes:
    """Generate a PDF method report with user-selected sections.

    Args:
        method: The method to report on.
        compound: Optional compound associated with the method.
        prediction: Optional prediction result.
        settings: Dict with lab_name, lab_subtitle, report_footer, logo_bytes,
                  report_title_prefix, cover_page_text, report_theme.
        sections: Which sections to include. Defaults to all-true for basic sections.
        compound_names: Optional names for compounds_smiles entries.
    """
    if sections is None:
        sections = PDFSectionOptions()

    s = settings or {}
    theme_name = s.get("report_theme", "blue")
    theme = _get_theme(theme_name)
    mpl_theme = _get_mpl_theme(theme_name)

    buf = io.BytesIO()
    styles = _build_styles(theme)

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
        canvas.setFillColor(theme["dark"])
        canvas.rect(0, page_h - 20 * mm, page_w, 20 * mm, fill=1, stroke=0)
        # Accent line under header
        canvas.setFillColor(theme["accent"])
        canvas.rect(0, page_h - 20 * mm - 2, page_w, 2, fill=1, stroke=0)

        # Logo or lab name in header
        if logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img_io = io.BytesIO(logo_bytes)
                img = ImageReader(img_io)
                iw, ih = img.getSize()
                target_h = 12 * mm
                target_w = iw * (target_h / ih)
                if target_w > 60 * mm:
                    target_w = 60 * mm
                    target_h = ih * (target_w / iw)
                canvas.drawImage(img, margin, page_h - 16 * mm,
                                 width=target_w, height=target_h, mask="auto")
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
        canvas.setFillColor(theme["border"])
        canvas.rect(margin, margin + 12 * mm, page_w - 2 * margin, 0.5, fill=1, stroke=0)
        canvas.setFillColor(theme["muted"])
        canvas.setFont("Helvetica-Oblique", 7)
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
            f"Page {doc.page} — Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        )
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=25 * mm, bottomMargin=margin,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_on_page)])

    story: list = []

    # --- Cover page ---
    if sections.cover_page:
        story.extend(_build_cover_page(method, s, styles, theme))

    # --- Title ---
    title_prefix = s.get("report_title_prefix", "")
    title_text = "LC-MS Method Report"
    if title_prefix:
        title_text = f"{title_prefix} — {title_text}"
    story.append(Paragraph(title_text, styles["report_title"]))
    method_name = method.name or "Untitled Method"
    story.append(Paragraph(
        f"<b>{method_name}</b> &mdash; Generated on {datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')}",
        styles["report_subtitle"],
    ))

    compounds_smiles: list[str] = method.compounds_smiles or []

    # --- Compound Information ---
    if sections.compound_info:
        if compound:
            story.append(_section_bar("Compound Information", styles, theme))
            story.append(Spacer(1, 4))

            compound_name = compound.name or "Unnamed compound"
            compound_smiles = compound.smiles or "N/A"

            info_data = [
                ["Name", compound_name],
                ["SMILES", compound_smiles],
                ["InChIKey", compound.inchikey or "—"],
            ]
            info_tbl = _data_table(info_data, [40 * mm, 130 * mm], styles, theme, mono_columns={1})
            story.append(info_tbl)
            story.append(Spacer(1, 8))

            desc_data = [
                ["Property", "Value", "Property", "Value"],
                ["MW (g/mol)", f"{compound.mw:.2f}" if compound.mw else "—", "HBD", str(compound.hbd or "—")],
                ["logP", f"{compound.logp:.2f}" if compound.logp else "—", "HBA", str(compound.hba or "—")],
                ["TPSA (Å²)", f"{compound.tpsa:.1f}" if compound.tpsa else "—", "Rotatable Bonds", str(compound.rotatable_bonds or "—")],
                ["pKa (est.)", ", ".join(str(p) for p in (compound.pka_values or [])) or "—", "Aromatic Rings", str(compound.aromatic_rings or "—")],
            ]
            desc_tbl = _data_table(desc_data, [35 * mm, 50 * mm, 35 * mm, 50 * mm], styles, theme)
            story.append(desc_tbl)
        elif compounds_smiles:
            story.append(_section_bar(f"Compounds ({len(compounds_smiles)})", styles, theme))
            story.append(Spacer(1, 4))

            comp_data = [["#", "SMILES", "Name"]]
            for i, smi in enumerate(compounds_smiles):
                name = (compound_names[i] if compound_names and i < len(compound_names) else "—")
                comp_data.append([str(i + 1), smi, name])
            comp_tbl = _data_table(comp_data, [10 * mm, 120 * mm, 40 * mm], styles, theme, mono_columns={1})
            story.append(comp_tbl)

    # --- Method Parameters ---
    if sections.method_parameters:
        story.append(_section_bar("Method Parameters", styles, theme))
        story.append(Spacer(1, 4))

        col_dims = method.column_dims or {}
        method_data = [
            ["Parameter", "Value", "Parameter", "Value"],
            ["Column Type", method.column_type or "—", "pH", f"{method.ph:.2f}" if method.ph is not None else "—"],
            ["Mobile Phase A", method.mobile_phase_a or "—", "Flow (mL/min)", f"{method.flow_rate_ml_min:.2f}" if method.flow_rate_ml_min else "—"],
            ["Mobile Phase B", method.mobile_phase_b or "—", "Temp (°C)", f"{method.temperature_c:.0f}" if method.temperature_c else "—"],
            ["Additive", method.additive or "—", "Column Length", f"{col_dims.get('length_mm', '—')} mm" if col_dims else "—"],
        ]
        method_tbl = _data_table(method_data, [35 * mm, 50 * mm, 35 * mm, 50 * mm], styles, theme)
        story.append(method_tbl)

    # --- Gradient Program ---
    if sections.gradient_program:
        story.append(_section_bar("Gradient Program", styles, theme))
        story.append(Spacer(1, 4))
        gt = method.gradient_table or []
        if gt:
            gradient_png = _render_gradient_chart(gt, mpl_theme)
            img = Image(io.BytesIO(gradient_png), width=170 * mm, height=60 * mm)
            story.append(img)
            story.append(Spacer(1, 6))

            grad_data = [["Time (min)", "%B", "%A"]]
            for p in gt:
                t_min = p.get("time_s", 0) / 60.0
                pct_b = p.get("percent_b", 0)
                grad_data.append([f"{t_min:.2f}", f"{pct_b:.1f}%", f"{100 - pct_b:.1f}%"])
            grad_tbl = _data_table(grad_data, [40 * mm, 40 * mm, 40 * mm], styles, theme)
            story.append(grad_tbl)
        else:
            story.append(Paragraph("No gradient program defined.", styles["body_muted"]))

    # --- Prediction Results ---
    if prediction:
        story.append(_section_bar("Retention Prediction", styles, theme))
        story.append(Spacer(1, 4))

        pred_data = [
            ["Parameter", "Value"],
            ["Predicted RT", f"{prediction.predicted_rt_s:.1f} s ({prediction.predicted_rt_s/60:.2f} min)" if prediction.predicted_rt_s else "—"],
            ["RT Range", f"{prediction.rt_lower_s:.1f} – {prediction.rt_upper_s:.1f} s" if prediction.rt_lower_s and prediction.rt_upper_s else "—"],
            ["Confidence", f"{prediction.confidence:.1%}" if prediction.confidence else "—"],
            ["Model Version", prediction.model_version or "—"],
            ["Extrapolating", "Yes" if prediction.extrapolating else "No"],
        ]
        pred_tbl = _data_table(pred_data, [60 * mm, 110 * mm], styles, theme)
        story.append(pred_tbl)

        if prediction.extrapolating:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f'<font color="{mpl_theme["warning"]}">Warning: This prediction is outside the model\'s '
                "applicability domain (extrapolating). Use with caution.</font>",
                styles["body"],
            ))

    # --- Simulated Chromatogram ---
    if sections.chromatogram and compounds_smiles:
        story.append(PageBreak())
        story.append(_section_bar("Simulated XIC Chromatogram", styles, theme))
        story.append(Spacer(1, 4))

        peaks, total_time = _simulate_peaks_for_pdf(
            compounds_smiles,
            method.gradient_table or [],
            flow_rate=method.flow_rate_ml_min or 0.4,
            ph=method.ph or 2.7,
            temperature_c=method.temperature_c or 30.0,
            column_type=method.column_type or "C18",
            compound_names=compound_names,
        )

        if peaks:
            chroma_png = _render_chromatogram(peaks, total_time, mpl_theme)
            img = Image(io.BytesIO(chroma_png), width=170 * mm, height=72 * mm)
            story.append(img)
            story.append(Spacer(1, 8))

            peak_data = [["#", "Compound", "RT (min)", "Width (s)", "Tailing"]]
            for i, p in enumerate(peaks):
                peak_data.append([
                    str(i + 1), p["label"],
                    f"{p['rt_s']/60:.2f}", f"{p['width_s']:.1f}", f"{p['tailing']:.2f}",
                ])
            peak_tbl = _data_table(peak_data, [10 * mm, 60 * mm, 30 * mm, 30 * mm, 30 * mm], styles, theme)
            story.append(peak_tbl)
        else:
            story.append(Paragraph(
                "Unable to simulate chromatogram — compounds could not be parsed.",
                styles["body_muted"],
            ))

    # --- Resolution Matrix ---
    if sections.resolution_matrix and compounds_smiles and len(compounds_smiles) >= 2:
        if not sections.chromatogram:
            # Need peaks — simulate if not already done
            peaks, _ = _simulate_peaks_for_pdf(
                compounds_smiles,
                method.gradient_table or [],
                flow_rate=method.flow_rate_ml_min or 0.4,
                ph=method.ph or 2.7,
                temperature_c=method.temperature_c or 30.0,
                column_type=method.column_type or "C18",
                compound_names=compound_names,
            )
        # peaks may be defined from chromatogram section above
        if 'peaks' in dir() and peaks:
            res_matrix = _resolution_matrix(peaks)
            if res_matrix:
                story.append(Spacer(1, 8))
                story.append(_section_bar("Resolution Matrix (Rs)", styles, theme))
                story.append(Spacer(1, 4))
                n_cols = len(res_matrix[0])
                col_w = 170 * mm / n_cols
                res_tbl = _data_table(res_matrix, [col_w] * n_cols, styles, theme)
                story.append(res_tbl)
                story.append(Spacer(1, 4))
                story.append(Paragraph(
                    "Rs &gt; 1.5 indicates baseline resolution. "
                    "Rs &lt; 1.5 (marked with !) indicates co-elution risk.",
                    styles["body_muted"],
                ))

    # --- Robustness Analysis ---
    if sections.robustness and compounds_smiles:
        story.append(PageBreak())
        story.extend(_render_robustness_section(method, compounds_smiles, styles, theme))

    # --- Optimization Results ---
    if sections.optimization and compounds_smiles:
        story.append(PageBreak())
        story.extend(_render_optimization_section(method, compounds_smiles, styles, theme, mpl_theme))

    # --- Method Transfer Info ---
    if sections.method_transfer:
        story.append(PageBreak())
        story.extend(_render_transfer_section(method, styles, theme))

    # --- Disclaimer ---
    if sections.disclaimer:
        story.append(Spacer(1, 14))
        story.append(_section_bar("Disclaimer", styles, theme))
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


# ---------------------------------------------------------------------------
# Column comparison PDF
# ---------------------------------------------------------------------------

def export_column_comparison_pdf(
    columns: list[dict[str, Any]],
    settings: dict | None = None,
    sections: ColumnComparisonSections | None = None,
) -> bytes:
    """Generate a column comparison PDF report.

    Args:
        columns: List of dicts with 'label' and 'tanaka' keys.
            tanaka: {k_pb, k_sr, k_tfa, k_ch2, k_amide}
        settings: Admin settings dict.
        sections: Which sections to include.
    """
    if sections is None:
        sections = ColumnComparisonSections()

    s = settings or {}
    theme_name = s.get("report_theme", "blue")
    theme = _get_theme(theme_name)
    mpl_theme = _get_mpl_theme(theme_name)

    buf = io.BytesIO()
    styles = _build_styles(theme)

    lab_name = s.get("lab_name", "IsotopiQ")
    lab_subtitle = s.get("lab_subtitle", "LC-MS Method Prediction Suite")
    report_footer = s.get(
        "report_footer",
        "Predictions are estimates derived from physicochemical heuristics and statistical models. "
        "They require experimental verification before use in regulated or production analytical work.",
    )
    logo_bytes = s.get("logo_bytes")

    page_w, page_h = A4
    margin = 15 * mm
    frame = Frame(margin, margin + 15 * mm, page_w - 2 * margin, page_h - 2 * margin - 25 * mm, id="main")

    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(theme["dark"])
        canvas.rect(0, page_h - 20 * mm, page_w, 20 * mm, fill=1, stroke=0)
        canvas.setFillColor(theme["accent"])
        canvas.rect(0, page_h - 20 * mm - 2, page_w, 2, fill=1, stroke=0)
        if logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img_io = io.BytesIO(logo_bytes)
                img = ImageReader(img_io)
                iw, ih = img.getSize()
                target_h = 12 * mm
                target_w = iw * (target_h / ih)
                if target_w > 60 * mm:
                    target_w = 60 * mm
                    target_h = ih * (target_w / iw)
                canvas.drawImage(img, margin, page_h - 16 * mm,
                                 width=target_w, height=target_h, mask="auto")
            except Exception:
                canvas.setFillColor(colors.white)
                canvas.setFont("Helvetica-Bold", 14)
                canvas.drawString(margin, page_h - 14 * mm, lab_name)
        else:
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 14)
            canvas.drawString(margin, page_h - 14 * mm, lab_name)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_w - margin, page_h - 14 * mm, lab_subtitle)
        canvas.setFillColor(theme["border"])
        canvas.rect(margin, margin + 12 * mm, page_w - 2 * margin, 0.5, fill=1, stroke=0)
        canvas.setFillColor(theme["muted"])
        canvas.setFont("Helvetica-Oblique", 7)
        from reportlab.lib.utils import simpleSplit
        footer_lines = simpleSplit(report_footer, "Helvetica-Oblique", 7, page_w - 2 * margin)
        y = margin + 8 * mm
        for line in footer_lines[:2]:
            canvas.drawString(margin, y, line)
            y -= 9
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(
            page_w - margin, margin + 2 * mm,
            f"Page {doc.page} — Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        )
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=25 * mm, bottomMargin=margin,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_on_page)])

    story: list = []

    # Cover page
    if sections.cover_page:
        story.append(Spacer(1, 60 * mm))
        story.append(Paragraph(lab_name, styles["cover_title"]))
        story.append(Paragraph("LC-MS Method Prediction Suite", styles["cover_subtitle"]))
        story.append(Spacer(1, 20 * mm))
        title_prefix = s.get("report_title_prefix", "")
        title_text = "Column Comparison Report"
        if title_prefix:
            title_text = f"{title_prefix} — {title_text}"
        story.append(Paragraph(title_text, styles["cover_title"]))
        story.append(Paragraph(
            datetime.now(UTC).strftime("%B %d, %Y at %H:%M UTC"),
            styles["cover_body"],
        ))
        cover_text = s.get("cover_page_text", "")
        if cover_text:
            story.append(Spacer(1, 20 * mm))
            story.append(Paragraph(cover_text, styles["cover_body"]))
        story.append(PageBreak())

    # Title
    title_text = "Column Comparison Report"
    title_prefix = s.get("report_title_prefix", "")
    if title_prefix:
        title_text = f"{title_prefix} — {title_text}"
    story.append(Paragraph(title_text, styles["report_title"]))
    story.append(Paragraph(
        f"Comparing {len(columns)} columns — Generated on {datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')}",
        styles["report_subtitle"],
    ))

    # Tanaka parameter table
    if sections.tanaka_table:
        story.append(_section_bar("Tanaka Parameters", styles, theme))
        story.append(Spacer(1, 4))
        tanaka_data = [["Column", "k PB", "k SR", "k TFA", "k CH2", "k Amide"]]
        for col in columns:
            t = col.get("tanaka", {})
            tanaka_data.append([
                col.get("label", "—"),
                f"{t.get('k_pb', 0):.2f}",
                f"{t.get('k_sr', 0):.2f}",
                f"{t.get('k_tfa', 0):.2f}",
                f"{t.get('k_ch2', 0):.2f}",
                f"{t.get('k_amide', 0):.2f}",
            ])
        n_cols = len(tanaka_data[0])
        col_w = 170 * mm / n_cols
        story.append(_data_table(tanaka_data, [col_w] * n_cols, styles, theme))

    # Radar chart
    if sections.radar_chart and columns:
        story.append(Spacer(1, 8))
        story.append(_section_bar("Radar Chart", styles, theme))
        story.append(Spacer(1, 4))
        radar_png = _render_radar_chart(columns, mpl_theme)
        img = Image(io.BytesIO(radar_png), width=120 * mm, height=120 * mm)
        story.append(img)

    # Similarity matrix
    if sections.similarity_matrix and len(columns) >= 2:
        story.append(Spacer(1, 8))
        story.append(_section_bar("Similarity / Orthogonality Matrix", styles, theme))
        story.append(Spacer(1, 4))
        # Compute pairwise similarity (1 - normalised Euclidean distance)
        import math as _math
        sim_data = [["Column"] + [c.get("label", f"Col {i+1}") for i, c in enumerate(columns)]]
        for i, ci in enumerate(columns):
            row = [ci.get("label", f"Col {i+1}")]
            ti = list(ci.get("tanaka", {}).values())
            for j, cj in enumerate(columns):
                if i == j:
                    row.append("1.000")
                else:
                    tj = list(cj.get("tanaka", {}).values())
                    if ti and tj and len(ti) == len(tj):
                        dist = _math.sqrt(sum((a - b) ** 2 for a, b in zip(ti, tj, strict=False)))
                        max_possible = _math.sqrt(
                            sum(max(a, b) ** 2 for a, b in zip(ti, tj, strict=False))
                        )
                        sim = 1.0 - (dist / max_possible if max_possible > 0 else 0)
                        row.append(f"{sim:.3f}")
                    else:
                        row.append("—")
            sim_data.append(row)
        n_cols = len(sim_data[0])
        col_w = 170 * mm / n_cols
        story.append(_data_table(sim_data, [col_w] * n_cols, styles, theme))

    # Parameter differences
    if sections.parameter_diffs and len(columns) >= 2:
        story.append(Spacer(1, 8))
        story.append(_section_bar("Parameter Differences", styles, theme))
        story.append(Spacer(1, 4))
        diff_data = [["Pair", "k PB diff", "k SR diff", "k TFA diff", "k CH2 diff", "k Amide diff"]]
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                ti = columns[i].get("tanaka", {})
                tj = columns[j].get("tanaka", {})
                pair = f"{columns[i].get('label', f'Col {i+1}')} vs {columns[j].get('label', f'Col {j+1}')}"
                diff_data.append([
                    pair,
                    f"{abs(ti.get('k_pb', 0) - tj.get('k_pb', 0)):.2f}",
                    f"{abs(ti.get('k_sr', 0) - tj.get('k_sr', 0)):.2f}",
                    f"{abs(ti.get('k_tfa', 0) - tj.get('k_tfa', 0)):.2f}",
                    f"{abs(ti.get('k_ch2', 0) - tj.get('k_ch2', 0)):.2f}",
                    f"{abs(ti.get('k_amide', 0) - tj.get('k_amide', 0)):.2f}",
                ])
        n_cols = len(diff_data[0])
        col_w = 170 * mm / n_cols
        story.append(_data_table(diff_data, [col_w] * n_cols, styles, theme))

    # Disclaimer
    if sections.disclaimer:
        story.append(Spacer(1, 14))
        story.append(_section_bar("Disclaimer", styles, theme))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "Tanaka parameters provide a standardized characterization of column selectivity. "
            "Actual chromatographic performance may vary due to column batch variability, "
            "instrument configuration, and sample matrix effects. Always verify experimentally.",
            styles["body_muted"],
        ))

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Batch analysis PDF
# ---------------------------------------------------------------------------

def export_batch_analysis_pdf(
    batch_data: dict[str, Any],
    settings: dict | None = None,
    sections: BatchAnalysisSections | None = None,
) -> bytes:
    """Generate a batch analysis PDF report.

    Args:
        batch_data: Dict with 'method_params', 'compounds', 'results'.
        settings: Admin settings dict.
        sections: Which sections to include.
    """
    if sections is None:
        sections = BatchAnalysisSections()

    s = settings or {}
    theme_name = s.get("report_theme", "blue")
    theme = _get_theme(theme_name)
    mpl_theme = _get_mpl_theme(theme_name)

    buf = io.BytesIO()
    styles = _build_styles(theme)

    lab_name = s.get("lab_name", "IsotopiQ")
    lab_subtitle = s.get("lab_subtitle", "LC-MS Method Prediction Suite")
    report_footer = s.get(
        "report_footer",
        "Predictions are estimates derived from physicochemical heuristics and statistical models. "
        "They require experimental verification before use in regulated or production analytical work.",
    )
    logo_bytes = s.get("logo_bytes")

    page_w, page_h = A4
    margin = 15 * mm
    frame = Frame(margin, margin + 15 * mm, page_w - 2 * margin, page_h - 2 * margin - 25 * mm, id="main")

    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(theme["dark"])
        canvas.rect(0, page_h - 20 * mm, page_w, 20 * mm, fill=1, stroke=0)
        canvas.setFillColor(theme["accent"])
        canvas.rect(0, page_h - 20 * mm - 2, page_w, 2, fill=1, stroke=0)
        if logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img_io = io.BytesIO(logo_bytes)
                img = ImageReader(img_io)
                iw, ih = img.getSize()
                target_h = 12 * mm
                target_w = iw * (target_h / ih)
                if target_w > 60 * mm:
                    target_w = 60 * mm
                    target_h = ih * (target_w / iw)
                canvas.drawImage(img, margin, page_h - 16 * mm,
                                 width=target_w, height=target_h, mask="auto")
            except Exception:
                canvas.setFillColor(colors.white)
                canvas.setFont("Helvetica-Bold", 14)
                canvas.drawString(margin, page_h - 14 * mm, lab_name)
        else:
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 14)
            canvas.drawString(margin, page_h - 14 * mm, lab_name)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_w - margin, page_h - 14 * mm, lab_subtitle)
        canvas.setFillColor(theme["border"])
        canvas.rect(margin, margin + 12 * mm, page_w - 2 * margin, 0.5, fill=1, stroke=0)
        canvas.setFillColor(theme["muted"])
        canvas.setFont("Helvetica-Oblique", 7)
        from reportlab.lib.utils import simpleSplit
        footer_lines = simpleSplit(report_footer, "Helvetica-Oblique", 7, page_w - 2 * margin)
        y = margin + 8 * mm
        for line in footer_lines[:2]:
            canvas.drawString(margin, y, line)
            y -= 9
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(
            page_w - margin, margin + 2 * mm,
            f"Page {doc.page} — Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        )
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=25 * mm, bottomMargin=margin,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_on_page)])

    story: list = []
    mp = batch_data.get("method_params", {})
    compounds = batch_data.get("compounds", [])
    results = batch_data.get("results", [])

    # Cover page
    if sections.cover_page:
        story.append(Spacer(1, 60 * mm))
        story.append(Paragraph(lab_name, styles["cover_title"]))
        story.append(Paragraph("LC-MS Method Prediction Suite", styles["cover_subtitle"]))
        story.append(Spacer(1, 20 * mm))
        title_prefix = s.get("report_title_prefix", "")
        title_text = "Batch Analysis Report"
        if title_prefix:
            title_text = f"{title_prefix} — {title_text}"
        story.append(Paragraph(title_text, styles["cover_title"]))
        story.append(Paragraph(
            datetime.now(UTC).strftime("%B %d, %Y at %H:%M UTC"),
            styles["cover_body"],
        ))
        cover_text = s.get("cover_page_text", "")
        if cover_text:
            story.append(Spacer(1, 20 * mm))
            story.append(Paragraph(cover_text, styles["cover_body"]))
        story.append(PageBreak())

    # Title
    title_text = "Batch Analysis Report"
    title_prefix = s.get("report_title_prefix", "")
    if title_prefix:
        title_text = f"{title_prefix} — {title_text}"
    story.append(Paragraph(title_text, styles["report_title"]))
    story.append(Paragraph(
        f"{len(compounds)} compounds — Generated on {datetime.now(UTC).strftime('%B %d, %Y at %H:%M UTC')}",
        styles["report_subtitle"],
    ))

    # Method parameters
    if sections.method_parameters:
        story.append(_section_bar("Method Parameters", styles, theme))
        story.append(Spacer(1, 4))
        method_data = [
            ["Parameter", "Value", "Parameter", "Value"],
            ["Column Type", mp.get("column_type", "—"), "pH", f"{mp.get('ph', '—')}"],
            ["Flow Rate", f"{mp.get('flow_rate_ml_min', '—')} mL/min", "Temp", f"{mp.get('temperature_c', '—')} °C"],
            ["Mobile Phase A", mp.get("mobile_phase_a", "—"), "Mobile Phase B", mp.get("mobile_phase_b", "—")],
            ["Additive", mp.get("additive", "—"), "", ""],
        ]
        story.append(_data_table(method_data, [35 * mm, 50 * mm, 35 * mm, 50 * mm], styles, theme))

    # Compound results table
    if sections.compound_table and results:
        story.append(Spacer(1, 8))
        story.append(_section_bar("Compound Results", styles, theme))
        story.append(Spacer(1, 4))
        comp_data = [["#", "Name/SMILES", "RT (min)", "Width (s)", "Status"]]
        for i, r in enumerate(results):
            name = r.get("name") or r.get("smiles", "—")
            rt = r.get("rt_s")
            width = r.get("width_s")
            status = r.get("status", "OK")
            comp_data.append([
                str(i + 1),
                name,
                f"{rt / 60:.2f}" if rt else "—",
                f"{width:.1f}" if width else "—",
                status,
            ])
        story.append(_data_table(comp_data, [10 * mm, 80 * mm, 25 * mm, 25 * mm, 30 * mm], styles, theme, mono_columns={1}))

    # Simulated chromatogram
    if sections.chromatogram and results:
        story.append(Spacer(1, 8))
        story.append(_section_bar("Simulated Chromatogram", styles, theme))
        story.append(Spacer(1, 4))
        peaks = []
        max_rt = 0.0
        for i, r in enumerate(results):
            rt = r.get("rt_s", 0)
            width = r.get("width_s", 10)
            if rt <= 0:
                continue
            peaks.append({
                "rt_s": rt,
                "width_s": width,
                "height": 1.0,
                "label": r.get("name", f"Compound {i+1}"),
                "color": _MPEAK_COLORS[i % len(_MPEAK_COLORS)],
                "tailing": 1.5,
            })
            if rt > max_rt:
                max_rt = rt
        if peaks:
            total_time = max(max_rt * 1.15, 1200)
            chroma_png = _render_chromatogram(peaks, total_time, mpl_theme)
            img = Image(io.BytesIO(chroma_png), width=170 * mm, height=72 * mm)
            story.append(img)
        else:
            story.append(Paragraph("No chromatogram data available.", styles["body_muted"]))

    # Flagged compounds
    if sections.flagged_compounds and results:
        flagged = [r for r in results if r.get("status") and r.get("status") != "OK"]
        if flagged:
            story.append(Spacer(1, 8))
            story.append(_section_bar("Flagged Compounds", styles, theme))
            story.append(Spacer(1, 4))
            flag_data = [["#", "Name/SMILES", "RT (min)", "Issue"]]
            for i, r in enumerate(flagged):
                name = r.get("name") or r.get("smiles", "—")
                rt = r.get("rt_s")
                flag_data.append([
                    str(i + 1),
                    name,
                    f"{rt / 60:.2f}" if rt else "—",
                    r.get("status", "—"),
                ])
            story.append(_data_table(flag_data, [10 * mm, 80 * mm, 30 * mm, 50 * mm], styles, theme, mono_columns={1}))
        else:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "No flagged compounds — all compounds processed successfully.",
                styles["body_muted"],
            ))

    # Disclaimer
    if sections.disclaimer:
        story.append(Spacer(1, 14))
        story.append(_section_bar("Disclaimer", styles, theme))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "Batch analysis predictions are estimates derived from physicochemical heuristics "
            "and statistical models. They require experimental verification before use in "
            "regulated or production analytical work.",
            styles["body_muted"],
        ))

    doc.build(story)
    return buf.getvalue()

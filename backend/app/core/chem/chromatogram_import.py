"""CSV/TXT chromatogram import.

Parses common Agilent, Chromeleon, and Empower-style CSV/TXT
chromatogram exports, validates structure, detects peaks, and
returns time/intensity arrays.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any

MAX_FILE_SIZE_MB = 10
MAX_POINTS = 100_000


@dataclass
class ChromatogramData:
    """Parsed chromatogram data."""
    time_min: list[float]
    intensity: list[float]
    detector: str = "UV"
    wavelength_nm: float | None = None
    sample_name: str = ""
    n_points: int = 0
    peaks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_min": [round(t, 4) for t in self.time_min],
            "intensity": [round(i, 2) for i in self.intensity],
            "detector": self.detector,
            "wavelength_nm": self.wavelength_nm,
            "sample_name": self.sample_name,
            "n_points": self.n_points,
            "peaks": self.peaks,
        }


class ChromatogramImportError(Exception):
    """Raised when chromatogram import fails."""
    pass


def parse_chromatogram_csv(
    content: str,
    filename: str = "",
) -> ChromatogramData:
    """Parse a CSV/TXT chromatogram file.

    Supports multiple formats:
    - Agilent .csv: time,intensity columns
    - Chromeleon .txt: tab-separated with header
    - Empower .csv: with metadata header
    - Generic: two-column time/intensity
    """
    if not content or not content.strip():
        raise ChromatogramImportError("Empty file content")

    # Check file size (approximate)
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ChromatogramImportError(f"File too large (max {MAX_FILE_SIZE_MB} MB)")

    # Auto-detect delimiter
    first_line = content.split("\n")[0]
    if "\t" in first_line:
        delimiter = "\t"
    elif "," in first_line:
        delimiter = ","
    elif ";" in first_line:
        delimiter = ";"
    else:
        delimiter = ","  # default

    # Parse into rows
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        raise ChromatogramImportError("No data rows found")

    # Find the data start (skip metadata headers)
    data_start = 0
    sample_name = filename
    wavelength: float | None = None
    detector = "UV"

    for i, row in enumerate(rows[:30]):  # check first 30 rows for headers
        if not row:
            continue
        # Look for metadata
        row_str = " ".join(row).lower()
        if "sample" in row_str and ":" in " ".join(row):
            for cell in row:
                if "sample" in cell.lower() and ":" in cell:
                    sample_name = cell.split(":")[-1].strip()
        if "wavelength" in row_str or "wl" in row_str:
            for cell in row:
                m = re.search(r"(\d+\.?\d*)\s*nm", cell)
                if m:
                    wavelength = float(m.group(1))
        if "detector" in row_str:
            for cell in row:
                if "uv" in cell.lower() or "dad" in cell.lower():
                    detector = "UV"
                elif "ms" in cell.lower() or "tic" in cell.lower():
                    detector = "MS"

        # Check if this row has numeric data (time, intensity)
        if len(row) >= 2:
            try:
                float(row[0].strip())
                float(row[1].strip())
                data_start = i
                break
            except (ValueError, IndexError):
                continue

    # Extract time and intensity columns
    time_min: list[float] = []
    intensity: list[float] = []

    # Determine column indices (default 0=time, 1=intensity)
    time_col = 0
    int_col = 1

    # Check if the first data row is actually a header
    if data_start < len(rows):
        first_data = rows[data_start]
        if first_data and len(first_data) >= 2:
            try:
                float(first_data[0].strip())
            except ValueError:
                # It's a header — find time/intensity columns
                for ci, cell in enumerate(first_data):
                    cell_lower = cell.lower().strip()
                    if "time" in cell_lower or "rt" in cell_lower or "min" in cell_lower:
                        time_col = ci
                    elif "intensity" in cell_lower or "abs" in cell_lower or "au" in cell_lower or "signal" in cell_lower or "count" in cell_lower:
                        int_col = ci
                data_start += 1

    for row in rows[data_start:]:
        if not row or len(row) <= max(time_col, int_col):
            continue
        try:
            t = float(row[time_col].strip())
            i_val = float(row[int_col].strip())
            time_min.append(t)
            intensity.append(i_val)
        except (ValueError, IndexError):
            continue

        if len(time_min) > MAX_POINTS:
            raise ChromatogramImportError(f"Too many data points (max {MAX_POINTS})")

    if len(time_min) < 2:
        raise ChromatogramImportError(
            f"Not enough data points ({len(time_min)}). Expected at least 2 time/intensity pairs."
        )

    # Detect peaks using simple threshold + local maxima
    peaks = detect_peaks(time_min, intensity)

    return ChromatogramData(
        time_min=time_min,
        intensity=intensity,
        detector=detector,
        wavelength_nm=wavelength,
        sample_name=sample_name,
        n_points=len(time_min),
        peaks=peaks,
    )


def detect_peaks(
    time_min: list[float],
    intensity: list[float],
    min_height: float | None = None,
    min_width_points: int = 3,
) -> list[dict[str, Any]]:
    """Detect peaks using local maxima with threshold.

    Returns list of peaks with:
    - rt_min: retention time
    - height: peak height
    - width_min: estimated width
    - area: estimated area
    """
    if len(intensity) < 3:
        return []

    # Auto-determine threshold: 5% of max intensity or 3x noise
    max_int = max(intensity)
    if min_height is None:
        # Estimate noise as median of bottom 20% of points
        sorted_int = sorted(intensity)
        noise_level = sorted_int[len(sorted_int) // 5] if sorted_int else 0
        min_height = max(noise_level * 3, max_int * 0.02)

    peaks: list[dict[str, Any]] = []

    # Find local maxima
    for i in range(1, len(intensity) - 1):
        if intensity[i] <= min_height:
            continue
        if intensity[i] > intensity[i - 1] and intensity[i] >= intensity[i + 1]:
            # Check width (count points above threshold on each side)
            left = i
            while left > 0 and intensity[left] > min_height:
                left -= 1
            right = i
            while right < len(intensity) - 1 and intensity[right] > min_height:
                right += 1

            width_points = right - left
            if width_points < min_width_points:
                continue

            # Estimate width in minutes
            if right < len(time_min) and left < len(time_min):
                width_min = time_min[right] - time_min[left]
            else:
                width_min = 0.0

            # Estimate area (trapezoidal)
            area = 0.0
            for j in range(left, right):
                if j + 1 < len(intensity):
                    area += (intensity[j] + intensity[j + 1]) / 2.0 * (
                        time_min[j + 1] - time_min[j] if j + 1 < len(time_min) else 0
                    )

            peaks.append({
                "rt_min": round(time_min[i], 4),
                "height": round(intensity[i], 2),
                "width_min": round(width_min, 4),
                "area": round(area, 2),
                "index": i,
            })

    # Merge peaks that are very close (< 0.05 min)
    merged: list[dict[str, Any]] = []
    for p in peaks:
        if merged and abs(p["rt_min"] - merged[-1]["rt_min"]) < 0.05:
            # Keep the taller one
            if p["height"] > merged[-1]["height"]:
                merged[-1] = p
        else:
            merged.append(p)

    return merged

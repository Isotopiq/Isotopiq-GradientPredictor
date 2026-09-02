"""mzXML file parser: extract ion chromatograms and detect peaks.

Uses pyteomics for robust mzXML parsing with a fallback to xml.etree.
Peak detection uses scipy.signal.find_peaks with a fallback to simple
max + FWHM estimation.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ScanData:
    """A single MS scan."""
    scan_number: int
    retention_time_s: float
    ms_level: int
    mz_array: np.ndarray
    intensity_array: np.ndarray
    polarity: str | None = None
    base_peak_mz: float | None = None
    base_peak_intensity: float | None = None
    total_ion_current: float | None = None


@dataclass
class XICPoint:
    """A single point in an extracted ion chromatogram."""
    retention_time_s: float
    intensity: float


@dataclass
class DetectedPeak:
    """A detected peak in an XIC."""
    retention_time_s: float
    retention_time_min: float
    intensity: float
    peak_width_s: float | None = None
    signal_to_noise: float | None = None
    start_rt_s: float | None = None
    end_rt_s: float | None = None


@dataclass
class CompoundPeakResult:
    """Peak detection result for a single compound."""
    compound_id: str | None = None
    compound_name: str | None = None
    smiles: str | None = None
    target_mz: float | None = None
    mz_tolerance_ppm: float | None = None
    xic: list[XICPoint] = field(default_factory=list)
    peaks: list[DetectedPeak] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "compound_id": self.compound_id,
            "compound_name": self.compound_name,
            "smiles": self.smiles,
            "target_mz": self.target_mz,
            "mz_tolerance_ppm": self.mz_tolerance_ppm,
            "peaks": [
                {
                    "retention_time_s": p.retention_time_s,
                    "retention_time_min": p.retention_time_min,
                    "intensity": p.intensity,
                    "peak_width_s": p.peak_width_s,
                    "signal_to_noise": p.signal_to_noise,
                }
                for p in self.peaks
            ],
            "xic_points": len(self.xic),
            "error": self.error,
        }


@dataclass
class MzXmlSummary:
    """Summary of an mzXML file."""
    num_scans: int = 0
    num_ms1_scans: int = 0
    num_ms2_scans: int = 0
    rt_start_s: float | None = None
    rt_end_s: float | None = None
    polarity: str | None = None
    instrument: str | None = None
    scans: list[ScanData] = field(default_factory=list)


class MzXmlParseError(ValueError):
    """Raised when an mzXML file cannot be parsed."""


def _decode_base64_peaks(
    data: str, precision: int = 64, byte_order: str = "network"
) -> tuple[np.ndarray, np.ndarray]:
    """Decode base64-encoded peak data from mzXML.

    mzXML stores m/z and intensity arrays as base64-encoded binary data,
    interleaved as [mz1, int1, mz2, int2, ...].

    byte_order: "network" = big-endian (">"), "little" = little-endian ("<")
    """
    import base64
    import struct

    raw = base64.b64decode(data)
    dtype = "d" if precision == 64 else "f"
    endian = ">" if byte_order == "network" else "<"

    # Calculate number of pairs
    byte_size = 8 if precision == 64 else 4
    num_pairs = len(raw) // (2 * byte_size)

    # Unpack interleaved pairs
    format_str = f"{endian}{num_pairs * 2}{dtype}"
    values = struct.unpack(format_str, raw[:num_pairs * 2 * byte_size])

    mz = np.array(values[0::2], dtype=np.float64)
    intensity = np.array(values[1::2], dtype=np.float64)
    return mz, intensity


def parse_mzxml(content: bytes, max_scans: int = 0) -> MzXmlSummary:
    """Parse an mzXML file and extract MS1 scans.

    Args:
        content: Raw bytes of the mzXML file
        max_scans: Maximum number of scans to parse (0 = all)

    Returns:
        MzXmlSummary with scan data

    Raises:
        MzXmlParseError: If the file cannot be parsed
    """
    if not content:
        raise MzXmlParseError("Empty file content")

    summary = MzXmlSummary()

    # Try pyteomics first for robust parsing
    try:
        return _parse_with_pyteomics(content, max_scans)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback to custom XML parser
    return _parse_with_etree(content, max_scans)


def _parse_with_pyteomics(content: bytes, max_scans: int = 0) -> MzXmlSummary:
    """Parse mzXML using pyteomics."""
    from pyteomics import mzxml

    summary = MzXmlSummary()
    scans: list[ScanData] = []

    with io.BytesIO(content) as f:
        reader = mzxml.read(f)
        for i, scan in enumerate(reader):
            if max_scans > 0 and i >= max_scans:
                break

            rt_s = float(scan.get("retentionTime", 0))
            ms_level = int(scan.get("msLevel", 1))
            scan_num = int(scan.get("num", i + 1))
            polarity = scan.get("polarity", "")

            mz_array = scan.get("m/z array", np.array([]))
            int_array = scan.get("intensity array", np.array([]))

            scan_data = ScanData(
                scan_number=scan_num,
                retention_time_s=rt_s,
                ms_level=ms_level,
                mz_array=np.asarray(mz_array, dtype=np.float64),
                intensity_array=np.asarray(int_array, dtype=np.float64),
                polarity=polarity,
                total_ion_current=float(scan.get("totIonCurrent", 0)) if int_array.size > 0 else float(np.sum(int_array)),
            )
            scans.append(scan_data)

            if ms_level == 1:
                summary.num_ms1_scans += 1
            elif ms_level == 2:
                summary.num_ms2_scans += 1

    summary.scans = scans
    summary.num_scans = len(scans)
    if scans:
        summary.rt_start_s = scans[0].retention_time_s
        summary.rt_end_s = scans[-1].retention_time_s
        summary.polarity = scans[0].polarity

    return summary


def _parse_with_etree(content: bytes, max_scans: int = 0) -> MzXmlSummary:
    """Parse mzXML using xml.etree.ElementTree (fallback)."""
    summary = MzXmlSummary()
    scans: list[ScanData] = []

    # mzXML files use a namespace, so element tags will be like
    # "{http://sashimi.sourceforge.net/...}scan" — we need to strip the namespace
    # Also handle retentionTime format: "PT120S" → 120.0 seconds

    context = ET.iterparse(io.BytesIO(content), events=("end",))

    scan_count = 0
    for event, elem in context:
        # Strip namespace from tag
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag != "scan":
            continue

        if max_scans > 0 and scan_count >= max_scans:
            elem.clear()
            break

        # Extract scan attributes
        rt_str = elem.get("retentionTime", "PT0S")
        rt_s = _parse_retention_time(rt_str)
        ms_level = int(elem.get("msLevel", 1))
        scan_num = int(elem.get("num", scan_count + 1))
        polarity = elem.get("polarity", "")
        tot_ion = elem.get("totIonCurrent")
        base_peak_mz = elem.get("basePeakMz")
        base_peak_intensity = elem.get("basePeakIntensity")

        # Find peaks element (may be namespaced)
        peaks_elem = None
        for child in elem:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag == "peaks":
                peaks_elem = child
                break

        mz_array = np.array([])
        int_array = np.array([])

        if peaks_elem is not None and peaks_elem.text:
            precision = int(peaks_elem.get("precision", 64))
            byte_order = peaks_elem.get("byteOrder", "network")
            try:
                mz_array, int_array = _decode_base64_peaks(
                    peaks_elem.text.strip(), precision, byte_order
                )
            except Exception:
                pass

        scan_data = ScanData(
            scan_number=scan_num,
            retention_time_s=rt_s,
            ms_level=ms_level,
            mz_array=mz_array,
            intensity_array=int_array,
            polarity=polarity,
            base_peak_mz=float(base_peak_mz) if base_peak_mz else None,
            base_peak_intensity=float(base_peak_intensity) if base_peak_intensity else None,
            total_ion_current=float(tot_ion) if tot_ion else (float(np.sum(int_array)) if int_array.size > 0 else None),
        )
        scans.append(scan_data)
        scan_count += 1

        if ms_level == 1:
            summary.num_ms1_scans += 1
        elif ms_level == 2:
            summary.num_ms2_scans += 1

        # Clear element to free memory
        elem.clear()

    summary.scans = scans
    summary.num_scans = len(scans)
    if scans:
        summary.rt_start_s = scans[0].retention_time_s
        summary.rt_end_s = scans[-1].retention_time_s
        summary.polarity = scans[0].polarity

    return summary


def _parse_retention_time(rt_str: str) -> float:
    """Parse retention time from mzXML format.

    mzXML uses ISO 8601 duration format: "PT120S" = 120 seconds, "PT2.5M" = 150 seconds.
    """
    if not rt_str:
        return 0.0
    # Remove "PT" prefix
    rt_str = rt_str.strip()
    if rt_str.startswith("PT"):
        rt_str = rt_str[2:]
    # Try to parse as seconds (most common)
    if rt_str.endswith("S"):
        try:
            return float(rt_str[:-1])
        except ValueError:
            return 0.0
    # Minutes
    if rt_str.endswith("M"):
        try:
            return float(rt_str[:-1]) * 60.0
        except ValueError:
            return 0.0
    # Hours
    if rt_str.endswith("H"):
        try:
            return float(rt_str[:-1]) * 3600.0
        except ValueError:
            return 0.0
    # Plain number (seconds)
    try:
        return float(rt_str)
    except ValueError:
        return 0.0


def extract_xic(
    scans: list[ScanData],
    target_mz: float,
    mz_tolerance_ppm: float = 10.0,
    ms_level: int = 1,
) -> list[XICPoint]:
    """Extract an ion chromatogram for a target m/z.

    Args:
        scans: List of MS scans
        target_mz: Target m/z value
        mz_tolerance_ppm: Mass tolerance in ppm
        ms_level: MS level to extract from (default 1)

    Returns:
        List of XIC points (retention time + intensity)
    """
    mz_tol = target_mz * mz_tolerance_ppm / 1e6
    mz_lo = target_mz - mz_tol
    mz_hi = target_mz + mz_tol

    xic: list[XICPoint] = []
    for scan in scans:
        if scan.ms_level != ms_level:
            continue
        if scan.mz_array.size == 0:
            xic.append(XICPoint(retention_time_s=scan.retention_time_s, intensity=0.0))
            continue

        # Find peaks within the m/z window
        mask = (scan.mz_array >= mz_lo) & (scan.mz_array <= mz_hi)
        if np.any(mask):
            intensity = float(np.sum(scan.intensity_array[mask]))
        else:
            intensity = 0.0

        xic.append(XICPoint(retention_time_s=scan.retention_time_s, intensity=intensity))

    return xic


def detect_peaks(
    xic: list[XICPoint],
    min_intensity: float = 0.0,
    min_snr: float = 3.0,
    max_peaks: int = 5,
) -> list[DetectedPeak]:
    """Detect peaks in an extracted ion chromatogram.

    Uses scipy.signal.find_peaks with prominence filtering, with a fallback
    to simple max + FWHM estimation.

    Args:
        xic: List of XIC points
        min_intensity: Minimum peak intensity
        min_snr: Minimum signal-to-noise ratio
        max_peaks: Maximum number of peaks to return

    Returns:
        List of detected peaks, sorted by intensity (descending)
    """
    if not xic or len(xic) < 3:
        return []

    rts = np.array([p.retention_time_s for p in xic])
    intensities = np.array([p.intensity for p in xic])

    # Filter by minimum intensity
    if np.max(intensities) < min_intensity:
        return []

    peaks: list[DetectedPeak] = []

    # Try scipy first
    try:
        peaks = _detect_peaks_scipy(rts, intensities, min_snr, max_peaks)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback to simple max + FWHM
    if not peaks:
        peaks = _detect_peaks_simple(rts, intensities, min_snr, max_peaks)

    return peaks


def _detect_peaks_scipy(
    rts: np.ndarray,
    intensities: np.ndarray,
    min_snr: float,
    max_peaks: int,
) -> list[DetectedPeak]:
    """Detect peaks using scipy.signal.find_peaks."""
    from scipy.signal import find_peaks, peak_widths

    # Estimate noise level
    noise = np.median(intensities[intensities > 0]) if np.any(intensities > 0) else 1.0
    if noise <= 0:
        noise = 1.0

    # Calculate minimum height based on SNR
    min_height = noise * min_snr

    # Find peaks with prominence filtering
    peak_indices, properties = find_peaks(
        intensities,
        height=min_height,
        prominence=min_height * 0.5,
        distance=3,
    )

    if len(peak_indices) == 0:
        return []

    # Calculate peak widths
    widths, width_heights, left_ips, right_ips = peak_widths(intensities, peak_indices, rel_height=0.5)

    # Sort by intensity (descending)
    sorted_idx = np.argsort(intensities[peak_indices])[::-1]

    peaks: list[DetectedPeak] = []
    for idx in sorted_idx[:max_peaks]:
        peak_idx = peak_indices[idx]
        rt_s = float(rts[peak_idx])
        intensity = float(intensities[peak_idx])
        width_s = float(widths[idx]) * (rts[1] - rts[0]) if len(rts) > 1 else None
        snr = intensity / noise

        peaks.append(DetectedPeak(
            retention_time_s=rt_s,
            retention_time_min=rt_s / 60.0,
            intensity=intensity,
            peak_width_s=width_s,
            signal_to_noise=float(snr),
        ))

    return peaks


def _detect_peaks_simple(
    rts: np.ndarray,
    intensities: np.ndarray,
    min_snr: float,
    max_peaks: int,
) -> list[DetectedPeak]:
    """Detect peaks using simple max + FWHM estimation (fallback)."""
    # Estimate noise as the median of non-zero intensities
    nonzero = intensities[intensities > 0]
    noise = float(np.median(nonzero)) if len(nonzero) > 0 else 1.0
    if noise <= 0:
        noise = 1.0

    min_height = noise * min_snr

    # Find local maxima
    peak_indices: list[int] = []
    for i in range(1, len(intensities) - 1):
        if (
            intensities[i] > intensities[i - 1]
            and intensities[i] >= intensities[i + 1]
            and intensities[i] >= min_height
        ):
            peak_indices.append(i)

    if not peak_indices:
        # If no local maxima found, check if there's a single dominant point
        max_idx = int(np.argmax(intensities))
        if intensities[max_idx] >= min_height:
            peak_indices = [max_idx]
        else:
            return []

    # Sort by intensity (descending)
    peak_indices.sort(key=lambda i: intensities[i], reverse=True)
    peak_indices = peak_indices[:max_peaks]

    peaks: list[DetectedPeak] = []
    for idx in peak_indices:
        rt_s = float(rts[idx])
        intensity = float(intensities[idx])
        snr = intensity / noise

        # Estimate FWHM
        half_max = intensity / 2.0
        # Walk left
        left_idx = idx
        while left_idx > 0 and intensities[left_idx] > half_max:
            left_idx -= 1
        # Walk right
        right_idx = idx
        while right_idx < len(intensities) - 1 and intensities[right_idx] > half_max:
            right_idx += 1

        width_s = float(rts[right_idx] - rts[left_idx]) if right_idx > left_idx else None

        peaks.append(DetectedPeak(
            retention_time_s=rt_s,
            retention_time_min=rt_s / 60.0,
            intensity=intensity,
            peak_width_s=width_s,
            signal_to_noise=float(snr),
        ))

    return peaks


def extract_compound_peaks(
    scans: list[ScanData],
    compounds: list[dict[str, Any]],
    mz_tolerance_ppm: float = 10.0,
    min_snr: float = 3.0,
    max_peaks_per_compound: int = 3,
) -> list[CompoundPeakResult]:
    """Extract XICs and detect peaks for a list of compounds.

    Args:
        scans: List of MS1 scans from parse_mzxml
        compounds: List of compound dicts with 'smiles', 'name', 'id', and 'target_mz'
                   If target_mz is not provided, it will be computed from SMILES using RDKit
        mz_tolerance_ppm: Mass tolerance for XIC extraction
        min_snr: Minimum signal-to-noise ratio for peak detection
        max_peaks_per_compound: Maximum peaks to report per compound

    Returns:
        List of CompoundPeakResult objects
    """
    results: list[CompoundPeakResult] = []

    for compound in compounds:
        result = CompoundPeakResult(
            compound_id=compound.get("id"),
            compound_name=compound.get("name"),
            smiles=compound.get("smiles"),
            target_mz=compound.get("target_mz"),
            mz_tolerance_ppm=mz_tolerance_ppm,
        )

        target_mz = compound.get("target_mz")
        if target_mz is None:
            # Try to compute [M+H]+ from SMILES using RDKit
            smiles = compound.get("smiles")
            if smiles:
                try:
                    target_mz = _compute_mhplus(smiles)
                    result.target_mz = target_mz
                except Exception as exc:
                    result.error = f"Could not compute m/z: {exc}"
                    results.append(result)
                    continue
            else:
                result.error = "No SMILES or target_mz provided"
                results.append(result)
                continue

        if target_mz is None or target_mz <= 0:
            result.error = "Invalid target m/z"
            results.append(result)
            continue

        # Extract XIC
        xic = extract_xic(scans, target_mz, mz_tolerance_ppm)
        result.xic = xic

        # Detect peaks
        peaks = detect_peaks(xic, min_snr=min_snr, max_peaks=max_peaks_per_compound)
        result.peaks = peaks

        if not peaks:
            result.error = "No peaks detected above noise threshold"

        results.append(result)

    return results


def _compute_mhplus(smiles: str) -> float | None:
    """Compute [M+H]+ m/z from SMILES using RDKit."""
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    exact_mass = Descriptors.ExactMolWt(mol)
    # [M+H]+ = exact_mass + mass_of_proton
    return exact_mass + 1.007276

"""LipidMaps REST API client for lipid shorthand resolution.

LipidMaps (https://www.lipidmaps.org) provides a REST API for looking up
lipid structures by name, abbreviation, or molecular formula.

This module resolves lipidomics shorthand notation such as:
  PC(32:1), LPE(14:0), TG(54:3), Cer(d18:1/24:0), CoQ10, etc.

The API endpoint pattern is:
  GET /rest/compound/name/{name}/all/json/
  GET /rest/compound/formula/{formula}/all/json/
"""
from __future__ import annotations

import re
import urllib.parse

import httpx

LIPIDMAPS_BASE = "https://www.lipidmaps.org/rest"

# Timeout and retry settings
_TIMEOUT = 20.0
_MAX_RETRIES = 2

# Lipid class shorthand expansion — maps common abbreviations to full names
# that LipidMaps can search for.
LIPID_ABBREVIATIONS: dict[str, str] = {
    # Glycerophospholipids
    "PC": "phosphatidylcholine",
    "PE": "phosphatidylethanolamine",
    "PS": "phosphatidylserine",
    "PI": "phosphatidylinositol",
    "PG": "phosphatidylglycerol",
    "PA": "phosphatidic acid",
    "LPC": "lysophosphatidylcholine",
    "LPE": "lysophosphatidylethanolamine",
    "LPS": "lysophosphatidylserine",
    "LPI": "lysophosphatidylinositol",
    "LPA": "lysophosphatidic acid",
    # Glycerolipids
    "TG": "triacylglycerol",
    "DG": "diacylglycerol",
    "MG": "monoacylglycerol",
    # Sphingolipids
    "Cer": "ceramide",
    "SM": "sphingomyelin",
    "Sph": "sphingosine",
    "So": "sphingosine",
    "Sa": "sphinganine",
    "dhCer": "dihydroceramide",
    "HexCer": "hexosylceramide",
    "LacCer": "lactosylceramide",
    "GlcCer": "glucosylceramide",
    "GalCer": "galactosylceramide",
    # Sterol lipids
    "CE": "cholesteryl ester",
    "FC": "free cholesterol",
    # Prenol lipids
    "CoQ": "coenzyme Q",
    "CoQ9": "coenzyme Q9",
    "CoQ10": "coenzyme Q10",
    # Fatty acids
    "FA": "fatty acid",
    "HFA": "hydroxy fatty acid",
    # Others
    "Phytosphingosine": "phytosphingosine",
}

# Regex to detect lipid shorthand notation
# Matches patterns like: PC(32:1), LPE(14:0), TG(42:1), Cer(d18:1/24:0), CoQ10
_LIPID_PATTERN = re.compile(
    r"^[A-Z][A-Za-z]{0,8}"  # class abbreviation (1-9 chars, starts uppercase)
    r"(?:_?(?:Na|NH4|K|Li|H))?"  # optional adduct annotation
    r"\s*\("  # opening paren
    r"[a-z]?\d+:\d+"  # chain notation: e.g. 32:1, d18:1
    r"(?:/\d+:\d+)*"  # additional chains
    r"(?:/[a-z]?\d+:\d+)*"
    r"\)"  # closing paren
    r"$"
)

# Simpler pattern for things like CoQ10, Phytosphingosine(16:0)
_LIPID_NAME_PATTERN = re.compile(
    r"^(?:CoQ\d+|Phytosphingosine|Sphingosine|Sphinganine|Ceramide)"
    r"(?:\s*\([a-z]?\d+:\d+(?:/\d+:\d+)*\))?$",
    re.IGNORECASE,
)


class LipidMapsError(RuntimeError):
    """Raised when LipidMaps API requests fail."""


def looks_like_lipid(name: str) -> bool:
    """Heuristic: does this name look like lipid shorthand?

    Returns True for patterns like:
      PC(32:1), LPE(14:0), TG_Na(42:1), Cer(d18:1/24:0), CoQ10
    """
    name = name.strip()
    if not name:
        return False

    # Check shorthand pattern
    if _LIPID_PATTERN.match(name):
        return True

    # Check known lipid names
    if _LIPID_NAME_PATTERN.match(name):
        return True

    # Check if the prefix is a known lipid abbreviation
    # e.g. "DG_Na(40:3)" → prefix "DG" is known
    prefix_match = re.match(r"^([A-Za-z]+?)(?:_?(?:Na|NH4|K|Li|H))?\(", name)
    if prefix_match:
        prefix = prefix_match.group(1)
        if prefix in LIPID_ABBREVIATIONS:
            return True

    return False


def _expand_lipid_name(name: str) -> str:
    """Try to expand a lipid shorthand to a more searchable name.

    For example: PC(32:1) → phosphatidylcholine 32:1
    """
    name = name.strip()

    # Extract the class prefix
    prefix_match = re.match(r"^([A-Za-z]+?)(?:_?(?:Na|NH4|K|Li|H))?\(", name)
    if prefix_match:
        prefix = prefix_match.group(1)
        full_name = LIPID_ABBREVIATIONS.get(prefix)
        if full_name:
            # Extract chain info
            chain_match = re.search(r"\(([^)]+)\)", name)
            if chain_match:
                chains = chain_match.group(1)
                # Remove adduct notation from chain if present
                return f"{full_name} {chains}"
            return full_name

    # Check if the whole name (minus chains) is a known lipid name
    for abbrev, full in LIPID_ABBREVIATIONS.items():
        if name.lower().startswith(abbrev.lower()):
            return full

    return name


async def search_by_name(name: str) -> list[dict]:
    """Search LipidMaps by common name or shorthand.

    Returns a list of dicts with keys:
      name, smiles, inchikey, formula, mw, lipid_class, source
    """
    name = name.strip()
    if not name:
        return []

    # Try the original name first, then the expanded name
    queries = [name]
    expanded = _expand_lipid_name(name)
    if expanded != name:
        queries.append(expanded)

    for query in queries:
        results = await _search_name(query)
        if results:
            return results

    return []


async def search_by_formula(formula: str) -> list[dict]:
    """Search LipidMaps by molecular formula.

    Returns a list of dicts with keys:
      name, smiles, inchikey, formula, mw, lipid_class, source
    """
    formula = formula.strip()
    if not formula:
        return []

    return await _search_formula(formula)


async def _search_name(name: str) -> list[dict]:
    """Internal: query LipidMaps REST API by name."""
    encoded = urllib.parse.quote(name, safe="")
    url = f"{LIPIDMAPS_BASE}/compound/name/{encoded}/all/json/"

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
            if resp.status_code == 404:
                return []
            if resp.status_code != 200:
                if attempt < _MAX_RETRIES:
                    continue
                return []
            data = resp.json()
            return _parse_lipidmaps_response(data)
        except (httpx.HTTPError, Exception):
            if attempt < _MAX_RETRIES:
                continue
            return []
    return []


async def _search_formula(formula: str) -> list[dict]:
    """Internal: query LipidMaps REST API by formula."""
    encoded = urllib.parse.quote(formula, safe="")
    url = f"{LIPIDMAPS_BASE}/compound/formula/{encoded}/all/json/"

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
            if resp.status_code == 404:
                return []
            if resp.status_code != 200:
                if attempt < _MAX_RETRIES:
                    continue
                return []
            data = resp.json()
            return _parse_lipidmaps_response(data)
        except (httpx.HTTPError, Exception):
            if attempt < _MAX_RETRIES:
                continue
            return []
    return []


def _parse_lipidmaps_response(data: dict | list) -> list[dict]:
    """Parse LipidMaps JSON response into our standard format.

    The API can return either a single object or a list.
    """
    results: list[dict] = []

    # LipidMaps can return a dict with a list under various keys,
    # or a bare list, or a single compound dict
    items: list[dict] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Common response structures
        for key in ("LM_compounds", "compounds", "data", "results"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        if not items and ("lm_id" in data or "LM_ID" in data or "smiles" in data):
            # Single compound response
            items = [data]

    for item in items:
        if not isinstance(item, dict):
            continue
        smiles = item.get("smiles") or item.get("SMILES") or ""
        if not smiles:
            continue
        results.append({
            "name": item.get("common_name") or item.get("name") or item.get("abbreviation") or "",
            "smiles": smiles,
            "inchikey": item.get("inchikey") or item.get("InChIKey") or "",
            "formula": item.get("formula") or item.get("molecular_formula") or "",
            "mw": float(item.get("mass") or item.get("molecular_weight") or 0.0),
            "lipid_class": item.get("category") or item.get("class") or "",
            "source": "lipidmaps",
            "provider_id": item.get("lm_id") or item.get("LM_ID") or "",
        })

    return results

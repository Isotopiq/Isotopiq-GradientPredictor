"""PubChem REST lookup (name / CAS -> SMILES, InChIKey)."""
from __future__ import annotations

import httpx

from app.config import settings


class PubChemError(RuntimeError):
    pass


async def lookup_by_name(name: str) -> dict[str, str]:
    """Look up a compound by common name. Returns dict with smiles, inchikey, mw, formula."""
    base = settings.pubchem_base_url.rstrip("/")
    url = f"{base}/compound/name/{_quote(name)}/property/CanonicalSMILES,ConnectivitySMILES,InChIKey,MolecularFormula,MolecularWeight/JSON"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise PubChemError(f"PubChem request failed: {exc}") from exc
    if resp.status_code == 404:
        raise PubChemError(f"Compound '{name}' not found in PubChem")
    if resp.status_code != 200:
        raise PubChemError(f"PubChem returned {resp.status_code}")
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    if not props:
        raise PubChemError(f"No properties returned for '{name}'")
    p = props[0]
    return {
        "smiles": p.get("CanonicalSMILES") or p.get("ConnectivitySMILES", ""),
        "inchikey": p.get("InChIKey", ""),
        "formula": p.get("MolecularFormula", ""),
        "mw": p.get("MolecularWeight", ""),
    }


async def lookup_by_cas(cas: str) -> dict[str, str]:
    """Look up a compound by CAS Registry Number via PubChem xref."""
    base = settings.pubchem_base_url.rstrip("/")
    # PubChem supports CAS via synonym search
    url = f"{base}/compound/synonyms/{_quote(cas)}/property/CanonicalSMILES,ConnectivitySMILES,InChIKey,MolecularFormula,MolecularWeight/JSON"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise PubChemError(f"PubChem request failed: {exc}") from exc
    if resp.status_code == 404:
        raise PubChemError(f"CAS '{cas}' not found in PubChem")
    if resp.status_code != 200:
        raise PubChemError(f"PubChem returned {resp.status_code}")
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    if not props:
        raise PubChemError(f"No properties returned for CAS '{cas}'")
    p = props[0]
    return {
        "smiles": p.get("CanonicalSMILES") or p.get("ConnectivitySMILES", ""),
        "inchikey": p.get("InChIKey", ""),
        "formula": p.get("MolecularFormula", ""),
        "mw": p.get("MolecularWeight", ""),
    }


def _quote(s: str) -> str:
    import urllib.parse

    return urllib.parse.quote(s.strip(), safe="")

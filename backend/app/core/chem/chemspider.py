"""ChemSpider search (Royal Society of Chemistry).

Uses the ChemSpider SimpleSearch API via the proxy JSON endpoint.
Note: ChemSpider requires an API key. If no key is configured, this
module gracefully returns empty results so the UI can fall back to PubChem.
"""
from __future__ import annotations

import os
import httpx


class ChemSpiderError(RuntimeError):
    pass


def get_api_key() -> str | None:
    return os.getenv("CHEMSPIDER_API_KEY")


async def search_by_name(name: str, limit: int = 10) -> list[dict[str, str]]:
    """Search ChemSpider by compound name. Returns list of hits.

    Each hit: { name, smiles, inchikey, formula, mw, source: 'chemspider' }
    Returns empty list if no API key is configured.
    """
    api_key = get_api_key()
    if not api_key:
        return []

    base = "https://www.chemspider.com/api"
    headers = {"apikey": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Search by name
        try:
            resp = await client.post(
                f"{base}/search/name",
                json={"name": name, "count": limit},
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise ChemSpiderError(f"ChemSpider request failed: {exc}") from exc

        if resp.status_code == 403:
            # Invalid API key — return empty
            return []
        if resp.status_code != 200:
            return []

        data = resp.json()
        results: list[dict[str, str]] = []
        for item in data.get("results", [])[:limit]:
            csid = item.get("csid", "")
            # Fetch properties for each hit
            try:
                props_resp = await client.get(
                    f"{base}/records/{csid}/properties",
                    headers=headers,
                )
                if props_resp.status_code == 200:
                    props = props_resp.json()
                    results.append({
                        "name": props.get("common_name", name),
                        "smiles": props.get("smiles", ""),
                        "inchikey": props.get("inchikey", ""),
                        "formula": props.get("formula", ""),
                        "mw": str(props.get("average_mass", props.get("molecular_weight", ""))),
                        "source": "chemspider",
                    })
            except (httpx.HTTPError, KeyError):
                continue

        return results


async def search_compounds_multi_source(name: str, limit: int = 10) -> list[dict[str, str]]:
    """Search both PubChem and ChemSpider, merge results.

    Returns deduplicated list by InChIKey.
    """
    from app.core.chem.pubchem import lookup_by_name
    from app.core.chem import pubchem as pc

    results: list[dict[str, str]] = []

    # PubChem: search by name (returns multiple via the search endpoint)
    pubchem_results = await _pubchem_search_multi(name, limit)
    results.extend(pubchem_results)

    # ChemSpider (if API key configured)
    try:
        cs_results = await search_by_name(name, limit)
        results.extend(cs_results)
    except ChemSpiderError:
        pass

    # Deduplicate by InChIKey
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for r in results:
        key = r.get("inchikey", "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(r)

    return deduped[:limit]


async def _pubchem_search_multi(name: str, limit: int) -> list[dict[str, str]]:
    """Search PubChem for multiple matches by name."""
    import urllib.parse
    from app.config import settings

    base = settings.pubchem_base_url.rstrip("/")
    quoted = urllib.parse.quote(name.strip(), safe="")
    # Use the name search with multiple results
    url = f"{base}/compound/name/{quoted}/property/CanonicalSMILES,InChIKey,MolecularFormula,MolecularWeight/JSON"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError:
            return []

    if resp.status_code != 200:
        return []

    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    results: list[dict[str, str]] = []
    for p in props[:limit]:
        results.append({
            "name": name,
            "smiles": p.get("CanonicalSMILES", ""),
            "inchikey": p.get("InChIKey", ""),
            "formula": p.get("MolecularFormula", ""),
            "mw": p.get("MolecularWeight", ""),
            "source": "pubchem",
        })
    return results

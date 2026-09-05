"""Import resolver service: async batch resolution of CSV compound entries.

Resolves compound names/formulas/SMILES via PubChem and optionally LipidMaps,
with rate-limited concurrent lookups and progress tracking.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.chem.descriptors import compute_descriptors
from app.core.chem.lipidmaps import (
    looks_like_lipid,
)
from app.core.chem.lipidmaps import (
    search_by_formula as lipidmaps_search_formula,
)
from app.core.chem.lipidmaps import (
    search_by_name as lipidmaps_search_name,
)
from app.core.chem.parser import ChemParseError, parse_mol
from app.core.chem.pubchem import PubChemError, lookup_by_cas, lookup_by_name

logger = logging.getLogger(__name__)

# Rate limiting: PubChem allows ~5 requests per second
_PUBCHEM_CONCURRENCY = 5
_PUBCHEM_DELAY_S = 0.25  # 250ms between batches
_LIPIDMAPS_CONCURRENCY = 3

# Per-request timeout
_TIMEOUT_S = 20.0


@dataclass
class _JobState:
    """In-memory state for a resolution job."""

    job_id: str
    status: str = "pending"  # pending | running | complete | failed
    total: int = 0
    processed: int = 0
    resolved: int = 0
    unresolved: int = 0
    ambiguous: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    use_lipidmaps: bool = False


# Global job registry (in-memory, transient)
_jobs: dict[str, _JobState] = {}
_jobs_lock = asyncio.Lock()


async def start_resolution_job(
    entries: list[dict[str, Any]],
    use_lipidmaps: bool = False,
) -> str:
    """Start a background resolution job. Returns the job_id."""
    job_id = str(uuid.uuid4())
    state = _JobState(
        job_id=job_id,
        total=len(entries),
        use_lipidmaps=use_lipidmaps,
    )
    async with _jobs_lock:
        _jobs[job_id] = state

    # Launch background task
    asyncio.create_task(_run_resolution(job_id, entries, use_lipidmaps))
    return job_id


async def get_resolution_job(job_id: str) -> _JobState | None:
    """Get the current state of a resolution job."""
    async with _jobs_lock:
        return _jobs.get(job_id)


async def _run_resolution(
    job_id: str,
    entries: list[dict[str, Any]],
    use_lipidmaps: bool,
) -> None:
    """Run the resolution job in the background."""
    async with _jobs_lock:
        state = _jobs.get(job_id)
        if state is None:
            return
        state.status = "running"

    try:
        # Use a semaphore to limit concurrent PubChem requests
        sem = asyncio.Semaphore(_PUBCHEM_CONCURRENCY)

        async def resolve_one(idx: int, entry: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                result = await _resolve_entry(entry, use_lipidmaps)
                # Update progress
                async with _jobs_lock:
                    s = _jobs.get(job_id)
                    if s is not None:
                        s.processed += 1
                        if result["status"] == "resolved":
                            s.resolved += 1
                        elif result["status"] == "ambiguous":
                            s.ambiguous += 1
                        else:
                            s.unresolved += 1
                        s.results.append(result)
                        s.progress_pct = (s.processed / s.total) * 100.0 if s.total > 0 else 0.0
                return result

        # Process entries with limited concurrency
        # Process in small batches to allow progress updates
        batch_size = _PUBCHEM_CONCURRENCY
        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            tasks = [resolve_one(i + j, e) for j, e in enumerate(batch)]
            await asyncio.gather(*tasks, return_exceptions=True)
            # Small delay between batches to respect rate limits
            await asyncio.sleep(_PUBCHEM_DELAY_S)

        async with _jobs_lock:
            s = _jobs.get(job_id)
            if s is not None:
                s.status = "complete"
                s.progress_pct = 100.0

    except Exception as exc:
        logger.exception("Resolution job %s failed", job_id)
        async with _jobs_lock:
            s = _jobs.get(job_id)
            if s is not None:
                s.status = "failed"
                s.error = str(exc)


async def _resolve_entry(
    entry: dict[str, Any],
    use_lipidmaps: bool,
) -> dict[str, Any]:
    """Resolve a single CSV entry to a compound structure.

    Strategy:
    1. If SMILES already in entry → parse with RDKit → resolved
    2. If InChIKey in entry → PubChem lookup by InChIKey
    3. If CAS in entry → PubChem lookup by CAS
    4. PubChem name lookup
    5. If use_lipidmaps and name looks like lipid → LipidMaps
    6. If formula available → LipidMaps or PubChem formula search → ambiguous
    7. All fail → unresolved
    """
    row_index = entry.get("row_index", 0)
    name = (entry.get("name") or "").strip()
    formula = (entry.get("formula") or "").strip() or None
    rt = entry.get("rt")
    charge = entry.get("charge")
    cas = (entry.get("cas") or "").strip() or None
    smiles_in = (entry.get("smiles") or "").strip() or None
    inchikey_in = (entry.get("inchikey") or "").strip() or None

    base_result: dict[str, Any] = {
        "row_index": row_index,
        "name": name,
        "formula": formula,
        "rt": rt,
        "charge": charge,
        "cas": cas,
        "smiles": None,
        "inchikey": None,
        "mw": None,
        "logp": None,
        "tpsa": None,
        "source": "unresolved",
        "status": "unresolved",
        "candidates": [],
        "warnings": [],
    }

    # 1. SMILES already provided
    if smiles_in:
        try:
            parsed = parse_mol(smiles_in)
            desc = compute_descriptors(parsed.mol)
            base_result.update({
                "smiles": parsed.smiles,
                "inchikey": parsed.inchikey,
                "mw": desc.mw,
                "logp": desc.logp,
                "tpsa": desc.tpsa,
                "source": "manual",
                "status": "resolved",
            })
            return base_result
        except ChemParseError:
            base_result["warnings"].append(f"Invalid SMILES: {smiles_in}")

    # 2. InChIKey provided → PubChem lookup
    if inchikey_in:
        try:
            result = await _pubchem_lookup_by_inchikey(inchikey_in)
            if result:
                _apply_pubchem_result(base_result, result)
                return base_result
        except Exception:
            pass

    # 3. CAS provided → PubChem lookup
    if cas:
        try:
            result = await lookup_by_cas(cas)
            _apply_pubchem_result(base_result, result)
            return base_result
        except PubChemError:
            base_result["warnings"].append(f"CAS '{cas}' not found in PubChem")
        except Exception:
            pass

    # 4. PubChem name lookup
    if name:
        try:
            result = await lookup_by_name(name)
            _apply_pubchem_result(base_result, result)
            return base_result
        except PubChemError:
            pass  # try next strategy
        except Exception:
            pass

    # 5. LipidMaps lookup
    if use_lipidmaps and name and looks_like_lipid(name):
        try:
            candidates = await lipidmaps_search_name(name)
            if candidates:
                if len(candidates) == 1:
                    _apply_lipidmaps_result(base_result, candidates[0])
                    return base_result
                else:
                    # Multiple candidates — mark as ambiguous
                    base_result["status"] = "ambiguous"
                    base_result["source"] = "lipidmaps"
                    base_result["candidates"] = candidates[:10]  # limit
                    # Use first candidate as default
                    _apply_lipidmaps_result(base_result, candidates[0])
                    base_result["warnings"].append(
                        f"Multiple LipidMaps matches ({len(candidates)}) — select the correct one"
                    )
                    return base_result
        except Exception:
            pass

        # Try LipidMaps by formula if name search failed
        if formula and base_result["status"] == "unresolved":
            try:
                candidates = await lipidmaps_search_formula(formula)
                if candidates:
                    if len(candidates) == 1:
                        _apply_lipidmaps_result(base_result, candidates[0])
                        return base_result
                    else:
                        base_result["status"] = "ambiguous"
                        base_result["source"] = "lipidmaps"
                        base_result["candidates"] = candidates[:10]
                        _apply_lipidmaps_result(base_result, candidates[0])
                        base_result["warnings"].append(
                            f"Multiple LipidMaps formula matches ({len(candidates)})"
                        )
                        return base_result
            except Exception:
                pass

    # 6. Formula-only search via PubChem (always, not just lipids)
    if formula and base_result["status"] == "unresolved":
        try:
            candidates = await _pubchem_search_by_formula(formula)
            if candidates:
                if len(candidates) == 1:
                    _apply_pubchem_result(base_result, candidates[0])
                    return base_result
                else:
                    base_result["status"] = "ambiguous"
                    base_result["source"] = "pubchem"
                    base_result["candidates"] = [
                        {
                            "smiles": c.get("smiles", ""),
                            "inchikey": c.get("inchikey", ""),
                            "formula": c.get("formula", ""),
                            "mw": float(c.get("mw", 0)),
                            "name": c.get("name", ""),
                            "source": "pubchem",
                            "provider_id": str(c.get("cid", "")),
                        }
                        for c in candidates[:10]
                    ]
                    _apply_pubchem_result(base_result, candidates[0])
                    base_result["warnings"].append(
                        f"Multiple PubChem formula matches ({len(candidates)})"
                    )
                    return base_result
        except Exception:
            pass

    # 7. All strategies failed
    if name:
        base_result["warnings"].append(f"Could not resolve '{name}' via any source")
    return base_result


def _apply_pubchem_result(result: dict[str, Any], pubchem: dict[str, str]) -> None:
    """Apply a PubChem lookup result to the result dict."""
    smiles = pubchem.get("smiles", "")
    if not smiles:
        return
    try:
        parsed = parse_mol(smiles)
        desc = compute_descriptors(parsed.mol)
        result.update({
            "smiles": parsed.smiles,
            "inchikey": pubchem.get("inchikey") or parsed.inchikey,
            "mw": desc.mw,
            "logp": desc.logp,
            "tpsa": desc.tpsa,
            "source": "pubchem",
            "status": "resolved",
        })
        if pubchem.get("formula"):
            result["formula"] = pubchem["formula"]
    except ChemParseError:
        result["warnings"].append(f"Failed to parse PubChem SMILES: {smiles}")


def _apply_lipidmaps_result(result: dict[str, Any], lm: dict[str, Any]) -> None:
    """Apply a LipidMaps lookup result to the result dict."""
    smiles = lm.get("smiles", "")
    if not smiles:
        return
    try:
        parsed = parse_mol(smiles)
        desc = compute_descriptors(parsed.mol)
        result.update({
            "smiles": parsed.smiles,
            "inchikey": lm.get("inchikey") or parsed.inchikey,
            "mw": desc.mw if not lm.get("mw") else float(lm["mw"]),
            "logp": desc.logp,
            "tpsa": desc.tpsa,
            "source": "lipidmaps",
            "status": "resolved",
        })
        if lm.get("formula"):
            result["formula"] = lm["formula"]
        if lm.get("name"):
            result["resolved_name"] = lm["name"]
    except ChemParseError:
        result["warnings"].append(f"Failed to parse LipidMaps SMILES: {smiles}")


async def _pubchem_lookup_by_inchikey(inchikey: str) -> dict[str, str] | None:
    """Look up a compound in PubChem by InChIKey."""
    import urllib.parse

    from app.config import settings

    base = settings.pubchem_base_url.rstrip("/")
    encoded = urllib.parse.quote(inchikey.strip(), safe="")
    url = (
        f"{base}/compound/inchikey/{encoded}"
        "/property/CanonicalSMILES,InChIKey,MolecularFormula,MolecularWeight/JSON"
    )
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if not props:
            return None
        p = props[0]
        return {
            "smiles": p.get("CanonicalSMILES", ""),
            "inchikey": p.get("InChIKey", ""),
            "formula": p.get("MolecularFormula", ""),
            "mw": p.get("MolecularWeight", ""),
        }
    except Exception:
        return None


async def _pubchem_search_by_formula(formula: str) -> list[dict[str, Any]]:
    """Search PubChem by molecular formula. Returns multiple candidates."""
    import urllib.parse

    from app.config import settings

    base = settings.pubchem_base_url.rstrip("/")
    encoded = urllib.parse.quote(formula.strip(), safe="")
    url = (
        f"{base}/compound/formula/{encoded}"
        "/property/CanonicalSMILES,InChIKey,MolecularFormula,MolecularWeight/JSON"
        "?MaxRecords=10"
    )
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        results: list[dict[str, Any]] = []
        for p in props:
            results.append({
                "smiles": p.get("CanonicalSMILES", ""),
                "inchikey": p.get("InChIKey", ""),
                "formula": p.get("MolecularFormula", ""),
                "mw": p.get("MolecularWeight", ""),
                "cid": p.get("CID", ""),
                "name": "",
            })
        return results
    except Exception:
        return []

"""Compound routes."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.pubchem import PubChemError, lookup_by_cas, lookup_by_name
from app.core.chem.chemspider import search_compounds_multi_source, ChemSpiderError
from app.core.chem.logd import fraction_ionized, logd_at_ph
from app.core.chem.parser import ChemParseError, parse_mol
from app.core.chem.pka import estimate_pka_sites
from app.core.chem.descriptors import compute_descriptors
from app.deps import CurrentUser, DBSession
from app.schemas.compound import CompoundBatchCreate, CompoundCreate, CompoundOut, PubChemLookupOut
from app.services import compound_service

router = APIRouter(prefix="/compounds", tags=["compounds"])


@router.post("", response_model=CompoundOut, status_code=status.HTTP_201_CREATED)
async def create_compound(
    data: CompoundCreate,
    db: DBSession,
    current: CurrentUser,
) -> CompoundOut:
    try:
        compound = await compound_service.create_compound(db, current.id, data)
    except compound_service.CompoundServiceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return CompoundOut.model_validate(compound)


@router.get("", response_model=list[CompoundOut])
async def list_compounds(
    db: DBSession,
    current: CurrentUser,
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[CompoundOut]:
    items, _ = await compound_service.list_compounds(db, current.id, search, limit, offset)
    return [CompoundOut.model_validate(c) for c in items]


# --- Static routes (MUST be before /{compound_id}) ---


@router.get("/pubchem/lookup", response_model=PubChemLookupOut)
async def pubchem_lookup(
    name: str | None = Query(None),
    cas: str | None = Query(None),
) -> PubChemLookupOut:
    if not name and not cas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide name or cas query param")
    try:
        if cas:
            result = await lookup_by_cas(cas)
            label = cas
        else:
            result = await lookup_by_name(name or "")
            label = name or ""
    except PubChemError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return PubChemLookupOut(
        name=label,
        smiles=result["smiles"],
        inchikey=result["inchikey"],
        formula=result["formula"],
        mw=result["mw"],
    )


@router.get("/search/multi")
async def search_compounds_multi(
    name: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict[str, str]]:
    """Search PubChem + ChemSpider by compound name. Returns a merged, deduplicated list."""
    try:
        results = await search_compounds_multi_source(name, limit)
    except (PubChemError, ChemSpiderError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return results


@router.get("/depiction", response_class=HTMLResponse)
async def depict_molecule(
    smiles: str = Query(...),
    width: int = Query(400, ge=50, le=2000),
    height: int = Query(300, ge=50, le=2000),
) -> str:
    """Render a 2D SVG depiction of a molecule from SMILES."""
    try:
        from app.core.chem.depiction import render_2d_svg
        return render_2d_svg(smiles, width, height)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, f"Depiction not available: {exc}") from exc


@router.post("/batch", response_model=list[CompoundOut], status_code=status.HTTP_201_CREATED)
async def batch_create_compounds(
    data: CompoundBatchCreate,
    db: DBSession,
    current: CurrentUser,
) -> list[CompoundOut]:
    """Create multiple compounds at once."""
    results: list[CompoundOut] = []
    for item in data.compounds:
        try:
            compound = await compound_service.create_compound(db, current.id, item)
            results.append(CompoundOut.model_validate(compound))
        except compound_service.CompoundServiceError:
            continue  # Skip invalid entries
    return results


@router.get("/pka-plot")
async def pka_plot(smiles: str = Query(...)) -> dict[str, Any]:
    """Return pKa sites and ionization fractions across pH range for plotting."""
    try:
        parsed = parse_mol(smiles)
    except ChemParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    mol = parsed.mol
    sites = estimate_pka_sites(mol)
    descriptors = compute_descriptors(mol)
    logp = descriptors.logp

    # Compute fractions across pH 0-14
    ph_range = [round(0.1 * i, 1) for i in range(141)]
    fractions: list[dict[str, float]] = []
    for ph in ph_range:
        total_ionized = 0.0
        for site in sites:
            f = fraction_ionized(site, ph)
            total_ionized = max(total_ionized, f)
        ld = logd_at_ph(mol, ph, logp)
        fractions.append({
            "ph": ph,
            "fraction_ionized": round(total_ionized, 4),
            "logd": round(ld, 4),
        })

    # Recommended pH: avoid ±1.5 of any pKa
    pka_values = sorted({round(s.pka, 2) for s in sites})
    recommended_ph = 2.7  # default
    if pka_values:
        # Find pH farthest from all pKa values in range 2-10
        best_ph = 2.7
        best_dist = 0.0
        for candidate in [round(0.1 * i, 1) for i in range(20, 101)]:
            min_dist = min(abs(candidate - p) for p in pka_values)
            if min_dist > best_dist:
                best_dist = min_dist
                best_ph = candidate
        if best_dist >= 1.5:
            recommended_ph = best_ph

    return {
        "smiles": smiles,
        "sites": [
            {
                "pka": s.pka,
                "acid_base": s.acid_base,
                "atom_idx": s.atom_idx,
            }
            for s in sites
        ],
        "pka_values": pka_values,
        "logp": logp,
        "fractions": fractions,
        "recommended_ph": recommended_ph,
    }


# --- Parameterized routes (MUST be last) ---


@router.get("/{compound_id}", response_model=CompoundOut)
async def get_compound(compound_id: uuid.UUID, db: DBSession, current: CurrentUser) -> CompoundOut:
    compound = await compound_service.get_compound(db, compound_id)
    if compound is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound not found")
    if compound.owner_id is not None and compound.owner_id != current.id and not compound.is_shared:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return CompoundOut.model_validate(compound)


@router.delete("/{compound_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compound(compound_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    compound = await compound_service.get_compound(db, compound_id)
    if compound is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound not found")
    if compound.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    await compound_service.delete_compound(db, compound_id)

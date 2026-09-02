"""Compound routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.pubchem import PubChemError, lookup_by_cas, lookup_by_name
from app.core.chem.chemspider import search_compounds_multi_source, ChemSpiderError
from app.deps import CurrentUser, DBSession
from app.schemas.compound import CompoundCreate, CompoundOut, PubChemLookupOut
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

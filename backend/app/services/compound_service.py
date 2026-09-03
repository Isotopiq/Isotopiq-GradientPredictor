"""Compound service: parse -> descriptors -> persist."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.descriptors import compute_descriptors
from app.core.chem.parser import ChemParseError, parse_mol
from app.core.chem.pka import estimate_pka_values
from app.core.chem.pubchem import PubChemError, lookup_by_cas, lookup_by_name
from app.models.compound import Compound
from app.schemas.compound import CompoundCreate, CompoundUpdate


class CompoundServiceError(ValueError):
    pass


async def create_compound(
    db: AsyncSession, owner_id: uuid.UUID | None, data: CompoundCreate
) -> Compound:
    """Create a compound from SMILES/InChI/molfile, optionally via PubChem lookup."""
    smiles = data.smiles
    inchi = data.inchi
    molfile = data.molfile
    name = data.name
    cas = data.cas

    if data.lookup and (name or cas):
        try:
            if cas:
                result = await lookup_by_cas(cas)
            else:
                result = await lookup_by_name(name or "")
        except PubChemError as exc:
            raise CompoundServiceError(str(exc)) from exc
        smiles = result["smiles"] or smiles
        # We have inchikey but not inchi; keep smiles as primary
        inchikey = result.get("inchikey")
    else:
        inchikey = None

    raw = smiles or inchi or molfile
    if not raw:
        raise CompoundServiceError("Provide smiles, inchi, molfile, or a name/cas with lookup=True")

    try:
        parsed = parse_mol(raw)
    except ChemParseError as exc:
        raise CompoundServiceError(str(exc)) from exc

    descriptors = compute_descriptors(parsed.mol)
    pka_values = estimate_pka_values(parsed.mol)

    compound = Compound(
        owner_id=owner_id,
        name=name,
        smiles=parsed.smiles,
        inchi=parsed.inchi,
        inchikey=inchikey or parsed.inchikey,
        molfile=parsed.molfile,
        cas=cas,
        mw=descriptors.mw,
        logp=descriptors.logp,
        pka_values=pka_values,  # type: ignore[arg-type]
        tpsa=descriptors.tpsa,
        hbd=descriptors.hbd,
        hba=descriptors.hba,
        rotatable_bonds=descriptors.rotatable_bonds,
        aromatic_rings=descriptors.aromatic_rings,
        source=data.source,
    )
    db.add(compound)
    await db.commit()
    await db.refresh(compound)
    return compound


async def get_compound(db: AsyncSession, compound_id: uuid.UUID) -> Compound | None:
    return await db.get(Compound, compound_id)


async def list_compounds(
    db: AsyncSession,
    owner_id: uuid.UUID | None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Compound], int]:
    stmt = select(Compound).order_by(Compound.created_at.desc())
    if owner_id is not None:
        # Show owned + shared
        stmt = stmt.where((Compound.owner_id == owner_id) | (Compound.is_shared.is_(True)))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (Compound.name.ilike(like))
            | (Compound.smiles.ilike(like))
            | (Compound.inchikey.ilike(like))
            | (Compound.cas.ilike(like))
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    # Total count (approximate; fine for small datasets)
    count_stmt = select(Compound)
    if owner_id is not None:
        count_stmt = count_stmt.where(
            (Compound.owner_id == owner_id) | (Compound.is_shared.is_(True))
        )
    total_result = await db.execute(count_stmt)
    total = len(list(total_result.scalars().all()))
    return items, total


async def delete_compound(db: AsyncSession, compound_id: uuid.UUID) -> bool:
    compound = await db.get(Compound, compound_id)
    if compound is None:
        return False
    await db.delete(compound)
    await db.commit()
    return True


async def update_compound(
    db: AsyncSession, compound_id: uuid.UUID, data: CompoundUpdate
) -> Compound | None:
    """Partially update a compound's editable fields (name, cas, is_shared)."""
    compound = await db.get(Compound, compound_id)
    if compound is None:
        return None
    if data.name is not None:
        compound.name = data.name.strip() or None
    if data.cas is not None:
        compound.cas = data.cas.strip() or None
    if data.is_shared is not None:
        compound.is_shared = data.is_shared
    await db.commit()
    await db.refresh(compound)
    return compound


def compute_descriptor_dict(compound: Compound) -> dict[str, Any]:
    return {
        "mw": compound.mw,
        "logp": compound.logp,
        "tpsa": compound.tpsa,
        "hbd": compound.hbd,
        "hba": compound.hba,
        "rotatable_bonds": compound.rotatable_bonds,
        "aromatic_rings": compound.aromatic_rings,
        "pka_values": compound.pka_values or [],
    }

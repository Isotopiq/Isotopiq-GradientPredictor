"""Compound schemas."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompoundCreate(BaseModel):
    """Input to create a compound. Exactly one of smiles/inchi/molfile should be provided,
    OR name for PubChem lookup (set lookup=True)."""

    smiles: str | None = None
    inchi: str | None = None
    molfile: str | None = None
    name: str | None = None
    cas: str | None = None
    lookup: bool = False  # if True and name/cas given, resolve via PubChem
    source: str = "manual"


class CompoundOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None
    is_shared: bool
    name: str | None = None
    smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    molfile: str | None = None
    cas: str | None = None
    mw: float | None = None
    logp: float | None = None
    logd_at_ph: float | None = None
    pka_values: list[Any] | None = None
    tpsa: float | None = None
    hbd: int | None = None
    hba: int | None = None
    rotatable_bonds: int | None = None
    aromatic_rings: int | None = None
    source: str


class DescriptorOut(BaseModel):
    mw: float
    logp: float
    tpsa: float
    hbd: int
    hba: int
    rotatable_bonds: int
    aromatic_rings: int
    num_rings: int
    num_heavy_atoms: int
    num_heteroatoms: int
    fraction_csp3: float
    pka_values: list[float] = Field(default_factory=list)
    logd_at_recommended_ph: float | None = None


class PubChemLookupOut(BaseModel):
    name: str
    smiles: str
    inchikey: str
    formula: str
    mw: str


class CompoundUpdate(BaseModel):
    """Partial update for a compound. All fields optional."""
    name: str | None = None
    cas: str | None = None
    is_shared: bool | None = None


class CompoundBatchCreate(BaseModel):
    """Batch create multiple compounds."""
    compounds: list[CompoundCreate] = Field(min_length=1, max_length=500)

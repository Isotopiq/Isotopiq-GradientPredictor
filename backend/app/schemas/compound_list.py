"""CompoundList schemas."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompoundListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = None
    compound_ids: list[uuid.UUID] = Field(default_factory=list)


class CompoundListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    compound_ids: list[uuid.UUID] | None = None


class CompoundListOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    compound_ids: list[Any]


# ---------------------------------------------------------------------------
# CSV Import schemas
# ---------------------------------------------------------------------------


class CSVCompoundEntry(BaseModel):
    """A single parsed row from the uploaded CSV."""

    row_index: int
    name: str = ""
    formula: str | None = None
    rt: float | None = None
    charge: int | None = None
    smiles: str | None = None
    inchikey: str | None = None
    cas: str | None = None


class CSVParseResult(BaseModel):
    """Result of parsing a CSV file."""

    entries: list[CSVCompoundEntry]
    total_rows: int
    columns_detected: dict[str, str]  # original_header -> canonical_field


class ImportResolveRequest(BaseModel):
    """Request to start resolving parsed CSV entries."""

    entries: list[CSVCompoundEntry] = Field(min_length=1, max_length=5000)
    use_lipidmaps: bool = False


class ImportResolveJobCreated(BaseModel):
    """Response after starting a resolution job."""

    job_id: str


class ResolvedCandidate(BaseModel):
    """A single candidate structure for a resolved compound."""

    smiles: str
    inchikey: str | None = None
    formula: str | None = None
    mw: float | None = None
    name: str | None = None
    source: str  # "pubchem" | "lipidmaps" | "manual"
    provider_id: str | None = None


class ResolvedCompound(BaseModel):
    """A resolved (or unresolved) compound from the import job."""

    row_index: int
    name: str
    formula: str | None = None
    rt: float | None = None
    charge: int | None = None
    cas: str | None = None
    smiles: str | None = None
    inchikey: str | None = None
    mw: float | None = None
    logp: float | None = None
    tpsa: float | None = None
    source: str = "unresolved"  # "pubchem" | "lipidmaps" | "manual" | "unresolved"
    status: str = "unresolved"  # "resolved" | "unresolved" | "ambiguous"
    candidates: list[ResolvedCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ImportResolveStatus(BaseModel):
    """Status of a resolution job (polled by frontend)."""

    job_id: str
    status: str  # "pending" | "running" | "complete" | "failed"
    progress_pct: float = 0.0
    total: int = 0
    processed: int = 0
    resolved: int = 0
    unresolved: int = 0
    ambiguous: int = 0
    results: list[ResolvedCompound] = Field(default_factory=list)
    error: str | None = None


class ImportConfirmRequest(BaseModel):
    """Request to confirm and persist imported compounds."""

    list_name: str = Field(min_length=1, max_length=256)
    list_description: str | None = None
    compounds: list[dict[str, Any]] = Field(
        min_length=1,
        max_length=5000,
        description="List of {smiles, name?, cas?, source?} dicts for confirmed compounds",
    )


class ImportConfirmResult(BaseModel):
    """Result of confirming an import."""

    compound_list: CompoundListOut
    compounds_created: int
    compounds_reused: int

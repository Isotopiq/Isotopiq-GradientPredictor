"""Compound list routes: CRUD for named compound lists + CSV import."""
from __future__ import annotations

import csv
import io
import logging
import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.core.chem.descriptors import compute_descriptors
from app.core.chem.parser import ChemParseError, parse_mol
from app.deps import CurrentUser, DBSession
from app.models.compound import Compound
from app.schemas.compound_list import (
    CompoundListCreate,
    CompoundListOut,
    CompoundListUpdate,
    CSVCompoundEntry,
    CSVParseResult,
    ImportConfirmRequest,
    ImportConfirmResult,
    ImportResolveJobCreated,
    ImportResolveRequest,
    ImportResolveStatus,
    ResolvedCompound,
)
from app.services import compound_list_service
from app.services.import_resolver import get_resolution_job, start_resolution_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compound-lists", tags=["compound-lists"])

# CSV import limits
_MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
_MAX_CSV_ROWS = 5000

# Column header aliases (case-insensitive) → canonical field name
_COLUMN_ALIASES: dict[str, str] = {
    "compound": "name",
    "name": "name",
    "compound_name": "name",
    "molecule": "name",
    "molecule_name": "name",
    "formula": "formula",
    "molecular_formula": "formula",
    "rt": "rt",
    "retention_time": "rt",
    "retention_time_min": "rt",
    "rtime": "rt",
    "charge": "charge",
    "z": "charge",
    "smiles": "smiles",
    "canonical_smiles": "smiles",
    "isomeric_smiles": "smiles",
    "inchikey": "inchikey",
    "inchi_key": "inchikey",
    "cas": "cas",
    "cas_number": "cas",
    "cas_no": "cas",
}


@router.post("", response_model=CompoundListOut, status_code=status.HTTP_201_CREATED)
async def create_compound_list(
    data: CompoundListCreate,
    db: DBSession,
    current: CurrentUser,
) -> CompoundListOut:
    cl = await compound_list_service.create_list(db, current.id, data)
    return CompoundListOut.model_validate(cl)


@router.get("", response_model=list[CompoundListOut])
async def list_compound_lists(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[CompoundListOut]:
    items = await compound_list_service.list_lists(db, current.id, limit, offset)
    return [CompoundListOut.model_validate(cl) for cl in items]


@router.get("/{list_id}", response_model=CompoundListOut)
async def get_compound_list(
    list_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
) -> CompoundListOut:
    cl = await compound_list_service.get_list(db, list_id)
    if cl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound list not found")
    if cl.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return CompoundListOut.model_validate(cl)


@router.put("/{list_id}", response_model=CompoundListOut)
async def update_compound_list(
    list_id: uuid.UUID,
    data: CompoundListUpdate,
    db: DBSession,
    current: CurrentUser,
) -> CompoundListOut:
    cl = await compound_list_service.update_list(db, list_id, current.id, data)
    if cl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound list not found")
    return CompoundListOut.model_validate(cl)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compound_list(
    list_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
) -> None:
    deleted = await compound_list_service.delete_list(db, list_id, current.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound list not found")


# ---------------------------------------------------------------------------
# CSV Import endpoints
# ---------------------------------------------------------------------------


def _detect_columns(header: list[str]) -> dict[str, str]:
    """Map CSV header names to canonical field names.

    Returns a dict of {original_header: canonical_field} for recognized columns.
    """
    mapping: dict[str, str] = {}
    for h in header:
        key = h.strip().lower().replace(" ", "_").replace("-", "_")
        if key in _COLUMN_ALIASES:
            mapping[h] = _COLUMN_ALIASES[key]
    return mapping


def _parse_csv_content(content: str) -> CSVParseResult:
    """Parse CSV text into a CSVParseResult."""
    # Use csv.reader to handle edge cases (quoted fields, empty columns, etc.)
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV file is empty")

    header = rows[0]
    # Strip BOM from first header cell if present
    if header and header[0].startswith("\ufeff"):
        header[0] = header[0].lstrip("\ufeff")

    col_map = _detect_columns(header)
    if "name" not in col_map.values():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "CSV must contain a compound/name column",
        )

    entries: list[CSVCompoundEntry] = []
    for i, row in enumerate(rows[1:], start=1):
        if not row or all(c.strip() == "" for c in row):
            continue  # skip empty rows

        # Build a dict of {canonical_field: value} for this row
        row_data: dict[str, str] = {}
        for j, cell in enumerate(row):
            if j >= len(header):
                break
            orig_header = header[j]
            canonical = col_map.get(orig_header)
            if canonical:
                row_data[canonical] = cell.strip()

        name = row_data.get("name", "").strip()
        if not name:
            continue  # skip rows without a name

        def _parse_float(val: str | None) -> float | None:
            if val is None or val.strip() == "":
                return None
            try:
                return float(val.strip())
            except ValueError:
                return None

        def _parse_int(val: str | None) -> int | None:
            if val is None or val.strip() == "":
                return None
            try:
                return int(float(val.strip()))
            except ValueError:
                return None

        entries.append(CSVCompoundEntry(
            row_index=i,
            name=name,
            formula=row_data.get("formula") or None,
            rt=_parse_float(row_data.get("rt")),
            charge=_parse_int(row_data.get("charge")),
            smiles=row_data.get("smiles") or None,
            inchikey=row_data.get("inchikey") or None,
            cas=row_data.get("cas") or None,
        ))

        if len(entries) >= _MAX_CSV_ROWS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"CSV exceeds maximum of {_MAX_CSV_ROWS} rows",
            )

    return CSVParseResult(
        entries=entries,
        total_rows=len(entries),
        columns_detected=col_map,
    )


@router.post("/import/parse", response_model=CSVParseResult)
async def parse_csv(
    current: CurrentUser,
    file: UploadFile = File(...),  # noqa: B008
) -> CSVParseResult:
    """Parse a CSV file and return structured compound entries.

    Accepts CSV files with columns like: compound, formula, rt, charge, smiles, inchikey, cas.
    Flexible header detection — see _COLUMN_ALIASES for recognized names.
    """
    content_bytes = await file.read()
    if len(content_bytes) > _MAX_CSV_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"File exceeds maximum size of {_MAX_CSV_SIZE_BYTES // 1024 // 1024} MB",
        )

    # Decode — try UTF-8, fall back to latin-1
    try:
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1")

    return _parse_csv_content(content)


@router.post("/import/resolve", response_model=ImportResolveJobCreated)
async def start_resolve(
    data: ImportResolveRequest,
    current: CurrentUser,
) -> ImportResolveJobCreated:
    """Start a background resolution job for parsed CSV entries.

    Returns a job_id that can be polled via GET /compound-lists/import/resolve/{job_id}.
    """
    entries = [e.model_dump() for e in data.entries]
    job_id = await start_resolution_job(entries, use_lipidmaps=data.use_lipidmaps)
    return ImportResolveJobCreated(job_id=job_id)


@router.get("/import/resolve/{job_id}", response_model=ImportResolveStatus)
async def get_resolve_status(
    job_id: str,
    current: CurrentUser,
) -> ImportResolveStatus:
    """Poll the status of a resolution job."""
    state = await get_resolution_job(job_id)
    if state is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return ImportResolveStatus(
        job_id=state.job_id,
        status=state.status,
        progress_pct=round(state.progress_pct, 1),
        total=state.total,
        processed=state.processed,
        resolved=state.resolved,
        unresolved=state.unresolved,
        ambiguous=state.ambiguous,
        results=[ResolvedCompound(**r) for r in state.results],
        error=state.error,
    )


@router.post("/import/confirm", response_model=ImportConfirmResult)
async def confirm_import(
    data: ImportConfirmRequest,
    db: DBSession,
    current: CurrentUser,
) -> ImportConfirmResult:
    """Confirm and persist imported compounds.

    Creates compounds from the provided SMILES (deduplicating by InChIKey),
    then creates a CompoundList with the confirmed compound IDs.
    """
    compound_ids: list[uuid.UUID] = []
    compounds_created = 0
    compounds_reused = 0

    for c in data.compounds:
        smiles = (c.get("smiles") or "").strip()
        if not smiles:
            continue

        # Check if compound already exists (by InChIKey)
        try:
            parsed = parse_mol(smiles)
        except ChemParseError as exc:
            logger.warning("Skipping invalid SMILES in import confirm: %s", exc)
            continue

        inchikey = parsed.inchikey
        existing = None
        if inchikey:
            from sqlalchemy import select

            stmt = (
                select(Compound)
                .where(Compound.inchikey == inchikey)
                .where(
                    (Compound.owner_id == current.id)
                    | (Compound.is_shared == True)  # noqa: E712
                )
                .limit(1)
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

        if existing:
            compound_ids.append(existing.id)
            compounds_reused += 1
            continue

        # Create new compound
        desc = compute_descriptors(parsed.mol)
        from app.core.chem.pka import estimate_pka_values

        pka_values = estimate_pka_values(parsed.mol)
        compound = Compound(
            owner_id=current.id,
            name=c.get("name"),
            smiles=parsed.smiles,
            inchi=parsed.inchi,
            inchikey=inchikey,
            molfile=parsed.molfile,
            cas=c.get("cas"),
            mw=desc.mw,
            logp=desc.logp,
            pka_values=pka_values,  # type: ignore[arg-type]
            tpsa=desc.tpsa,
            hbd=desc.hbd,
            hba=desc.hba,
            rotatable_bonds=desc.rotatable_bonds,
            aromatic_rings=desc.aromatic_rings,
            source=c.get("source", "import"),
        )
        db.add(compound)
        await db.flush()
        compound_ids.append(compound.id)
        compounds_created += 1

    await db.commit()

    # Create the compound list
    create_data = CompoundListCreate(
        name=data.list_name,
        description=data.list_description,
        compound_ids=compound_ids,
    )
    cl = await compound_list_service.create_list(db, current.id, create_data)

    return ImportConfirmResult(
        compound_list=CompoundListOut.model_validate(cl),
        compounds_created=compounds_created,
        compounds_reused=compounds_reused,
    )

"""Method import routes: parse .meth files and extract peaks from mzXML.

Supports:
- Parsing .meth files with editable method conditions
- Multiple mzXML file uploads
- Peak extraction across all mzXML files
- Training new models or incrementally improving existing ones
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.meth_parser import MethParseError, ParsedMethod, parse_meth_file
from app.core.chem.mzxml_parser import (
    MzXmlParseError,
    extract_compound_peaks,
    parse_mzxml,
)
from app.core.ml.registry import get_artifact, list_artifacts
from app.core.ml.trainer import TrainingSample, train_model
from app.deps import CurrentUser, DBSession
from app.services import compound_service
from app.services.method_service import compute_method_signature
from pydantic import BaseModel

router = APIRouter(prefix="/method-import", tags=["method-import"])


class ParsedMethodOut(BaseModel):
    """Parsed chromatography method conditions."""
    instrument: str | None = None
    method_name: str | None = None
    column_temp_c: float | None = None
    flow_rate_ml_min: float | None = None
    solvent_a: str | None = None
    solvent_b: str | None = None
    method_end_time_min: float | None = None
    injection_volume_ul: float | None = None
    sampler_temp_c: float | None = None
    percent_b_start: float | None = None
    percent_b_end: float | None = None
    gradient_time_min: float | None = None
    gradient_table: list[dict[str, Any]] = []
    warnings: list[str] = []


class MzXmlSummaryOut(BaseModel):
    """Summary of an mzXML file."""
    filename: str = ""
    num_scans: int = 0
    num_ms1_scans: int = 0
    num_ms2_scans: int = 0
    rt_start_s: float | None = None
    rt_end_s: float | None = None
    polarity: str | None = None


class PeakDetectionResult(BaseModel):
    """Peak detection result for a single compound."""
    compound_id: str | None = None
    compound_name: str | None = None
    smiles: str | None = None
    target_mz: float | None = None
    mz_tolerance_ppm: float | None = None
    peaks: list[dict[str, Any]] = []
    xic_points: int = 0
    error: str | None = None


class ExtractPeaksResponse(BaseModel):
    """Response from peak extraction endpoint."""
    mzxml_summaries: list[MzXmlSummaryOut] = []
    results: list[PeakDetectionResult] = []
    method_conditions: ParsedMethodOut | None = None


class ModelSummary(BaseModel):
    """Summary of an existing model for selection."""
    id: str
    column_type: str
    model_type: str
    version: int
    n_samples: int
    trained_at: str


@router.post("/parse-meth", response_model=ParsedMethodOut)
async def parse_meth(
    current: CurrentUser,
    file: UploadFile = File(...),
) -> ParsedMethodOut:
    """Parse a Thermo Chromeleon .meth file and extract chromatography conditions."""
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    try:
        parsed = parse_meth_file(content)
    except MethParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return ParsedMethodOut(**parsed.to_dict())


@router.post("/parse-mzxml", response_model=MzXmlSummaryOut)
async def parse_mzxml_route(
    current: CurrentUser,
    file: UploadFile = File(...),
) -> MzXmlSummaryOut:
    """Parse an mzXML file and return a summary (no peak extraction)."""
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    try:
        summary = parse_mzxml(content)
    except MzXmlParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MzXmlSummaryOut(
        filename=file.filename or "",
        num_scans=summary.num_scans,
        num_ms1_scans=summary.num_ms1_scans,
        num_ms2_scans=summary.num_ms2_scans,
        rt_start_s=summary.rt_start_s,
        rt_end_s=summary.rt_end_s,
        polarity=summary.polarity,
    )


@router.get("/models", response_model=list[ModelSummary])
async def list_models(
    db: DBSession,
    current: CurrentUser,
    column_type: str | None = None,
) -> list[ModelSummary]:
    """List existing trained models for incremental training selection."""
    artifacts = await list_artifacts(db, column_type=column_type, limit=100)
    return [
        ModelSummary(
            id=str(a.id),
            column_type=a.column_type,
            model_type=a.model_type,
            version=a.version,
            n_samples=a.n_samples,
            trained_at=a.trained_at.isoformat() if a.trained_at else "",
        )
        for a in artifacts
    ]


async def _fetch_compounds_async(
    db: AsyncSession, current: CurrentUser, compound_ids: str
) -> list[dict[str, Any]]:
    """Parse compound IDs and fetch from DB."""
    try:
        ids = [uuid.UUID(cid.strip()) for cid in compound_ids.split(",") if cid.strip()]
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid compound ID: {exc}") from exc

    if not ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No compound IDs provided")

    compounds: list[dict[str, Any]] = []
    for cid in ids:
        compound = await compound_service.get_compound(db, cid)
        if compound is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Compound {cid} not found")
        if compound.owner_id != current.id and not compound.is_shared:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Not allowed to access compound {cid}")
        compounds.append({
            "id": str(compound.id),
            "name": compound.name,
            "smiles": compound.smiles,
        })
    return compounds


def _build_method_conditions(
    method_conditions: ParsedMethod | None,
    # User-edited overrides
    override_flow: float | None = None,
    override_temp: float | None = None,
    override_percent_b_start: float | None = None,
    override_percent_b_end: float | None = None,
    override_gradient_time: float | None = None,
    override_ph: float | None = None,
) -> dict[str, float]:
    """Build method conditions dict from parsed values + user overrides."""
    ph = override_ph or 2.7
    percent_b_start = 5.0
    percent_b_end = 95.0
    gradient_time_min = 20.0
    flow_rate = 0.4
    temperature = 30.0

    if method_conditions:
        if method_conditions.percent_b_start is not None:
            percent_b_start = method_conditions.percent_b_start
        if method_conditions.percent_b_end is not None:
            percent_b_end = method_conditions.percent_b_end
        if method_conditions.gradient_time_min is not None:
            gradient_time_min = method_conditions.gradient_time_min
        if method_conditions.flow_rate_ml_min is not None:
            flow_rate = method_conditions.flow_rate_ml_min
        if method_conditions.column_temp_c is not None:
            temperature = method_conditions.column_temp_c

    # Apply user overrides
    if override_flow is not None:
        flow_rate = override_flow
    if override_temp is not None:
        temperature = override_temp
    if override_percent_b_start is not None:
        percent_b_start = override_percent_b_start
    if override_percent_b_end is not None:
        percent_b_end = override_percent_b_end
    if override_gradient_time is not None:
        gradient_time_min = override_gradient_time
    if override_ph is not None:
        ph = override_ph

    return {
        "ph": ph,
        "percent_b_start": percent_b_start,
        "percent_b_end": percent_b_end,
        "gradient_time_min": gradient_time_min,
        "flow_rate_ml_min": flow_rate,
        "temperature_c": temperature,
    }


@router.post("/extract-peaks", response_model=ExtractPeaksResponse)
async def extract_peaks(
    db: DBSession,
    current: CurrentUser,
    mzxml_files: list[UploadFile] = File(...),
    compound_ids: str = Form(...),
    meth_file: UploadFile | None = File(None),
    mz_tolerance_ppm: float = Form(10.0),
    min_snr: float = Form(3.0),
    max_peaks_per_compound: int = Form(3),
) -> ExtractPeaksResponse:
    """Extract peaks from one or more mzXML files for a list of compounds.

    Optionally parse a .meth file to include chromatography conditions.
    Compounds are specified by their database IDs (comma-separated UUIDs).
    When multiple mzXML files are provided, scans from all files are combined
    and the strongest peak across all files is reported per compound.
    """
    compounds = await _fetch_compounds_async(db, current, compound_ids)

    # Parse all mzXML files and combine scans
    all_scans: list = []
    summaries: list[MzXmlSummaryOut] = []

    for mzxml_file in mzxml_files:
        content = await mzxml_file.read()
        if not content:
            continue
        try:
            summary = parse_mzxml(content)
        except MzXmlParseError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Error parsing {mzxml_file.filename}: {exc}",
            ) from exc
        all_scans.extend(summary.scans)
        summaries.append(MzXmlSummaryOut(
            filename=mzxml_file.filename or "",
            num_scans=summary.num_scans,
            num_ms1_scans=summary.num_ms1_scans,
            num_ms2_scans=summary.num_ms2_scans,
            rt_start_s=summary.rt_start_s,
            rt_end_s=summary.rt_end_s,
            polarity=summary.polarity,
        ))

    if not all_scans:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No scans found in mzXML file(s)")

    # Optionally parse .meth file
    method_conditions = None
    if meth_file:
        meth_content = await meth_file.read()
        if meth_content:
            try:
                parsed = parse_meth_file(meth_content)
                method_conditions = ParsedMethodOut(**parsed.to_dict())
            except MethParseError:
                pass  # Non-fatal

    # Extract peaks from combined scans
    peak_results = extract_compound_peaks(
        scans=all_scans,
        compounds=compounds,
        mz_tolerance_ppm=mz_tolerance_ppm,
        min_snr=min_snr,
        max_peaks_per_compound=max_peaks_per_compound,
    )

    return ExtractPeaksResponse(
        mzxml_summaries=summaries,
        results=[PeakDetectionResult(**r.to_dict()) for r in peak_results],
        method_conditions=method_conditions,
    )


@router.post("/train-from-peaks", response_model=dict)
async def train_from_peaks(
    db: DBSession,
    current: CurrentUser,
    mzxml_files: list[UploadFile] = File(...),
    compound_ids: str = Form(...),
    meth_file: UploadFile | None = File(None),
    column_type: str = Form("C18"),
    model_type: str = Form("xgboost"),
    mz_tolerance_ppm: float = Form(10.0),
    min_snr: float = Form(3.0),
    # User-editable method condition overrides
    override_flow: float | None = Form(None),
    override_temp: float | None = Form(None),
    override_percent_b_start: float | None = Form(None),
    override_percent_b_end: float | None = Form(None),
    override_gradient_time: float | None = Form(None),
    override_ph: float | None = Form(None),
    # Incremental training: provide existing artifact ID to merge data
    existing_artifact_id: str | None = Form(None),
) -> dict[str, Any]:
    """Full pipeline: parse .meth + mzXML(s), extract peaks, and train a model.

    Generates training samples from detected peaks and chromatography conditions,
    then trains a retention model. Supports:
    - Multiple mzXML files (scans combined, strongest peak per compound used)
    - User-edited method condition overrides
    - Incremental training: pass existing_artifact_id to merge new samples with
      the existing model's training data and retrain
    """
    compounds = await _fetch_compounds_async(db, current, compound_ids)

    # Parse all mzXML files and combine scans
    all_scans: list = []
    for mzxml_file in mzxml_files:
        content = await mzxml_file.read()
        if not content:
            continue
        try:
            summary = parse_mzxml(content)
        except MzXmlParseError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Error parsing {mzxml_file.filename}: {exc}",
            ) from exc
        all_scans.extend(summary.scans)

    if not all_scans:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No scans found in mzXML file(s)")

    # Parse .meth file for method conditions
    parsed_method: ParsedMethod | None = None
    if meth_file:
        meth_content = await meth_file.read()
        if meth_content:
            try:
                parsed_method = parse_meth_file(meth_content)
            except MethParseError:
                pass

    # Build method conditions with user overrides
    conditions = _build_method_conditions(
        parsed_method,
        override_flow=override_flow,
        override_temp=override_temp,
        override_percent_b_start=override_percent_b_start,
        override_percent_b_end=override_percent_b_end,
        override_gradient_time=override_gradient_time,
        override_ph=override_ph,
    )

    # Extract peaks (use strongest peak per compound)
    peak_results = extract_compound_peaks(
        scans=all_scans,
        compounds=compounds,
        mz_tolerance_ppm=mz_tolerance_ppm,
        min_snr=min_snr,
        max_peaks_per_compound=1,
    )

    # Build new training samples
    new_samples: list[TrainingSample] = []
    for result in peak_results:
        if result.error or not result.peaks:
            continue
        if not result.smiles:
            continue

        peak = result.peaks[0]
        new_samples.append(TrainingSample(
            smiles=result.smiles,
            column_type=column_type,
            ph=conditions["ph"],
            percent_b_start=conditions["percent_b_start"],
            percent_b_end=conditions["percent_b_end"],
            gradient_time_min=conditions["gradient_time_min"],
            flow_rate_ml_min=conditions["flow_rate_ml_min"],
            temperature_c=conditions["temperature_c"],
            observed_rt_s=peak.retention_time_s,
        ))

    if not new_samples:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No training samples generated — no peaks detected for the given compounds",
        )

    # If incremental training, load existing model's samples and merge
    all_samples = new_samples
    existing_info: dict[str, Any] = {}
    if existing_artifact_id:
        try:
            artifact_id = uuid.UUID(existing_artifact_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Invalid artifact ID: {exc}"
            ) from exc

        existing_artifact = await get_artifact(db, artifact_id)
        if existing_artifact is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Existing model not found")

        # Load stored runs for the same column type to get historical data
        from app.core.ml.trainer import load_stored_runs
        existing_samples = await load_stored_runs(db, column_type)
        if existing_samples:
            all_samples = existing_samples + new_samples
            existing_info = {
                "existing_samples_loaded": len(existing_samples),
                "existing_model_version": existing_artifact.version,
                "existing_model_type": existing_artifact.model_type,
            }

    # Train model
    try:
        artifact = await train_model(
            db=db,
            owner_id=current.id,
            column_type=column_type,
            model_type=model_type,
            samples=all_samples,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Training failed: {exc}") from exc

    return {
        "artifact_id": str(artifact.id),
        "n_samples": len(all_samples),
        "n_new_samples": len(new_samples),
        "column_type": column_type,
        "model_type": model_type,
        "compounds_used": [r.compound_name or r.smiles for r in peak_results if r.peaks],
        "compounds_no_peaks": [r.compound_name or r.smiles for r in peak_results if not r.peaks],
        "incremental": existing_artifact_id is not None,
        **existing_info,
    }

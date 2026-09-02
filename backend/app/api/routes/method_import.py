"""Method import routes: parse .meth files and extract peaks from mzXML."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chem.meth_parser import MethParseError, parse_meth_file
from app.core.chem.mzxml_parser import (
    MzXmlParseError,
    extract_compound_peaks,
    parse_mzxml,
)
from app.deps import CurrentUser, DBSession
from app.services import compound_service
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
    mzxml_summary: MzXmlSummaryOut
    results: list[PeakDetectionResult] = []
    method_conditions: ParsedMethodOut | None = None


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
        num_scans=summary.num_scans,
        num_ms1_scans=summary.num_ms1_scans,
        num_ms2_scans=summary.num_ms2_scans,
        rt_start_s=summary.rt_start_s,
        rt_end_s=summary.rt_end_s,
        polarity=summary.polarity,
    )


@router.post("/extract-peaks", response_model=ExtractPeaksResponse)
async def extract_peaks(
    db: DBSession,
    current: CurrentUser,
    mzxml_file: UploadFile = File(...),
    compound_ids: str = Form(...),
    meth_file: UploadFile | None = File(None),
    mz_tolerance_ppm: float = Form(10.0),
    min_snr: float = Form(3.0),
    max_peaks_per_compound: int = Form(3),
) -> ExtractPeaksResponse:
    """Extract peaks from an mzXML file for a list of compounds.

    Optionally parse a .meth file to include chromatography conditions.
    Compounds are specified by their database IDs (comma-separated UUIDs).
    """
    # Parse compound IDs
    try:
        ids = [uuid.UUID(cid.strip()) for cid in compound_ids.split(",") if cid.strip()]
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid compound ID: {exc}") from exc

    if not ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No compound IDs provided")

    # Fetch compounds from DB
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

    # Parse mzXML
    mzxml_content = await mzxml_file.read()
    if not mzxml_content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty mzXML file")
    try:
        mzxml_summary = parse_mzxml(mzxml_content)
    except MzXmlParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # Optionally parse .meth file
    method_conditions = None
    if meth_file:
        meth_content = await meth_file.read()
        if meth_content:
            try:
                parsed = parse_meth_file(meth_content)
                method_conditions = ParsedMethodOut(**parsed.to_dict())
            except MethParseError as exc:
                pass  # Non-fatal — continue without method conditions

    # Extract peaks
    peak_results = extract_compound_peaks(
        scans=mzxml_summary.scans,
        compounds=compounds,
        mz_tolerance_ppm=mz_tolerance_ppm,
        min_snr=min_snr,
        max_peaks_per_compound=max_peaks_per_compound,
    )

    return ExtractPeaksResponse(
        mzxml_summary=MzXmlSummaryOut(
            num_scans=mzxml_summary.num_scans,
            num_ms1_scans=mzxml_summary.num_ms1_scans,
            num_ms2_scans=mzxml_summary.num_ms2_scans,
            rt_start_s=mzxml_summary.rt_start_s,
            rt_end_s=mzxml_summary.rt_end_s,
            polarity=mzxml_summary.polarity,
        ),
        results=[
            PeakDetectionResult(**r.to_dict()) for r in peak_results
        ],
        method_conditions=method_conditions,
    )


@router.post("/train-from-peaks", response_model=dict)
async def train_from_peaks(
    db: DBSession,
    current: CurrentUser,
    mzxml_file: UploadFile = File(...),
    compound_ids: str = Form(...),
    meth_file: UploadFile = File(None),
    column_type: str = Form("C18"),
    model_type: str = Form("xgboost"),
    mz_tolerance_ppm: float = Form(10.0),
    min_snr: float = Form(3.0),
) -> dict[str, Any]:
    """Full pipeline: parse .meth + mzXML, extract peaks, and train a model.

    Generates training samples from detected peaks and chromatography conditions,
    then trains a retention model using the existing training pipeline.
    """
    from app.core.ml.trainer import TrainingSample, train_model
    from app.services import ml_service

    # Parse compound IDs
    try:
        ids = [uuid.UUID(cid.strip()) for cid in compound_ids.split(",") if cid.strip()]
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid compound ID: {exc}") from exc

    if not ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No compound IDs provided")

    # Fetch compounds
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

    # Parse mzXML
    mzxml_content = await mzxml_file.read()
    if not mzxml_content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty mzXML file")
    try:
        mzxml_summary = parse_mzxml(mzxml_content)
    except MzXmlParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # Parse .meth file for method conditions
    method_conditions = None
    if meth_file:
        meth_content = await meth_file.read()
        if meth_content:
            try:
                method_conditions = parse_meth_file(meth_content)
            except MethParseError:
                pass

    # Extract peaks
    peak_results = extract_compound_peaks(
        scans=mzxml_summary.scans,
        compounds=compounds,
        mz_tolerance_ppm=mz_tolerance_ppm,
        min_snr=min_snr,
        max_peaks_per_compound=1,  # Use only the strongest peak for training
    )

    # Build training samples
    samples: list[TrainingSample] = []
    for result in peak_results:
        if result.error or not result.peaks:
            continue
        if not result.smiles:
            continue

        # Use the strongest peak (first in list, sorted by intensity)
        peak = result.peaks[0]

        # Get method conditions
        ph = 2.7  # Default — could be parsed from solvent description
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

        samples.append(TrainingSample(
            smiles=result.smiles,
            column_type=column_type,
            ph=ph,
            percent_b_start=percent_b_start,
            percent_b_end=percent_b_end,
            gradient_time_min=gradient_time_min,
            flow_rate_ml_min=flow_rate,
            temperature_c=temperature,
            observed_rt_s=peak.retention_time_s,
        ))

    if not samples:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No training samples generated — no peaks detected for the given compounds",
        )

    # Train model
    try:
        artifact = await train_model(
            db=db,
            owner_id=current.id,
            column_type=column_type,
            model_type=model_type,
            samples=samples,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Training failed: {exc}") from exc

    return {
        "artifact_id": str(artifact.id),
        "n_samples": len(samples),
        "column_type": column_type,
        "model_type": model_type,
        "compounds_used": [r.compound_name or r.smiles for r in peak_results if r.peaks],
        "compounds_no_peaks": [r.compound_name or r.smiles for r in peak_results if not r.peaks],
    }

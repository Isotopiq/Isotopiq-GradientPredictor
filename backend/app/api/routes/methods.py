"""Method routes: suggest, CRUD, gradient simulation, chromatogram, templates, sharing."""
from __future__ import annotations

import math
import secrets
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.rules.templates import (
    get_categories,
    get_template,
    list_templates,
    template_to_dict,
    template_to_gradient_table,
)
from app.deps import CurrentUser, DBSession
from app.schemas.method import (
    BufferCalcOut,
    BufferCalcRequest,
    ChromatogramOut,
    ChromatogramRequest,
    GradientSimulateOut,
    GradientSimulateRequest,
    MethodCompoundAdd,
    MethodCreate,
    MethodOut,
    MethodSuggestionOut,
    MethodSuggestionRequest,
    MethodTransferOut,
    MethodTransferRequest,
    MobilePhaseCheckRequest,
    ModelSelectionOut,
    ModelSelectionRequest,
    MultiCompoundSuggestionOut,
    MultiCompoundSuggestionRequest,
    OptimizeGradientOut,
    OptimizeGradientRequest,
    PeakTrackingRequest,
    PhDistributionOut,
    PhDistributionRequest,
    PhSuitabilityOut,
    PhSuitabilityRequest,
    PredictionEquationOut,
    PredictionEquationRequest,
    PredictRTOut,
    PredictRTRequest,
    ResolutionMap1DOut,
    ResolutionMap1DRequest,
    ResolutionMap2DOut,
    ResolutionMap2DRequest,
    TernaryOptimizeOut,
    TernaryOptimizeRequest,
    UserTemplateCreate,
    UserTemplateOut,
    UserTemplateUpdate,
    VanDeemterOut,
    VanDeemterRequest,
)
from app.services import compound_service, method_service

router = APIRouter(prefix="/methods", tags=["methods"])


# --- Retention models registry ---

@router.get("/retention-models")
async def get_retention_models(current: CurrentUser) -> dict:
    """Return all supported retention mechanisms and models, plus auto-selection.

    Query params (all optional):
      column_type: Column type string (e.g. "C18")
      column_id: Commercial column ID
      has_calibration: bool
      has_known_compounds: bool
      has_ml_model: bool
      percent_b_range: float
      mechanism: Override mechanism
    """
    from app.core.lss.retention_models import (
        RETENTION_MECHANISMS,
        RETENTION_MODELS,
    )

    return {
        "mechanisms": {
            key: {
                "key": m.key,
                "label": m.label,
                "description": m.description,
                "column_types": list(m.column_types),
                "solvent_model": m.solvent_model,
            }
            for key, m in RETENTION_MECHANISMS.items()
        },
        "models": {
            key: {
                "key": m.key,
                "label": m.label,
                "equation": m.equation,
                "applicable_mechanisms": list(m.applicable_mechanisms),
                "requires": m.requires,
                "reference": m.reference,
                "implemented": m.implemented,
            }
            for key, m in RETENTION_MODELS.items()
        },
    }


@router.get("/retention-models/auto-select")
async def auto_select_retention_model(
    current: CurrentUser,
    column_type: str | None = None,
    column_id: str | None = None,
    has_calibration: bool = False,
    has_known_compounds: bool = False,
    has_ml_model: bool = False,
    percent_b_range: float = 90.0,
    mechanism: str | None = None,
) -> dict:
    """Auto-select the best retention model for the given parameters."""
    from app.core.lss.retention_models import (
        RETENTION_MECHANISMS,
        RETENTION_MODELS,
        auto_select_model,
        get_models_for_mechanism,
        infer_mechanism_from_column,
    )

    inferred_mechanism = infer_mechanism_from_column(column_type)
    selected = auto_select_model(
        column_type=column_type,
        column_id=column_id,
        has_calibration=has_calibration,
        has_known_compounds=has_known_compounds,
        has_ml_model=has_ml_model,
        percent_b_range=percent_b_range,
        mechanism=mechanism,
    )
    applicable = get_models_for_mechanism(mechanism or inferred_mechanism)

    return {
        "mechanism": mechanism or inferred_mechanism,
        "mechanism_info": {
            "key": RETENTION_MECHANISMS[mechanism or inferred_mechanism].key,
            "label": RETENTION_MECHANISMS[mechanism or inferred_mechanism].label,
        },
        "selected_model": selected,
        "selected_model_info": {
            "key": RETENTION_MODELS[selected].key,
            "label": RETENTION_MODELS[selected].label,
            "equation": RETENTION_MODELS[selected].equation,
            "requires": RETENTION_MODELS[selected].requires,
        },
        "applicable_models": applicable,
    }


@router.post("/compare-models")
async def compare_models(data: GradientSimulateRequest, current: CurrentUser) -> dict:
    """Run all applicable retention models and return a comparison of predicted RTs.

    Uses the same inputs as /gradient/simulate but runs every applicable model
    for the inferred (or overridden) mechanism, returning predicted RTs and
    confidence for each.
    """
    from app.core.lss.retention_models import compare_models as _compare

    has_calibration = bool(data.calibration_runs and len(data.calibration_runs) >= 2)

    return _compare(
        column_type=data.column_type,
        column_id=data.column_id,
        logp=data.logp,
        mw=data.mw,
        tpsa=data.tpsa,
        hbd=data.hbd,
        hba=data.hba,
        gradient_table=data.gradient_table,
        flow_rate_ml_min=data.flow_rate_ml_min,
        column_void_volume_ml=data.column_void_volume_ml,
        smiles=data.smiles,
        ph=data.ph,
        has_calibration=has_calibration,
        has_ml_model=False,
        dwell_volume_ml=data.dwell_volume_ml,
        dead_volume_ml=data.dead_volume_ml,
        mechanism=data.retention_mechanism,
    )


# --- Action routes (no path params, safe to be first) ---


@router.post("/suggest", response_model=MethodSuggestionOut)
async def suggest_method(data: MethodSuggestionRequest, current: CurrentUser) -> MethodSuggestionOut:
    try:
        result = method_service.suggest(data)
    except method_service.MethodServiceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MethodSuggestionOut.model_validate(result)


@router.post("/gradient/simulate", response_model=GradientSimulateOut)
async def simulate_gradient(data: GradientSimulateRequest, current: CurrentUser) -> GradientSimulateOut:
    result = method_service.simulate_gradient(data)
    return GradientSimulateOut.model_validate(result)


@router.post("/chromatogram", response_model=ChromatogramOut)
async def simulate_chromatogram(data: ChromatogramRequest, current: CurrentUser) -> ChromatogramOut:
    result = method_service.simulate_chromatogram_from_request(data)
    return ChromatogramOut.model_validate(result)


@router.post("/suggest-multi", response_model=MultiCompoundSuggestionOut)
async def suggest_multi_method(data: MultiCompoundSuggestionRequest, current: CurrentUser) -> MultiCompoundSuggestionOut:
    result = method_service.suggest_multi(
        smiles_list=data.smiles_list,
        ionization_mode=data.ionization_mode,
        retention_goal=data.retention_goal,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
        column_type=data.column_type,
        retention_model=data.retention_model,
        retention_mechanism=data.retention_mechanism,
        column_id=data.column_id,
        ph=data.ph,
        dwell_volume_ml=data.dwell_volume_ml,
        dead_volume_ml=data.dead_volume_ml,
    )
    return MultiCompoundSuggestionOut.model_validate(result)


@router.post("/optimize-gradient", response_model=OptimizeGradientOut)
async def optimize_gradient(data: OptimizeGradientRequest, current: CurrentUser) -> OptimizeGradientOut:
    """Grid-search for the gradient parameters that maximize separation."""
    result = method_service.optimize_gradient_separation(
        smiles_list=data.smiles_list,
        flow_rate_ml_min=data.flow_rate_ml_min,
        gradient_time_min=data.gradient_time_min,
        column_type=data.column_type,
        ph=data.ph,
        temperature_c=data.temperature_c,
        suitability=data.suitability.model_dump() if data.suitability else None,
    )
    return OptimizeGradientOut.model_validate(result)


@router.post("/adducts")
async def predict_adducts(data: dict, current: CurrentUser) -> dict:
    """Predict expected m/z values for common ESI adducts from SMILES."""
    from rdkit.Chem import Descriptors

    from app.core.chem.descriptors import predict_adducts as compute_adducts
    from app.core.chem.parser import ChemParseError, parse_mol

    smiles = data.get("smiles", "")
    if not smiles:
        raise HTTPException(status_code=400, detail="smiles is required")
    try:
        mol = parse_mol(smiles).mol
    except ChemParseError:
        raise HTTPException(status_code=400, detail="Invalid SMILES")

    mono_mass = Descriptors.ExactMolWt(mol)
    adducts = compute_adducts(mono_mass)
    return {
        "monoisotopic_mass": round(mono_mass, 4),
        "adducts": adducts,
    }


@router.post("/dwell-volume/calculate")
async def calculate_dwell_volume(data: dict, current: CurrentUser) -> dict:
    """F13: Calculate dwell volume from a measured midpoint time.

    Dwell volume = (midpoint_time - gradient_time/2) * flow_rate

    Also supports dead volume calculation: Vdead = tR_uracil * flow_rate
    """
    flow_rate = data.get("flow_rate_ml_min", 0.0)
    gradient_time_min = data.get("gradient_time_min", 0.0)
    midpoint_time_min = data.get("midpoint_time_min", 0.0)

    if flow_rate <= 0:
        raise HTTPException(status_code=400, detail="flow_rate_ml_min must be > 0")

    # Dwell volume calculation
    dwell_volume = None
    dwell_time = None
    if midpoint_time_min > 0 and gradient_time_min > 0:
        dwell_time = midpoint_time_min - gradient_time_min / 2.0
        dwell_volume = dwell_time * flow_rate

    # Dead volume calculation (from uracil RT)
    dead_volume = None
    uracil_rt_min = data.get("uracil_rt_min")
    if uracil_rt_min is not None and uracil_rt_min > 0:
        dead_volume = uracil_rt_min * flow_rate

    return {
        "dwell_volume_ml": round(dwell_volume, 4) if dwell_volume is not None else None,
        "dwell_time_min": round(dwell_time, 4) if dwell_time is not None else None,
        "dead_volume_ml": round(dead_volume, 4) if dead_volume is not None else None,
    }


# --- F6: Prediction Equation Mode ---


@router.post("/prediction-equation/build", response_model=PredictionEquationOut)
async def build_prediction_equation(data: PredictionEquationRequest, current: CurrentUser) -> PredictionEquationOut:
    """Build a retention prediction equation from >=5 known compounds."""
    from app.core.ml.prediction_equation import (
        KnownCompoundRT,
    )
    from app.core.ml.prediction_equation import (
        build_prediction_equation as _build,
    )

    if len(data.compounds) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 5 compounds to build prediction equation, got {len(data.compounds)}",
        )

    compounds = [
        KnownCompoundRT(
            smiles=c.smiles,
            rt_min=c.rt_min,
            column_type=c.column_type,
            ph=c.ph,
            gradient_time_min=c.gradient_time_min,
            flow_rate_ml_min=c.flow_rate_ml_min,
            temperature_c=c.temperature_c,
        )
        for c in data.compounds
    ]

    try:
        eq = _build(compounds, descriptor_names=data.descriptor_names)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PredictionEquationOut(**eq.to_dict())


@router.post("/prediction-equation/predict", response_model=PredictRTOut)
async def predict_rt(data: PredictRTRequest, current: CurrentUser) -> PredictRTOut:
    """Predict retention time for a new compound using a fitted equation."""
    from app.core.ml.prediction_equation import PredictionEquation
    from app.core.ml.prediction_equation import predict_rt as _predict

    eq = PredictionEquation(
        coefficients=data.coefficients,
        intercept=data.intercept,
        r=data.r,
        r_squared=data.r ** 2,
        std_dev=data.std_dev,
        n=0,
        descriptor_names=data.descriptor_names,
        descriptor_means=data.descriptor_means,
        descriptor_stds=data.descriptor_stds,
    )

    try:
        result = _predict(eq, data.smiles, ph=data.ph)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PredictRTOut(**result.to_dict())


# --- F9: Model Selection ---


@router.post("/model-selection", response_model=ModelSelectionOut)
async def model_selection(data: ModelSelectionRequest, current: CurrentUser) -> ModelSelectionOut:
    """Fit linear/quadratic/log-log models and suggest the best one."""
    from app.core.ml.model_selection import (
        CalibrationPoint,
        GradientModel,
        evaluate_fit,
        fit_model,
    )

    if len(data.points) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 calibration points")

    points = [
        CalibrationPoint(
            gradient_time_min=p.gradient_time_min,
            observed_rt_min=p.observed_rt_min,
            compound_id=p.compound_id,
        )
        for p in data.points
    ]

    all_models = []
    for model_type in GradientModel:
        try:
            fit = fit_model(model_type, points)
            quality = evaluate_fit(fit, points, data.bad_peaks_threshold)
            all_models.append({
                "model": model_type.value,
                "fit": fit.to_dict(),
                "quality": quality.to_dict(),
            })
        except Exception:
            continue

    if not all_models:
        raise HTTPException(status_code=400, detail="Could not fit any model")

    # Sort by R²
    all_models.sort(key=lambda m: m["fit"]["r_squared"], reverse=True)

    best = all_models[0]
    return ModelSelectionOut(
        best_model=best["model"],
        best_fit=best["fit"],
        all_models=all_models,
        best_quality=best["quality"],
    )


# --- F10: pH Selector ---


@router.post("/ph-distribution", response_model=PhDistributionOut)
async def ph_distribution(data: PhDistributionRequest, current: CurrentUser) -> PhDistributionOut:
    """Compute ionic species distribution across pH range for a compound."""
    from app.core.chem.ph_selector import ph_distribution as _ph_dist

    try:
        result = _ph_dist(data.smiles, data.ph_min, data.ph_max, data.steps, data.logp)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PhDistributionOut(**result.to_dict())


@router.post("/ph-suitability", response_model=PhSuitabilityOut)
async def ph_suitability(data: PhSuitabilityRequest, current: CurrentUser) -> PhSuitabilityOut:
    """Compute pH suitability map for a mixture of compounds."""
    from app.core.chem.ph_selector import ph_suitability as _ph_suit

    if not data.smiles_list:
        raise HTTPException(status_code=400, detail="smiles_list is required")

    try:
        result = _ph_suit(data.smiles_list, data.ph_min, data.ph_max, data.steps, data.buffer_count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PhSuitabilityOut(**result.to_dict())


# --- F4/F5: Resolution Maps ---


@router.post("/resolution-map/1d", response_model=ResolutionMap1DOut)
async def resolution_map_1d(data: ResolutionMap1DRequest, current: CurrentUser) -> ResolutionMap1DOut:
    """Compute 1D resolution map across a variable range."""
    from app.core.lss.resolution_map import resolution_map_1d as _rmap_1d

    fixed = {
        "ph": data.ph,
        "temperature": data.temperature,
        "flow_rate": data.flow_rate,
        "gradient_time": data.gradient_time,
        "percent_b_start": data.percent_b_start,
        "percent_b_end": data.percent_b_end,
        "column_type": data.column_type,
        "column_void_volume_ml": data.column_void_volume_ml,
        "dwell_volume_ml": data.dwell_volume_ml,
        "dead_volume_ml": data.dead_volume_ml,
    }
    if data.suitability:
        fixed["suitability"] = data.suitability.model_dump()

    try:
        result = _rmap_1d(
            data.smiles_list,
            data.variable,
            (data.var_min, data.var_max),
            data.steps,
            fixed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ResolutionMap1DOut(**result.to_dict())


@router.post("/resolution-map/2d", response_model=ResolutionMap2DOut)
async def resolution_map_2d(data: ResolutionMap2DRequest, current: CurrentUser) -> ResolutionMap2DOut:
    """Compute 2D resolution map (heatmap)."""
    from app.core.lss.resolution_map import resolution_map_2d as _rmap_2d

    fixed = {
        "ph": data.ph,
        "temperature": data.temperature,
        "flow_rate": data.flow_rate,
        "gradient_time": data.gradient_time,
        "percent_b_start": data.percent_b_start,
        "percent_b_end": data.percent_b_end,
        "column_type": data.column_type,
        "column_void_volume_ml": data.column_void_volume_ml,
        "dwell_volume_ml": data.dwell_volume_ml,
        "dead_volume_ml": data.dead_volume_ml,
    }
    if data.suitability:
        fixed["suitability"] = data.suitability.model_dump()

    try:
        result = _rmap_2d(
            data.smiles_list,
            data.var_x,
            (data.var_x_min, data.var_x_max),
            data.steps_x,
            data.var_y,
            (data.var_y_min, data.var_y_max),
            data.steps_y,
            fixed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ResolutionMap2DOut(**result.to_dict())


# --- F8: Ternary Solvent Optimization ---


@router.post("/ternary-optimize", response_model=TernaryOptimizeOut)
async def ternary_optimize(data: TernaryOptimizeRequest, current: CurrentUser) -> TernaryOptimizeOut:
    """Optimize ternary solvent ratios."""
    from app.core.lss.ternary_optimization import ternary_optimize as _ternary

    try:
        result = _ternary(
            smiles_list=data.smiles_list,
            solvent_a=data.solvent_a,
            solvent_b=data.solvent_b,
            solvent_c=data.solvent_c,
            gradient_time_min=data.gradient_time_min,
            flow_rate_ml_min=data.flow_rate_ml_min,
            ph=data.ph,
            temperature_c=data.temperature_c,
            column_type=data.column_type,
            mode=data.mode,
            grid_resolution=data.grid_resolution,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TernaryOptimizeOut(**result.to_dict())


# --- F2: Method Transfer Assistant ---


@router.post("/method-transfer", response_model=MethodTransferOut)
async def method_transfer(data: MethodTransferRequest, current: CurrentUser) -> MethodTransferOut:
    """Transfer a method from one column to another."""
    from app.core.lss.method_transfer import ColumnSpec, SourceMethod, transfer_method

    src_col = ColumnSpec(
        length_mm=data.source_column.length_mm,
        inner_diameter_mm=data.source_column.inner_diameter_mm,
        particle_size_um=data.source_column.particle_size_um,
        dwell_volume_ml=data.source_column.dwell_volume_ml,
        dead_volume_ml=data.source_column.dead_volume_ml,
    )
    tgt_col = ColumnSpec(
        length_mm=data.target_column.length_mm,
        inner_diameter_mm=data.target_column.inner_diameter_mm,
        particle_size_um=data.target_column.particle_size_um,
        dwell_volume_ml=data.target_column.dwell_volume_ml,
        dead_volume_ml=data.target_column.dead_volume_ml,
    )

    source = SourceMethod(
        column=src_col,
        flow_rate_ml_min=data.flow_rate_ml_min,
        gradient_table=data.gradient_table,
        injection_volume_ul=data.injection_volume_ul,
        temperature_c=data.temperature_c,
    )

    result = transfer_method(source, tgt_col, preserve_resolution=data.preserve_resolution)
    return MethodTransferOut(**result.to_dict())


# --- Van Deemter Mapper / Flow Optimizer ---


@router.post("/van-deemter", response_model=VanDeemterOut)
async def van_deemter_map(data: VanDeemterRequest, db: DBSession, current: CurrentUser) -> VanDeemterOut:
    """Van Deemter efficiency analysis and optimal flow-rate selection.

    Computes the plate-height curve H(F), the efficiency optimum
    u_opt = sqrt(b/c)*Dm/dp, an optional kinetic (speed) optimum at a
    target plate count and pressure limit, an assessment of the current
    flow rate, and a diameter map of optimal flows across standard IDs.
    Accepts either a column_id from the database or explicit dimensions.
    """
    from app.core.lss import van_deemter as vd

    notes: list[str] = []

    # Resolve column geometry
    column_label = "Custom column"
    if data.column_id:
        from app.core.chem.columns_db import get_column
        db_col = get_column(data.column_id)
        if db_col is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
        column_label = f"{db_col.brand} {db_col.name}"
        length_mm = data.length_mm or db_col.length_mm
        id_mm = data.inner_diameter_mm or db_col.inner_diameter_mm
        dp_um = data.particle_size_um or db_col.particle_size_um
        particle_type = data.particle_type or (
            db_col.phase.particle_type if db_col.phase else "fully_porous"
        )
    else:
        if not (data.length_mm and data.inner_diameter_mm and data.particle_size_um):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Provide column_id or all of length_mm, inner_diameter_mm, "
                "particle_size_um",
            )
        length_mm = data.length_mm
        id_mm = data.inner_diameter_mm
        dp_um = data.particle_size_um
        particle_type = data.particle_type or "fully_porous"

    if particle_type not in vd.VD_COEFFICIENTS:
        notes.append(
            f"Unknown particle_type '{particle_type}' — using fully_porous "
            f"coefficients"
        )
        particle_type = "fully_porous"

    col = vd.ColumnGeometry(
        length_mm=length_mm,
        inner_diameter_mm=id_mm,
        particle_size_um=dp_um,
        particle_type=particle_type,
        porosity_total=data.porosity_total,
        porosity_interstitial=data.porosity_interstitial,
    )
    eps_t = col.resolved_eps_t()

    # Mobile phase viscosity (tabulated Snyder & Dolan data)
    try:
        eta_cp = vd.mobile_phase_viscosity_cp(
            data.solvent_b, data.fraction_b, data.temperature_c
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    # Diffusion coefficient — resolve the analyte-size mode first. MW only
    # affects the optimal flow (Dm ~ MW^-0.6); h_min and N are independent.
    compound_mws: list[float] = []
    compound_names: list[str] = []
    if data.analyte_mode == "compound" and data.compound_ids:
        from sqlalchemy import select as _select

        from app.models.compound import Compound

        result = await db.execute(
            _select(Compound).where(Compound.id.in_(data.compound_ids))
        )
        found = {c.id: c for c in result.scalars()}
        for cid in data.compound_ids:
            cpd = found.get(cid)
            if cpd is None or (
                cpd.owner_id != current.id and not cpd.is_shared and not current.is_admin
            ):
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, f"Compound {cid} not found"
                )
            if cpd.mw is None:
                notes.append(f"Compound '{cpd.name}' has no MW — skipped")
                continue
            compound_mws.append(cpd.mw)
            compound_names.append(cpd.name)
        if not compound_mws:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "None of the selected compounds have a molecular weight",
            )

    mws: list[float]
    mw_source: str
    if data.dm_m2_s:
        mws, mw_source = [], "dm_override"
        notes.append("Dm supplied directly — analyte MW inputs not used")
    elif data.analyte_mode == "compound" and compound_mws:
        mws, mw_source = compound_mws, "compound"
    elif data.analyte_mode == "mz" and data.mz:
        try:
            mws = [vd.mz_to_neutral_mw(data.mz, data.charge)]
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        mw_source = "mz"
        notes.append(
            f"Neutral mass {mws[0]:.1f} Da from m/z {data.mz} "
            f"(charge {data.charge:+d}, proton adducts assumed)"
        )
    elif data.analyte_mode == "mw_range" and data.mw_min and data.mw_max:
        lo, hi = min(data.mw_min, data.mw_max), max(data.mw_min, data.mw_max)
        mws, mw_source = [lo, hi], "mw_range"
    elif data.analyte_mw:
        mws, mw_source = [data.analyte_mw], "mw"
    else:
        mws = [vd.DEFAULT_ANALYTE_MW]
        mw_source = "typical"
        notes.append(
            f"No analyte size given — using typical small-molecule MW "
            f"{vd.DEFAULT_ANALYTE_MW:.0f} Da. Optimal flow scales ~MW^-0.6, "
            f"so this is a weak assumption."
        )

    if mws:
        dm_per_mw = {
            mw: vd.wilke_chang_dm_m2_s(
                mw, data.solvent_b, data.fraction_b, data.temperature_c, eta_cp
            )
            for mw in set(mws)
        }
        # Representative MW = geometric mean of the extremes (log-space
        # centre, matching the MW^-0.6 dependence of Dm).
        mw_rep = math.sqrt(min(mws) * max(mws))
        dm = dm_per_mw[min(mws, key=lambda m: abs(m - mw_rep))]
        dm_extremes = (dm_per_mw[min(mws)], dm_per_mw[max(mws)])
        analytes = {
            "source": mw_source,
            "mws": sorted(set(round(m, 1) for m in mws)),
            "mw_used": round(mw_rep, 1),
            "mw_min": round(min(mws), 1),
            "mw_max": round(max(mws), 1),
            "compound_names": compound_names or None,
        }
        if len(set(mws)) > 1:
            notes.append(
                f"Analyte MW range {min(mws):.0f}–{max(mws):.0f} Da — curve "
                f"band and flow window show the spread; the headline optimum "
                f"uses the geometric-mean MW {mw_rep:.0f} Da"
            )
    else:
        dm = data.dm_m2_s
        dm_extremes = None
        analytes = {
            "source": mw_source,
            "mws": [],
            "mw_used": None,
            "mw_min": None,
            "mw_max": None,
            "compound_names": None,
        }

    a, b, c = col.coeffs()

    # Efficiency optimum
    opt_eff = vd.optimize_efficiency(col, dm, eta_cp, data.max_pressure_bar)
    notes.extend(opt_eff.notes)

    # Speed optimum (kinetic) if target plates requested
    opt_speed = None
    if data.target_plates:
        opt_speed = vd.optimize_speed(
            col, dm, eta_cp, data.target_plates, data.max_pressure_bar
        )
        notes.extend(opt_speed.notes)

    # Flow range for the curve
    f_lo = data.flow_min_ml_min or max(0.02, opt_eff.flow_ml_min * 0.1)
    if data.flow_max_ml_min:
        f_hi = data.flow_max_ml_min
    else:
        # Cover 4x optimum, capped where pressure hits 1.2x the limit
        f_press = opt_eff.flow_ml_min * (
            data.max_pressure_bar * 1.2 / max(opt_eff.pressure_bar, 1.0)
        )
        f_hi = max(opt_eff.flow_ml_min * 4.0, 0.1)
        if opt_eff.pressure_bar > 0:
            f_hi = min(f_hi, max(f_press, opt_eff.flow_ml_min * 1.5))
    if f_hi <= f_lo:
        f_hi = f_lo * 4.0

    band = dm_extremes if (dm_extremes and dm_extremes[0] != dm_extremes[1]) else None
    curve = vd.van_deemter_curve(col, dm, eta_cp, f_lo, f_hi, data.points, band_dm=band)

    # Optimal-flow window across the analyte MW extremes (only meaningful
    # when more than one MW was resolved).
    flow_window = None
    if band is not None:
        a_, b_, c_ = col.coeffs()
        u_lo = vd.optimal_velocity_mm_s(dp_um, min(band), a_, b_, c_)
        u_hi = vd.optimal_velocity_mm_s(dp_um, max(band), a_, b_, c_)
        flow_window = {
            "low_flow_ml_min": round(
                vd.linear_velocity_to_flow(u_lo, id_mm, eps_t), 4
            ),
            "high_flow_ml_min": round(
                vd.linear_velocity_to_flow(u_hi, id_mm, eps_t), 4
            ),
        }

    # Diameter map
    ids = tuple(data.diameter_ids_mm) if data.diameter_ids_mm else vd.STANDARD_IDS_MM
    dmap = vd.diameter_map(col, dm, eta_cp, data.current_flow_ml_min, ids)

    # Assessment of a supplied current flow
    assessment = None
    if data.current_flow_ml_min:
        assessment = vd.assess_flow(col, dm, eta_cp, data.current_flow_ml_min)
        if assessment["pressure_bar"] > data.max_pressure_bar:
            notes.append(
                f"Current flow {data.current_flow_ml_min} mL/min gives "
                f"{assessment['pressure_bar']:.0f} bar > limit "
                f"{data.max_pressure_bar:.0f} bar"
            )

    return VanDeemterOut(
        column={
            "label": column_label,
            "length_mm": length_mm,
            "inner_diameter_mm": id_mm,
            "particle_size_um": dp_um,
            "porosity_total": eps_t,
            "porosity_interstitial": data.porosity_interstitial,
            "holdup_volume_ml": round(
                vd.holdup_volume_ml(id_mm, length_mm, eps_t), 4
            ),
        },
        particle_type=particle_type,
        coefficients={"a": a, "b": b, "c": c},
        solvent={
            "solvent_b": data.solvent_b,
            "fraction_b": data.fraction_b,
            "temperature_c": data.temperature_c,
        },
        analytes=analytes,
        flow_window=flow_window,
        dm_m2_s=dm,
        viscosity_cp=eta_cp,
        curve=[p.to_dict() for p in curve],
        optimum_efficiency=opt_eff.to_dict(),
        optimum_speed=opt_speed.to_dict() if opt_speed else None,
        current_assessment=assessment,
        diameter_map=[r.to_dict() for r in dmap],
        notes=notes,
    )


# --- F15: Mobile Phase Editor / Buffer Calculator ---


@router.post("/buffer/calculate", response_model=BufferCalcOut)
async def calculate_buffer_ph(data: BufferCalcRequest, current: CurrentUser) -> BufferCalcOut:
    """Calculate pH of a buffer solution."""
    from app.core.chem.buffer_calculator import calculate_buffer_ph as _calc

    result = _calc(data.buffer, data.concentration, data.unit)
    return BufferCalcOut(**result.to_dict())


@router.post("/mobile-phase/check")
async def check_mobile_phase(data: MobilePhaseCheckRequest, current: CurrentUser) -> dict:
    """Check mobile phase compatibility."""
    from app.core.chem.buffer_calculator import MobilePhase, check_compatibility

    mp = MobilePhase(
        solvent_a=data.solvent_a,
        solvent_b=data.solvent_b,
        buffer=data.buffer,
        buffer_percent=data.buffer_percent,
        buffer_unit=data.buffer_unit,
        ph_target=data.ph_target,
    )
    return check_compatibility(mp)


@router.get("/buffers/list")
async def list_buffers(current: CurrentUser) -> dict:
    """List all available buffers with their properties."""
    from app.core.chem.buffer_calculator import list_buffers as _list
    return _list()


# --- F14: Peak Tracking ---


@router.post("/peak-tracking")
async def peak_tracking(data: PeakTrackingRequest, current: CurrentUser) -> dict:
    """Track/match peaks across multiple chromatograms."""
    from app.core.chem.peak_tracking import TrackPeak, track_peaks

    chromatograms = {
        chrom_id: [
            TrackPeak(
                rt_min=p.rt_min,
                area=p.area,
                height=p.height,
                width_min=p.width_min,
                uv_spectrum=p.uv_spectrum,
                compound_name=p.compound_name,
            )
            for p in peaks
        ]
        for chrom_id, peaks in data.chromatograms.items()
    }

    result = track_peaks(
        chromatograms,
        rt_tolerance_min=data.rt_tolerance_min,
        area_tolerance_pct=data.area_tolerance_pct,
        min_confidence=data.min_confidence,
        solvent_front_rt_min=data.solvent_front_rt_min,
        min_area=data.min_area,
    )

    return result.to_dict()


@router.post("/robustness")
async def method_robustness(data: dict, current: CurrentUser) -> dict:
    """Analyze method robustness by perturbing pH, temperature, and flow."""
    smiles_list = data.get("smiles_list", [])
    gradient_table = data.get("gradient_table", [])
    flow_rate = data.get("flow_rate_ml_min", 0.4)
    ph = data.get("ph", 2.7)
    temperature_c = data.get("temperature_c", 30.0)
    column_type = data.get("column_type", "C18")

    if not smiles_list or not gradient_table:
        raise HTTPException(status_code=400, detail="smiles_list and gradient_table are required")

    result = method_service.analyze_robustness(
        smiles_list=smiles_list,
        gradient_table=gradient_table,
        flow_rate_ml_min=flow_rate,
        ph=ph,
        temperature_c=temperature_c,
        column_type=column_type,
    )
    return result


@router.post("", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def create_method(data: MethodCreate, db: DBSession, current: CurrentUser) -> MethodOut:
    method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(method)


@router.get("", response_model=list[MethodOut])
async def list_methods(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[MethodOut]:
    # All users see all methods (collaborative library)
    items = await method_service.list_methods(db, None, limit, offset)
    return [MethodOut.model_validate(m) for m in items]


# --- Static path segments (MUST be before /{method_id}) ---


# --- Method Templates ---

@router.get("/templates/list")
async def list_method_templates(current: CurrentUser, category: str | None = Query(None)) -> list[dict]:
    """List available method templates."""
    templates = list_templates(category)
    return [template_to_dict(t) for t in templates]


@router.get("/templates/categories")
async def list_template_categories(current: CurrentUser) -> list[str]:
    """List template categories."""
    return get_categories()


@router.post("/templates/{template_id}/apply", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def apply_template(
    template_id: str,
    db: DBSession,
    current: CurrentUser,
    name: str | None = Query(None),
) -> MethodOut:
    """Create a method from a template (built-in or user-created)."""
    # First check built-in templates
    template = get_template(template_id)
    if template is not None:
        gradient_table = template_to_gradient_table(template)
        data = MethodCreate(
            name=name or template.name,
            column_type=template.column_type,
            column_dims={
                "length_mm": template.column_length_mm,
                "particle_size_um": template.particle_size_um,
            },
            mobile_phase_a=template.mobile_phase_a,
            mobile_phase_b=template.mobile_phase_b,
            additive=template.additive,
            ph=template.ph,
            gradient_table=gradient_table,
            flow_rate_ml_min=template.flow_rate_ml_min,
            temperature_c=template.temperature_c,
        )
        method = await method_service.create_method(db, current.id, data)
        return MethodOut.model_validate(method)

    # Check user-created templates
    import uuid as uuid_mod

    from sqlalchemy import select

    from app.models.user_method_template import UserMethodTemplate

    try:
        tmpl_uuid = uuid_mod.UUID(template_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")

    stmt = select(UserMethodTemplate).where(UserMethodTemplate.id == tmpl_uuid)
    result = await db.execute(stmt)
    user_tmpl = result.scalar_one_or_none()
    if user_tmpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if user_tmpl.owner_id != current.id and not user_tmpl.is_shared:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    # Build gradient table from template params
    t_total = user_tmpl.gradient_time_min * 60
    gradient_table = [
        {"time_s": 0, "percent_b": user_tmpl.percent_b_start},
        {"time_s": 60, "percent_b": user_tmpl.percent_b_start},
        {"time_s": t_total - 120, "percent_b": user_tmpl.percent_b_end},
        {"time_s": t_total, "percent_b": user_tmpl.percent_b_end},
    ]
    data = MethodCreate(
        name=name or user_tmpl.name,
        column_type=user_tmpl.column_type,
        column_dims={
            "length_mm": user_tmpl.column_length_mm,
            "particle_size_um": user_tmpl.particle_size_um,
        },
        mobile_phase_a=user_tmpl.mobile_phase_a,
        mobile_phase_b=user_tmpl.mobile_phase_b,
        additive=user_tmpl.additive,
        ph=user_tmpl.ph,
        gradient_table=gradient_table,
        flow_rate_ml_min=user_tmpl.flow_rate_ml_min,
        temperature_c=user_tmpl.temperature_c,
    )
    method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(method)


# --- User-Created Template CRUD ---


@router.get("/templates/user/list", response_model=list[UserTemplateOut])
async def list_user_templates(
    db: DBSession,
    current: CurrentUser,
) -> list[UserTemplateOut]:
    """List user-created templates (own + shared)."""
    from sqlalchemy import select

    from app.models.user_method_template import UserMethodTemplate

    stmt = select(UserMethodTemplate).where(
        (UserMethodTemplate.owner_id == current.id) | (UserMethodTemplate.is_shared == True)
    ).order_by(UserMethodTemplate.created_at.desc())
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return [UserTemplateOut.model_validate(t) for t in templates]


@router.post("/templates/user/create", response_model=UserTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_user_template(
    data: UserTemplateCreate,
    db: DBSession,
    current: CurrentUser,
) -> UserTemplateOut:
    """Create a new user-defined method template."""
    from app.models.user_method_template import UserMethodTemplate

    template = UserMethodTemplate(
        owner_id=current.id,
        name=data.name,
        category=data.category,
        description=data.description,
        column_type=data.column_type,
        mobile_phase_a=data.mobile_phase_a,
        mobile_phase_b=data.mobile_phase_b,
        additive=data.additive,
        ph=data.ph,
        percent_b_start=data.percent_b_start,
        percent_b_end=data.percent_b_end,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
        temperature_c=data.temperature_c,
        column_length_mm=data.column_length_mm,
        particle_size_um=data.particle_size_um,
        is_shared=data.is_shared,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return UserTemplateOut.model_validate(template)


@router.patch("/templates/user/{template_id}", response_model=UserTemplateOut)
async def update_user_template(
    template_id: uuid.UUID,
    data: UserTemplateUpdate,
    db: DBSession,
    current: CurrentUser,
) -> UserTemplateOut:
    """Update an existing user-created template."""
    from sqlalchemy import select

    from app.models.user_method_template import UserMethodTemplate

    stmt = select(UserMethodTemplate).where(UserMethodTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if template.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)
    return UserTemplateOut.model_validate(template)


@router.delete("/templates/user/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_template(
    template_id: uuid.UUID,
    db: DBSession,
    current: CurrentUser,
) -> None:
    """Delete a user-created template."""
    from sqlalchemy import select

    from app.models.user_method_template import UserMethodTemplate

    stmt = select(UserMethodTemplate).where(UserMethodTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if template.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    await db.delete(template)
    await db.commit()


# --- Method Sharing (public route) ---

@router.get("/shared/{token}", response_model=MethodOut)
async def get_shared_method(token: str, db: DBSession) -> MethodOut:
    """Get a shared method by token (public, no auth required)."""
    from sqlalchemy import select

    from app.models.method import Method

    stmt = select(Method).where(Method.share_token == token)
    result = await db.execute(stmt)
    method = result.scalar_one_or_none()
    if method is None or not method.is_shared:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared method not found")
    return MethodOut.model_validate(method)


# --- Parameterized routes (MUST be last) ---


@router.get("/{method_id}", response_model=MethodOut)
async def get_method(method_id: uuid.UUID, db: DBSession, current: CurrentUser) -> MethodOut:
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id is not None and method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return MethodOut.model_validate(method)


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_method(method_id: uuid.UUID, db: DBSession, current: CurrentUser) -> None:
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    await method_service.delete_method(db, method_id)


@router.post("/{method_id}/share", response_model=MethodOut)
async def share_method(
    method_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Generate a share token for a method."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    method.is_shared = True
    if not method.share_token:
        method.share_token = secrets.token_urlsafe(16)
    await db.commit()
    await db.refresh(method)
    return MethodOut.model_validate(method)


@router.post("/{method_id}/unshare", response_model=MethodOut)
async def unshare_method(
    method_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Revoke sharing for a method (disables the share link)."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    method.is_shared = False
    method.share_token = None
    await db.commit()
    await db.refresh(method)
    return MethodOut.model_validate(method)


@router.post("/{method_id}/compounds", response_model=MethodOut)
async def add_method_compound(
    method_id: uuid.UUID, data: MethodCompoundAdd, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Append a compound to an existing method's compound list (owner or admin)."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if method.owner_id != current.id and not current.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    from app.core.chem.parser import ChemParseError, parse_mol
    try:
        parse_mol(data.smiles)
    except ChemParseError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid SMILES") from None
    if data.compound_id is not None:
        compound = await compound_service.get_compound(db, data.compound_id)
        if compound is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Compound not found")
        if (
            compound.owner_id is not None
            and compound.owner_id != current.id
            and not compound.is_shared
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
        if compound.smiles and compound.smiles != data.smiles:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "SMILES does not match the saved compound"
            )
    await method_service.add_compound_to_method(
        db, method, data.smiles, name=data.name, compound_id=data.compound_id
    )
    return MethodOut.model_validate(method)


@router.post("/{method_id}/fork", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def fork_method(
    method_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Copy a method (e.g. a shared one) into the current user's account."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")
    if (method.owner_id is not None and method.owner_id != current.id
            and not method.is_shared):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    data = MethodCreate(
        name=f"{method.name or 'Method'} (copy)",
        column_type=method.column_type,
        column_dims=method.column_dims,
        mobile_phase_a=method.mobile_phase_a,
        mobile_phase_b=method.mobile_phase_b,
        additive=method.additive,
        ph=method.ph,
        gradient_table=method.gradient_table,
        flow_rate_ml_min=method.flow_rate_ml_min,
        temperature_c=method.temperature_c,
    )
    new_method = await method_service.create_method(db, current.id, data)
    return MethodOut.model_validate(new_method)

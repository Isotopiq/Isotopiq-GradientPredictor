"""Method routes: suggest, CRUD, gradient simulation, chromatogram, templates, sharing."""
from __future__ import annotations

import uuid
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.core.rules.templates import (
    get_categories,
    get_template,
    list_templates,
    template_to_dict,
    template_to_gradient_table,
)
from app.schemas.method import (
    ChromatogramOut,
    ChromatogramRequest,
    GradientSimulateOut,
    GradientSimulateRequest,
    MethodCreate,
    MethodOut,
    MethodSuggestionOut,
    MethodSuggestionRequest,
    MultiCompoundSuggestionRequest,
    MultiCompoundSuggestionOut,
    OptimizeGradientRequest,
    OptimizeGradientOut,
    UserTemplateCreate,
    UserTemplateUpdate,
    UserTemplateOut,
    KnownCompoundRTSchema,
    PredictionEquationRequest,
    PredictionEquationOut,
    PredictRTRequest,
    PredictRTOut,
    CalibrationPointSchema,
    ModelSelectionRequest,
    ModelSelectionOut,
    PhDistributionRequest,
    PhDistributionOut,
    PhSuitabilityRequest,
    PhSuitabilityOut,
    ResolutionMap1DRequest,
    ResolutionMap1DOut,
    ResolutionMap2DRequest,
    ResolutionMap2DOut,
    TernaryOptimizeRequest,
    TernaryOptimizeOut,
    ColumnSpecSchema,
    MethodTransferRequest,
    MethodTransferOut,
    BufferCalcRequest,
    BufferCalcOut,
    MobilePhaseCheckRequest,
    PeakTrackingRequest,
)
from app.services import method_service

router = APIRouter(prefix="/methods", tags=["methods"])


# --- Action routes (no path params, safe to be first) ---


@router.post("/suggest", response_model=MethodSuggestionOut)
async def suggest_method(data: MethodSuggestionRequest) -> MethodSuggestionOut:
    try:
        result = method_service.suggest(data)
    except method_service.MethodServiceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MethodSuggestionOut.model_validate(result)


@router.post("/gradient/simulate", response_model=GradientSimulateOut)
async def simulate_gradient(data: GradientSimulateRequest) -> GradientSimulateOut:
    result = method_service.simulate_gradient(data)
    return GradientSimulateOut.model_validate(result)


@router.post("/chromatogram", response_model=ChromatogramOut)
async def simulate_chromatogram(data: ChromatogramRequest) -> ChromatogramOut:
    result = method_service.simulate_chromatogram_from_request(data)
    return ChromatogramOut.model_validate(result)


@router.post("/suggest-multi", response_model=MultiCompoundSuggestionOut)
async def suggest_multi_method(data: MultiCompoundSuggestionRequest) -> MultiCompoundSuggestionOut:
    result = method_service.suggest_multi(
        smiles_list=data.smiles_list,
        ionization_mode=data.ionization_mode,
        retention_goal=data.retention_goal,
        gradient_time_min=data.gradient_time_min,
        flow_rate_ml_min=data.flow_rate_ml_min,
        column_type=data.column_type,
    )
    return MultiCompoundSuggestionOut.model_validate(result)


@router.post("/optimize-gradient", response_model=OptimizeGradientOut)
async def optimize_gradient(data: OptimizeGradientRequest) -> OptimizeGradientOut:
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
async def predict_adducts(data: dict) -> dict:
    """Predict expected m/z values for common ESI adducts from SMILES."""
    from app.core.chem.parser import ChemParseError, parse_mol
    from app.core.chem.descriptors import predict_adducts as compute_adducts
    from rdkit.Chem import Descriptors

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
async def calculate_dwell_volume(data: dict) -> dict:
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
async def build_prediction_equation(data: PredictionEquationRequest) -> PredictionEquationOut:
    """Build a retention prediction equation from >=5 known compounds."""
    from app.core.ml.prediction_equation import (
        KnownCompoundRT,
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
async def predict_rt(data: PredictRTRequest) -> PredictRTOut:
    """Predict retention time for a new compound using a fitted equation."""
    from app.core.ml.prediction_equation import PredictionEquation, predict_rt as _predict

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
async def model_selection(data: ModelSelectionRequest) -> ModelSelectionOut:
    """Fit linear/quadratic/log-log models and suggest the best one."""
    from app.core.ml.model_selection import (
        CalibrationPoint,
        GradientModel,
        fit_model,
        evaluate_fit,
        suggest_best_model,
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
async def ph_distribution(data: PhDistributionRequest) -> PhDistributionOut:
    """Compute ionic species distribution across pH range for a compound."""
    from app.core.chem.ph_selector import ph_distribution as _ph_dist

    try:
        result = _ph_dist(data.smiles, data.ph_min, data.ph_max, data.steps, data.logp)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PhDistributionOut(**result.to_dict())


@router.post("/ph-suitability", response_model=PhSuitabilityOut)
async def ph_suitability(data: PhSuitabilityRequest) -> PhSuitabilityOut:
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
async def resolution_map_1d(data: ResolutionMap1DRequest) -> ResolutionMap1DOut:
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
async def resolution_map_2d(data: ResolutionMap2DRequest) -> ResolutionMap2DOut:
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
async def ternary_optimize(data: TernaryOptimizeRequest) -> TernaryOptimizeOut:
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
async def method_transfer(data: MethodTransferRequest) -> MethodTransferOut:
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


# --- F15: Mobile Phase Editor / Buffer Calculator ---


@router.post("/buffer/calculate", response_model=BufferCalcOut)
async def calculate_buffer_ph(data: BufferCalcRequest) -> BufferCalcOut:
    """Calculate pH of a buffer solution."""
    from app.core.chem.buffer_calculator import calculate_buffer_ph as _calc

    result = _calc(data.buffer, data.concentration, data.unit)
    return BufferCalcOut(**result.to_dict())


@router.post("/mobile-phase/check")
async def check_mobile_phase(data: MobilePhaseCheckRequest) -> dict:
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
async def list_buffers() -> dict:
    """List all available buffers with their properties."""
    from app.core.chem.buffer_calculator import list_buffers as _list
    return _list()


# --- F14: Peak Tracking ---


@router.post("/peak-tracking")
async def peak_tracking(data: PeakTrackingRequest) -> dict:
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
async def method_robustness(data: dict) -> dict:
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
    items = await method_service.list_methods(db, current.id, limit, offset)
    return [MethodOut.model_validate(m) for m in items]


# --- Static path segments (MUST be before /{method_id}) ---


# --- Method Templates ---

@router.get("/templates/list")
async def list_method_templates(category: str | None = Query(None)) -> list[dict]:
    """List available method templates."""
    templates = list_templates(category)
    return [template_to_dict(t) for t in templates]


@router.get("/templates/categories")
async def list_template_categories() -> list[str]:
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
    from sqlalchemy import select
    from app.models.user_method_template import UserMethodTemplate
    import uuid as uuid_mod

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


@router.post("/{method_id}/fork", response_model=MethodOut, status_code=status.HTTP_201_CREATED)
async def fork_method(
    method_id: uuid.UUID, db: DBSession, current: CurrentUser
) -> MethodOut:
    """Copy a method (e.g. a shared one) into the current user's account."""
    method = await method_service.get_method(db, method_id)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Method not found")

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

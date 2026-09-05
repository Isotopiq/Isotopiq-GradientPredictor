"""Method schemas."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class GradientPoint(BaseModel):
    time_s: float
    percent_b: float


class MethodCreate(BaseModel):
    name: str | None = None
    column_type: str
    column_dims: dict[str, Any] | None = None
    mobile_phase_a: str | None = None
    mobile_phase_b: str | None = None
    additive: str | None = None
    ph: float | None = None
    gradient_table: list[dict[str, Any]] | None = None
    flow_rate_ml_min: float | None = None
    temperature_c: float | None = None
    method_signature: str | None = None
    compounds_smiles: list[str] | None = None
    dwell_volume_ml: float | None = None
    dead_volume_ml: float | None = None


class MethodOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None
    name: str | None = None
    column_type: str
    column_dims: dict[str, Any] | None = None
    mobile_phase_a: str | None = None
    mobile_phase_b: str | None = None
    additive: str | None = None
    ph: float | None = None
    gradient_table: list[dict[str, Any]] | None = None
    flow_rate_ml_min: float | None = None
    temperature_c: float | None = None
    method_signature: str | None = None
    is_shared: bool = False
    share_token: str | None = None
    compounds_smiles: list[str] | None = None
    dwell_volume_ml: float | None = None
    dead_volume_ml: float | None = None


class MethodSuggestionRequest(BaseModel):
    smiles: str | None = None
    inchi: str | None = None
    molfile: str | None = None
    ionization_mode: str = "ESI+"
    retention_goal: str = "neutral"
    gradient_time_min: float = 20.0
    flow_rate_ml_min: float = 0.4
    column_type: str | None = None  # override the heuristic column choice


class ColumnSuggestionOut(BaseModel):
    column_type: str
    rationale: str
    alternatives: list[str]


class PhSuggestionOut(BaseModel):
    recommended_ph: float
    rationale: str
    warning_zones: list[tuple[float, float]]


class AdditiveSuggestionOut(BaseModel):
    additive: str
    rationale: str
    alternatives: list[str]


class MethodSuggestionOut(BaseModel):
    column: ColumnSuggestionOut
    ph: PhSuggestionOut
    additive: AdditiveSuggestionOut
    gradient: dict
    pka_values: list[float]
    logd_at_recommended_ph: float
    ionizable: bool
    permanently_charged: bool
    descriptors: dict


class GradientSimulateRequest(BaseModel):
    gradient_table: list[dict[str, Any]]
    flow_rate_ml_min: float = 0.4
    column_void_volume_ml: float = 0.4
    logp: float = 2.0
    mw: float = 200.0
    tpsa: float = 0.0
    hbd: int = 0
    hba: int = 0
    column_type: str = "C18"
    column_id: str | None = None  # commercial column ID for PIRM
    smiles: str | None = None  # for multi-pKa logD calculation
    ph: float | None = None  # for logD adjustment
    calibration_runs: list[dict[str, Any]] | None = None
    dwell_volume_ml: float | None = None  # F1: system dwell volume
    dead_volume_ml: float | None = None  # F1: column dead volume
    retention_model: str | None = None  # override model selection
    retention_mechanism: str | None = None  # override mechanism


class GradientSimulateOut(BaseModel):
    predicted_rt_s: float
    gradient_table: list[dict[str, Any]]
    method: str  # "lss_fit" | "heuristic" | "pirm"
    confidence: float | None = None
    extrapolating: bool | None = None
    rt_lower_s: float | None = None
    rt_upper_s: float | None = None


class ChromatogramRequest(BaseModel):
    peaks: list[dict[str, Any]]  # [{rt_s, width_s, height, label, color}]
    total_time_s: float = 1500.0
    n_points: int = 500


class ChromatogramOut(BaseModel):
    times: list[float]
    intensities: list[float]
    peaks: list[dict[str, Any]]


class MultiCompoundSuggestionRequest(BaseModel):
    smiles_list: list[str]
    ionization_mode: str = "ESI+"
    retention_goal: str = "neutral"
    gradient_time_min: float = 25.0
    flow_rate_ml_min: float = 0.4
    column_type: str | None = None  # override the heuristic column choice


class MultiCompoundSuggestionOut(BaseModel):
    per_compound: list[dict[str, Any]]
    gradient: dict
    resolution_matrix: list[dict[str, Any]]
    co_elution_count: int


class SuitabilityCriteriaSchema(BaseModel):
    min_resolution: float = 1.5
    max_run_time_min: float = 60.0
    min_k: float = 0.5
    max_k: float = 20.0
    min_peak_height_ratio: float | None = None


class OptimizeGradientRequest(BaseModel):
    smiles_list: list[str]
    flow_rate_ml_min: float = 0.4
    gradient_time_min: float = 20.0
    column_type: str | None = None
    ph: float = 2.7
    temperature_c: float = 30.0
    suitability: SuitabilityCriteriaSchema | None = None  # F7


class OptimizeGradientOut(BaseModel):
    per_compound: list[dict[str, Any]]
    gradient: dict
    resolution_matrix: list[dict[str, Any]]
    co_elution_count: int
    optimization: dict[str, Any] = {}
    suitability: dict[str, Any] | None = None  # F7


# --- User Method Templates ---


class UserTemplateCreate(BaseModel):
    name: str
    category: str = "Custom"
    description: str | None = None
    column_type: str
    mobile_phase_a: str | None = None
    mobile_phase_b: str | None = None
    additive: str | None = None
    ph: float | None = None
    percent_b_start: float = 5.0
    percent_b_end: float = 95.0
    gradient_time_min: float = 20.0
    flow_rate_ml_min: float = 0.4
    temperature_c: float = 30.0
    column_length_mm: int = 100
    particle_size_um: float = 1.8
    is_shared: bool = False


class UserTemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    column_type: str | None = None
    mobile_phase_a: str | None = None
    mobile_phase_b: str | None = None
    additive: str | None = None
    ph: float | None = None
    percent_b_start: float | None = None
    percent_b_end: float | None = None
    gradient_time_min: float | None = None
    flow_rate_ml_min: float | None = None
    temperature_c: float | None = None
    column_length_mm: int | None = None
    particle_size_um: float | None = None
    is_shared: bool | None = None


class UserTemplateOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID | None = None
    name: str
    category: str
    description: str | None = None
    column_type: str
    mobile_phase_a: str | None = None
    mobile_phase_b: str | None = None
    additive: str | None = None
    ph: float | None = None
    percent_b_start: float
    percent_b_end: float
    gradient_time_min: float
    flow_rate_ml_min: float
    temperature_c: float
    column_length_mm: int
    particle_size_um: float
    is_shared: bool = False


# --- F6: Prediction Equation Mode ---


class KnownCompoundRTSchema(BaseModel):
    smiles: str
    rt_min: float
    column_type: str = "C18"
    ph: float = 2.7
    gradient_time_min: float = 20.0
    flow_rate_ml_min: float = 0.4
    temperature_c: float = 30.0


class PredictionEquationRequest(BaseModel):
    compounds: list[KnownCompoundRTSchema]
    descriptor_names: list[str] | None = None


class PredictionEquationOut(BaseModel):
    coefficients: dict[str, float]
    intercept: float
    r: float
    r_squared: float
    std_dev: float
    n: int
    descriptor_names: list[str]
    descriptor_means: dict[str, float]
    descriptor_stds: dict[str, float]


class PredictRTRequest(BaseModel):
    coefficients: dict[str, float]
    intercept: float
    descriptor_names: list[str]
    descriptor_means: dict[str, float]
    descriptor_stds: dict[str, float]
    std_dev: float
    r: float
    smiles: str
    ph: float = 2.7


class PredictRTOut(BaseModel):
    predicted_rt_min: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    in_applicability_domain: bool
    extrapolation_warnings: list[str]


# --- F9: Model Selection ---


class CalibrationPointSchema(BaseModel):
    gradient_time_min: float
    observed_rt_min: float
    compound_id: str | None = None


class ModelSelectionRequest(BaseModel):
    points: list[CalibrationPointSchema]
    bad_peaks_threshold: float = 0.75


class ModelSelectionOut(BaseModel):
    best_model: str
    best_fit: dict[str, Any]
    all_models: list[dict[str, Any]]
    best_quality: dict[str, Any]


# --- F10: pH Selector ---


class PhDistributionRequest(BaseModel):
    smiles: str
    ph_min: float = 0.0
    ph_max: float = 14.0
    steps: int = 100
    logp: float = 2.0


class PhDistributionOut(BaseModel):
    ph_values: list[float]
    species_fractions: list[list[float]]
    net_charges: list[float]
    pka_sites: list[dict[str, Any]]
    smiles: str


class PhSuitabilityRequest(BaseModel):
    smiles_list: list[str]
    ph_min: float = 2.0
    ph_max: float = 10.0
    steps: int = 80
    buffer_count: int = 4


class PhSuitabilityOut(BaseModel):
    ph_values: list[float]
    zones: list[str]
    min_logd: list[float]
    recommended_phs: list[float]
    buffer_suggestions: list[dict[str, Any]]


# --- F4/F5: Resolution Maps ---


class ResolutionMap1DRequest(BaseModel):
    smiles_list: list[str]
    variable: str  # gradient_time, ph, temperature, flow_rate, percent_b_start, percent_b_end
    var_min: float
    var_max: float
    steps: int = 20
    ph: float = 2.7
    temperature: float = 30.0
    flow_rate: float = 0.4
    gradient_time: float = 20.0
    percent_b_start: float = 5.0
    percent_b_end: float = 95.0
    column_type: str = "C18"
    column_void_volume_ml: float = 0.4
    dwell_volume_ml: float | None = None
    dead_volume_ml: float | None = None
    suitability: SuitabilityCriteriaSchema | None = None


class ResolutionMap1DOut(BaseModel):
    variable: str
    x_values: list[float]
    min_rs: list[float]
    per_compound_rts: list[list[float]]
    co_elution_points: list[dict[str, Any]]
    suitability_scores: list[float]


class ResolutionMap2DRequest(BaseModel):
    smiles_list: list[str]
    var_x: str
    var_x_min: float
    var_x_max: float
    steps_x: int = 10
    var_y: str
    var_y_min: float
    var_y_max: float
    steps_y: int = 8
    ph: float = 2.7
    temperature: float = 30.0
    flow_rate: float = 0.4
    gradient_time: float = 20.0
    percent_b_start: float = 5.0
    percent_b_end: float = 95.0
    column_type: str = "C18"
    column_void_volume_ml: float = 0.4
    dwell_volume_ml: float | None = None
    dead_volume_ml: float | None = None
    suitability: SuitabilityCriteriaSchema | None = None


class ResolutionMap2DOut(BaseModel):
    var_x: str
    var_y: str
    x_values: list[float]
    y_values: list[float]
    rs_grid: list[list[float]]
    optimal_point: dict[str, float]
    suitability_grid: list[list[float]]


# --- F8: Ternary Solvent Optimization ---


class TernaryOptimizeRequest(BaseModel):
    smiles_list: list[str]
    solvent_a: str = "water"
    solvent_b: str = "acn"
    solvent_c: str = "meoh"
    gradient_time_min: float = 20.0
    flow_rate_ml_min: float = 0.4
    ph: float = 2.7
    temperature_c: float = 30.0
    column_type: str = "C18"
    mode: str = "ternary"  # "binary" or "ternary"
    grid_resolution: int = 5


class TernaryOptimizeOut(BaseModel):
    solvent_a: str
    solvent_b: str
    solvent_c: str
    mode: str
    optimal: dict[str, Any] | None
    points: list[dict[str, Any]]


# --- F2: Method Transfer Assistant ---


class ColumnSpecSchema(BaseModel):
    length_mm: float
    inner_diameter_mm: float
    particle_size_um: float
    dwell_volume_ml: float = 0.0
    dead_volume_ml: float = 0.0


class MethodTransferRequest(BaseModel):
    source_column: ColumnSpecSchema
    target_column: ColumnSpecSchema
    flow_rate_ml_min: float
    gradient_table: list[dict[str, Any]]
    injection_volume_ul: float = 5.0
    temperature_c: float = 30.0
    preserve_resolution: bool = True


class MethodTransferOut(BaseModel):
    column: dict[str, Any]
    flow_rate_ml_min: float
    gradient_table: list[dict[str, Any]]
    injection_volume_ul: float
    temperature_c: float
    scaling_factors: dict[str, float]
    notes: list[str]


# --- F15: Mobile Phase Editor / Buffer Calculator ---


class BufferCalcRequest(BaseModel):
    buffer: str
    concentration: float
    unit: str = "percent"  # "percent" or "mM"


class BufferCalcOut(BaseModel):
    estimated_ph: float
    buffer_name: str
    concentration_mM: float
    ms_compatible: bool
    warnings: list[str]
    recipe: str


class MobilePhaseCheckRequest(BaseModel):
    solvent_a: str = "water"
    solvent_b: str = "acn"
    buffer: str | None = None
    buffer_percent: float = 0.0
    buffer_unit: str = "percent"
    ph_target: float | None = None


# --- F14: Peak Tracking ---


class TrackPeakSchema(BaseModel):
    rt_min: float
    area: float = 0.0
    height: float = 0.0
    width_min: float = 0.0
    uv_spectrum: list[float] | None = None
    compound_name: str = ""


class PeakTrackingRequest(BaseModel):
    chromatograms: dict[str, list[TrackPeakSchema]]
    rt_tolerance_min: float = 0.15
    area_tolerance_pct: float = 50.0
    min_confidence: float = 0.3
    solvent_front_rt_min: float = 0.5
    min_area: float = 1000.0

"""Method schemas."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

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
    calibration_runs: list[dict[str, Any]] | None = None


class GradientSimulateOut(BaseModel):
    predicted_rt_s: float
    gradient_table: list[dict[str, Any]]
    method: str  # "lss_fit" | "heuristic"


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


class OptimizeGradientRequest(BaseModel):
    smiles_list: list[str]
    flow_rate_ml_min: float = 0.4
    gradient_time_min: float = 20.0
    column_type: str | None = None
    ph: float = 2.7
    temperature_c: float = 30.0


class OptimizeGradientOut(BaseModel):
    per_compound: list[dict[str, Any]]
    gradient: dict
    resolution_matrix: list[dict[str, Any]]
    co_elution_count: int
    optimization: dict[str, Any] = {}


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

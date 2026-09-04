// Type definitions mirroring backend Pydantic schemas

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  has_profile_picture: boolean;
  last_login_at: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  has_profile_picture: boolean;
  last_login_at: string | null;
  created_at: string | null;
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Compound {
  id: string;
  owner_id: string | null;
  is_shared: boolean;
  name: string | null;
  smiles: string | null;
  inchi: string | null;
  inchikey: string | null;
  molfile: string | null;
  cas: string | null;
  mw: number | null;
  logp: number | null;
  logd_at_ph: number | null;
  pka_values: number[] | null;
  tpsa: number | null;
  hbd: number | null;
  hba: number | null;
  rotatable_bonds: number | null;
  aromatic_rings: number | null;
  source: string;
}

export interface CompoundCreate {
  smiles?: string;
  inchi?: string;
  molfile?: string;
  name?: string;
  cas?: string;
  lookup?: boolean;
  source?: string;
}

export interface CompoundList {
  id: string;
  owner_id: string | null;
  name: string;
  description: string | null;
  compound_ids: string[];
  created_at?: string;
  updated_at?: string;
}

export interface CompoundListCreate {
  name: string;
  description?: string;
  compound_ids: string[];
}

export interface CompoundListUpdate {
  name?: string;
  description?: string;
  compound_ids?: string[];
}

export interface GradientPoint {
  time_s: number;
  percent_b: number;
}

export interface Method {
  id: string;
  owner_id: string | null;
  name: string | null;
  column_type: string;
  column_dims: Record<string, unknown> | null;
  mobile_phase_a: string | null;
  mobile_phase_b: string | null;
  additive: string | null;
  ph: number | null;
  gradient_table: GradientPoint[] | null;
  flow_rate_ml_min: number | null;
  temperature_c: number | null;
  method_signature: string | null;
  is_shared: boolean;
  share_token: string | null;
  compounds_smiles: string[] | null;
  dwell_volume_ml: number | null;
  dead_volume_ml: number | null;
}

export interface MethodCreate {
  name?: string;
  column_type: string;
  column_dims?: Record<string, unknown>;
  mobile_phase_a?: string;
  mobile_phase_b?: string;
  additive?: string;
  ph?: number;
  gradient_table?: GradientPoint[];
  flow_rate_ml_min?: number;
  temperature_c?: number;
  compounds_smiles?: string[];
  dwell_volume_ml?: number;
  dead_volume_ml?: number;
}

export interface ColumnSuggestion {
  column_type: string;
  rationale: string;
  alternatives: string[];
}

export interface PhSuggestion {
  recommended_ph: number;
  rationale: string;
  warning_zones: [number, number][];
}

export interface AdditiveSuggestion {
  additive: string;
  rationale: string;
  alternatives: string[];
}

export interface DescriptorInfo {
  mw: number;
  logp: number;
  tpsa: number;
  hbd: number;
  hba: number;
  rotatable_bonds: number;
  aromatic_rings: number;
  num_rings: number;
  num_heavy_atoms: number;
  num_heteroatoms: number;
  fraction_csp3: number;
}

export interface MethodSuggestion {
  column: ColumnSuggestion;
  ph: PhSuggestion;
  additive: AdditiveSuggestion;
  gradient: {
    gradient_table: GradientPoint[];
    flow_rate_ml_min: number;
    gradient_time_min: number;
    percent_b_start: number;
    percent_b_end: number;
    column_length_mm: number;
  };
  pka_values: number[];
  logd_at_recommended_ph: number;
  ionizable: boolean;
  permanently_charged: boolean;
  descriptors: DescriptorInfo;
}

export interface MethodSuggestionRequest {
  smiles?: string;
  inchi?: string;
  molfile?: string;
  ionization_mode?: string;
  retention_goal?: string;
  gradient_time_min?: number;
  flow_rate_ml_min?: number;
  column_type?: string;
}

export interface GradientSimulateRequest {
  gradient_table: GradientPoint[];
  flow_rate_ml_min?: number;
  column_void_volume_ml?: number;
  logp?: number;
  mw?: number;
  tpsa?: number;
  hbd?: number;
  hba?: number;
  column_type?: string;
  column_id?: string;
  smiles?: string;
  ph?: number;
  calibration_runs?: Array<{
    gradient_time_s: number;
    phi_start: number;
    phi_end: number;
    observed_rt_s: number;
  }>;
  dwell_volume_ml?: number;
  dead_volume_ml?: number;
}

export interface GradientSimulateResult {
  predicted_rt_s: number;
  gradient_table: GradientPoint[];
  method: string;
  confidence?: number;
  extrapolating?: boolean;
  rt_lower_s?: number;
  rt_upper_s?: number;
}

export interface ChromatogramRequest {
  peaks: Array<{
    rt_s: number;
    width_s?: number;
    height?: number;
    label?: string;
    color?: string;
  }>;
  total_time_s?: number;
  n_points?: number;
}

export interface ChromatogramResult {
  times: number[];
  intensities: number[];
  peaks: Array<{
    rt_s: number;
    width_s: number;
    height: number;
    label: string;
    color: string;
    tailing?: number;
  }>;
}

export interface Prediction {
  id: string;
  compound_id: string;
  method_id: string;
  predicted_rt_s: number | null;
  rt_lower_s: number | null;
  rt_upper_s: number | null;
  confidence: number;
  extrapolating: boolean;
  model_version: string;
}

export interface Run {
  id: string;
  compound_id: string;
  method_id: string;
  owner_id: string | null;
  observed_rt_s: number;
  peak_width_s: number | null;
  notes: string | null;
  run_date: string | null;
}

export interface ModelArtifact {
  id: string;
  column_type: string;
  method_signature: string;
  model_type: string;
  version: number;
  artifact_path: string;
  train_metrics: Record<string, unknown> | null;
  feature_schema: Record<string, unknown> | null;
  trained_at: string;
  n_samples: number;
}

export interface TrainResponse {
  artifact_id: string;
  column_type: string;
  model_type: string;
  version: number;
  n_samples: number;
  metrics: Record<string, number>;
  trained_at: string;
}

// --- New types for megaplan features ---

export interface StationaryPhase {
  carbon_load_pct: number;
  ligand_length: number;
  bonding_density_umol_m2: number;
  surface_area_m2_g: number;
  pore_size_a: number;
  endcapped: boolean;
  polar_embedded: boolean;
  particle_type: string;
  base_material: string;
  hydrophobicity_index: number;
}

export interface ColumnSpec {
  id: string;
  brand: string;
  name: string;
  chemistry: string;
  particle_size_um: number;
  length_mm: number;
  inner_diameter_mm: number;
  ph_min: number;
  ph_max: number;
  temperature_max_c: number;
  usp_code: string | null;
  notes: string;
  stationary_phase?: StationaryPhase;
}

export interface PIRMPredictionResult {
  predicted_rt_s: number;
  rt_lower_s: number;
  rt_upper_s: number;
  confidence: number;
  extrapolating: boolean;
  model_version: string;
  model_params: {
    log_k0: number;
    s: number;
    t0_s: number;
    v_void_ml: number;
    k0_breakdown: Record<string, number>;
    s_breakdown: Record<string, number>;
  };
  stationary_phase: StationaryPhase;
}

export interface MethodTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  column_type: string;
  mobile_phase_a: string;
  mobile_phase_b: string;
  additive: string;
  ph: number;
  percent_b_start: number;
  percent_b_end: number;
  gradient_time_min: number;
  flow_rate_ml_min: number;
  temperature_c: number;
  column_length_mm: number;
  particle_size_um: number;
}

export interface UserMethodTemplate {
  id: string;
  owner_id: string | null;
  name: string;
  category: string;
  description: string | null;
  column_type: string;
  mobile_phase_a: string | null;
  mobile_phase_b: string | null;
  additive: string | null;
  ph: number | null;
  percent_b_start: number;
  percent_b_end: number;
  gradient_time_min: number;
  flow_rate_ml_min: number;
  temperature_c: number;
  column_length_mm: number;
  particle_size_um: number;
  is_shared: boolean;
}

export interface UserTemplateCreate {
  name: string;
  category?: string;
  description?: string;
  column_type: string;
  mobile_phase_a?: string;
  mobile_phase_b?: string;
  additive?: string;
  ph?: number;
  percent_b_start?: number;
  percent_b_end?: number;
  gradient_time_min?: number;
  flow_rate_ml_min?: number;
  temperature_c?: number;
  column_length_mm?: number;
  particle_size_um?: number;
  is_shared?: boolean;
}

export interface PkaPlotData {
  smiles: string;
  sites: Array<{ pka: number; acid_base: string; atom_idx: number }>;
  pka_values: number[];
  logp: number;
  fractions: Array<{ ph: number; fraction_ionized: number; logd: number }>;
  recommended_ph: number;
}

export interface FeatureImportance {
  model_id: string;
  model_type: string;
  column_type: string;
  version: number;
  features: Array<{ name: string; importance: number }>;
}

export interface ModelHistory {
  column_type: string;
  method_signature: string;
  versions: Array<{
    id: string;
    version: number;
    model_type: string;
    n_samples: number;
    r2: number | null;
    rmse: number | null;
    residual_std: number | null;
    trained_at: string | null;
  }>;
}

export interface CalibrationData {
  points: Array<{
    compound_smiles: string;
    compound_name: string | null;
    predicted_rt_s: number;
    observed_rt_s: number;
    residual: number;
    model_version: string;
    confidence: number;
  }>;
  n_points: number;
  regression: {
    slope: number;
    intercept: number;
    r2: number;
    rmse: number;
  };
}

export interface Notification {
  id: string;
  type: string;
  column_type: string;
  new_run_count: number;
  last_trained_at: string | null;
  message: string;
  severity: 'info' | 'warning';
}

// --- Multi-compound method suggestion ---

export interface MultiCompoundEntry {
  index: number;
  smiles: string;
  name?: string;
  error?: string;
  column?: { column_type: string; rationale: string };
  pka_values?: number[];
  logp?: number;
  logd?: number;
  mw?: number;
  tpsa?: number;
  hbd?: number;
  hba?: number;
  rotatable_bonds?: number;
  aromatic_rings?: number;
  num_rings?: number;
  predicted_rt_s?: number;
  peak_width_s?: number;
}

export interface ResolutionPair {
  compound_a: number;
  compound_b: number;
  rt_a: number;
  rt_b: number;
  resolution: number;
  co_elution_risk: boolean;
}

export interface MultiCompoundSuggestion {
  per_compound: MultiCompoundEntry[];
  gradient: {
    gradient_table: GradientPoint[];
    flow_rate_ml_min: number;
    gradient_time_min: number;
    percent_b_start: number;
    percent_b_end: number;
    column_length_mm: number;
  };
  resolution_matrix: ResolutionPair[];
  co_elution_count: number;
}

// F7: Suitability Criteria
export interface SuitabilityCriteria {
  min_resolution: number;
  max_run_time_min: number;
  min_k: number;
  max_k: number;
  min_peak_height_ratio?: number | null;
}

export interface CriterionResult {
  name: string;
  passed: boolean;
  value: number;
  target: string;
  detail: string;
}

export interface SuitabilityEvaluation {
  overall_score: number;
  all_passed: boolean;
  criteria: CriterionResult[];
}

// F6: Prediction Equation Mode
export interface KnownCompoundRT {
  smiles: string;
  rt_min: number;
  column_type?: string;
  ph?: number;
  gradient_time_min?: number;
  flow_rate_ml_min?: number;
  temperature_c?: number;
}

export interface PredictionEquation {
  coefficients: Record<string, number>;
  intercept: number;
  r: number;
  r_squared: number;
  std_dev: number;
  n: number;
  descriptor_names: string[];
  descriptor_means: Record<string, number>;
  descriptor_stds: Record<string, number>;
}

export interface PredictionResult {
  predicted_rt_min: number;
  confidence_interval_lower: number;
  confidence_interval_upper: number;
  in_applicability_domain: boolean;
  extrapolation_warnings: string[];
}

// F9: Model Selection
export interface CalibrationPoint {
  gradient_time_min: number;
  observed_rt_min: number;
  compound_id?: string | null;
}

export interface ModelFit {
  model_type: string;
  coefficients: number[];
  r_squared: number;
  rmse: number;
  max_residual: number;
  n_points: number;
}

export interface FitQuality {
  r_squared: number;
  rmse: number;
  max_residual: number;
  bad_peaks_count: number;
  bad_peaks_threshold: number;
  residuals: number[];
}

export interface ModelSelectionResult {
  best_model: string;
  best_fit: ModelFit;
  all_models: Array<{ model: string; fit: ModelFit; quality: FitQuality }>;
  best_quality: FitQuality;
}

// F10: pH Selector
export interface PkaSite {
  pka: number;
  acid_base: string;
  atom_idx: number;
}

export interface PhDistribution {
  ph_values: number[];
  species_fractions: number[][];
  net_charges: number[];
  pka_sites: PkaSite[];
  smiles: string;
}

export interface PhSuitabilityMap {
  ph_values: number[];
  zones: string[];
  min_logd: number[];
  recommended_phs: number[];
  buffer_suggestions: Array<{
    name: string;
    pKa: number;
    range: [number, number];
    ms_compatible: boolean;
    recipe: string;
  }>;
}

// F4/F5: Resolution Maps
export interface ResolutionMap1D {
  variable: string;
  x_values: number[];
  min_rs: number[];
  per_compound_rts: number[][];
  co_elution_points: Array<{ x: number; min_rs: number }>;
  suitability_scores: number[];
}

export interface ResolutionMap2D {
  var_x: string;
  var_y: string;
  x_values: number[];
  y_values: number[];
  rs_grid: number[][];
  optimal_point: { x: number; y: number; rs: number };
  suitability_grid: number[][];
}

// F8: Ternary Solvent Optimization
export interface TernaryPoint {
  frac_a: number;
  frac_b: number;
  frac_c: number;
  min_rs: number;
}

export interface TernaryOptResult {
  solvent_a: string;
  solvent_b: string;
  solvent_c: string;
  mode: string;
  optimal: {
    frac_a: number;
    frac_b: number;
    frac_c: number;
    min_rs: number;
    rts: number[];
  } | null;
  points: TernaryPoint[];
}

// F2: Method Transfer
export interface TransferColumnSpec {
  length_mm: number;
  inner_diameter_mm: number;
  particle_size_um: number;
  dwell_volume_ml?: number;
  dead_volume_ml?: number;
}

export interface MethodTransferResult {
  column: TransferColumnSpec;
  flow_rate_ml_min: number;
  gradient_table: Array<{ time_s: number; percent_b: number }>;
  injection_volume_ul: number;
  temperature_c: number;
  scaling_factors: Record<string, number>;
  notes: string[];
}

// F3: Tanaka Column Comparison
export interface TanakaParameters {
  column_name: string;
  column_type: string;
  k_pb: number;
  alpha_ch2: number;
  alpha_t_o: number;
  alpha_c_p: number;
  alpha_b_a_76: number;
  alpha_b_a_27: number;
}

export interface ColumnComparisonResult {
  column_a: TanakaParameters;
  column_b: TanakaParameters;
  cdf: number;
  parameter_differences: Record<string, number>;
  similarity: number;
  orthogonality: number;
}

// F15: Mobile Phase Editor / Buffer Calculator
export interface BufferCalcResult {
  estimated_ph: number;
  buffer_name: string;
  concentration_mM: number;
  ms_compatible: boolean;
  warnings: string[];
  recipe: string;
}

export interface MobilePhaseCheckResult {
  ms_compatible: boolean;
  warnings: string[];
}

// F14: Peak Tracking
export interface TrackPeak {
  rt_min: number;
  area: number;
  height: number;
  width_min: number;
  uv_spectrum?: number[] | null;
  compound_name?: string;
}

export interface PeakMatch {
  peaks: Array<TrackPeak & { chromatogram_id: string }>;
  confidence: number;
  mean_rt: number;
  rt_std: number;
  mean_area: number;
  area_cv: number;
  matched: boolean;
}

export interface PeakTrackingResult {
  matches: PeakMatch[];
  unmatched: Array<TrackPeak & { chromatogram_id: string }>;
  n_chromatograms: number;
  n_matched_groups: number;
}

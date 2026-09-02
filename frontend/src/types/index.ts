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
}

export interface GradientSimulateRequest {
  gradient_table: GradientPoint[];
  flow_rate_ml_min?: number;
  column_void_volume_ml?: number;
  logp?: number;
  calibration_runs?: Array<{
    gradient_time_s: number;
    phi_start: number;
    phi_end: number;
    observed_rt_s: number;
  }>;
}

export interface GradientSimulateResult {
  predicted_rt_s: number;
  gradient_table: GradientPoint[];
  method: string;
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

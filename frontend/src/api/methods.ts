import { apiClient } from './client';
import type {
  Method,
  MethodCreate,
  MethodSuggestion,
  MethodSuggestionRequest,
  MethodTemplate,
  UserMethodTemplate,
  UserTemplateCreate,
  GradientSimulateRequest,
  GradientSimulateResult,
  ChromatogramRequest,
  ChromatogramResult,
  MultiCompoundSuggestion,
  KnownCompoundRT,
  PredictionEquation,
  PredictionResult,
  CalibrationPoint,
  ModelSelectionResult,
  PhDistribution,
  PhSuitabilityMap,
  ResolutionMap1D,
  ResolutionMap2D,
  TernaryOptResult,
  ColumnSpec,
  TransferColumnSpec,
  MethodTransferResult,
  BufferCalcResult,
  MobilePhaseCheckResult,
  TrackPeak,
  PeakTrackingResult,
} from '@/types';

export const methodsApi = {
  suggest: async (data: MethodSuggestionRequest) => {
    const { data: result } = await apiClient.post<MethodSuggestion>('/methods/suggest', data);
    return result;
  },

  suggestMulti: async (smilesList: string[], params?: {
    ionization_mode?: string;
    retention_goal?: string;
    gradient_time_min?: number;
    flow_rate_ml_min?: number;
    column_type?: string;
  }) => {
    const { data: result } = await apiClient.post<MultiCompoundSuggestion>('/methods/suggest-multi', {
      smiles_list: smilesList,
      ...params,
    });
    return result;
  },

  optimizeGradient: async (smilesList: string[], params?: {
    flow_rate_ml_min?: number;
    gradient_time_min?: number;
    column_type?: string;
    ph?: number;
    temperature_c?: number;
    suitability?: {
      min_resolution?: number;
      max_run_time_min?: number;
      min_k?: number;
      max_k?: number;
    };
  }) => {
    const { data: result } = await apiClient.post<MultiCompoundSuggestion & {
      optimization?: {
        percent_b_start: number;
        percent_b_end: number;
        gradient_time_min: number;
        min_resolution: number;
        configurations_tested: number;
      };
      suitability?: {
        overall_score: number;
        all_passed: boolean;
        criteria: Array<{
          name: string;
          passed: boolean;
          value: number;
          target: string;
          detail: string;
        }>;
      };
    }>('/methods/optimize-gradient', {
      smiles_list: smilesList,
      ...params,
    });
    return result;
  },

  simulateGradient: async (data: GradientSimulateRequest) => {
    const { data: result } = await apiClient.post<GradientSimulateResult>(
      '/methods/gradient/simulate',
      data,
    );
    return result;
  },

  simulateChromatogram: async (data: ChromatogramRequest) => {
    const { data: result } = await apiClient.post<ChromatogramResult>(
      '/methods/chromatogram',
      data,
    );
    return result;
  },

  predictAdducts: async (smiles: string) => {
    const { data: result } = await apiClient.post<{
      monoisotopic_mass: number;
      adducts: {
        positive: Array<{ adduct: string; mz: number; charge: number }>;
        negative: Array<{ adduct: string; mz: number; charge: number }>;
      };
    }>('/methods/adducts', { smiles });
    return result;
  },

  analyzeRobustness: async (params: {
    smiles_list: string[];
    gradient_table: Array<{ time_s: number; percent_b: number }>;
    flow_rate_ml_min?: number;
    ph?: number;
    temperature_c?: number;
    column_type?: string;
  }) => {
    const { data: result } = await apiClient.post<{
      perturbations: Array<{
        parameter: string;
        delta: string;
        rts: number[];
        min_resolution: number;
        resolution_change: number;
      }>;
      sensitivity_score: number;
      most_sensitive_compound: number;
      baseline_min_resolution: number;
      baseline_rts: number[];
    }>('/methods/robustness', params);
    return result;
  },

  create: async (data: MethodCreate) => {
    const { data: result } = await apiClient.post<Method>('/methods', data);
    return result;
  },

  list: async (limit = 50, offset = 0) => {
    const { data } = await apiClient.get<Method[]>('/methods', {
      params: { limit, offset },
    });
    return data;
  },

  get: async (id: string) => {
    const { data } = await apiClient.get<Method>(`/methods/${id}`);
    return data;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/methods/${id}`);
  },

  // Templates
  listTemplates: async (category?: string) => {
    const { data } = await apiClient.get<MethodTemplate[]>('/methods/templates/list', {
      params: category ? { category } : {},
    });
    return data;
  },

  templateCategories: async () => {
    const { data } = await apiClient.get<string[]>('/methods/templates/categories');
    return data;
  },

  applyTemplate: async (templateId: string, name?: string) => {
    const { data } = await apiClient.post<Method>(
      `/methods/templates/${templateId}/apply`,
      {},
      { params: name ? { name } : {} },
    );
    return data;
  },

  // Sharing
  share: async (id: string) => {
    const { data } = await apiClient.post<Method>(`/methods/${id}/share`);
    return data;
  },

  unshare: async (id: string) => {
    const { data } = await apiClient.post<Method>(`/methods/${id}/unshare`);
    return data;
  },

  getShared: async (token: string) => {
    const { data } = await apiClient.get<Method>(`/methods/shared/${token}`);
    return data;
  },

  fork: async (id: string) => {
    const { data } = await apiClient.post<Method>(`/methods/${id}/fork`);
    return data;
  },

  // User-created templates
  listUserTemplates: async () => {
    const { data } = await apiClient.get<UserMethodTemplate[]>('/methods/templates/user/list');
    return data;
  },

  createUserTemplate: async (tmpl: UserTemplateCreate) => {
    const { data } = await apiClient.post<UserMethodTemplate>('/methods/templates/user/create', tmpl);
    return data;
  },

  updateUserTemplate: async (id: string, tmpl: Partial<UserTemplateCreate>) => {
    const { data } = await apiClient.patch<UserMethodTemplate>(`/methods/templates/user/${id}`, tmpl);
    return data;
  },

  deleteUserTemplate: async (id: string) => {
    await apiClient.delete(`/methods/templates/user/${id}`);
  },

  // F6: Prediction Equation Mode
  buildPredictionEquation: async (compounds: KnownCompoundRT[], descriptorNames?: string[]) => {
    const { data } = await apiClient.post<PredictionEquation>(
      '/methods/prediction-equation/build',
      { compounds, descriptor_names: descriptorNames },
    );
    return data;
  },

  predictRT: async (params: {
    equation: PredictionEquation;
    smiles: string;
    ph?: number;
  }) => {
    const { data } = await apiClient.post<PredictionResult>(
      '/methods/prediction-equation/predict',
      {
        coefficients: params.equation.coefficients,
        intercept: params.equation.intercept,
        descriptor_names: params.equation.descriptor_names,
        descriptor_means: params.equation.descriptor_means,
        descriptor_stds: params.equation.descriptor_stds,
        std_dev: params.equation.std_dev,
        r: params.equation.r,
        smiles: params.smiles,
        ph: params.ph ?? 2.7,
      },
    );
    return data;
  },

  // F9: Model Selection
  modelSelection: async (points: CalibrationPoint[], badPeaksThreshold?: number) => {
    const { data } = await apiClient.post<ModelSelectionResult>(
      '/methods/model-selection',
      { points, bad_peaks_threshold: badPeaksThreshold ?? 0.75 },
    );
    return data;
  },

  // F10: pH Selector
  phDistribution: async (smiles: string, phMin?: number, phMax?: number, steps?: number, logp?: number) => {
    const { data } = await apiClient.post<PhDistribution>(
      '/methods/ph-distribution',
      { smiles, ph_min: phMin ?? 0, ph_max: phMax ?? 14, steps: steps ?? 100, logp: logp ?? 2.0 },
    );
    return data;
  },

  phSuitability: async (smilesList: string[], phMin?: number, phMax?: number, bufferCount?: number) => {
    const { data } = await apiClient.post<PhSuitabilityMap>(
      '/methods/ph-suitability',
      { smiles_list: smilesList, ph_min: phMin ?? 2, ph_max: phMax ?? 10, buffer_count: bufferCount ?? 4 },
    );
    return data;
  },

  // F4: 1D Resolution Map
  resolutionMap1D: async (params: {
    smiles_list: string[];
    variable: string;
    var_min: number;
    var_max: number;
    steps?: number;
    ph?: number;
    temperature?: number;
    flow_rate?: number;
    gradient_time?: number;
    percent_b_start?: number;
    percent_b_end?: number;
    column_type?: string;
  }) => {
    const { data } = await apiClient.post<ResolutionMap1D>('/methods/resolution-map/1d', params);
    return data;
  },

  // F5: 2D Resolution Map
  resolutionMap2D: async (params: {
    smiles_list: string[];
    var_x: string;
    var_x_min: number;
    var_x_max: number;
    steps_x?: number;
    var_y: string;
    var_y_min: number;
    var_y_max: number;
    steps_y?: number;
    ph?: number;
    temperature?: number;
    flow_rate?: number;
    gradient_time?: number;
    percent_b_start?: number;
    percent_b_end?: number;
    column_type?: string;
  }) => {
    const { data } = await apiClient.post<ResolutionMap2D>('/methods/resolution-map/2d', params);
    return data;
  },

  // F8: Ternary Solvent Optimization
  ternaryOptimize: async (params: {
    smiles_list: string[];
    solvent_a?: string;
    solvent_b?: string;
    solvent_c?: string;
    gradient_time_min?: number;
    flow_rate_ml_min?: number;
    ph?: number;
    temperature_c?: number;
    column_type?: string;
    mode?: string;
    grid_resolution?: number;
  }) => {
    const { data } = await apiClient.post<TernaryOptResult>('/methods/ternary-optimize', params);
    return data;
  },

  // F2: Method Transfer
  methodTransfer: async (params: {
    source_column: TransferColumnSpec;
    target_column: TransferColumnSpec;
    flow_rate_ml_min: number;
    gradient_table: Array<{ time_s: number; percent_b: number }>;
    injection_volume_ul?: number;
    temperature_c?: number;
    preserve_resolution?: boolean;
  }) => {
    const { data } = await apiClient.post<MethodTransferResult>('/methods/method-transfer', params);
    return data;
  },

  // F15: Buffer Calculator
  calculateBuffer: async (buffer: string, concentration: number, unit?: string) => {
    const { data } = await apiClient.post<BufferCalcResult>('/methods/buffer/calculate', {
      buffer, concentration, unit: unit ?? 'percent',
    });
    return data;
  },

  checkMobilePhase: async (params: {
    solvent_a?: string;
    solvent_b?: string;
    buffer?: string;
    buffer_percent?: number;
    buffer_unit?: string;
    ph_target?: number;
  }) => {
    const { data } = await apiClient.post<MobilePhaseCheckResult>('/methods/mobile-phase/check', params);
    return data;
  },

  listBuffers: async () => {
    const { data } = await apiClient.get<{
      acids: Record<string, any>;
      bases: Record<string, any>;
      salts: Record<string, any>;
    }>('/methods/buffers/list');
    return data;
  },

  // F14: Peak Tracking
  peakTracking: async (params: {
    chromatograms: Record<string, TrackPeak[]>;
    rt_tolerance_min?: number;
    area_tolerance_pct?: number;
    min_confidence?: number;
    solvent_front_rt_min?: number;
    min_area?: number;
  }) => {
    const { data } = await apiClient.post<PeakTrackingResult>('/methods/peak-tracking', params);
    return data;
  },
};

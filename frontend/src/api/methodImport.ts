import { apiClient } from './client';

export interface ParsedMethod {
  instrument: string | null;
  method_name: string | null;
  column_temp_c: number | null;
  flow_rate_ml_min: number | null;
  solvent_a: string | null;
  solvent_b: string | null;
  method_end_time_min: number | null;
  injection_volume_ul: number | null;
  sampler_temp_c: number | null;
  percent_b_start: number | null;
  percent_b_end: number | null;
  gradient_time_min: number | null;
  gradient_table: Array<{
    time_min: number;
    flow_rate_ml_min: number | null;
    percent_b: number | null;
    curve: number | null;
  }>;
  warnings: string[];
}

export interface MzXmlSummary {
  filename: string;
  num_scans: number;
  num_ms1_scans: number;
  num_ms2_scans: number;
  rt_start_s: number | null;
  rt_end_s: number | null;
  polarity: string | null;
}

export interface PeakDetectionResult {
  compound_id: string | null;
  compound_name: string | null;
  smiles: string | null;
  target_mz: number | null;
  mz_tolerance_ppm: number | null;
  peaks: Array<{
    retention_time_s: number;
    retention_time_min: number;
    intensity: number;
    peak_width_s: number | null;
    signal_to_noise: number | null;
  }>;
  xic_points: number;
  error: string | null;
}

export interface ExtractPeaksResponse {
  mzxml_summaries: MzXmlSummary[];
  results: PeakDetectionResult[];
  method_conditions: ParsedMethod | null;
}

export interface TrainFromPeaksResponse {
  artifact_id: string;
  n_samples: number;
  n_new_samples: number;
  column_type: string;
  model_type: string;
  compounds_used: string[];
  compounds_no_peaks: string[];
  incremental: boolean;
  existing_samples_loaded?: number;
  existing_model_version?: number;
}

export interface ModelSummary {
  id: string;
  column_type: string;
  model_type: string;
  version: number;
  n_samples: number;
  trained_at: string;
}

export interface MethodConditionOverrides {
  override_flow?: number;
  override_temp?: number;
  override_percent_b_start?: number;
  override_percent_b_end?: number;
  override_gradient_time?: number;
  override_ph?: number;
}

export const methodImportApi = {
  parseMeth: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<ParsedMethod>('/method-import/parse-meth', formData, {
      headers: { 'Content-Type': undefined },
    });
    return data;
  },

  parseMzxml: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<MzXmlSummary>('/method-import/parse-mzxml', formData, {
      headers: { 'Content-Type': undefined },
    });
    return data;
  },

  listModels: async (columnType?: string) => {
    const { data } = await apiClient.get<ModelSummary[]>('/method-import/models', {
      params: columnType ? { column_type: columnType } : undefined,
    });
    return data;
  },

  extractPeaks: async (
    mzxmlFiles: File[],
    compoundIds: string[],
    options?: {
      methFile?: File;
      mz_tolerance_ppm?: number;
      min_snr?: number;
      max_peaks_per_compound?: number;
    },
  ) => {
    const formData = new FormData();
    for (const f of mzxmlFiles) {
      formData.append('mzxml_files', f);
    }
    formData.append('compound_ids', compoundIds.join(','));
    if (options?.methFile) {
      formData.append('meth_file', options.methFile);
    }
    if (options?.mz_tolerance_ppm) {
      formData.append('mz_tolerance_ppm', String(options.mz_tolerance_ppm));
    }
    if (options?.min_snr) {
      formData.append('min_snr', String(options.min_snr));
    }
    if (options?.max_peaks_per_compound) {
      formData.append('max_peaks_per_compound', String(options.max_peaks_per_compound));
    }
    const { data } = await apiClient.post<ExtractPeaksResponse>(
      '/method-import/extract-peaks',
      formData,
      { headers: { 'Content-Type': undefined } },
    );
    return data;
  },

  trainFromPeaks: async (
    mzxmlFiles: File[],
    compoundIds: string[],
    options?: {
      methFile?: File;
      column_type?: string;
      model_type?: string;
      mz_tolerance_ppm?: number;
      min_snr?: number;
      existing_artifact_id?: string;
    } & MethodConditionOverrides,
  ) => {
    const formData = new FormData();
    for (const f of mzxmlFiles) {
      formData.append('mzxml_files', f);
    }
    formData.append('compound_ids', compoundIds.join(','));
    if (options?.methFile) {
      formData.append('meth_file', options.methFile);
    }
    formData.append('column_type', options?.column_type || 'C18');
    formData.append('model_type', options?.model_type || 'xgboost');
    if (options?.mz_tolerance_ppm) {
      formData.append('mz_tolerance_ppm', String(options.mz_tolerance_ppm));
    }
    if (options?.min_snr) {
      formData.append('min_snr', String(options.min_snr));
    }
    if (options?.existing_artifact_id) {
      formData.append('existing_artifact_id', options.existing_artifact_id);
    }
    // Method condition overrides
    if (options?.override_flow != null) {
      formData.append('override_flow', String(options.override_flow));
    }
    if (options?.override_temp != null) {
      formData.append('override_temp', String(options.override_temp));
    }
    if (options?.override_percent_b_start != null) {
      formData.append('override_percent_b_start', String(options.override_percent_b_start));
    }
    if (options?.override_percent_b_end != null) {
      formData.append('override_percent_b_end', String(options.override_percent_b_end));
    }
    if (options?.override_gradient_time != null) {
      formData.append('override_gradient_time', String(options.override_gradient_time));
    }
    if (options?.override_ph != null) {
      formData.append('override_ph', String(options.override_ph));
    }
    const { data } = await apiClient.post<TrainFromPeaksResponse>(
      '/method-import/train-from-peaks',
      formData,
      { headers: { 'Content-Type': undefined } },
    );
    return data;
  },

  // F11: CSV/TXT Chromatogram Import
  parseChromatogramCsv: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<{
      time_min: number[];
      intensity: number[];
      detector: string;
      wavelength_nm: number | null;
      sample_name: string;
      n_points: number;
      peaks: Array<{ rt_min: number; height: number; width_min: number; area: number; index: number }>;
    }>('/method-import/parse-chromatogram-csv', formData, {
      headers: { 'Content-Type': undefined },
    });
    return data;
  },
};

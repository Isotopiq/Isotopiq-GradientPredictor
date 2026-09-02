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
  mzxml_summary: MzXmlSummary;
  results: PeakDetectionResult[];
  method_conditions: ParsedMethod | null;
}

export interface TrainFromPeaksResponse {
  artifact_id: string;
  n_samples: number;
  column_type: string;
  model_type: string;
  compounds_used: string[];
  compounds_no_peaks: string[];
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

  extractPeaks: async (
    mzxmlFile: File,
    compoundIds: string[],
    options?: {
      methFile?: File;
      mz_tolerance_ppm?: number;
      min_snr?: number;
      max_peaks_per_compound?: number;
    },
  ) => {
    const formData = new FormData();
    formData.append('mzxml_file', mzxmlFile);
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
    mzxmlFile: File,
    compoundIds: string[],
    options?: {
      methFile?: File;
      column_type?: string;
      model_type?: string;
      mz_tolerance_ppm?: number;
      min_snr?: number;
    },
  ) => {
    const formData = new FormData();
    formData.append('mzxml_file', mzxmlFile);
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
    const { data } = await apiClient.post<TrainFromPeaksResponse>(
      '/method-import/train-from-peaks',
      formData,
      { headers: { 'Content-Type': undefined } },
    );
    return data;
  },
};

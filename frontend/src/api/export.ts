import { apiClient } from './client';

export interface MethodExportSections {
  method_parameters: boolean;
  gradient_program: boolean;
  compound_info: boolean;
  chromatogram: boolean;
  resolution_matrix: boolean;
  robustness: boolean;
  optimization: boolean;
  method_transfer: boolean;
  cover_page: boolean;
  disclaimer: boolean;
}

export interface ColumnComparisonExportSections {
  tanaka_table: boolean;
  radar_chart: boolean;
  similarity_matrix: boolean;
  parameter_diffs: boolean;
  cover_page: boolean;
  disclaimer: boolean;
}

export interface BatchAnalysisExportSections {
  method_parameters: boolean;
  compound_table: boolean;
  chromatogram: boolean;
  flagged_compounds: boolean;
  cover_page: boolean;
  disclaimer: boolean;
}

export interface PredictorExportRequest {
  name?: string;
  column_type: string;
  ph?: number;
  flow_rate_ml_min?: number;
  temperature_c?: number;
  mobile_phase_a?: string;
  mobile_phase_b?: string;
  additive?: string;
  gradient_table: { time_s: number; percent_b: number }[];
  compounds_smiles: string[];
  compound_names?: string[];
  dwell_volume_ml?: number;
  dead_volume_ml?: number;
  sections?: Record<string, boolean>;
}

function downloadBlob(data: Blob, filename: string) {
  const url = URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function sectionsToQuery(sections: Record<string, boolean>): string {
  return Object.entries(sections)
    .filter(([, v]) => v)
    .map(([k]) => k)
    .join(',');
}

export const exportApi = {
  // Method library export
  methodPdf: async (id: string, sections: Record<string, boolean>) => {
    const resp = await apiClient.get(`/export/method/${id}`, {
      params: { format: 'pdf', sections: sectionsToQuery(sections) },
      responseType: 'blob',
    });
    downloadBlob(resp.data, `method_${id}.pdf`);
  },

  methodCsv: async (id: string) => {
    const resp = await apiClient.get(`/export/method/${id}`, {
      params: { format: 'csv' },
      responseType: 'blob',
    });
    downloadBlob(resp.data, `method_${id}.csv`);
  },

  methodInstrument: async (id: string, format: 'agilent' | 'waters' | 'thermo', ext: string) => {
    const resp = await apiClient.get(`/export/method/${id}`, {
      params: { format },
      responseType: 'blob',
    });
    downloadBlob(resp.data, `method_${id}.${ext}`);
  },

  // Predictor export (unsaved method)
  predictorPdf: async (data: PredictorExportRequest) => {
    const resp = await apiClient.post('/export/predictor', data, { responseType: 'blob' });
    downloadBlob(resp.data, 'predictor_report.pdf');
  },

  // Shared method export (no auth)
  sharedPdf: async (token: string, sections: Record<string, boolean>) => {
    const resp = await apiClient.get(`/export/shared/${token}`, {
      params: { sections: sectionsToQuery(sections) },
      responseType: 'blob',
    });
    downloadBlob(resp.data, `shared_method.pdf`);
  },

  // Column comparison export
  columnComparisonPdf: async (columns: { label: string; tanaka: Record<string, number> }[], sections: Record<string, boolean>) => {
    const resp = await apiClient.post('/export/column-comparison', { columns, sections }, { responseType: 'blob' });
    downloadBlob(resp.data, 'column_comparison.pdf');
  },

  // Batch analysis export
  batchAnalysisPdf: async (data: {
    method_params: Record<string, unknown>;
    compounds: Record<string, unknown>[];
    results: Record<string, unknown>[];
  }, sections: Record<string, boolean>) => {
    const resp = await apiClient.post('/export/batch-analysis', { ...data, sections }, { responseType: 'blob' });
    downloadBlob(resp.data, 'batch_analysis.pdf');
  },
};

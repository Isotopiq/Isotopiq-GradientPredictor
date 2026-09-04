import { apiClient } from './client';
import type { ColumnSpec, PIRMPredictionResult, TanakaParameters, ColumnComparisonResult } from '@/types';

export interface ColumnListResponse {
  columns: ColumnSpec[];
  total: number;
  limit: number;
  offset: number;
}

export interface PIRMPredictionParams {
  column_id: string;
  logp: number;
  mw: number;
  tpsa?: number;
  gradient_table: Array<{ time_s: number; percent_b: number }>;
  flow_rate_ml_min?: number;
}

export const columnsApi = {
  list: async (params?: {
    chemistry?: string;
    brand?: string;
    search?: string;
    particle_size?: number;
    limit?: number;
    offset?: number;
  }) => {
    const { data } = await apiClient.get<ColumnListResponse>('/columns', { params });
    return data;
  },

  get: async (id: string) => {
    const { data } = await apiClient.get<ColumnSpec>(`/columns/${id}`);
    return data;
  },

  brands: async () => {
    const { data } = await apiClient.get<string[]>('/columns/meta/brands');
    return data;
  },

  chemistries: async () => {
    const { data } = await apiClient.get<string[]>('/columns/meta/chemistries');
    return data;
  },

  predictRetention: async (params: PIRMPredictionParams) => {
    const { data } = await apiClient.post<PIRMPredictionResult>(
      '/columns/predict-retention',
      params
    );
    return data;
  },

  // F3: Tanaka Column Comparison
  getTanakaReference: async () => {
    const { data } = await apiClient.get<{ reference_columns: Record<string, TanakaParameters> }>(
      '/columns/tanaka/reference',
    );
    return data;
  },

  compareColumns: async (a: TanakaParameters, b: TanakaParameters) => {
    const { data } = await apiClient.post<ColumnComparisonResult>('/columns/tanaka/compare', {
      column_a: a, column_b: b,
    });
    return data;
  },

  compareAllColumns: async (columns: TanakaParameters[], reference?: TanakaParameters) => {
    const { data } = await apiClient.post<{
      comparisons: ColumnComparisonResult[];
      clusters: Record<string, string[]>;
    }>('/columns/tanaka/compare-all', { columns, reference });
    return data;
  },
};

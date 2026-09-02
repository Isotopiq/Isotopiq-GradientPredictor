import { apiClient } from './client';
import type { ModelArtifact, FeatureImportance, ModelHistory, CalibrationData } from '@/types';

export const mlApi = {
  trainFromCsv: async (file: File, columnType: string, modelType: string) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post(
      '/ml/train/csv',
      formData,
      {
        params: { column_type: columnType, model_type: modelType },
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    );
    return data;
  },

  listModels: async (columnType?: string) => {
    const { data } = await apiClient.get<ModelArtifact[]>('/ml/models', {
      params: columnType ? { column_type: columnType } : {},
    });
    return data;
  },

  getModel: async (id: string) => {
    const { data } = await apiClient.get<ModelArtifact>(`/ml/models/${id}`);
    return data;
  },

  deleteModel: async (id: string) => {
    await apiClient.delete(`/ml/models/${id}`);
  },

  stats: async () => {
    const { data } = await apiClient.get('/ml/stats');
    return data;
  },

  featureImportance: async (id: string) => {
    const { data } = await apiClient.get<FeatureImportance>(`/ml/models/${id}/feature-importance`);
    return data;
  },

  modelHistory: async (id: string) => {
    const { data } = await apiClient.get<ModelHistory>(`/ml/models/${id}/history`);
    return data;
  },

  performanceTrends: async () => {
    const { data } = await apiClient.get('/ml/performance-trends');
    return data;
  },

  calibration: async () => {
    const { data } = await apiClient.get<CalibrationData>('/ml/calibration');
    return data;
  },
};

import { apiClient } from './client';
import type { ModelArtifact } from '@/types';

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
};

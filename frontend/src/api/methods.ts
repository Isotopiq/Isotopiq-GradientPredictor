import { apiClient } from './client';
import type {
  Method,
  MethodCreate,
  MethodSuggestion,
  MethodSuggestionRequest,
  GradientSimulateRequest,
  GradientSimulateResult,
  ChromatogramRequest,
  ChromatogramResult,
} from '@/types';

export const methodsApi = {
  suggest: async (data: MethodSuggestionRequest) => {
    const { data: result } = await apiClient.post<MethodSuggestion>('/methods/suggest', data);
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
};

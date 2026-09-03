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
  }) => {
    const { data: result } = await apiClient.post<MultiCompoundSuggestion & {
      optimization?: {
        percent_b_start: number;
        percent_b_end: number;
        gradient_time_min: number;
        min_resolution: number;
        configurations_tested: number;
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
};

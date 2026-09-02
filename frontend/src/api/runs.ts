import { apiClient } from './client';
import type { Run } from '@/types';

export const runsApi = {
  create: async (data: {
    compound_id: string;
    method_id: string;
    observed_rt_s: number;
    peak_width_s?: number;
    notes?: string;
    run_date?: string;
  }) => {
    const { data: result } = await apiClient.post<Run>('/runs', data);
    return result;
  },

  list: async (params?: { compound_id?: string; method_id?: string }) => {
    const { data } = await apiClient.get<Run[]>('/runs', { params });
    return data;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/runs/${id}`);
  },
};

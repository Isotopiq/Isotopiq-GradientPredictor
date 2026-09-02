import { apiClient } from './client';
import type { ColumnSpec } from '@/types';

export const columnsApi = {
  list: async (params?: { chemistry?: string; brand?: string; limit?: number }) => {
    const { data } = await apiClient.get<ColumnSpec[]>('/columns', { params });
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
};

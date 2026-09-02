import { apiClient } from './client';
import type { Compound, CompoundCreate } from '@/types';

export const compoundsApi = {
  create: async (data: CompoundCreate) => {
    const { data: result } = await apiClient.post<Compound>('/compounds', data);
    return result;
  },

  list: async (search?: string, limit = 50, offset = 0) => {
    const { data } = await apiClient.get<Compound[]>('/compounds', {
      params: { search, limit, offset },
    });
    return data;
  },

  get: async (id: string) => {
    const { data } = await apiClient.get<Compound>(`/compounds/${id}`);
    return data;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/compounds/${id}`);
  },

  pubchemLookup: async (params: { name?: string; cas?: string }) => {
    const { data } = await apiClient.get('/compounds/pubchem/lookup', { params });
    return data;
  },
};

import { apiClient } from './client';
import type { Compound, CompoundCreate, PkaPlotData } from '@/types';

export const compoundsApi = {
  create: async (data: CompoundCreate) => {
    const { data: result } = await apiClient.post<Compound>('/compounds', data);
    return result;
  },

  batchCreate: async (compounds: CompoundCreate[]) => {
    const { data } = await apiClient.post<Compound[]>('/compounds/batch', { compounds });
    return data;
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

  update: async (id: string, data: { name?: string; cas?: string; is_shared?: boolean }) => {
    const { data: result } = await apiClient.patch<Compound>(`/compounds/${id}`, data);
    return result;
  },

  pubchemLookup: async (params: { name?: string; cas?: string }) => {
    const { data } = await apiClient.get('/compounds/pubchem/lookup', { params });
    return data;
  },

  searchMulti: async (name: string, limit = 10) => {
    const { data } = await apiClient.get('/compounds/search/multi', {
      params: { name, limit },
    });
    return data;
  },

  pkaPlot: async (smiles: string) => {
    const { data } = await apiClient.get<PkaPlotData>('/compounds/pka-plot', {
      params: { smiles },
    });
    return data;
  },

  depiction: async (smiles: string, width = 400, height = 300) => {
    const { data } = await apiClient.get<string>('/compounds/depiction', {
      params: { smiles, width, height },
      responseType: 'text',
    });
    return data;
  },
};

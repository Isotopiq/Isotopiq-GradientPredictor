import { apiClient } from './client';
import type { CompoundList, CompoundListCreate, CompoundListUpdate } from '@/types';

export const compoundListsApi = {
  list: async (limit = 50, offset = 0) => {
    const { data } = await apiClient.get<CompoundList[]>('/compound-lists', {
      params: { limit, offset },
    });
    return data;
  },

  get: async (id: string) => {
    const { data } = await apiClient.get<CompoundList>(`/compound-lists/${id}`);
    return data;
  },

  create: async (data: CompoundListCreate) => {
    const { data: result } = await apiClient.post<CompoundList>('/compound-lists', data);
    return result;
  },

  update: async (id: string, data: CompoundListUpdate) => {
    const { data: result } = await apiClient.put<CompoundList>(`/compound-lists/${id}`, data);
    return result;
  },

  delete: async (id: string) => {
    await apiClient.delete(`/compound-lists/${id}`);
  },
};

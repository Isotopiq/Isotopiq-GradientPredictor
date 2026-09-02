import { apiClient } from './client';
import type { Prediction } from '@/types';

export const predictionsApi = {
  create: async (compoundId: string, methodId: string) => {
    const { data } = await apiClient.post<Prediction>('/predictions', {
      compound_id: compoundId,
      method_id: methodId,
    });
    return data;
  },
};

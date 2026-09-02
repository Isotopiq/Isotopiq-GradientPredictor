import { apiClient } from './client';
import type { TokenPair, User } from '@/types';

export const authApi = {
  register: async (email: string, password: string, fullName?: string) => {
    const { data } = await apiClient.post<TokenPair>('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return data;
  },

  login: async (email: string, password: string) => {
    const { data } = await apiClient.post<TokenPair>('/auth/login', {
      email,
      password,
    });
    return data;
  },

  me: async () => {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },
};

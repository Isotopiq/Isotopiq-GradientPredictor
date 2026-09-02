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

  login: async (email: string, password: string, rememberMe?: boolean) => {
    const { data } = await apiClient.post<TokenPair>('/auth/login-remember', {
      email,
      password,
      remember_me: rememberMe ?? false,
    });
    return data;
  },

  forgotPassword: async (email: string) => {
    const { data } = await apiClient.post<{ message: string }>('/auth/forgot-password', {
      email,
    });
    return data;
  },

  resetPassword: async (token: string, newPassword: string) => {
    const { data } = await apiClient.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return data;
  },

  me: async () => {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },

  updateProfile: async (updates: { full_name?: string; email?: string }) => {
    const { data } = await apiClient.put<User>('/auth/profile', updates);
    return data;
  },

  uploadProfilePicture: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<User>('/auth/profile/picture', formData, {
      headers: { 'Content-Type': undefined },
    });
    return data;
  },

  deleteProfilePicture: async () => {
    const { data } = await apiClient.delete<User>('/auth/profile/picture');
    return data;
  },
};

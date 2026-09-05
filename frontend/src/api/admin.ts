import { apiClient } from './client';
import type { AdminUser, AuditLogEntry } from '@/types';

export interface AppSettings {
  lab_name: string;
  lab_subtitle: string;
  lab_address: string | null;
  lab_website: string | null;
  has_logo: boolean;
  logo_mime_type: string | null;
  report_footer: string;
  registration_enabled: boolean;
  report_title_prefix: string | null;
  cover_page_text: string | null;
  report_theme: string;
  include_cover_page_default: boolean;
}

export interface AdminStats {
  users: { total: number; active: number };
  compounds: number;
  methods: number;
  runs: number;
  audit_logs: number;
}

export const adminApi = {
  getSettings: async () => {
    const { data } = await apiClient.get<AppSettings>('/admin/settings');
    return data;
  },

  getPublicSettings: async () => {
    const { data } = await apiClient.get<{ registration_enabled: boolean; lab_name: string; lab_subtitle: string }>(
      '/admin/public-settings',
    );
    return data;
  },

  updateSettings: async (updates: Partial<AppSettings>) => {
    const { data } = await apiClient.put<AppSettings>('/admin/settings', updates);
    return data;
  },

  uploadLogo: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<AppSettings>('/admin/logo', formData, {
      headers: { 'Content-Type': undefined },
    });
    return data;
  },

  deleteLogo: async () => {
    const { data } = await apiClient.delete<AppSettings>('/admin/logo');
    return data;
  },

  // User management
  listUsers: async (search?: string) => {
    const { data } = await apiClient.get<AdminUser[]>('/admin/users', {
      params: search ? { search } : undefined,
    });
    return data;
  },

  updateUser: async (userId: string, updates: { is_admin?: boolean; is_active?: boolean; full_name?: string }) => {
    const { data } = await apiClient.put<AdminUser>(`/admin/users/${userId}`, updates);
    return data;
  },

  deleteUser: async (userId: string) => {
    await apiClient.delete(`/admin/users/${userId}`);
  },

  // Audit logs
  getAuditLogs: async (limit = 100, offset = 0, action?: string) => {
    const { data } = await apiClient.get<{ logs: AuditLogEntry[]; total: number; limit: number; offset: number }>(
      '/admin/audit-logs',
      { params: { limit, offset, action: action || undefined } },
    );
    return data;
  },

  clearAuditLogs: async () => {
    const { data } = await apiClient.delete<{ deleted: number }>('/admin/audit-logs');
    return data;
  },

  // Stats
  getStats: async () => {
    const { data } = await apiClient.get<AdminStats>('/admin/stats');
    return data;
  },
};

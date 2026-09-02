import { apiClient } from './client';
import type { Notification } from '@/types';

export const notificationsApi = {
  list: async () => {
    const { data } = await apiClient.get<Notification[]>('/notifications');
    return data;
  },

  dismiss: async (id: string) => {
    const { data } = await apiClient.post('/notifications/dismiss', { notification_id: id });
    return data;
  },
};

import { apiClient } from './client';
import type {
  CompoundList,
  CompoundListCreate,
  CompoundListUpdate,
  CSVCompoundEntry,
  CSVParseResult,
  ImportConfirmResult,
  ImportResolveStatus,
} from '@/types';

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

  // CSV Import
  parseCsv: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post<CSVParseResult>(
      '/compound-lists/import/parse',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return data;
  },

  startResolve: async (entries: CSVCompoundEntry[], useLipidmaps: boolean) => {
    const { data } = await apiClient.post<{ job_id: string }>(
      '/compound-lists/import/resolve',
      { entries, use_lipidmaps: useLipidmaps },
    );
    return data;
  },

  getResolveStatus: async (jobId: string) => {
    const { data } = await apiClient.get<ImportResolveStatus>(
      `/compound-lists/import/resolve/${jobId}`,
    );
    return data;
  },

  confirmImport: async (
    listName: string,
    listDescription: string | undefined,
    compounds: { smiles: string; name?: string; cas?: string; source?: string }[],
  ) => {
    const { data } = await apiClient.post<ImportConfirmResult>(
      '/compound-lists/import/confirm',
      { list_name: listName, list_description: listDescription, compounds },
    );
    return data;
  },
};

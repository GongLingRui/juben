import api from './api';

export async function getMemorySettings(params: { user_id: string; project_id?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/memory/settings`, params);
}

export async function updateMemorySettings(payload: {
  user_id: string;
  project_id?: string;
  user_enabled?: boolean;
  project_enabled?: boolean;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/memory/settings`, payload);
}

export async function getMemoryMetrics(params: { user_id: string; session_id: string; query?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/memory/metrics`, params);
}

export async function getMemoryQuality(params: { user_id: string; session_id: string; query?: string }) {
  return api.get<{ success: boolean; data: any }>(`/juben/user/memory/quality`, params);
}

export async function listMemorySnapshots(params: { user_id: string; session_id: string; project_id?: string }) {
  return api.get<{ success: boolean; data: any[] }>(`/juben/user/memory/snapshots`, params);
}

export async function createMemorySnapshot(payload: {
  user_id: string;
  session_id: string;
  project_id?: string;
  label?: string;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/memory/snapshots`, payload);
}

export async function restoreMemorySnapshot(snapshotId: string, payload: { user_id: string; session_id: string }) {
  return api.post<{ success: boolean; data: any }>(`/juben/user/memory/snapshots/${snapshotId}/restore`, payload);
}


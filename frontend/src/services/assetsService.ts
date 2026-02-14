import api from './api';

export async function listAssets(projectId: string) {
  return api.get<{ success: boolean; data: any[] }>(`/juben/assets`, { project_id: projectId });
}

export async function createAsset(payload: {
  project_id: string;
  artifact_id?: string;
  name: string;
  asset_type?: string;
  tags?: string[];
  collection?: string;
  source?: string;
  metadata?: Record<string, any>;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/assets`, payload);
}

export async function updateAsset(projectId: string, assetId: string, payload: Record<string, any>) {
  return api.put<{ success: boolean; data: any }>(`/juben/assets/${assetId}`, payload, { project_id: projectId });
}

export async function deleteAsset(projectId: string, assetId: string) {
  return api.delete<{ success: boolean }>(`/juben/assets/${assetId}`, { project_id: projectId });
}

export async function listAssetCollections(projectId: string) {
  return api.get<{ success: boolean; data: Record<string, any[]> }>(`/juben/assets/collections`, { project_id: projectId });
}

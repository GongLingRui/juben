import api from './api';

export async function listReleaseTemplates() {
  return api.get<{ success: boolean; data: Record<string, any> }>(`/juben/release/templates`);
}

export async function calculateRoi(payload: {
  views: number;
  ctr: number;
  cvr: number;
  arpu: number;
  cost: number;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/release/roi`, payload);
}

export async function generateChecklist(payload: {
  platform: string;
  title: string;
  episodes: number;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/release/checklist`, payload);
}

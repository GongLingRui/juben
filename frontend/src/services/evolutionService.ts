/**
 * Evolution service
 */

import api from './api';

export type EvolutionStatusResponse = {
  success: boolean;
  data?: any;
  error?: string;
};

export type EvolutionReportResponse = {
  success: boolean;
  data?: any;
  error?: string;
};

export type VersionsResponse = {
  success: boolean;
  data: any[];
  error?: string;
};

export type ABTestStatusResponse = {
  success: boolean;
  data?: any;
  error?: string;
};

export async function getEvolutionStatus(): Promise<EvolutionStatusResponse> {
  return api.get<EvolutionStatusResponse>('/juben/evolution/status');
}

export async function triggerEvolution(agent_name: string): Promise<EvolutionStatusResponse> {
  return api.post<EvolutionStatusResponse>('/juben/evolution/trigger', { agent_name });
}

export async function getVersions(agent_name: string, status?: string): Promise<VersionsResponse> {
  const params: Record<string, string> = { agent_name };
  if (status) params.status = status;
  return api.get<VersionsResponse>('/juben/evolution/versions', params);
}

export async function getABTestStatus(agent_name: string): Promise<ABTestStatusResponse> {
  return api.get<ABTestStatusResponse>('/juben/evolution/ab/test', { agent_name });
}

export async function promoteVersion(agent_name: string, version_id: string): Promise<EvolutionStatusResponse> {
  return api.post<EvolutionStatusResponse>('/juben/evolution/ab/promote', { agent_name, version_id });
}

export async function getEvolutionReport(date?: string): Promise<EvolutionReportResponse> {
  const params: Record<string, string> = {};
  if (date) params.date = date;
  return api.get<EvolutionReportResponse>('/juben/evolution/report', params);
}

import api from './api';

export async function listPipelineTemplates() {
  return api.get<{ success: boolean; data: any[] }>(`/juben/pipelines/templates`);
}

export async function runPipeline(payload: {
  template_id: string;
  user_input: string;
  user_id: string;
  session_id: string;
  project_id?: string;
}) {
  return api.post<{ success: boolean; data: any }>(`/juben/pipelines/run`, payload);
}

export async function listPipelineRuns(projectId?: string) {
  return api.get<{ success: boolean; data: any[] }>(`/juben/pipelines/runs`, projectId ? { project_id: projectId } : undefined);
}

export async function getPipelineRun(runId: string) {
  return api.get<{ success: boolean; data: any }>(`/juben/pipelines/runs/${runId}`);
}

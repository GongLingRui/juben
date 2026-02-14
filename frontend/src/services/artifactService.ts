import api from './api';

type CreateArtifactPayload = {
  content: string;
  filename: string;
  file_type: string;
  agent_source: string;
  user_id: string;
  session_id: string;
  project_id: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, any>;
};

export async function createArtifact(payload: CreateArtifactPayload): Promise<{
  success: boolean;
  data?: any;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data?: any;
      message?: string;
    }>('/juben/files/artifacts', payload);
    return {
      success: response.success,
      data: response.data,
      message: response.message
    };
  } catch (error) {
    console.error('创建 Artifact 失败:', error);
    return { success: false, message: '创建 Artifact 失败' };
  }
}

/**
 * 项目服务
 * 提供项目相关的API调用
 */

import api from './api';
import type { Project, ProjectFile, ProjectCreateRequest, ProjectUpdateRequest } from '@/types';

/**
 * 获取项目列表
 */
export async function getProjects(params?: {
  user_id?: string;
  status?: string;
  tags?: string[];
  page?: number;
  page_size?: number;
}): Promise<{
  success: boolean;
  projects: Project[];
  total: number;
  page: number;
  page_size: number;
}> {
  try {
    const response = await api.get<{
      success: boolean;
      projects: any[];
      total: number;
      page: number;
      page_size: number;
    }>('/juben/projects', {
      user_id: params?.user_id || 'default_user',
      status: params?.status,
      tags: params?.tags,
      page: params?.page || 1,
      page_size: params?.page_size || 20
    });

    return {
      success: response.success,
      projects: response.projects || [],
      total: response.total || 0,
      page: response.page || 1,
      page_size: response.page_size || 20
    };
  } catch (error) {
    console.error('获取项目列表失败:', error);
    return {
      success: false,
      projects: [],
      total: 0,
      page: 1,
      page_size: 20
    };
  }
}

/**
 * 获取项目详情
 */
export async function getProject(projectId: string): Promise<{
  success: boolean;
  project?: Project;
  files?: ProjectFile[];
  message?: string;
}> {
  try {
    const response = await api.get<{
      success: boolean;
      project: any;
      files: any[];
    }>(`/juben/projects/${projectId}`);

    return {
      success: response.success,
      project: response.project,
      files: response.files || []
    };
  } catch (error) {
    console.error('获取项目详情失败:', error);
    return {
      success: false
    };
  }
}

/**
 * 创建项目
 */
export async function createProject(data: ProjectCreateRequest): Promise<{
  success: boolean;
  project?: Project;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: any;
    }>('/juben/projects', data);

    return {
      success: response.success,
      project: response.data,
      message: '项目创建成功'
    };
  } catch (error) {
    console.error('创建项目失败:', error);
    return {
      success: false,
      message: '创建项目失败'
    };
  }
}

/**
 * 更新项目
 */
export async function updateProject(
  projectId: string,
  data: ProjectUpdateRequest
): Promise<{
  success: boolean;
  project?: Project;
  message?: string;
}> {
  try {
    const response = await api.put<{
      success: boolean;
      data: any;
    }>(`/juben/projects/${projectId}`, data);

    return {
      success: response.success,
      project: response.data,
      message: '项目更新成功'
    };
  } catch (error) {
    console.error('更新项目失败:', error);
    return {
      success: false,
      message: '更新项目失败'
    };
  }
}

/**
 * 删除项目
 */
export async function deleteProject(
  projectId: string,
  permanent: boolean = false
): Promise<{
  success: boolean;
  message?: string;
}> {
  try {
    const response = await api.delete<{
      success: boolean;
    }>(`/juben/projects/${projectId}`, {
      permanent
    });

    return {
      success: response.success,
      message: permanent ? '项目已永久删除' : '项目已删除'
    };
  } catch (error) {
    console.error('删除项目失败:', error);
    return {
      success: false,
      message: '删除项目失败'
    };
  }
}

/**
 * 获取项目文件列表
 */
export async function getProjectFiles(
  projectId: string,
  fileType?: string
): Promise<{
  success: boolean;
  files: ProjectFile[];
}> {
  try {
    const response = await api.get<{
      success: boolean;
      data: any[];
    }>(`/juben/projects/${projectId}/files`, {
      file_type: fileType
    });

    return {
      success: response.success,
      files: response.data || []
    };
  } catch (error) {
    console.error('获取文件列表失败:', error);
    return {
      success: false,
      files: []
    };
  }
}

export async function createProjectFile(projectId: string, payload: {
  filename: string;
  file_type: string;
  content: any;
  agent_source?: string;
  tags?: string[];
}): Promise<{
  success: boolean;
  data?: ProjectFile;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: any;
      message?: string;
    }>(`/juben/projects/${projectId}/files`, payload);
    return {
      success: response.success,
      data: response.data,
      message: response.message
    };
  } catch (error) {
    console.error('创建项目文件失败:', error);
    return {
      success: false,
      message: '创建项目文件失败'
    };
  }
}

export async function getLatestProjectFile(projectId: string, fileType?: string): Promise<{
  success: boolean;
  data?: ProjectFile;
}> {
  try {
    const response = await api.get<{
      success: boolean;
      data: any;
    }>(`/juben/projects/${projectId}/files/latest`, {
      file_type: fileType
    });
    return {
      success: response.success,
      data: response.data || undefined
    };
  } catch (error) {
    console.error('获取最新文件失败:', error);
    return { success: false };
  }
}

export async function listProjectMembers(projectId: string) {
  return api.get<{ success: boolean; data: any[] }>(`/juben/projects/${projectId}/members`);
}

export async function addProjectMember(projectId: string, payload: { user_id: string; role?: string; display_name?: string }) {
  return api.post<{ success: boolean; data: any[] }>(`/juben/projects/${projectId}/members`, payload);
}

export async function updateProjectMember(projectId: string, userId: string, payload: { role?: string; display_name?: string }) {
  return api.put<{ success: boolean; data: any[] }>(`/juben/projects/${projectId}/members/${userId}`, payload);
}

export async function removeProjectMember(projectId: string, userId: string) {
  return api.delete<{ success: boolean; data: any[] }>(`/juben/projects/${projectId}/members/${userId}`);
}

/**
 * 获取单个文件
 */
export async function getProjectFile(
  projectId: string,
  fileId: string
): Promise<{
  success: boolean;
  file?: ProjectFile;
}> {
  try {
    const response = await api.get<{
      success: boolean;
      data: any;
    }>(`/juben/projects/${projectId}/files/${fileId}`);

    return {
      success: response.success,
      file: response.data
    };
  } catch (error) {
    console.error('获取文件失败:', error);
    return {
      success: false
    };
  }
}

/**
 * 添加文件到项目
 */
export async function addProjectFile(
  projectId: string,
  data: {
    filename: string;
    file_type: string;
    content: any;
    agent_source?: string;
    tags?: string[];
  }
): Promise<{
  success: boolean;
  file?: ProjectFile;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: any;
    }>(`/juben/projects/${projectId}/files`, data);

    return {
      success: response.success,
      file: response.data,
      message: '文件创建成功'
    };
  } catch (error) {
    console.error('创建文件失败:', error);
    return {
      success: false,
      message: '创建文件失败'
    };
  }
}

/**
 * 更新文件
 */
export async function updateProjectFile(
  projectId: string,
  fileId: string,
  data: {
    filename?: string;
    content?: any;
    tags?: string[];
  }
): Promise<{
  success: boolean;
  file?: ProjectFile;
  message?: string;
}> {
  try {
    const response = await api.put<{
      success: boolean;
      data: any;
    }>(`/juben/projects/${projectId}/files/${fileId}`, data);

    return {
      success: response.success,
      file: response.data,
      message: '文件更新成功'
    };
  } catch (error) {
    console.error('更新文件失败:', error);
    return {
      success: false,
      message: '更新文件失败'
    };
  }
}

/**
 * 删除文件
 */
export async function deleteProjectFile(
  projectId: string,
  fileId: string
): Promise<{
  success: boolean;
  message?: string;
}> {
  try {
    const response = await api.delete<{
      success: boolean;
    }>(`/juben/projects/${projectId}/files/${fileId}`);

    return {
      success: response.success,
      message: '文件删除成功'
    };
  } catch (error) {
    console.error('删除文件失败:', error);
    return {
      success: false,
      message: '删除文件失败'
    };
  }
}

/**
 * 搜索项目
 */
export async function searchProjects(params: {
  query?: string;
  tags?: string[];
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}): Promise<{
  success: boolean;
  projects: Project[];
  total: number;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      projects: any[];
      total: number;
    }>('/juben/projects/search', params);

    return {
      success: response.success,
      projects: response.projects || [],
      total: response.total || 0
    };
  } catch (error) {
    console.error('搜索项目失败:', error);
    return {
      success: false,
      projects: [],
      total: 0
    };
  }
}

/**
 * 导出项目
 */
export async function exportProject(
  projectId: string,
  format: 'json' | 'txt' | 'md' | 'pdf',
  options?: {
    include_files?: boolean;
    file_types?: string[];
  }
): Promise<{
  success: boolean;
  download_url?: string;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: {
        download_url: string;
      };
    }>(`/juben/projects/${projectId}/export`, {
      format,
      ...options
    });

    return {
      success: response.success,
      download_url: response.data?.download_url,
      message: '导出成功'
    };
  } catch (error) {
    console.error('导出项目失败:', error);
    return {
      success: false,
      message: '导出失败'
    };
  }
}

/**
 * 获取所有标签
 */
export async function getAllTags(): Promise<{
  success: boolean;
  tags: string[];
}> {
  try {
    const response = await api.get<{
      success: boolean;
      data: {
        tags: string[];
      };
    }>('/juben/projects/tags/all');

    return {
      success: response.success,
      tags: response.data?.tags || []
    };
  } catch (error) {
    console.error('获取标签失败:', error);
    return {
      success: false,
      tags: []
    };
  }
}

/**
 * 归档项目
 */
export async function archiveProject(
  projectId: string
): Promise<{
  success: boolean;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
    }>(`/juben/projects/${projectId}/archive`, {});

    return {
      success: response.success,
      message: '项目已归档'
    };
  } catch (error) {
    console.error('归档项目失败:', error);
    return {
      success: false,
      message: '归档项目失败'
    };
  }
}

/**
 * 恢复项目
 */
export async function restoreProject(
  projectId: string
): Promise<{
  success: boolean;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
    }>(`/juben/projects/${projectId}/restore`, {});

    return {
      success: response.success,
      message: '项目已恢复'
    };
  } catch (error) {
    console.error('恢复项目失败:', error);
    return {
      success: false,
      message: '恢复项目失败'
    };
  }
}

/**
 * 复制项目
 */
export async function duplicateProject(
  projectId: string,
  newName?: string
): Promise<{
  success: boolean;
  project?: Project;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: any;
    }>(`/juben/projects/${projectId}/duplicate`, {
      new_name: newName
    });

    return {
      success: response.success,
      project: response.data,
      message: '项目复制成功'
    };
  } catch (error) {
    console.error('复制项目失败:', error);
    return {
      success: false,
      message: '复制项目失败'
    };
  }
}

/**
 * 保存为模板
 */
export async function saveAsTemplate(
  projectId: string,
  templateName: string,
  templateDescription?: string
): Promise<{
  success: boolean;
  template_id?: string;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: {
        template_id: string;
      };
    }>(`/juben/projects/${projectId}/save-template`, {
      template_name: templateName,
      template_description: templateDescription
    });

    return {
      success: response.success,
      template_id: response.data?.template_id,
      message: '模板保存成功'
    };
  } catch (error) {
    console.error('保存模板失败:', error);
    return {
      success: false,
      message: '保存模板失败'
    };
  }
}

/**
 * 获取模板列表
 */
export async function getTemplates(): Promise<{
  success: boolean;
  templates: Array<{
    id: string;
    name: string;
    description: string;
    project_id: string;
    created_at: string;
  }>;
}> {
  try {
    const response = await api.get<{
      success: boolean;
      data: {
        templates: any[];
      };
    }>('/juben/projects/templates');

    return {
      success: response.success,
      templates: response.data?.templates || []
    };
  } catch (error) {
    console.error('获取模板列表失败:', error);
    return {
      success: false,
      templates: []
    };
  }
}

/**
 * 从模板创建项目
 */
export async function createFromTemplate(
  templateId: string,
  projectName: string
): Promise<{
  success: boolean;
  project?: Project;
  message?: string;
}> {
  try {
    const response = await api.post<{
      success: boolean;
      data: any;
    }>(`/juben/projects/templates/${templateId}/create`, {
      project_name: projectName
    });

    return {
      success: response.success,
      project: response.data,
      message: '项目创建成功'
    };
  } catch (error) {
    console.error('从模板创建项目失败:', error);
    return {
      success: false,
      message: '从模板创建项目失败'
    };
  }
}

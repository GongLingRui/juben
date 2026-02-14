/**
 * 项目状态管理 Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Project, ProjectFile } from '@/types';
import * as projectService from '@/services/projectService';

interface ProjectState {
  // 项目列表
  projects: Project[];
  currentProject: Project | null;
  projectFiles: ProjectFile[];

  // 加载状态
  isLoading: boolean;
  error: string | null;

  // 过滤和分页
  currentPage: number;
  pageSize: number;
  total: number;

  // 标签
  allTags: string[];
  selectedTags: string[];

  // 搜索查询
  searchQuery: string;
  statusFilter: Project['status'] | 'all';

  // Actions
  loadProjects: () => Promise<void>;
  loadProject: (projectId: string) => Promise<void>;
  createProject: (data: {
    name: string;
    description?: string;
    tags?: string[];
  }) => Promise<Project | null>;
  updateProject: (projectId: string, data: any) => Promise<void>;
  deleteProject: (projectId: string, permanent?: boolean) => Promise<void>;

  // 文件操作
  loadProjectFiles: (projectId: string) => Promise<void>;
  addFile: (projectId: string, data: any) => Promise<void>;
  updateFile: (projectId: string, fileId: string, data: any) => Promise<void>;
  deleteFile: (projectId: string, fileId: string) => Promise<void>;

  // 搜索和过滤
  setSearchQuery: (query: string) => void;
  setSelectedTags: (tags: string[]) => void;
  setCurrentPage: (page: number) => void;
  setStatusFilter: (status: Project['status'] | 'all') => void;

  // 标签
  loadAllTags: () => Promise<void>;

  // 清理
  clearCurrentProject: () => void;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      projects: [],
      currentProject: null,
      projectFiles: [],
      isLoading: false,
      error: null,
      currentPage: 1,
      pageSize: 20,
      total: 0,
      allTags: [],
      selectedTags: [],
      searchQuery: '',
      statusFilter: 'all',

      // 加载项目列表
      loadProjects: async () => {
        set({ isLoading: true, error: null });
        try {
          const { projects, total } = await projectService.getProjects({
            page: get().currentPage,
            page_size: get().pageSize,
            tags: get().selectedTags.length > 0 ? get().selectedTags : undefined,
            status: get().statusFilter !== 'all' ? get().statusFilter : undefined,
          });

          set({
            projects,
            total,
            isLoading: false
          });
        } catch (error: any) {
          set({
            error: error?.message || '加载项目列表失败',
            isLoading: false
          });
        }
      },

      // 加载单个项目
      loadProject: async (projectId: string) => {
        set({ isLoading: true, error: null });
        try {
          const { project, files } = await projectService.getProject(projectId);

          if (!project) {
            throw new Error('项目不存在');
          }

          set({
            currentProject: project,
            projectFiles: files || [],
            isLoading: false
          });
        } catch (error: any) {
          set({
            error: error?.message || '加载项目详情失败',
            isLoading: false
          });
        }
      },

      // 创建项目
      createProject: async (data) => {
        set({ isLoading: true, error: null });
        try {
          const { project } = await projectService.createProject(data);

          if (project) {
            // 添加到项目列表
            set(state => ({
              projects: [project, ...state.projects],
              total: state.total + 1,
              isLoading: false
            }));

            return project;
          }

          set({ isLoading: false });
          return null;
        } catch (error: any) {
          set({
            error: error?.message || '创建项目失败',
            isLoading: false
          });
          return null;
        }
      },

      // 更新项目
      updateProject: async (projectId: string, data) => {
        set({ isLoading: true, error: null });
        try {
          const { project } = await projectService.updateProject(projectId, data);

          if (project) {
            // 更新项目列表中的项目
            set(state => ({
              projects: state.projects.map(p =>
                p.id === projectId ? project : p
              ),
              currentProject: state.currentProject?.id === projectId
                ? project
                : state.currentProject,
              isLoading: false
            }));
          }
        } catch (error: any) {
          set({
            error: error?.message || '更新项目失败',
            isLoading: false
          });
        }
      },

      // 删除项目
      deleteProject: async (projectId: string, permanent = false) => {
        set({ isLoading: true, error: null });
        try {
          await projectService.deleteProject(projectId, permanent);

          // 从列表中移除
          set(state => ({
            projects: state.projects.filter(p => p.id !== projectId),
            total: state.total - 1,
            currentProject: state.currentProject?.id === projectId
              ? null
              : state.currentProject,
            isLoading: false
          }));
        } catch (error: any) {
          set({
            error: error?.message || '删除项目失败',
            isLoading: false
          });
        }
      },

      // 加载项目文件
      loadProjectFiles: async (projectId: string) => {
        set({ isLoading: true, error: null });
        try {
          const { files } = await projectService.getProjectFiles(projectId);

          set({
            projectFiles: files || [],
            isLoading: false
          });
        } catch (error: any) {
          set({
            error: error?.message || '加载文件列表失败',
            isLoading: false
          });
        }
      },

      // 添加文件
      addFile: async (projectId: string, data) => {
        set({ isLoading: true, error: null });
        try {
          const { file } = await projectService.addProjectFile(projectId, data);

          if (file) {
            set(state => ({
              projectFiles: [...state.projectFiles, file],
              isLoading: false
            }));
          }
        } catch (error: any) {
          set({
            error: error?.message || '添加文件失败',
            isLoading: false
          });
        }
      },

      // 更新文件
      updateFile: async (projectId: string, fileId: string, data) => {
        set({ isLoading: true, error: null });
        try {
          const { file } = await projectService.updateProjectFile(projectId, fileId, data);

          if (file) {
            set(state => ({
              projectFiles: state.projectFiles.map(f =>
                f.id === fileId ? file : f
              ),
              isLoading: false
            }));
          }
        } catch (error: any) {
          set({
            error: error?.message || '更新文件失败',
            isLoading: false
          });
        }
      },

      // 删除文件
      deleteFile: async (projectId: string, fileId: string) => {
        set({ isLoading: true, error: null });
        try {
          await projectService.deleteProjectFile(projectId, fileId);

          set(state => ({
            projectFiles: state.projectFiles.filter(f => f.id !== fileId),
            isLoading: false
          }));
        } catch (error: any) {
          set({
            error: error?.message || '删除文件失败',
            isLoading: false
          });
        }
      },

      // 搜索查询
      setSearchQuery: (query: string) => {
        set({ searchQuery: query, currentPage: 1 });
      },

      // 标签过滤
      setSelectedTags: (tags: string[]) => {
        set({ selectedTags: tags, currentPage: 1 });
      },

      // 分页
      setCurrentPage: (page: number) => {
        set({ currentPage: page });
      },

      // 状态过滤
      setStatusFilter: (status) => {
        set({ statusFilter: status, currentPage: 1 });
      },

      // 加载所有标签
      loadAllTags: async () => {
        try {
          const { tags } = await projectService.getAllTags();
          set({ allTags: tags });
        } catch (error: any) {
          console.error('加载标签失败:', error);
        }
      },

      // 清理当前项目
      clearCurrentProject: () => {
        set({
          currentProject: null,
          projectFiles: [],
          error: null
        });
      },

      // 清理错误
      clearError: () => {
        set({ error: null });
      }
    }),
    { name: 'ProjectStore' }
  )
);

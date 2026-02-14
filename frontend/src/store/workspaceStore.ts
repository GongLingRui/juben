/**
 * 工作区状态管理 Store
 * 管理左侧工作区的显示内容（剧本、大纲、思维导图等）
 * 支持Notes系统（）
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { getAuthHeaderValue } from '@/services/api';

export type WorkspaceViewType = 'document' | 'mindmap' | 'json' | 'outline' | 'script' | 'evaluation' | 'notes';

export interface WorkspaceContent {
  id: string;
  type: WorkspaceViewType;
  title: string;
  content: string;
  metadata?: {
    agentName?: string;
    agentId?: string;
    timestamp?: string;
    format?: string;
    [key: string]: any;
  };
}

// Note数据结构（与后端保持一致）
export interface Note {
  id: string;
  user_id: string;
  session_id: string;
  action: string;  // Agent类型
  name: string;    // Note名称（如character1）
  title?: string;  // 可选标题
  context: string; // Note内容
  select_status: number;  // 0未选择，1已选择
  user_comment?: string;  // 用户评论
  metadata?: any;
  created_at: string;
  updated_at: string;
}

interface WorkspaceState {
  // 当前内容
  currentContent: WorkspaceContent | null;
  viewMode: WorkspaceViewType;

  // 历史记录（用于撤销/重做）
  contentHistory: WorkspaceContent[];
  historyIndex: number;

  // Notes系统
  notes: Note[];  // 当前会话的所有Notes
  selectedNotes: Note[];  // 用户选择的Notes
  notesGroupedByAction: Record<string, Note[]>;  // 按Agent类型分组的Notes
  isLoadingNotes: boolean;

  // 工具栏状态
  isDirty: boolean;
  canUndo: boolean;
  canRedo: boolean;

  // Actions - 内容管理
  setContent: (content: WorkspaceContent) => void;
  updateContent: (updates: Partial<WorkspaceContent>) => void;
  clearContent: () => void;
  setViewMode: (mode: WorkspaceViewType) => void;

  // 历史操作
  undo: () => void;
  redo: () => void;

  // 工具栏操作
  saveContent: () => Promise<void>;
  copyContent: () => Promise<void>;
  exportContent: (format: string) => Promise<void>;

  // Actions - Notes管理
  loadNotes: (userId: string, sessionId: string, action?: string) => Promise<void>;
  toggleNoteSelection: (note: Note) => Promise<void>;
  updateNoteSelection: (note: Note, selected: boolean, comment?: string) => Promise<void>;
  getSelectedNotes: () => Note[];
  exportNotes: (format: string) => Promise<void>;
  exportSelectedNotes: () => Promise<void>;
  createNoteFromContent: (content: WorkspaceContent) => Promise<string | null>;
  updateNotesSelectionBulk: (notes: Note[], selected: boolean) => Promise<void>;

  // 内部方法
  _addToHistory: (content: WorkspaceContent) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      currentContent: null,
      viewMode: 'document',
      contentHistory: [],
      historyIndex: -1,
      isDirty: false,
      canUndo: false,
      canRedo: false,

      // Notes初始状态
      notes: [],
      selectedNotes: [],
      notesGroupedByAction: {},
      isLoadingNotes: false,

      setContent: (content) => {
        set((state) => ({
          currentContent: content,
          viewMode: content.type,
          isDirty: false,
        }));
        get()._addToHistory(content);
      },

      updateContent: (updates) => {
        set((state) => {
          if (!state.currentContent) return state;
          const updated = { ...state.currentContent, ...updates };
          return {
            currentContent: updated,
            isDirty: true,
          };
        });
      },

      clearContent: () => {
        set({
          currentContent: null,
          isDirty: false,
        });
      },

      setViewMode: (mode) => {
        set({ viewMode: mode });
      },

      undo: () => {
        set((state) => {
          if (state.historyIndex <= 0) return state;
          const newIndex = state.historyIndex - 1;
          const content = state.contentHistory[newIndex];
          return {
            ...state,
            currentContent: content,
            historyIndex: newIndex,
            canUndo: newIndex > 0,
            canRedo: newIndex < state.contentHistory.length - 1,
            isDirty: true,
          };
        });
      },

      redo: () => {
        set((state) => {
          if (state.historyIndex >= state.contentHistory.length - 1) return state;
          const newIndex = state.historyIndex + 1;
          const content = state.contentHistory[newIndex];
          return {
            ...state,
            currentContent: content,
            historyIndex: newIndex,
            canUndo: newIndex > 0,
            canRedo: newIndex < state.contentHistory.length - 1,
            isDirty: true,
          };
        });
      },

      saveContent: async () => {
        const { currentContent } = get();
        if (!currentContent) return;

        try {
          const storageKey = `juben_workspace_content_${currentContent.id}`;
          localStorage.setItem(storageKey, JSON.stringify(currentContent));
          console.log('[Workspace] Content saved to localStorage:', currentContent.id);

          set({ isDirty: false });
        } catch (error) {
          console.error('[Workspace] Save failed:', error);
          throw error;
        }
      },

      copyContent: async () => {
        const { currentContent } = get();
        if (!currentContent) return;

        try {
          await navigator.clipboard.writeText(currentContent.content);
          console.log('[Workspace] Content copied to clipboard');
        } catch (error) {
          console.error('[Workspace] Copy failed:', error);
          throw error;
        }
      },

      exportContent: async (format: string) => {
        const { currentContent } = get();
        if (!currentContent) return;

        try {
          const blob = new Blob([currentContent.content], { type: 'text/plain' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${currentContent.title}.${format}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);

          console.log('[Workspace] Content exported as', format);
        } catch (error) {
          console.error('[Workspace] Export failed:', error);
          throw error;
        }
      },

      // Notes管理功能
      loadNotes: async (userId: string, sessionId: string, action?: string) => {
        set({ isLoadingNotes: true });
        try {
          const params = new URLSearchParams({
            user_id: userId,
            session_id: sessionId,
          });
          if (action) params.append('action', action);

          // 使用 /juben/notes/list 路径，与其他 API 调用保持一致
          const authHeader = getAuthHeaderValue();
          const response = await fetch(`/juben/notes/list?${params.toString()}`, {
            headers: {
              'Content-Type': 'application/json',
              ...(authHeader ? { Authorization: authHeader } : {}),
            },
          });
          const raw = await response.text();

          let data: any = null;
          try {
            data = raw ? JSON.parse(raw) : null;
          } catch (parseError) {
            console.error(
              '[Workspace] Load notes failed: 无法解析JSON，原始响应片段:',
              raw?.slice(0, 200)
            );
            set({ isLoadingNotes: false });
            return;
          }

          if (data && data.success) {
            set({
              notes: data.notes || [],
              notesGroupedByAction: data.grouped_by_action || {},
              isLoadingNotes: false,
            });
          } else {
            console.warn('[Workspace] Load notes 返回失败:', data?.message || '未知错误');
            set({ isLoadingNotes: false });
          }
        } catch (error) {
          console.error('[Workspace] Load notes failed:', error);
          set({ isLoadingNotes: false });
        }
      },

      toggleNoteSelection: async (note: Note) => {
        const newSelected = !note.select_status;
        await get().updateNoteSelection(note, newSelected);
      },

      updateNoteSelection: async (note: Note, selected: boolean, comment?: string) => {
        try {
          // 使用 /juben/notes/batch-select 路径，与其他 API 调用保持一致
          await fetch('/juben/notes/batch-select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: note.user_id,
              session_id: note.session_id,
              selections: [{
                action: note.action,
                name: note.name,
                selected: selected,
                user_comment: comment || note.user_comment,
              }],
            }),
          });

          // 更新本地状态
          set((state) => ({
            notes: state.notes.map(n =>
              n.id === note.id
                ? { ...n, select_status: selected ? 1 : 0, user_comment: comment || n.user_comment }
                : n
            ),
          }));

          // 重新加载已选择的Notes
          await get().loadNotes(note.user_id, note.session_id);
        } catch (error) {
          console.error('[Workspace] Update note selection failed:', error);
        }
      },

      getSelectedNotes: () => {
        const { notes } = get();
        return notes.filter(n => n.select_status === 1);
      },

      exportNotes: async (format: string) => {
        const { notes } = get();
        if (notes.length === 0) return;

        try {
          // 获取用户ID和会话ID（从第一个note或localStorage）
          const userId = notes[0]?.user_id || localStorage.getItem('userId') || 'default_user';
          const sessionId = notes[0]?.session_id || localStorage.getItem('sessionId') || 'default_session';

          const response = await fetch('/api/notes/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: userId,
              session_id: sessionId,
              export_format: format,
              include_user_comments: true,
            }),
          });

          const data = await response.json();

          if (data.success) {
            // 下载文件
            const blob = new Blob([data.exported_data], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = data.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          }
        } catch (error) {
          console.error('[Workspace] Export notes failed:', error);
        }
      },

      exportSelectedNotes: async () => {
        const { notes } = get();
        const selected = notes.filter(n => n.select_status === 1);
        if (selected.length === 0) return;

        const exportText = selected
          .map((note, index) => {
            const title = note.title || note.name || `Note ${index + 1}`;
            return `# ${title}\n${note.context}\n`;
          })
          .join('\n');

        try {
          const blob = new Blob([exportText], { type: 'text/plain;charset=utf-8' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `selected_notes_${new Date().toISOString().slice(0, 10)}.txt`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        } catch (error) {
          console.error('[Workspace] Export selected notes failed:', error);
        }
      },

      createNoteFromContent: async (content: WorkspaceContent) => {
        try {
          const userId = localStorage.getItem('userId') || 'default_user';
          const sessionId = localStorage.getItem('sessionId') || 'default_session';
          const action = content.metadata?.agentId || 'document';
          const name = `doc_${Date.now()}`;

          // 使用 /juben/notes/create 路径，与其他 API 调用保持一致
          const authHeader = getAuthHeaderValue();
          const response = await fetch('/juben/notes/create', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(authHeader ? { Authorization: authHeader } : {}),
            },
            body: JSON.stringify({
              user_id: userId,
              session_id: sessionId,
              action,
              name,
              context: content.content,
              title: content.title,
              content_type: 'document',
              metadata: content.metadata || {},
            }),
          });

          const raw = await response.text();
          let data: any = null;
          if (raw) {
            try {
              data = JSON.parse(raw);
            } catch {
              data = null;
            }
          }

          if (!response.ok) {
            console.error('[Workspace] Create note failed:', response.status, raw || 'empty response');
            return null;
          }

          if (data?.success) {
            await get().loadNotes(userId, sessionId);
            return data?.data?.note_id || null;
          }
          return null;
        } catch (error) {
          console.error('[Workspace] Create note from content failed:', error);
          return null;
        }
      },

      updateNotesSelectionBulk: async (notesList: Note[], selected: boolean) => {
        if (notesList.length === 0) return;
        const userId = notesList[0]?.user_id || localStorage.getItem('userId') || 'default_user';
        const sessionId = notesList[0]?.session_id || localStorage.getItem('sessionId') || 'default_session';
        try {
          // 使用 /juben/notes/batch-select 路径，与其他 API 调用保持一致
          const authHeader = getAuthHeaderValue();
          await fetch('/juben/notes/batch-select', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(authHeader ? { Authorization: authHeader } : {}),
            },
            body: JSON.stringify({
              user_id: userId,
              session_id: sessionId,
              selections: notesList.map((note) => ({
                action: note.action,
                name: note.name,
                selected,
                user_comment: note.user_comment,
              })),
            }),
          });

          set((state) => ({
            notes: state.notes.map(n =>
              notesList.some(target => target.id === n.id)
                ? { ...n, select_status: selected ? 1 : 0 }
                : n
            ),
          }));

          await get().loadNotes(userId, sessionId);
        } catch (error) {
          console.error('[Workspace] Bulk update note selection failed:', error);
        }
      },

      _addToHistory: (content) => {
        set((state) => {
          // 移除当前索引之后的所有历史记录
          const newHistory = state.contentHistory.slice(0, state.historyIndex + 1);
          newHistory.push(content);

          // 限制历史记录数量
          if (newHistory.length > 50) {
            newHistory.shift();
          }

          const newIndex = newHistory.length - 1;

          return {
            contentHistory: newHistory,
            historyIndex: newIndex,
            canUndo: newIndex > 0,
            canRedo: false,
          };
        });
      },
    }),
    { name: 'WorkspaceStore' }
  )
);

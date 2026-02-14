import { getAuthHeaderValue } from './api';

type CreateNotePayload = {
  user_id: string;
  session_id: string;
  action: string;
  name: string;
  context: string;
  title?: string;
  content_type?: string;
  metadata?: Record<string, any>;
};

async function parseResponseJsonSafe(response: Response): Promise<any> {
  const raw = await response.text();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getAuthHeaders(): HeadersInit {
  const authHeader = getAuthHeaderValue();
  return {
    'Content-Type': 'application/json',
    ...(authHeader ? { Authorization: authHeader } : {}),
  };
}

export type Note = {
  id: string;
  user_id: string;
  session_id: string;
  action: string;
  name: string;
  title?: string;
  context: string;
  select_status: number;
  user_comment?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
};

export async function createNote(payload: CreateNotePayload): Promise<{
  success: boolean;
  note_id?: string;
  message?: string;
}> {
  try {
    // 使用 /juben/notes/create 路径，与其他 API 调用保持一致
    const response = await fetch('/juben/notes/create', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await parseResponseJsonSafe(response);
    if (!response.ok) {
      // Handle both string and array/object detail formats
      let errorMsg = data?.message || `创建 Note 失败(${response.status})`;
      if (Array.isArray(data?.detail)) {
        errorMsg = data.detail.map((d: any) => d?.msg || String(d)).join('; ');
      } else if (typeof data?.detail === 'string') {
        errorMsg = data.detail;
      }
      console.error('[noteService] 创建 Note 失败:', response.status, errorMsg, data);
      return { success: false, message: errorMsg };
    }
    if (data?.success) {
      return { success: true, note_id: data?.data?.note_id };
    }
    return { success: false, message: data?.message || '创建 Note 失败' };
  } catch (error) {
    console.error('[noteService] 创建 Note 异常:', error);
    return { success: false, message: error instanceof Error ? error.message : '创建 Note 失败' };
  }
}

export async function listSessionNotes(userId: string, sessionId: string): Promise<{
  success: boolean;
  notes: Note[];
  message?: string;
}> {
  try {
    const params = new URLSearchParams({ session_id: sessionId });

    // 使用 /juben/notes/list 路径，与其他 API 调用保持一致
    const response = await fetch(`/juben/notes/list?user_id=${encodeURIComponent(userId)}&${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    const data = await parseResponseJsonSafe(response);
    if (!response.ok) {
      // Handle both string and array/object detail formats
      let errorMsg = data?.message || `获取 Note 列表失败(${response.status})`;
      if (Array.isArray(data?.detail)) {
        errorMsg = data.detail.map((d: any) => d?.msg || String(d)).join('; ');
      } else if (typeof data?.detail === 'string') {
        errorMsg = data.detail;
      }
      console.error('[noteService] 获取 Note 列表失败:', response.status, errorMsg);
      return { success: false, notes: [], message: errorMsg };
    }
    if (data?.success) {
      return { success: true, notes: data.notes || [] };
    }
    return { success: false, notes: [], message: data?.message || '获取 Note 列表失败' };
  } catch (error) {
    console.error('[noteService] 获取 Note 列表异常:', error);
    return { success: false, notes: [], message: error instanceof Error ? error.message : '获取 Note 列表失败' };
  }
}

export async function updateNoteContent(noteId: string, userId: string, content: string): Promise<{
  success: boolean;
  message?: string;
}> {
  try {
    const params = new URLSearchParams({ user_id: userId });
    // 使用 /juben/notes 路径，与其他 API 调用保持一致
    const response = await fetch(`/juben/notes/${noteId}?${params.toString()}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content }),
    });
    const data = await parseResponseJsonSafe(response);
    if (!response.ok) {
      return { success: false, message: data?.detail || `更新 Note 失败(${response.status})` };
    }
    if (data?.success) {
      return { success: true };
    }
    return { success: false, message: data?.message || '更新 Note 失败' };
  } catch (error) {
    console.error('更新 Note 失败:', error);
    return { success: false, message: '更新 Note 失败' };
  }
}

/**
 * OCR 服务
 * 提供 OCR 识别相关的 API 调用
 */

import { api } from './api';

// ==================== 类型定义 ====================

export type OCRStatus = 'processing' | 'completed' | 'failed';

export type OutputFormat = 'text' | 'markdown' | 'json' | 'structured';

export interface OCRStatusResponse {
  available: boolean;
  gpu_enabled: boolean;
  supported_formats: string[];
  output_formats: string[];
}

export interface OCRResult {
  task_id: string;
  status: OCRStatus;
  success: boolean;
  text?: string;
  metadata?: {
    processing_time?: number;
    box_count?: number;
    timestamp?: string;
    mode?: string;
    image_shape?: number[];
  };
  error?: string;
  saved_paths?: Record<string, string>;
}

export interface OCREvent {
  event: 'content' | 'progress' | 'error' | 'complete' | 'system';
  data: {
    content?: string;
    metadata?: Record<string, unknown>;
    timestamp: string;
    task_id?: string;
    status?: string;
    error?: string;
    [key: string]: unknown;
  };
}

export interface OCRTaskInfo {
  task_id: string;
  status: OCRStatus;
  filename: string;
  created_at: string;
  result?: OCRResult;
  error?: string;
}

// ==================== OCR 服务类 ====================

class OCRService {
  private basePath = '/juben/ocr';

  /**
   * 获取 OCR 服务状态
   */
  async getStatus(): Promise<OCRStatusResponse> {
    return api.get<OCRStatusResponse>(`${this.basePath}/status`);
  }

  /**
   * 上传文件进行 OCR 识别（流式）
   * @param file 上传的文件
   * @param options 识别选项
   * @param onMessage SSE 消息回调
   * @param onError 错误回调
   * @param onClose 关闭回调
   * @returns 关闭连接的函数
   */
  async uploadAndRecognize(
    file: File,
    options: {
      outputFormat?: OutputFormat;
      useStructure?: boolean;
      saveResult?: boolean;
    } = {},
    onMessage: (event: OCREvent) => void,
    onError?: (error: Error) => void,
    onClose?: () => void
  ): Promise<() => void> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('output_format', options.outputFormat || 'text');
    formData.append('use_structure', String(options.useStructure || false));
    formData.append('save_result', String(options.saveResult !== false));

    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/upload`;

    console.log('[OCR] Uploading file:', file.name, 'Size:', file.size);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let closed = false;

      const read = async () => {
        try {
          while (!closed) {
            const { done, value } = await reader.read();

            if (done) {
              console.log('[OCR] Stream completed');
              onClose?.();
              break;
            }

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data.trim()) {
                  try {
                    const event = JSON.parse(data);
                    onMessage(event);
                  } catch (e) {
                    console.error('[OCR] Error parsing event:', e, 'Data:', data);
                  }
                }
              }
            }
          }
        } catch (error) {
          console.error('[OCR] Read error:', error);
          if (!closed) {
            onError?.(error as Error);
          }
        }
      };

      read();

      return () => {
        console.log('[OCR] Closing connection');
        closed = true;
        reader.cancel();
      };
    } catch (error) {
      console.error('[OCR] Upload error:', error);
      throw error;
    }
  }

  /**
   * 批量 OCR 识别
   * @param filePaths 文件路径列表
   * @param outputFormat 输出格式
   * @param onProgress 进度回调
   * @returns 关闭连接的函数
   */
  async batchRecognize(
    filePaths: string[],
    outputFormat: OutputFormat = 'text',
    onProgress?: (completed: number, total: number) => void
  ): Promise<OCRResult[]> {
    // SSE 实现批量处理
    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/batch`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify({
        file_paths: filePaths,
        output_format: outputFormat,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const results: OCRResult[] = [];
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Response body is null');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data.trim()) {
            try {
              const event = JSON.parse(data);
              if (event.event === 'result') {
                results.push(event.data);
                onProgress?.(results.length, filePaths.length);
              }
            } catch (e) {
              console.error('[OCR] Error parsing batch event:', e);
            }
          }
        }
      }
    }

    return results;
  }

  /**
   * 获取 OCR 识别结果
   * @param taskId 任务 ID
   */
  async getResult(taskId: string): Promise<OCRResult> {
    return api.get<OCRResult>(`${this.basePath}/result/${taskId}`);
  }

  /**
   * 下载 OCR 识别结果
   * @param taskId 任务 ID
   * @param format 文件格式
   */
  async downloadResult(taskId: string, format: 'txt' | 'md' | 'json' = 'txt'): Promise<void> {
    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/download/${taskId}?format=${format}`;

    const response = await fetch(url, {
      headers: {
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    // 从响应头获取文件名
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `ocr_result.${format}`;
    if (contentDisposition) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
      if (matches?.[1]) {
        filename = matches[1].replace(/['"]/g, '');
      }
    }

    // 创建下载链接
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  /**
   * 删除任务记录
   * @param taskId 任务 ID
   */
  async deleteTask(taskId: string): Promise<{ success: boolean; message: string }> {
    return api.delete<{ success: boolean; message: string }>(`${this.basePath}/task/${taskId}`);
  }

  /**
   * 获取所有任务列表
   * @param limit 返回数量限制
   */
  async listTasks(limit: number = 50): Promise<{ success: boolean; data: OCRTaskInfo[]; total: number }> {
    return api.get<{ success: boolean; data: OCRTaskInfo[]; total: number }>(
      `${this.basePath}/tasks`,
      { limit: String(limit) }
    );
  }

  /**
   * 获取认证头
   */
  private getAuthHeader(): string | null {
    try {
      const raw = localStorage.getItem('auth-storage');
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      const token = parsed?.state?.tokens?.accessToken;
      return token ? `Bearer ${token}` : null;
    } catch {
      return null;
    }
  }

  /**
   * 检查 OCR 服务是否可用
   */
  async isAvailable(): Promise<boolean> {
    try {
      const status = await this.getStatus();
      return status.available;
    } catch {
      return false;
    }
  }
}

// 导出单例
export const ocrService = new OCRService();
export default ocrService;

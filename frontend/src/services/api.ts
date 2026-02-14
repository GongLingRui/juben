/**
 * API 客户端基础配置
 */

import { createLogger } from '@/utils/logger';
import { retryWithBackoff } from './retryService';

const log = createLogger('api');

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * API 客户端类 - 支持请求取消
 */
class APIClient {
  private baseURL: string;
  private abortControllers = new Map<string, AbortController>();
  private defaultRetry = {
    maxRetries: 2,
    initialDelay: 500,
    maxDelay: 4000,
    backoffFactor: 2,
    enableJitter: true,
  };

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private getAuthHeader(): string | null {
    return getAuthHeaderValue();
  }

  /**
   * 获取完整的 URL
   */
  private getUrl(path: string): string {
    return `${this.baseURL}${path}`;
  }

  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    path: string,
    data?: any,
    params?: Record<string, string>
  ): Promise<T> {
    const url = new URL(this.getUrl(path));
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    // 生成请求ID
    const requestId = `${method}:${path}:${Date.now()}:${Math.random()}`;

    // 创建 AbortController
    const abortController = new AbortController();
    this.abortControllers.set(requestId, abortController);

    const execute = async () => {
      try {
        const authHeader = this.getAuthHeader();
        const response = await fetch(url.toString(), {
          method,
          headers: {
            'Content-Type': 'application/json',
            ...(authHeader ? { Authorization: authHeader } : {}),
          },
          body: data ? JSON.stringify(data) : undefined,
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new APIError(response.status, await response.text());
        }

        return response.json();
      } finally {
        // 清理 AbortController
        this.abortControllers.delete(requestId);
      }
    };

    const result = await retryWithBackoff(execute, this.defaultRetry);
    if (!result.succeeded) {
      throw result.error;
    }
    return result.data as T;
  }

  /**
   * GET 请求
   */
  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>('GET', path, undefined, params);
  }

  /**
   * POST 请求
   */
  async post<T>(path: string, data?: any): Promise<T> {
    const url = this.getUrl(path);
    log.debug('POST Request:', url, data);
    try {
      const result = await this.request<T>('POST', path, data);
      log.debug('POST Success:', result);
      return result;
    } catch (error) {
      log.error('POST Error:', error);
      throw error;
    }
  }

  /**
   * PUT 请求
   */
  async put<T>(path: string, data?: any, params?: Record<string, string>): Promise<T> {
    return this.request<T>('PUT', path, data, params);
  }

  /**
   * DELETE 请求
   */
  async delete<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>('DELETE', path, undefined, params);
  }

  /**
   * 取消指定ID的请求
   */
  cancelRequest(requestId: string): boolean {
    const controller = this.abortControllers.get(requestId);
    if (controller) {
      controller.abort();
      return true;
    }
    return false;
  }

  /**
   * 取消所有进行中的请求
   */
  cancelAllRequests(): void {
    for (const [requestId, controller] of this.abortControllers) {
      controller.abort();
    }
    this.abortControllers.clear();
  }

  /**
   * 创建 SSE 连接
   */
  async connectSSE(
    path: string,
    data: any,
    onMessage: (event: MessageEvent) => void,
    onError?: (error: Error) => void,
    onClose?: () => void
  ): Promise<() => void> {
    const url = this.getUrl(path);
    console.log('[SSE] Connecting to:', url);
    console.log('[SSE] Request data:', JSON.stringify(data).substring(0, 200));

    // 添加fetch超时检测
    const timeoutId = setTimeout(() => {
      console.error('[SSE] Request timeout - no response after 30 seconds');
    }, 30000);

    try {
      console.log('[SSE] Calling fetch...');
      const authHeader = this.getAuthHeader();
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify(data),
      });

      clearTimeout(timeoutId);
      console.log('[SSE] Got response, status:', response.status);

      console.log('[SSE] Response status:', response.status);
      console.log('[SSE] Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[SSE] Response error:', errorText);
        throw new APIError(response.status, errorText);
      }

      if (!response.body) {
        console.error('[SSE] Response body is null');
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let closed = false;

      const read = async () => {
        try {
          console.log('[SSE] Starting to read stream...');
          while (!closed) {
            const { done, value } = await reader.read();

            if (done) {
              console.log('[SSE] Stream completed');
              onClose?.();
              break;
            }

            const chunk = decoder.decode(value, { stream: true });
            console.log('[SSE] Received chunk:', chunk.substring(0, 200));
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data.trim()) {
                  try {
                    const event = new MessageEvent('message', { data });
                    console.log('[SSE] Parsed event:', data.substring(0, 200));
                    onMessage(event);
                  } catch (e) {
                    console.error('[SSE] Error parsing event:', e);
                  }
                }
              }
            }
          }
        } catch (error) {
          console.error('[SSE] Read error:', error);
          if (!closed) {
            onError?.(error as Error);
          }
        }
      };

      read();

      // 返回关闭函数
      return () => {
        console.log('[SSE] Closing connection');
        closed = true;
        reader.cancel();
      };
    } catch (error) {
      console.error('[SSE] Connection error:', error);
      throw error;
    }
  }
}

/**
 * API 错误类
 */
export class APIError extends Error {
  constructor(
    public status: number,
    public message: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// 导出单例
export const api = new APIClient();

export default api;

export function getAuthHeaderValue(): string | null {
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

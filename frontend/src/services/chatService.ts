/**
 * 聊天服务 - 支持多Agent
 * 根据Agent配置使用不同的API端点
 */

import api, { APIError } from './api';
import type { ChatRequest, Message, SSEvent, Thought } from '@/types';
import { getAgentById } from '@/config/agents';
import { createSSEClient, type RobustSSEClient } from './sseClient';

/**
 * 发送聊天消息（非流式）
 */
export async function sendMessage(request: ChatRequest): Promise<Message> {
  try {
    // 获取agent配置来确定端点
    const agent = request.agent_id ? getAgentById(request.agent_id) : null;
    // 统一走 /juben/chat，由后端按 agent_id 分发，避免旧端点404
    const endpoint = '/juben/chat';

    const response = await api.post<{ success: boolean; data?: any }>(endpoint, request);

    if (!response.success) {
      throw new Error(response.data?.message || '发送失败');
    }

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: response.data?.content || '',
      timestamp: new Date().toISOString(),
      agentName: agent?.displayName || response.data?.agent,
      metadata: response.data?.metadata,
    };
  } catch (error) {
    if (error instanceof APIError) {
      throw new Error(`API 错误: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 发送聊天消息（流式）- 支持多Agent（旧版，兼容性保留）
 */
export function streamMessage(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onEvent: (event: SSEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  const endpoint = '/juben/chat';

  let fullContent = '';

  const closeConnection = api.connectSSE(
    endpoint,
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[chatService] Received SSE data:', data);

        // 兼容多种事件格式
        // 格式1: { event: "llm_chunk", data: { content: "..." } }
        // 格式2: { event_type: "message", data: "..." }
        const eventType = data.event || data.event_type || data.type;
        if (eventType === 'heartbeat') {
          return;
        }
        const eventData = data.data || {};

        // 处理内容类事件
        if (
          eventType === 'llm_chunk' ||
          eventType === 'message' ||
          eventType === 'data' ||
          eventType === 'content'
        ) {
          const content = eventData?.content || eventData || '';
          if (typeof content === 'string') {
            fullContent += content;
            console.log('[chatService] Calling onChunk with:', content.substring(0, 50));
            onChunk(content);
          }
        }

        // 处理系统事件
        if (eventType === 'system') {
          console.log('[chatService] Processing system event:', eventData);
          onEvent({
            event: 'system',
            data: {
              content: eventData?.content || eventData || '',
              type: 'system',
            },
            timestamp: data.timestamp || new Date().toISOString(),
          });
        }

        // 处理计费事件
        if (eventType === 'billing') {
          onEvent({
            event: 'billing',
            data: {
              content: eventData?.content || eventData || '',
              type: 'billing',
            },
            timestamp: data.timestamp || new Date().toISOString(),
          });
        }

        // 处理错误事件
        if (eventType === 'error' || eventType === 'workflow_error') {
          const errorMsg = eventData?.error || eventData?.message || eventData?.content || '未知错误';
          onEvent({
            event: 'error',
            data: {
              content: errorMsg,
              error: errorMsg,
            },
            timestamp: data.timestamp || new Date().toISOString(),
          });
        }

        // 处理工具事件
        if (
          eventType === 'tool_start' ||
          eventType === 'tool_complete' ||
          eventType === 'tool_processing' ||
          (eventType && eventType.startsWith('tool_'))
        ) {
          onEvent({
            event: eventType,
            data: eventData,
            timestamp: data.timestamp || new Date().toISOString(),
          });
        }

        // 检查是否完成
        if (
          eventType === 'done' ||
          eventType === 'complete' ||
          eventType === 'finished' ||
          eventType === 'end'
        ) {
          onComplete();
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e, event.data);
      }
    },
    onError,
    () => {
      onComplete();
    }
  );

  return closeConnection;
}

/**
 * 发送聊天消息（流式）- 简化版供 chatStore 使用
 */
export async function sendMessageToAgent(
  content: string,
  agentId: string,
  onChunk: (chunk: string, isThought: boolean) => void,
  onThought?: (thought: Thought) => void
): Promise<void> {
  const endpoint = '/juben/chat';

  const request: ChatRequest = {
    input: content,
    agent_id: agentId,
    project_id: localStorage.getItem('projectId') || undefined,
  };

  let thoughtStep = 0;

  await api.connectSSE(
    endpoint,
    request,
    (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.type || data.event_type || data.event;
        if (eventType === 'heartbeat') {
          return;
        }
        const eventData = data.data || {};

        const contentValue = eventData?.content || eventData || data.message || '';
        const contentType = eventData?.content_type || eventData?.type || data.content_type;

        const isThought =
          eventType === 'thinking' ||
          eventType === 'thought' ||
          contentType === 'thought' ||
          contentType === 'plan_step';

        if (typeof contentValue === 'string' && contentValue) {
          onChunk(contentValue, isThought);
          if (isThought && onThought) {
            thoughtStep += 1;
            onThought({
              step: thoughtStep,
              content: contentValue,
              timestamp: data.timestamp || new Date().toISOString(),
            });
          }
        }
      } catch (error) {
        console.error('[sendMessageToAgent] Error parsing SSE:', error);
      }
    },
    (error) => {
      console.error('[sendMessageToAgent] SSE error:', error);
      throw error;
    },
    () => {
      return;
    }
  );
}

/**
 * 聊天会话管理器
 * 使用 RobustSSEClient 提供健壮的 SSE 连接、断点续传和自动重连
 */
export class ChatSessionManager {
  private sseClient: RobustSSEClient | null = null;
  private currentRequest: ChatRequest | null = null;
  private eventHandlers: Map<string, Set<Function>> = new Map();

  constructor(config?: {
    maxReconnectAttempts?: number;
    reconnectDelay?: number;
    heartbeatInterval?: number;
    enableCache?: boolean;
  }) {
    this.sseClient = createSSEClient({
      endpoint: '/juben/chat',
      maxReconnectAttempts: config?.maxReconnectAttempts || 3,
      reconnectDelay: config?.reconnectDelay || 2000,
      heartbeatInterval: config?.heartbeatInterval || 30000,
      enableCache: config?.enableCache !== false,
    });

    // 注册事件处理器
    this.sseClient.onEvent((event) => this._handleSSEEvent(event));
    this.sseClient.onError((error) => this._handleError(error));
    this.sseClient.onStateChange((state) => this._handleStateChange(state));
  }

  /**
   * 发送消息
   */
  async sendMessage(
    request: ChatRequest,
    options?: {
      messageId?: string;
      fromSequence?: number;
    }
  ): Promise<void> {
    this.currentRequest = request;

    try {
      await this.sseClient!.connect(request, options);
    } catch (error) {
      this._handleError(error as Error);
      throw error;
    }
  }

  /**
   * 断点续传
   */
  async resume(fromSequence?: number): Promise<boolean> {
    if (!this.sseClient!.getState().currentMessageId) {
      console.warn('[ChatSessionManager] No message ID available for resume');
      return false;
    }

    if (!this.currentRequest) {
      console.warn('[ChatSessionManager] No request available for resume');
      return false;
    }

    try {
      await this.sseClient!.connect(this.currentRequest, {
        messageId: this.sseClient!.getState().currentMessageId,
        fromSequence: fromSequence || this.sseClient!.getState().lastSequence,
      });
      return true;
    } catch (error) {
      console.error('[ChatSessionManager] Resume failed:', error);
      return false;
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.sseClient?.disconnect();
  }

  /**
   * 获取当前状态
   */
  getState() {
    return this.sseClient?.getState();
  }

  /**
   * 订阅事件
   */
  on(event: string, handler: Function): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // 返回取消订阅函数
    return () => {
      this.eventHandlers.get(event)?.delete(handler);
    };
  }

  /**
   * 处理 SSE 事件
   */
  private _handleSSEEvent(event: SSEvent): void {
    console.log('[ChatSessionManager] SSE event:', event);

    // 触发 'event' 通用事件
    this._emit('event', event);

    // 根据事件类型触发特定事件
    switch (event.event) {
      case 'message':
        this._emit('message', event.data?.content || '');
        break;

      case 'thinking':
        this._emit('thinking', event.data?.content || '');
        break;

      case 'progress':
        this._emit('progress', event.data);
        break;

      case 'error':
        this._emit('error', new Error(event.data?.content || '未知错误'));
        break;

      case 'complete':
        this._emit('complete', event.data);
        break;

      case 'heartbeat':
        // 心跳事件不触发
        break;

      default:
        this._emit(event.event, event.data);
    }
  }

  /**
   * 处理错误
   */
  private _handleError(error: Error): void {
    console.error('[ChatSessionManager] Error:', error);
    this._emit('error', error);

    // 如果是网络错误，尝试重连
    if (this._isNetworkError(error)) {
      const state = this.sseClient!.getState();
      if (state.reconnectAttempts < 3) {
        this._emit('reconnecting', state.reconnectAttempts + 1);
      }
    }
  }

  /**
   * 处理状态变化
   */
  private _handleStateChange(state: any): void {
    console.log('[ChatSessionManager] State changed:', state);
    this._emit('stateChange', state);

    if (state.isConnected) {
      this._emit('connected');
    } else {
      this._emit('disconnected');
    }
  }

  /**
   * 判断是否是网络错误
   */
  private _isNetworkError(error: any): boolean {
    return (
      error?.name === 'TypeError' ||
      error?.message?.includes('fetch') ||
      error?.message?.includes('network')
    );
  }

  /**
   * 触发事件
   */
  private _emit(event: string, ...args: any[]): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(...args);
        } catch (error) {
          console.error(`[ChatSessionManager] Error in ${event} handler:`, error);
        }
      });
    }
  }

  /**
   * 清理资源
   */
  dispose(): void {
    this.disconnect();
    this.eventHandlers.clear();
    this.sseClient?.dispose();
  }
}

/**
 * 创建聊天会话（便捷函数）
 */
export function createChatSession(config?: {
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  enableCache?: boolean;
}): ChatSessionManager {
  return new ChatSessionManager(config);
}

/**
 * 获取聊天历史
 */
export async function getChatHistory(sessionId: string): Promise<Message[]> {
  try {
    const response = await api.get<{ success: boolean; messages?: Message[] }>(
      `/juben/history/${sessionId}`
    );

    return response.messages || [];
  } catch (error) {
    console.error('Failed to fetch chat history:', error);
    return [];
  }
}

/**
 * 清除聊天历史
 */
export async function clearChatHistory(sessionId: string): Promise<boolean> {
  try {
    const response = await api.delete<{ success: boolean }>(`/juben/history/${sessionId}`);
    return response.success;
  } catch (error) {
    console.error('Failed to clear chat history:', error);
    return false;
  }
}

/**
 * 分析意图
 */
export async function analyzeIntent(input: string): Promise<{
  intent: string;
  confidence: number;
  suggestedAgent?: string;
}> {
  console.log('[analyzeIntent] Starting intent analysis for:', input);
  try {
    const response = await api.post<{ success: boolean; intent_result?: any }>(
      '/juben/intent/analyze',
      { input }
    );
    console.log('[analyzeIntent] Got response:', response);

    const intentResult = response.intent_result || {};

    return {
      intent: intentResult.intent || 'general',
      confidence: intentResult.confidence || 0,
      suggestedAgent: intentResult.suggested_agent,
    };
  } catch (error) {
    console.error('Failed to analyze intent:', error);
    return { intent: 'general', confidence: 0 };
  }
}

/**
 * SSE 流式响应 Hook
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { streamMessage } from '@/services/chatService';
import type { ChatRequest, SSEEvent } from '@/types';

interface UseStreamOptions {
  onChunk?: (chunk: string) => void;
  onEvent?: (event: SSEEvent) => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

interface UseStreamReturn {
  isStreaming: boolean;
  content: string;
  events: SSEEvent[];
  startStream: (request: ChatRequest) => void;
  stopStream: () => void;
  reset: () => void;
}

export function useStream(options: UseStreamOptions = {}): UseStreamReturn {
  const { onChunk, onEvent, onComplete, onError } = options;

  const [isStreaming, setIsStreaming] = useState(false);
  const [content, setContent] = useState('');
  const [events, setEvents] = useState<SSEEvent[]>([]);

  const closeRef = useRef<(() => void) | null>(null);
  const contentRef = useRef('');
  const eventsRef = useRef<SSEEvent[]>([]);

  /**
   * 开始流式响应
   */
  const startStream = useCallback(
    (request: ChatRequest) => {
      setIsStreaming(true);
      setContent('');
      setEvents([]);
      contentRef.current = '';
      eventsRef.current = [];

      closeRef.current = streamMessage(
        request,
        (chunk) => {
          contentRef.current += chunk;
          setContent(contentRef.current);
          onChunk?.(chunk);
        },
        (event) => {
          eventsRef.current.push(event);
          setEvents([...eventsRef.current]);
          onEvent?.(event);
        },
        () => {
          setIsStreaming(false);
          onComplete?.();
        },
        (error) => {
          setIsStreaming(false);
          onError?.(error);
        }
      );
    },
    [onChunk, onEvent, onComplete, onError]
  );

  /**
   * 停止流式响应
   */
  const stopStream = useCallback(() => {
    if (closeRef.current) {
      closeRef.current();
      closeRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    stopStream();
    setContent('');
    setEvents([]);
    contentRef.current = '';
    eventsRef.current = [];
  }, [stopStream]);

  /**
   * 组件卸载时清理
   */
  useEffect(() => {
    return () => {
      if (closeRef.current) {
        closeRef.current();
      }
    };
  }, []);

  return {
    isStreaming,
    content,
    events,
    startStream,
    stopStream,
    reset,
  };
}

/**
 * 简化版流式 Hook，只关注内容
 */
export function useStreamContent(request: ChatRequest | null) {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!request) return;

    setIsStreaming(true);
    setContent('');
    setError(null);

    let currentContent = '';

    const close = streamMessage(
      request,
      (chunk) => {
        currentContent += chunk;
        setContent(currentContent);
      },
      () => {},
      () => {
        setIsStreaming(false);
      },
      (err) => {
        setError(err);
        setIsStreaming(false);
      }
    );

    return () => {
      close();
    };
  }, [request]);

  return { content, isStreaming, error };
}

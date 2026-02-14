/**
 * 工作流监控自定义 Hook
 * 管理 SSE 连接和工作流状态
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { WorkflowEvent, NodeStatus, WorkflowExecutionState } from '@/components/workflow/types';
import { API_BASE_URL } from '@/services/api';

interface UseWorkflowMonitorOptions {
  baseUrl?: string;
  onEvent?: (event: WorkflowEvent) => void;
  onError?: (error: Error) => void;
  autoConnect?: boolean;
}

interface UseWorkflowMonitorReturn {
  workflowId: string | null;
  executionState: WorkflowExecutionState | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  connect: (workflowId: string) => void;
  disconnect: () => void;
  getNodeStatus: (nodeId: string) => NodeStatus | undefined;
  reset: () => void;
}

export function useWorkflowMonitor(options: UseWorkflowMonitorOptions = {}): UseWorkflowMonitorReturn {
  const {
    baseUrl = API_BASE_URL,
    onEvent,
    onError,
    autoConnect = false,
  } = options;

  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [executionState, setExecutionState] = useState<WorkflowExecutionState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const nodeStatusesRef = useRef<Map<string, NodeStatus>>(new Map());
  const startTimeRef = useRef<string | null>(null);

  // 处理工作流事件
  const handleEvent = useCallback((event: WorkflowEvent) => {
    // 触发外部回调
    if (onEvent) {
      onEvent(event);
    }

    // 更新工作流 ID
    if ('workflow_id' in event && event.workflow_id) {
      setWorkflowId(event.workflow_id);
    } else if ('metadata' in event && event.metadata?.workflow_id) {
      setWorkflowId(event.metadata.workflow_id);
    }

    // 处理不同类型的事件
    switch (event.event_type) {
      case 'workflow_initialized':
        setExecutionState({
          workflowId: event.workflow_id,
          status: 'in_progress',
          currentStage: 'initialized',
          progress: 0,
          nodeStates: new Map(),
          startTime: event.timestamp,
        });
        startTimeRef.current = event.timestamp;
        break;

      case 'workflow_node_event':
        const { node_name, status, output_snapshot } = event.metadata || {};

        // 更新节点状态
        if (node_name && status) {
          nodeStatusesRef.current.set(node_name, status as NodeStatus);

          // 计算进度
          const totalNodes = 8; // 根据实际节点数调整
          const completedNodes = Array.from(nodeStatusesRef.current.values()).filter(
            (s) => s === NodeStatus.SUCCESS
          ).length;
          const progress = Math.round((completedNodes / totalNodes) * 100);

          setExecutionState((prev) => ({
            ...prev!,
            workflowId: event.metadata?.workflow_id || prev?.workflowId || '',
            status: 'in_progress',
            currentStage: node_name,
            progress,
            nodeStates: new Map(nodeStatusesRef.current),
            startTime: startTimeRef.current || event.timestamp,
          }));
        }
        break;

      case 'workflow_completed':
        setExecutionState((prev) => ({
          ...prev!,
          status: 'completed',
          currentStage: 'completed',
          progress: 100,
          endTime: event.timestamp,
        }));
        // 自动断开连接
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
          setIsConnected(false);
        }
        break;

      case 'workflow_paused':
        setExecutionState((prev) => ({
          ...prev!,
          status: 'paused',
          currentStage: 'paused',
        }));
        break;

      case 'workflow_error':
        setExecutionState((prev) => ({
          ...prev!,
          status: 'failed',
          endTime: event.timestamp,
        }));
        if (onError) {
          onError(new Error(event.error || 'Workflow error'));
        }
        break;
    }
  }, [onEvent, onError]);

  // 连接到工作流 SSE 端点
  const connect = useCallback((id: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setIsConnecting(true);
    setError(null);

    try {
      const url = `${baseUrl}/juben/plot-points-workflow/execute?workflow_id=${id}`;
      const eventSource = new EventSource(url);

      eventSource.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        setWorkflowId(id);
      };

      eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          handleEvent(data);
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      eventSource.onerror = (err) => {
        setIsConnected(false);
        setIsConnecting(false);
        const error = new Error('SSE connection error');
        setError(error);
        if (onError) {
          onError(error);
        }
        eventSource.close();
        eventSourceRef.current = null;
      };

      eventSourceRef.current = eventSource;
    } catch (err) {
      setIsConnecting(false);
      const error = err instanceof Error ? err : new Error('Failed to connect');
      setError(error);
      if (onError) {
        onError(error);
      }
    }
  }, [baseUrl, handleEvent, onError]);

  // 断开连接
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setWorkflowId(null);
    setExecutionState(null);
    nodeStatusesRef.current.clear();
    startTimeRef.current = null;
  }, []);

  // 获取节点状态
  const getNodeStatus = useCallback((nodeId: string) => {
    return nodeStatusesRef.current.get(nodeId);
  }, []);

  // 重置状态
  const reset = useCallback(() => {
    disconnect();
    setError(null);
  }, [disconnect]);

  // 清理
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // 自动连接
  useEffect(() => {
    if (autoConnect && workflowId) {
      connect(workflowId);
    }
  }, [autoConnect, workflowId, connect]);

  return {
    workflowId,
    executionState,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    getNodeStatus,
    reset,
  };
}

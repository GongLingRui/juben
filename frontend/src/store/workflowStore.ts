/**
 * 工作流状态管理 Store
 * 基于 Zustand 实现
 */

import { create } from 'zustand';
import { NodeStatus, WorkflowEvent, NodeDetails, WorkflowExecutionState } from '@/components/workflow/types';

interface WorkflowNodeState {
  id: string;
  status: NodeStatus;
  outputSnapshot?: string;
  error?: string;
  startTime?: string;
  endTime?: string;
  duration?: number;
  details?: NodeDetails;
}

interface WorkflowStore {
  // 当前工作流 ID
  currentWorkflowId: string | null;

  // 工作流执行状态
  executionState: WorkflowExecutionState | null;

  // 节点状态映射
  nodeStates: Map<string, WorkflowNodeState>;

  // 选中的节点
  selectedNodeId: string | null;

  // 事件历史
  eventHistory: WorkflowEvent[];

  // Actions
  setWorkflowId: (id: string | null) => void;
  setExecutionState: (state: WorkflowExecutionState | null) => void;
  updateNodeState: (nodeId: string, updates: Partial<WorkflowNodeState>) => void;
  getNodeState: (nodeId: string) => WorkflowNodeState | undefined;
  setSelectedNode: (nodeId: string | null) => void;
  addEvent: (event: WorkflowEvent) => void;
  clearEvents: () => void;
  reset: () => void;

  // 计算属性
  getProgress: () => number;
  getCompletedCount: () => number;
  getFailedCount: () => number;
}

const initialNodeStates = new Map<string, WorkflowNodeState>();

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  // 初始状态
  currentWorkflowId: null,
  executionState: null,
  nodeStates: initialNodeStates,
  selectedNodeId: null,
  eventHistory: [],

  // Actions
  setWorkflowId: (id) => set({ currentWorkflowId: id }),

  setExecutionState: (state) => set({ executionState: state }),

  updateNodeState: (nodeId, updates) => set((state) => {
    const newMap = new Map(state.nodeStates);
    const existing = newMap.get(nodeId) || {
      id: nodeId,
      status: NodeStatus.IDLE,
    };
    newMap.set(nodeId, { ...existing, ...updates });
    return { nodeStates: newMap };
  }),

  getNodeState: (nodeId) => {
    return get().nodeStates.get(nodeId);
  },

  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),

  addEvent: (event) => set((state) => ({
    eventHistory: [...state.eventHistory, event].slice(-100), // 保留最近100条
  })),

  clearEvents: () => set({ eventHistory: [] }),

  reset: () => set({
    currentWorkflowId: null,
    executionState: null,
    nodeStates: new Map(),
    selectedNodeId: null,
    eventHistory: [],
  }),

  // 计算属性
  getProgress: () => {
    const { nodeStates } = get();
    const total = 8; // 总节点数
    const completed = Array.from(nodeStates.values()).filter(
      (n) => n.status === NodeStatus.SUCCESS
    ).length;
    return total > 0 ? Math.round((completed / total) * 100) : 0;
  },

  getCompletedCount: () => {
    const { nodeStates } = get();
    return Array.from(nodeStates.values()).filter(
      (n) => n.status === NodeStatus.SUCCESS
    ).length;
  },

  getFailedCount: () => {
    const { nodeStates } = get();
    return Array.from(nodeStates.values()).filter(
      (n) => n.status === NodeStatus.FAILED
    ).length;
  },
}));

// 选择器 hooks
export const useWorkflowProgress = () => useWorkflowStore((state) => state.getProgress());
export const useWorkflowNodeState = (nodeId: string) =>
  useWorkflowStore((state) => state.getNodeState(nodeId));
export const useWorkflowSelectedNode = () =>
  useWorkflowStore((state) => {
    const selectedNodeId = state.selectedNodeId;
    return selectedNodeId ? state.getNodeState(selectedNodeId) : null;
  });

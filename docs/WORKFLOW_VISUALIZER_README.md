# React-Flow 工作流监控器

将枯燥的后端工作流等待过程转化为直观的、实时的逻辑流转图。

## 📦 安装

```bash
# 进入前端目录
cd frontend

# 安装依赖（已添加到 package.json）
pnpm install

# 或使用 npm
npm install
```

## 🚀 快速开始

### 1. 基础使用

```tsx
import { WorkflowVisualizer } from '@/components/workflow';

function MyComponent() {
  return (
    <div style={{ height: '600px' }}>
      <WorkflowVisualizer
        workflowId="your-workflow-id"
        onEvent={(event) => console.log('Workflow event:', event)}
      />
    </div>
  );
}
```

### 2. 使用自定义 Hook

```tsx
import { useWorkflowMonitor } from '@/hooks/useWorkflowMonitor';
import { WorkflowVisualizer } from '@/components/workflow';

function WorkflowPage() {
  const { workflowId, connect, disconnect, executionState } = useWorkflowMonitor({
    onEvent: (event) => console.log(event),
    onError: (error) => console.error(error),
  });

  const handleStart = async () => {
    // 启动工作流
    const response = await fetch('/juben/plot-points-workflow/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: '生成一个现代都市短剧',
        user_id: 'user123',
        session_id: 'session456',
      }),
    });

    // 获取 workflowId 并连接
    const data = await response.json();
    connect(data.workflow_id);
  };

  return (
    <div>
      <button onClick={handleStart}>启动工作流</button>
      <WorkflowVisualizer workflowId={workflowId} />
    </div>
  );
}
```

### 3. 使用 Zustand Store

```tsx
import { useWorkflowStore, useWorkflowProgress } from '@/store/workflowStore';
import { WorkflowVisualizer } from '@/components/workflow';

function WorkflowMonitor() {
  const progress = useWorkflowProgress();
  const completedCount = useWorkflowStore((s) => s.getCompletedCount());
  const selectedNode = useWorkflowStore((s) => s.getSelectedNode());

  return (
    <div>
      <div>进度: {progress}%</div>
      <div>已完成: {completedCount} 个节点</div>
      <WorkflowVisualizer workflowId="current-workflow" />
    </div>
  );
}
```

## 🎨 组件 API

### WorkflowVisualizer

| Prop | Type | 默认值 | 描述 |
|------|------|--------|------|
| `workflowId` | `string` | - | 工作流 ID |
| `onEvent` | `(event: WorkflowEvent) => void` | - | 事件回调 |
| `className` | `string` | `''` | 自定义样式类 |

### WorkflowDrawer

| Prop | Type | 默认值 | 描述 |
|------|------|--------|------|
| `isOpen` | `boolean` | - | 是否打开 |
| `onClose` | `() => void` | - | 关闭回调 |
| `details` | `NodeDetails \| null` | - | 节点详情 |

## 📊 工作流拓扑

```
┌─────────────┐
│ 输入验证     │
└──────┬──────┘
       │
┌──────▼──────┐
│ 文本预处理   │
└──────┬──────┘
       │
   ┌───┴───────────────────────────────┐
   │                                     │
┌──▼──────┐ ┌─────────┐ ┌─────────┐    │
│故事大纲  │ │人物小传 │ │大情节点 │◄───┘
└────┬─────┘ └────┬────┘ └────┬────┘
     │            │            │
     └─────────┬──┴────────────┘
               │
         ┌─────▼──────────┐
         │ 详细情节点      │
         └─────┬──────────┘
               │
         ┌─────▼──────────┐
         │ 结果格式化      │
         └─────┬──────────┘
               │
         ┌─────▼──────────┐
         │   思维导图     │
         └────────────────┘
```

## 🎯 节点状态

| 状态 | 颜色 | 描述 |
|------|------|------|
| `idle` | 灰色 | 未开始 |
| `waiting` | 蓝色 | 等待执行 |
| `processing` | 黄色 | 执行中（带动画） |
| `success` | 绿色 | 成功完成 |
| `failed` | 红色 | 执行失败 |
| `skipped` | 灰色 | 已跳过 |

## 📡 SSE 事件格式

### 工作流节点事件

```typescript
{
  event_type: 'workflow_node_event',
  agent_source: 'workflow_orchestrator',
  timestamp: '2026-02-07T12:00:00Z',
  data: '',
  metadata: {
    workflow_id: 'uuid',
    node_name: 'story_outline',
    status: 'success',
    output_snapshot: '故事大纲已生成 (字数: 1500)',
    error: null
  }
}
```

### 工作流状态事件

```typescript
{
  event_type: 'workflow_initialized',
  workflow_id: 'uuid',
  message: '工作流初始化完成',
  timestamp: '2026-02-07T12:00:00Z'
}
```

## 🎨 自定义样式

### 修改节点样式

编辑 `WorkflowNode.tsx` 中的 `statusColors` 对象：

```typescript
const statusColors = {
  [NodeStatus.SUCCESS]: {
    bg: 'bg-green-50',
    border: 'border-green-400',
    // ... 自定义样式
  },
};
```

### 修改节点布局

编辑 `WorkflowVisualizer.tsx` 中的 `createInitialNodes` 函数：

```typescript
const createInitialNodes = (): Node<WorkflowNodeData>[] => [
  {
    id: 'my_custom_node',
    type: 'workflow',
    position: { x: 100, y: 100 },
    data: { /* ... */ },
  },
];
```

## 🔧 高级用法

### 添加自定义边样式

```tsx
const customEdgeTypes: EdgeTypes = {
  custom: CustomEdgeComponent,
};

<ReactFlow edgeTypes={customEdgeTypes} />
```

### 集成到现有页面

```tsx
import { WorkflowVisualizer } from '@/components/workflow';
import { useWorkflowMonitor } from '@/hooks/useWorkflowMonitor';

export default function ExistingPage() {
  const { workflowId, connect } = useWorkflowMonitor();

  // 在现有的工作流启动逻辑中添加
  const handleExistingWorkflowStart = async () => {
    // ... 现有逻辑
    connect(newWorkflowId);
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* 现有内容 */}
      <div>{/* 现有的输入/输出区域 */}</div>

      {/* 工作流可视化 */}
      <div className="h-[600px]">
        <WorkflowVisualizer workflowId={workflowId} />
      </div>
    </div>
  );
}
```

## 📝 类型定义

所有类型定义都在 `types.ts` 中：

```typescript
import {
  NodeStatus,
  WorkflowNodeType,
  WorkflowNodeData,
  WorkflowEvent,
  NodeDetails,
  WorkflowExecutionState,
} from '@/components/workflow/types';
```

## 🐛 调试

### 启用调试模式

```tsx
<WorkflowVisualizer
  workflowId={workflowId}
  onEvent={(event) => console.log('[Workflow Debug]', event)}
/>
```

### 检查 SSE 连接

```tsx
const { isConnected, error, getNodeStatus } = useWorkflowMonitor();

useEffect(() => {
  console.log('Connected:', isConnected);
  console.log('Error:', error);
}, [isConnected, error]);
```

## 📄 许可

内部项目，仅供团队使用。

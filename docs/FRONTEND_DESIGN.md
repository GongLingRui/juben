# 剧本创作 Agent 平台 - 前端设计文档

> 设计日期: 2026-02-03
> 风格: 黑白简明生产级
> 技术栈: React + TypeScript + Tailwind CSS + Vite

---

## 一、设计理念

### 1.1 设计原则

| 原则 | 说明 |
|-----|------|
| **极简主义** | 黑白配色，去除一切不必要的装饰 |
| **信息层级** | 通过字体大小、粗细、留白建立视觉层级 |
| **功能优先** | 每个元素都有明确的功能目的 |
| **响应式** | 适配桌面、平板、手机 |
| **无障碍** | 符合 WCAG 2.1 AA 标准 |

### 1.2 配色方案

```css
/* 主色调 */
--color-primary: #000000;      /* 纯黑 - 主要文字、边框 */
--color-secondary: #FFFFFF;    /* 纯白 - 背景 */
--color-accent: #000000;       /* 黑色 - 强调、按钮 */

/* 中性色 */
--color-gray-50: #FAFAFA;
--color-gray-100: #F5F5F5;
--color-gray-200: #E5E5E5;
--color-gray-300: #D4D4D4;
--color-gray-400: #A3A3A3;
--color-gray-500: #737373;
--color-gray-600: #525252;
--color-gray-700: #404040;
--color-gray-800: #262626;
--color-gray-900: #171717;

/* 功能色 */
--color-success: #000000;      /* 成功 - 黑色 */
--color-warning: #525252;      /* 警告 - 深灰 */
--color-error: #000000;        /* 错误 - 黑色粗体 */
--color-info: #404040;         /* 信息 - 深灰 */
```

### 1.3 字体系统

```css
/* 字体栈 */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
             Roboto, Oxygen, Ubuntu, Cantarell, 'Fira Sans',
             'Droid Sans', 'Helvetica Neue', sans-serif;

/* 字体大小 */
--text-xs: 0.75rem;    /* 12px - 辅助信息 */
--text-sm: 0.875rem;   /* 14px - 次要文字 */
--text-base: 1rem;     /* 16px - 正文 */
--text-lg: 1.125rem;   /* 18px - 次要标题 */
--text-xl: 1.25rem;    /* 20px - 小标题 */
--text-2xl: 1.5rem;    /* 24px - 标题 */
--text-3xl: 1.875rem;  /* 30px - 大标题 */

/* 字重 */
font-weight: 400;  /* 常规 */
font-weight: 500;  /* 中等 */
font-weight: 600;  /* 半粗 */
font-weight: 700;  /* 粗体 */
```

---

## 二、页面布局

### 2.1 整体结构

```
┌─────────────────────────────────────────────────────────────┐
│                        顶部导航栏                             │
│  [Logo] [剧本创作] [创作助手] [评估] [分析] [知识库] [设置]  │
├──────────────────────┬──────────────────────────────────────┤
│                      │                                       │
│      侧边栏          │          主内容区                     │
│                      │                                       │
│  ┌────────────────┐ │  ┌────────────────────────────────┐  │
│  │   Agent 列表   │ │  │                                │  │
│  │                │ │  │        聊天对话区域            │  │
│  │ 策划助手 ●     │ │  │                                │  │
│  │ 创作助手       │ │  │  ┌──────────────────────────┐ │  │
│  │ 评估助手       │ │  │  │ 欢迎使用剧本创作助手     │ │  │
│  │ 网络搜索       │ │  │  │                          │ │  │
│  │ 知识库查询     │ │  │  │ 请输入您的问题...        │ │  │
│  │ 文件引用       │ │  │  └──────────────────────────┘ │  │
│  │ 故事分析       │ │  │                                │  │
│  │ 剧集分析       │ │  │                                │  │
│  │                │ │  │                                │  │
│  └────────────────┘ │  └────────────────────────────────┘  │
│                      │                                       │
│                      │  ┌────────────────────────────────┐  │
│                      │  │  [输入框]                      │  │
│                      │  │  [发送]                        │  │
│                      │  └────────────────────────────────┘  │
└──────────────────────┴──────────────────────────────────────┘
```

### 2.2 响应式断点

| 断点 | 屏幕宽度 | 布局调整 |
|-----|---------|---------|
| mobile | < 640px | 侧边栏隐藏，抽屉式菜单 |
| tablet | 640px - 1024px | 侧边栏可折叠 |
| desktop | > 1024px | 完整布局 |

---

## 三、核心组件

### 3.1 ChatMessage 聊天消息组件

```typescript
interface ChatMessageProps {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agentName?: string;
  status?: 'streaming' | 'complete' | 'error';
  metadata?: {
    agent?: string;
    thoughtChain?: string[];
    references?: Reference[];
  };
}
```

**视觉设计:**

| 元素 | 用户消息 | AI消息 |
|-----|---------|--------|
| 背景色 | 透明 | #FAFAFA |
| 对齐方式 | 右对齐 | 左对齐 |
| 最大宽度 | 70% | 85% |
| 边框 | 无 | 左侧 2px 黑色边框 |
| 内边距 | 12px 16px | 16px 20px |

### 3.2 StreamingText 流式文本组件

```typescript
interface StreamingTextProps {
  content: string;
  isStreaming: boolean;
  onComplete?: () => void;
}
```

**动画效果:**
- 光标闪烁动画
- 文字渐入效果 (0.15s per character)
- 代码块语法高亮

### 3.3 AgentSelector Agent选择器

```typescript
interface AgentSelectorProps {
  agents: Agent[];
  activeAgent: string;
  onAgentChange: (agentId: string) => void;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'active' | 'idle' | 'busy';
  model: string;
}
```

**视觉样式:**
- 列表项：hover 时背景变为 #F5F5F5
- 选中项：左侧 3px 黑色边框 + 半透明黑色背景
- 状态指示：● 活跃 / ○ 空闲 / ⟳ 忙碌

### 3.4 InputArea 输入区域

```typescript
interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  actions?: InputAction[];
}

interface InputAction {
  icon: string;
  label: string;
  onClick: () => void;
}
```

**特性:**
- 自动高度文本框
- 字符计数
- 快捷键支持 (Enter 发送, Shift+Enter 换行)
- 文件拖拽上传
- 语音输入按钮 (可选)

### 3.5 ThoughtChain 思考链组件

```typescript
interface ThoughtChainProps {
  thoughts: Thought[];
  expanded?: boolean;
}

interface Thought {
  step: number;
  content: string;
  timestamp: string;
}
```

**可折叠区域，默认展开:**

```
┌─ 🤔 思考过程 ───────────── [折叠] ─┐
│                                     │
│  1. 分析用户意图...                  │
│  2. 检索知识库...                    │
│  3. 生成响应...                      │
│                                     │
└─────────────────────────────────────┘
```

### 3.6 StatusBar 状态栏

```typescript
interface StatusBarProps {
  currentAgent: string;
  model: string;
  status: 'idle' | 'processing' | 'streaming' | 'error';
  responseTime?: number;
  tokensUsed?: number;
}
```

**显示在主内容区顶部:**

```
策划助手 · GLM-4-Flash · 响应中... · 已生成 234 tokens
```

---

## 四、交互流程

### 4.1 消息发送流程

```
用户输入
    ↓
[输入验证] → 空内容检查 / 长度限制
    ↓
[显示用户消息] → 立即上屏
    ↓
[创建AI消息占位] → 显示"思考中..."状态
    ↓
[建立SSE连接] → GET /juben/chat
    ↓
[接收流式数据] → 逐字符追加显示
    ↓
[更新状态栏] → 实时显示 token 数量
    ↓
[完成] → 标记消息完成，显示操作按钮
```

### 4.2 SSE 事件处理

```typescript
interface SSEEvent {
  event: 'message' | 'thought' | 'error' | 'metadata' | 'done';
  data: {
    content?: string;
    agent?: string;
    thought?: string;
    references?: Reference[];
    metadata?: Record<string, unknown>;
  };
  timestamp: string;
}
```

### 4.3 错误处理

| 错误类型 | UI表现 |
|---------|--------|
| 网络错误 | 重试按钮 + 错误提示 |
| 超时错误 | 重新发送按钮 |
| API错误 | 错误详情 + 反馈入口 |
| 流式中断 | 继续生成按钮 |

---

## 五、API 集成

### 5.1 聊天 API

```typescript
POST /juben/chat
Content-Type: application/json

{
  "input": "string",
  "user_id": "string",
  "session_id": "string",
  "model_provider": "zhipu",
  "enable_web_search": true,
  "enable_knowledge_base": true
}

Response: Stream (Server-Sent Events)
```

### 5.2 模型列表 API

```typescript
GET /juben/models?provider=zhipu

{
  "success": true,
  "provider": "zhipu",
  "models": [...],
  "default_model": "glm-4-flash",
  "purpose_models": {...}
}
```

### 5.3 Agent 列表 API

```typescript
GET /juben/agents

{
  "success": true,
  "agents": [
    {
      "id": "planner",
      "name": "策划助手",
      "description": "剧本策划和创作建议",
      "model": "glm-4-flash"
    }
  ]
}
```

---

## 六、性能优化

### 6.1 前端优化

| 技术 | 用途 |
|-----|------|
| 虚拟滚动 | 处理大量消息 |
| 防抖/节流 | 输入事件处理 |
| 代码分割 | 路由级别懒加载 |
| 缓存策略 | Service Worker |
| 离线支持 | IndexedDB |

### 6.2 渲染优化

```typescript
// 消息虚拟化
import { useVirtualizer } from '@tanstack/react-virtual';

// 流式文本优化
const [, setFormattedContent] = createSignal('');

// 使用 requestAnimationFrame 平滑更新
function appendText(chunk: string) {
  requestAnimationFrame(() => {
    setFormattedContent(prev => prev + chunk);
  });
}
```

---

## 七、状态管理

### 7.1 状态结构

```typescript
interface AppState {
  chat: {
    messages: Message[];
    currentSession: string | null;
    streamingMessage: string | null;
    isStreaming: boolean;
  };
  agents: {
    list: Agent[];
    activeAgent: string;
  };
  settings: {
    theme: 'light' | 'dark';
    model: string;
    streamEnabled: boolean;
  };
  ui: {
    sidebarOpen: boolean;
    thoughtChainExpanded: boolean;
  };
}
```

### 7.2 状态库选择

使用 [Zustand](https://zustand-demo.pmnd.rs/) 轻量级状态管理：

```typescript
import create from 'zustand';

const useStore = create((set) => ({
  messages: [],
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  // ...
}));
```

---

## 八、文件结构

```
frontend/
├── index.html                    # HTML 入口
├── vite.config.ts                # Vite 配置
├── tailwind.config.js            # Tailwind 配置
├── tsconfig.json                 # TypeScript 配置
├── package.json
├── src/
│   ├── main.tsx                  # 应用入口
│   ├── App.tsx                   # 根组件
│   ├── index.css                 # 全局样式
│   │
│   ├── pages/                    # 页面
│   │   ├── Chat.tsx              # 聊天主页
│   │   ├── Settings.tsx          # 设置页
│   │   └── History.tsx           # 历史记录
│   │
│   ├── components/               # 组件
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx         # 聊天容器
│   │   │   ├── ChatMessage.tsx           # 消息组件
│   │   │   ├── StreamingText.tsx         # 流式文本
│   │   │   ├── InputArea.tsx             # 输入区域
│   │   │   ├── ThoughtChain.tsx          # 思考链
│   │   │   └── MessageActions.tsx        # 消息操作
│   │   ├── layout/
│   │   │   ├── Header.tsx                # 顶部导航
│   │   │   ├── Sidebar.tsx               # 侧边栏
│   │   │   ├── AgentList.tsx             # Agent列表
│   │   │   └── StatusBar.tsx             # 状态栏
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Icon.tsx
│   │       ├── Avatar.tsx
│   │       └── Markdown.tsx
│   │
│   ├── hooks/                    # Hooks
│   │   ├── useChat.ts            # 聊天逻辑
│   │   ├── useStream.ts          # SSE 流处理
│   │   ├── useAgents.ts          # Agent管理
│   │   └── useDebounce.ts        # 防抖
│   │
│   ├── store/                    # 状态管理
│   │   ├── chatStore.ts
│   │   ├── agentStore.ts
│   │   └── settingsStore.ts
│   │
│   ├── services/                 # API服务
│   │   ├── api.ts                # API客户端
│   │   ├── chatService.ts        # 聊天服务
│   │   └── agentService.ts       # Agent服务
│   │
│   ├── types/                    # 类型定义
│   │   ├── chat.ts
│   │   ├── agent.ts
│   │   └── api.ts
│   │
│   ├── utils/                    # 工具函数
│   │   ├── format.ts             # 格式化
│   │   ├── markdown.ts           # Markdown处理
│   │   └── validation.ts         # 验证
│   │
│   └── assets/                   # 静态资源
│       └── icons/
└── public/                       # 公共资源
    └── favicon.ico
```

---

## 九、实施计划

### Phase 1: 基础框架 (Day 1)
- [ ] 项目初始化 (Vite + React + TypeScript)
- [ ] Tailwind CSS 配置
- [ ] 基础布局组件
- [ ] 路由设置

### Phase 2: 核心组件 (Day 2)
- [ ] ChatMessage 组件
- [ ] StreamingText 组件
- [ ] InputArea 组件
- [ ] AgentList 组件

### Phase 3: 功能集成 (Day 3)
- [ ] SSE 连接
- [ ] 聊天 API 集成
- [ ] 状态管理
- [ ] 错误处理

### Phase 4: 优化完善 (Day 4)
- [ ] 响应式适配
- [ ] 性能优化
- [ ] 无障碍优化
- [ ] 测试

---

## 十、依赖清单

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "zustand": "^4.5.0",
    "@tanstack/react-virtual": "^3.10.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "highlight.js": "^11.9.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  }
}
```

---

## 十一、参考资源

- [assistant-ui - React AI Chat Library](https://github.com/assistant-ui/assistant-ui)
- [Chatbot UI Examples](https://www.eleken.co/blog-posts/chatbot-ui-examples)
- [Chat UI Design Trends 2025](https://multitaskai.com/blog/chat-ui-design/)
- [Minimalist Chat Interface Design](https://easy-peasy.ai/ai-image-generator/images/minimalist-ai-chat-interface-black-white)
- [Vite Guide](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)

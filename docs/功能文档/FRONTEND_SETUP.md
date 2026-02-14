# 前端安装与部署文档

> 更新日期: 2026-02-03
> 前端框架: React + TypeScript + Vite + Tailwind CSS
> 风格: 黑白简明生产级设计

---

## 项目概述

剧本创作 Agent 平台前端是一个基于 React 的单页应用，采用黑白简明风格设计，支持与后端 API 进行流式交互，展示所有 40+ 个专业 Agents。

### 核心特性

- **黑白简明风格**: 极简主义设计，高对比度，专业感强
- **流式响应**: 实时显示 AI 生成内容
- **40+ Agents**: 支持策划、创作、评估、分析、工作流等各类 Agents
- **响应式设计**: 完美适配桌面、平板、手机
- **思考链展示**: 可展开/折叠的 AI 思考过程
- **Markdown 支持**: 完整支持代码高亮和 Markdown 格式

---

## 一、环境要求

| 软件 | 版本要求 | 说明 |
|-----|---------|------|
| Node.js | >= 18.0.0 | 推荐使用 LTS 版本 |
| npm | >= 9.0.0 | 或 pnpm >= 8.0.0 |
| 浏览器 | Chrome/Firefox/Safari/Edge | 现代浏览器 |

---

## 二、快速开始

### 2.1 安装依赖

```bash
cd frontend

# 使用 npm
npm install

# 或使用 pnpm (更快)
pnpm install
```

### 2.2 配置环境变量

创建 `.env.local` 文件：

```bash
# API 地址
VITE_API_BASE_URL=http://localhost:8000

# WebSocket 地址 (可选)
VITE_WS_BASE_URL=ws://localhost:8000

# 启用调试模式
VITE_DEBUG=true
```

### 2.3 启动开发服务器

```bash
npm run dev

# 或
pnpm dev
```

访问 http://localhost:5173

### 2.4 构建生产版本

```bash
npm run build

# 预览构建结果
npm run preview
```

---

## 三、项目结构说明

```
frontend/
├── src/
│   ├── main.tsx              # 应用入口
│   ├── App.tsx               # 根组件
│   ├── index.css             # 全局样式
│   ├── pages/                # 页面组件
│   ├── components/           # UI 组件
│   ├── hooks/                # 自定义 Hooks
│   ├── store/                # 状态管理
│   ├── services/             # API 服务
│   ├── types/                # TypeScript 类型
│   └── utils/                # 工具函数
├── public/                   # 静态资源
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## 四、开发指南

### 4.1 添加新页面

```tsx
// src/pages/NewPage.tsx
export default function NewPage() {
  return (
    <div className="min-h-screen bg-white">
      <h1 className="text-2xl font-semibold">新页面</h1>
    </div>
  );
}
```

### 4.2 添加新组件

```tsx
// src/components/NewComponent.tsx
interface Props {
  title: string;
  onClick?: () => void;
}

export function NewComponent({ title, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 bg-black text-white rounded"
    >
      {title}
    </button>
  );
}
```

### 4.3 添加 API 服务

```typescript
// src/services/newService.ts
import api from './api';

export async function newService(params: Params) {
  const response = await api.post('/endpoint', params);
  return response.data;
}
```

### 4.4 添加状态管理

```typescript
// src/store/newStore.ts
import create from 'zustand';

interface State {
  data: null | Data;
  setData: (data: Data) => void;
}

export const useNewStore = create<State>((set) => ({
  data: null,
  setData: (data) => set({ data }),
}));
```

---

## 五、样式指南

### 5.1 Tailwind CSS 类命名规范

```html
<!-- 布局 -->
<div class="flex flex-col gap-4 p-6">

<!-- 颜色 -->
<div class="text-black bg-white border-gray-200">

<!-- 间距 -->
<div class="m-4 p-6 px-8 py-4">

<!-- 字体 -->
<h1 class="text-2xl font-semibold">
<p class="text-base font-normal text-gray-600">

<!-- 边框 -->
<div class="border border-gray-200 rounded-lg">
```

### 5.2 自定义样式变量

```css
/* src/index.css */
@layer base {
  :root {
    --color-primary: #000000;
    --color-secondary: #FFFFFF;
    --font-sans: 'Inter', system-ui, sans-serif;
  }
}
```

---

## 六、调试技巧

### 6.1 查看组件状态

```typescript
import { useDevStore } from './store/devStore';

// 在开发环境中显示状态
if (import.meta.env.DEV) {
  console.log('Current state:', useDevStore.getState());
}
```

### 6.2 网络请求调试

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/juben': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### 6.3 React DevTools

安装浏览器扩展：
- Chrome: [React Developer Tools](https://chrome.google.com/webstore/detail/react-developer-tools/)
- Firefox: [React Developer Tools](https://addons.mozilla.org/firefox/addon/react-devtools/)

---

## 七、部署

### 7.1 Docker 部署

```dockerfile
# Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 7.2 Nginx 配置

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /juben {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 7.3 环境变量

生产环境创建 `.env.production`:

```bash
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_BASE_URL=wss://api.yourdomain.com
VITE_DEBUG=false
```

---

## 八、常见问题

### Q1: npm install 失败

```bash
# 清除缓存后重试
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Q2: 端口被占用

```bash
# 修改端口
npm run dev -- --port 3000
```

### Q3: API 跨域问题

在 `vite.config.ts` 中配置代理，参考上方"调试技巧"章节。

### Q4: 构建后白屏

检查：
1. `base` 配置是否正确
2. 路由模式是否匹配服务器配置
3. 环境变量是否正确设置

---

## 十、支持的 Agents 列表

### 策划类 (Planning)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `short_drama_planner` | 短剧策划助手 | 专业短剧策划和创作建议 |

### 创作类 (Creation)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `short_drama_creator` | 短剧创作助手 | 高质量剧本内容创作 |
| `story_summary_generator` | 故事大纲生成 | 精炼的故事大纲 |
| `detailed_plot_points` | 详细情节点 | 展开详细情节内容 |

### 评估类 (Evaluation)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `short_drama_evaluation` | 短剧评估助手 | 多维度剧本质量评估 |
| `script_evaluation` | 剧本评估专家 | 深度剧本分析评估 |
| `ip_evaluation` | IP价值评估 | IP商业价值评估 |
| `story_evaluation` | 故事质量评估 | 故事整体质量评估 |
| `story_outline_evaluation` | 大纲评估 | 故事大纲完整性评估 |
| `novel_screening_evaluation` | 小说筛选评估 | 小说改编可行性评估 |

### 分析类 (Analysis)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `story_five_elements` | 故事五元素分析 | 分析故事核心五元素 |
| `series_analysis` | 已播剧集分析 | 分析已播剧集数据和表现 |
| `drama_analysis` | 剧本深度分析 | 深度专业剧本分析 |
| `story_type_analyzer` | 故事类型分析 | 识别和分析故事类型 |

### 工作流类 (Workflow)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `plot_points_workflow` | 情节点工作流 | 完整的情节点生成工作流 |
| `drama_workflow` | 剧本创作工作流 | 端到端剧本创作流程 |
| `result_integrator` | 结果集成器 | 集成多个Agent结果 |

### 人物类 (Character)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `character_profile_generator` | 人物小传生成 | 生成详细人物小传 |
| `character_relationship_analyzer` | 人物关系分析 | 分析人物关系网络 |

### 故事类 (Story)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `mind_map` | 思维导图 | 生成故事结构思维导图 |
| `plot_points_analyzer` | 情节点分析 | 分析和优化情节点设计 |

### 工具类 (Utility)
| Agent ID | 名称 | 描述 |
|----------|------|------|
| `websearch` | 网络搜索 | 实时搜索网络信息 |
| `knowledge` | 知识库查询 | 查询剧本创作知识库 |
| `file_reference` | 文件引用解析 | 解析引用外部文件 |
| `document_generator` | 文档生成器 | 生成标准化剧本文档 |
| `output_formatter` | 输出格式化 | 格式化AI输出 |
| `series_info` | 剧集信息提取 | 提取剧集相关信息 |
| `series_name_extractor` | 剧名提取 | 智能识别短剧名称 |
| `text_splitter` | 文本分割 | 智能分割长文本 |
| `text_truncator` | 文本截断 | 按要求截断文本 |

---

## 十一、前端项目结构

```
frontend/
├── index.html                    # HTML 入口
├── package.json                  # 依赖配置
├── vite.config.ts                # Vite 配置
├── tailwind.config.js            # Tailwind 配置
├── tsconfig.json                 # TypeScript 配置
├── postcss.config.js             # PostCSS 配置
├── .env.example                  # 环境变量示例
│
├── public/                       # 静态资源
│
└── src/
    ├── main.tsx                  # 应用入口
    ├── App.tsx                   # 根组件
    ├── index.css                 # 全局样式
    │
    ├── config/
    │   └── agents.ts             # Agents 配置 (40+)
    │
    ├── pages/
    │   └── MainPage.tsx          # 主页面
    │
    ├── components/
    │   ├── layout/               # 布局组件
    │   │   ├── Header.tsx        # 顶部导航
    │   │   ├── Sidebar.tsx       # 侧边栏
    │   │   └── StatusBar.tsx     # 状态栏
    │   │
    │   ├── chat/                 # 聊天组件
    │   │   ├── ChatContainer.tsx # 聊天容器
    │   │   ├── ChatMessage.tsx   # 消息组件
    │   │   ├── StreamingText.tsx # 流式文本
    │   │   ├── ThoughtChain.tsx  # 思考链
    │   │   ├── MessageActions.tsx# 消息操作
    │   │   └── InputArea.tsx     # 输入区域
    │   │
    │   ├── common/               # 公共组件
    │   │   └── MobileMenu.tsx    # 移动端菜单
    │   │
    │   └── modals/               # 弹窗组件
    │       ├── SettingsModal.tsx     # 设置弹窗
    │       └── AgentDetailModal.tsx # Agent详情弹窗
    │
    ├── hooks/                    # 自定义 Hooks
    │   ├── useChat.ts            # 聊天逻辑
    │   ├── useStream.ts          # SSE 流处理
    │   └── useAgents.ts          # Agent 管理
    │
    ├── store/                    # 状态管理 (Zustand)
    │   ├── chatStore.ts          # 聊天状态
    │   ├── agentStore.ts         # Agent 状态
    │   ├── settingsStore.ts      # 设置状态
    │   └── uiStore.ts            # UI 状态
    │
    ├── services/                 # API 服务
    │   ├── api.ts                # API 客户端
    │   ├── chatService.ts        # 聊天服务
    │   └── agentService.ts       # Agent 服务
    │
    └── types/                    # 类型定义
        └── index.ts              # 全局类型
```

---

## 十二、更新日志

| 日期 | 版本 | 更新内容 |
|-----|------|---------|
| 2026-02-03 | 1.0.0 | 初始版本，完整的 React 前端系统 |

---

## 十三、参考资源

- [Chatbot UI Examples](https://www.eleken.co/blog-posts/chatbot-ui-examples)
- [Minimalist Chat Interface Design](https://easy-peasy.ai/ai-image-generator/images/minimalist-ai-chat-interface-black-white)
- [Chat UI Design Trends](https://multitaskai.com/blog/chat-ui-design/)
- [Vite Guide](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Zustand](https://zustand-demo.pmnd.rs/)
- [React Markdown](https://github.com/remarkjs/react-markdown)


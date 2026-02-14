# 剧本创作 Agent 平台 - 前端

> 黑白简明风格的生产级 React 前端应用
> 支持 40+ 专业 Agents，流式响应，实时交互

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **样式**: Tailwind CSS 3
- **状态管理**: Zustand 4
- **Markdown**: react-markdown + remark-gfm + rehype-highlight
- **图标**: Lucide React

## 快速开始

```bash
# 安装依赖
npm install

# 复制环境变量
cp .env.example .env.local

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## 核心功能

### 1. Agents 管理
- 支持 40+ 专业 Agents
- 按分类筛选 (策划/创作/评估/分析/工作流/人物/故事/工具)
- 搜索和快速切换
- Agent 详情展示

### 2. 聊天交互
- 实时流式响应
- 思考链展示
- Markdown 代码高亮
- 消息操作 (复制/收藏/重新生成)

### 3. 用户设置
- 主题切换 (浅色/深色)
- 字体大小调节
- 流式响应开关
- 自动滚动设置

### 4. 响应式设计
- 桌面端完整功能
- 平板侧边栏折叠
- 移动端适配

## 项目结构

```
src/
├── config/           # 配置文件
│   └── agents.ts     # Agents 配置 (40+)
├── components/       # 组件
│   ├── layout/       # 布局组件
│   ├── chat/         # 聊天组件
│   ├── common/       # 公共组件
│   └── modals/       # 弹窗组件
├── hooks/            # 自定义 Hooks
├── store/            # 状态管理
├── services/         # API 服务
├── types/            # 类型定义
└── pages/            # 页面
```

## 环境变量

```bash
# API 地址
VITE_API_BASE_URL=http://localhost:8000

# WebSocket 地址
VITE_WS_BASE_URL=ws://localhost:8000

# 应用配置
VITE_APP_TITLE=剧本创作 Agent 平台
VITE_APP_VERSION=1.0.0

# 功能开关
VITE_ENABLE_STREAM=true
VITE_ENABLE_VOICE_INPUT=false
VITE_ENABLE_FILE_UPLOAD=true

# 调试模式
VITE_DEBUG=true

# 默认设置
VITE_DEFAULT_MODEL=glm-4-flash
VITE_DEFAULT_THEME=light
VITE_DEFAULT_FONT_SIZE=md
```

## 开发指南

### 添加新 Agent

在 `src/config/agents.ts` 中添加 Agent 配置：

```typescript
{
  id: 'new_agent',
  name: 'NewAgent',
  displayName: '新 Agent',
  description: 'Agent 描述',
  category: 'creation',
  icon: '✨',
  model: 'glm-4-flash',
  apiEndpoint: '/juben/new-agent/chat',
  features: ['功能1', '功能2'],
  capabilities: ['能力1', '能力2'],
  inputExample: '示例输入',
  outputExample: '示例输出',
  status: 'active'
}
```

### 添加新页面

1. 在 `src/pages/` 创建页面组件
2. 在 `App.tsx` 中添加路由
3. 更新导航菜单

### 自定义样式

全局样式在 `src/index.css` 中定义：

```css
/* 添加自定义 CSS 变量 */
:root {
  --custom-color: #000000;
}

/* 添加 Tailwind 类 */
@layer components {
  .custom-class {
    @apply flex items-center gap-2;
  }
}
```

## 构建部署

### Docker 部署

```bash
# 构建镜像
docker build -t juben-frontend .

# 运行容器
docker run -p 5173:80 juben-frontend
```

### Nginx 部署

```bash
# 构建
npm run build

# 部署到 Nginx
cp -r dist/* /var/www/html/
```

## 常见问题

### 1. npm install 失败

```bash
# 清除缓存
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 2. 端口被占用

```bash
# 修改端口
npm run dev -- --port 3000
```

### 3. API 跨域

在 `vite.config.ts` 中配置代理。

## 参考资源

- [设计文档](../docs/FRONTEND_DESIGN.md)
- [安装指南](../docs/FRONTEND_SETUP.md)
- [Chatbot UI Examples](https://www.eleken.co/blog-posts/chatbot-ui-examples)

## License

MIT

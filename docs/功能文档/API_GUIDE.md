# Juben API 使用指南

> 版本: v1.0
> 更新日期: 2026-02-03
> 作者: Juben Team

---

## 目录

1. [快速开始](#1-快速开始)
2. [认证方式](#2-认证方式)
3. [核心API](#3-核心api)
4. [流式响应](#4-流式响应)
5. [错误处理](#5-错误处理)
6. [最佳实践](#6-最佳实践)
7. [SDK参考](#7-sdk参考)

---

## 1. 快速开始

### 1.1 基础请求示例

```bash
# 基础聊天请求
curl -X POST "http://localhost:8000/juben/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "帮我策划一个都市情感短剧",
    "user_id": "user_123",
    "session_id": "session_456"
  }'
```

### 1.2 使用API密钥

```bash
# 使用Bearer Token
curl -X POST "http://localhost:8000/juben/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": "策划一个复仇题材的短剧",
    "user_id": "user_123"
  }'
```

---

## 2. 认证方式

### 2.1 获取访问令牌

**端点**: `POST /auth/login`

**请求体**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 2.2 使用令牌

**请求头**:
```
Authorization: Bearer {access_token}
```

### 2.3 刷新令牌

**端点**: `POST /auth/refresh`

**请求体**:
```json
{
  "refresh_token": "your_refresh_token"
}
```

### 2.4 登出

**端点**: `POST /auth/logout`

**请求头**:
```
Authorization: Bearer {access_token}
```

---

## 3. 核心API

### 3.1 聊天接口

**端点**: `POST /juben/chat`

**说明**: 主要聊天接口，支持意图识别和智能Agent路由

**请求参数**:
```typescript
interface ChatRequest {
  input: string;              // 用户输入 (必填)
  user_id?: string;           // 用户ID (默认: "default_user")
  session_id?: string;        // 会话ID (可选，自动生成)
  model_provider?: string;    // 模型提供商 (zhipu/openrouter/openai)
  enable_web_search?: boolean;// 启用网络搜索 (默认: true)
  enable_knowledge_base?: boolean; // 启用知识库检索 (默认: true)
}
```

**请求示例**:
```bash
curl -X POST "http://localhost:8000/juben/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "input": "帮我策划一个关于隐形富豪的短剧",
    "user_id": "user_123",
    "session_id": "session_456",
    "model_provider": "zhipu",
    "enable_web_search": true
  }'
```

**响应格式** (SSE流式):
```
data: {"event":"message","data":{"content":"让我为您策划...","metadata":{}}}

data: {"event":"thought","data":{"content":"正在分析用户需求...","metadata":{}}}

data: {"event":"tool_call","data":{"content":"调用搜索工具...","metadata":{"tool":"web_search"}}}

data: {"event":"final_answer","data":{"content":"策划完成！","metadata":{}}}

data: [DONE]
```

### 3.2 策划接口

**端点**: `POST /juben/plan`

**说明**: 专门的短剧策划接口

**请求参数**:
```typescript
interface PlanningRequest {
  input: string;              // 策划需求描述
  genre?: string;             // 题材 (都市情感/古装言情/现代悬疑等)
  target_audience?: string;   // 目标受众
  episodes?: number;          // 集数
  user_id?: string;           // 用户ID
  session_id?: string;        // 会话ID
}
```

**请求示例**:
```bash
curl -X POST "http://localhost:8000/juben/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "策划一个都市复仇短剧，主角是隐藏身份的CEO",
    "genre": "都市情感",
    "target_audience": "25-35岁女性",
    "episodes": 80,
    "user_id": "user_123"
  }'
```

### 3.3 创作接口

**端点**: `POST /juben/create`

**说明**: 根据大纲/Note进行剧本创作

**请求参数**:
```typescript
interface CreationRequest {
  input: string;              // 创作指令
  outline?: string;           // 故事大纲
  selected_notes?: string[];  // 选中的Notes (["@note1", "@drama1"])
  user_id?: string;           // 用户ID
  session_id?: string;        // 会话ID
}
```

**请求示例**:
```bash
curl -X POST "http://localhost:8000/juben/create" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "根据 @note1 和 @drama1 创作详细剧本",
    "selected_notes": ["note1", "drama1"],
    "user_id": "user_123"
  }'
```

### 3.4 评估接口

**端点**: `POST /juben/evaluate`

**说明**: 对剧本/大纲进行专业评估

**请求参数**:
```typescript
interface EvaluationRequest {
  input: string;              // 评估需求
  script_content?: string;    // 剧本内容
  evaluation_criteria?: {     // 评估标准 (可选)
    dimensions: string[];     // 评估维度
    scoring_method: string;   // 评分方式
  };
  user_id?: string;
  session_id?: string;
}
```

**请求示例**:
```bash
curl -X POST "http://localhost:8000/juben/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "评估这个剧本的市场潜力",
    "script_content": "剧本内容...",
    "user_id": "user_123"
  }'
```

### 3.5 搜索接口

**网络搜索**:
```bash
# 端点: POST /juben/search/web
curl -X POST "http://localhost:8000/juben/search/web" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "2024年热门短剧题材",
    "count": 5,
    "user_id": "user_123"
  }'
```

**知识库搜索**:
```bash
# 端点: POST /juben/knowledge/search
curl -X POST "http://localhost:8000/juben/knowledge/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "都市复仇短剧策划技巧",
    "collection": "script_segments",
    "limit": 10,
    "user_id": "user_123"
  }'
```

### 3.6 系统信息接口

**健康检查**:
```bash
GET /juben/health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-03T00:00:00Z"
}
```

**Agent列表**:
```bash
GET /juben/agents
```

**响应**:
```json
{
  "agents": [
    {
      "name": "short_drama_planner",
      "description": "短剧策划Agent",
      "model_provider": "zhipu"
    }
  ]
}
```

**系统配置**:
```bash
GET /juben/config
```

**模型列表**:
```bash
GET /juben/models
```

---

## 4. 流式响应

### 4.1 事件类型

| 事件类型 | 说明 | 数据格式 |
|----------|------|----------|
| `message` | 普通消息 | `{content: string}` |
| `thought` | AI思考过程 | `{content: string}` |
| `tool_call` | 工具调用 | `{tool: string, args: object}` |
| `tool_result` | 工具结果 | `{result: object}` |
| `note` | Note创建 | `{note: object}` |
| `error` | 错误信息 | `{error: string}` |
| `final_answer` | 最终答案 | `{content: string}` |
| `done` | 完成 | `{}` |

### 4.2 处理流式响应

**JavaScript示例**:
```javascript
const response = await fetch('/juben/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    input: '策划一个短剧',
    user_id: 'user_123'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));

      switch (data.event) {
        case 'message':
          console.log('消息:', data.data.content);
          break;
        case 'thought':
          console.log('思考:', data.data.content);
          break;
        case 'final_answer':
          console.log('完成:', data.data.content);
          break;
      }
    }
  }
}
```

**Python示例**:
```python
import requests
import json

def stream_chat(input_text, user_id):
    response = requests.post(
        'http://localhost:8000/juben/chat',
        json={
            'input': input_text,
            'user_id': user_id
        },
        stream=True
    )

    for line in response.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            event_type = data.get('event')
            content = data.get('data', {}).get('content', '')

            if event_type == 'message':
                print(f"消息: {content}")
            elif event_type == 'thought':
                print(f"思考: {content}")
            elif event_type == 'final_answer':
                print(f"完成: {content}")
```

---

## 5. 错误处理

### 5.1 错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "error_code": "ERROR_CODE",
  "detail": "详细错误信息"
}
```

### 5.2 常见错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `UNAUTHORIZED` | 401 | 未授权或令牌无效 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求过于频繁 |
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `LLM_TIMEOUT` | 504 | LLM请求超时 |
| `DATABASE_ERROR` | 500 | 数据库错误 |

### 5.3 错误处理示例

```javascript
try {
  const response = await fetch('/juben/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: JSON.stringify({ input: '测试' })
  });

  if (!response.ok) {
    const error = await response.json();

    switch (error.error_code) {
      case 'UNAUTHORIZED':
        // 重新登录或刷新令牌
        await refreshToken();
        break;
      case 'RATE_LIMIT_EXCEEDED':
        // 延迟后重试
        await delay(5000);
        break;
      default:
        console.error('错误:', error.message);
    }
  }
} catch (error) {
  console.error('请求失败:', error);
}
```

---

## 6. 最佳实践

### 6.1 会话管理

```javascript
// 使用固定的session_id保持上下文
const sessionId = localStorage.getItem('session_id') || uuidv4();
localStorage.setItem('session_id', sessionId);

// 所有请求使用同一个session_id
const response = await fetch('/juben/chat', {
  method: 'POST',
  body: JSON.stringify({
    input: userInput,
    user_id: userId,
    session_id: sessionId  // 保持会话连续性
  })
});
```

### 6.2 流式响应处理

```javascript
// 使用EventSource处理SSE
const eventSource = new EventSource('/juben/chat/stream');

eventSource.addEventListener('message', (e) => {
  const data = JSON.parse(e.data);
  updateUI(data);
});

eventSource.addEventListener('error', (e) => {
  console.error('连接错误:', e);
  eventSource.close();
});
```

### 6.3 速率限制

```javascript
// 实现客户端速率限制
class RateLimiter {
  constructor(maxRequests = 10, perMilliseconds = 60000) {
    this.maxRequests = maxRequests;
    this.perMilliseconds = perMilliseconds;
    this.requests = [];
  }

  async acquire() {
    const now = Date.now();
    this.requests = this.requests.filter(t => now - t < this.perMilliseconds);

    if (this.requests.length >= this.maxRequests) {
      const waitTime = this.perMilliseconds - (now - this.requests[0]);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }

    this.requests.push(now);
  }
}

const limiter = new RateLimiter(10, 60000); // 10次/分钟

// 使用限流器
await limiter.acquire();
const response = await fetch('/juben/chat', {...});
```

### 6.4 错误重试

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);

      if (!response.ok && response.status >= 500 && i < maxRetries - 1) {
        // 服务器错误，重试
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        continue;
      }

      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
```

### 6.5 请求优化

```javascript
// 批量请求合并
class RequestBatcher {
  constructor(batchSize = 5, delay = 100) {
    this.batch = [];
    this.batchSize = batchSize;
    this.delay = delay;
    this.timer = null;
  }

  add(request) {
    return new Promise((resolve) => {
      this.batch.push({ request, resolve });

      if (this.batch.length >= this.batchSize) {
        this.flush();
      } else if (!this.timer) {
        this.timer = setTimeout(() => this.flush(), this.delay);
      }
    });
  }

  async flush() {
    clearTimeout(this.timer);
    this.timer = null;

    const batch = this.batch.splice(0);

    // 并发执行
    const results = await Promise.allSettled(
      batch.map(({ request }) => fetch(request.url, request.options))
    );

    results.forEach((result, i) => {
      batch[i].resolve(result);
    });
  }
}
```

---

## 7. SDK参考

### 7.1 Python SDK

```python
from juben_sdk import JubenClient

# 初始化客户端
client = JubenClient(
    api_key="your_api_key",
    base_url="http://localhost:8000"
)

# 基础聊天
async def chat_example():
    response = await client.chat(
        input="策划一个短剧",
        user_id="user_123"
    )

    async for event in response:
        if event.event_type == "message":
            print(event.data.content)

# 流式响应
async def stream_example():
    async for chunk in client.chat_stream(
        input="创作剧本",
        user_id="user_123"
    ):
        print(chunk)

# 策划
async def plan_example():
    result = await client.plan(
        input="都市复仇短剧",
        genre="都市情感",
        target_audience="25-35岁女性",
        user_id="user_123"
    )
    print(result)
```

### 7.2 JavaScript SDK

```javascript
import { JubenClient } from '@juben/sdk';

// 初始化客户端
const client = new JubenClient({
  apiKey: 'your_api_key',
  baseURL: 'http://localhost:8000'
});

// 基础聊天
async function chatExample() {
  const response = await client.chat({
    input: '策划一个短剧',
    userId: 'user_123'
  });

  console.log(response);
}

// 流式响应
async function streamExample() {
  const stream = await client.chatStream({
    input: '创作剧本',
    userId: 'user_123'
  });

  for await (const event of stream) {
    console.log(event);
  }
}

// 策划
async function planExample() {
  const result = await client.plan({
    input: '都市复仇短剧',
    genre: '都市情感',
    targetAudience: '25-35岁女性',
    userId: 'user_123'
  });

  console.log(result);
}
```

### 7.3 CLI工具

```bash
# 安装CLI
pip install juben-cli

# 配置
juben config set api_key YOUR_API_KEY
juben config set base_url http://localhost:8000

# 使用
juben chat "策划一个短剧"
juben plan --genre 都市情感 --episodes 80 "都市复仇短剧"
juben evaluate script.txt

# 流式输出
juben chat --stream "帮我创作剧本"
```

---

## 附录

### A. 完整API端点列表

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/auth/login` | POST | 用户登录 | 否 |
| `/auth/refresh` | POST | 刷新令牌 | 否 |
| `/auth/logout` | POST | 用户登出 | 是 |
| `/juben/chat` | POST | 主聊天接口 | 是 |
| `/juben/plan` | POST | 短剧策划 | 是 |
| `/juben/create` | POST | 剧本创作 | 是 |
| `/juben/evaluate` | POST | 剧本评估 | 是 |
| `/juben/search/web` | POST | 网络搜索 | 是 |
| `/juben/knowledge/search` | POST | 知识库搜索 | 是 |
| `/juben/health` | GET | 健康检查 | 否 |
| `/juben/agents` | GET | Agent列表 | 是 |
| `/juben/models` | GET | 模型列表 | 是 |
| `/juben/config` | GET | 系统配置 | 是 |

### B. 相关文档

- [架构设计文档](./ARCHITECTURE.md)
- [Agent开发指南](./AGENT_DEVELOPMENT.md)
- [部署运维手册](./DEPLOYMENT.md)

# 流式响应优化说明

## 概述

重构了 `apis/core/api_routes.py` 中的流式响应逻辑，实现了：

1. **Redis 暂存**：缓存最后 50 个生成的 token
2. **断点续传**：新增 `/juben/chat/resume` 接口
3. **异常处理**：Agent 异常自动转换为 SSE 错误事件
4. **心跳机制**：防止长连接超时

## 文件结构

```
utils/
└── stream_manager.py              # 流式响应管理器（新增）

apis/
└── core/
    ├── api_routes.py               # API 路由（已重构）
    └── schemas.py                  # 数据模型（已添加 ResumeRequest）

docs/
└── STREAM_OPTIMIZATION_GUIDE.md    # 本文档
```

## 核心功能

### 1. Redis 暂存机制

```python
# Redis 键格式
stream:cache:{message_id}           # 事件缓存列表
stream:meta:{message_id}            # 消息元数据

# 配置
MAX_CACHE_SIZE = 50                 # 最多缓存 50 个事件
CACHE_TTL = 3600                    # 缓存过期时间（1小时）
```

### 2. 断点续传接口

```bash
# POST /juben/chat/resume
{
    "message_id": "msg_user_123_session_abc_20260207_123456_a1b2c3d4",
    "session_id": "session_abc",
    "user_id": "user_123",
    "from_sequence": 10              # 从序列号 10 开始恢复
}
```

### 3. SSE 事件格式

```javascript
// 标准 SSE 事件
data: {
    "event": "message",
    "data": {
        "content": "你好！",
        "metadata": {},
        "timestamp": "2026-02-07T12:34:56",
        "message_id": "msg_xxx",
        "sequence": 1
    }
}

// 错误事件
data: {
    "event": "error",
    "data": {
        "content": "处理失败: ...",
        "metadata": {
            "error_type": "ValueError",
            "error_details": "..."
        },
        "timestamp": "2026-02-07T12:34:56"
    }
}

// 心跳事件（每 30 秒）
data: {
    "event": "heartbeat",
    "data": {
        "content": "ping",
        "metadata": {"last_sequence": 10}
    }
}

// 完成事件
data: {
    "event": "complete",
    "data": {
        "content": "",
        "metadata": {"message_id": "msg_xxx", "total_events": 50}
    }
}
```

## API 端点

### POST /juben/chat

发送聊天请求，返回流式响应。

**请求：**
```json
{
    "input": "帮我创作一个短剧剧本",
    "user_id": "user_123",
    "session_id": "session_abc",
    "model": "glm-4-flash"
}
```

**响应头：**
```
X-Message-ID: msg_user_123_session_abc_20260207_123456_a1b2c3d4
X-Session-ID: session_abc
Content-Type: text/event-stream
```

**响应体（SSE）：**
```
data: {"event":"message","data":{"content":"好的","sequence":1}}

data: {"event":"message","data":{"content":"，我","sequence":2}}

data: {"event":"complete","data":{"total_events":50}}
```

### POST /juben/chat/resume

断点续传接口，从指定序列号恢复流式传输。

**请求：**
```json
{
    "message_id": "msg_user_123_session_abc_20260207_123456_a1b2c3d4",
    "session_id": "session_abc",
    "user_id": "user_123",
    "from_sequence": 10
}
```

**响应：**
- 返回从 `from_sequence` 之后的所有缓存事件
- 如果消息已完成，发送完成事件
- 如果消息未完成，提示前端重新发起请求

### GET /juben/chat/message/{message_id}

获取消息的元数据和缓存状态。

**响应：**
```json
{
    "success": true,
    "message_id": "msg_xxx",
    "meta": {
        "message_id": "msg_xxx",
        "session_id": "session_abc",
        "user_id": "user_123",
        "created_at": "2026-02-07T12:34:56",
        "status": "completed"
    },
    "cache_size": 50,
    "cache_available": true
}
```

## 前端集成示例

### 基本流式请求

```javascript
async function streamChat(input, sessionId) {
    const response = await fetch('/juben/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            input,
            session_id: sessionId,
            user_id: 'user_123'
        })
    });

    // 获取 message_id 用于断点续传
    const messageId = response.headers.get('X-Message-ID');
    const sessionId = response.headers.get('X-Session-ID');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';
    let lastSequence = 0;

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                handleEvent(data);
                lastSequence = data.data.sequence || lastSequence;
            }
        }
    }

    return {messageId, sessionId, lastSequence};
}

function handleEvent(event) {
    switch (event.event) {
        case 'message':
            // 处理消息
            appendToChat(event.data.content);
            break;
        case 'thinking':
            // 处理思考过程
            showThinking(event.data.content);
            break;
        case 'heartbeat':
            // 心跳，忽略
            console.log('heartbeat at sequence', event.data.metadata.last_sequence);
            break;
        case 'error':
            // 处理错误
            showError(event.data.content);
            break;
        case 'complete':
            // 完成
            console.log('completed, total events:', event.data.metadata.total_events);
            break;
    }
}
```

### 断点续传

```javascript
async function resumeChat(messageId, fromSequence) {
    const response = await fetch('/juben/chat/resume', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message_id: messageId,
            session_id: 'session_abc',
            user_id: 'user_123',
            from_sequence: fromSequence
        })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                handleEvent(data);
            }
        }
    }
}
```

### 网络断线重连

```javascript
class ChatStreamManager {
    constructor() {
        this.currentMessageId = null;
        this.lastSequence = 0;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
    }

    async sendChat(input, sessionId) {
        try {
            const result = await streamChat(input, sessionId);
            this.currentMessageId = result.messageId;
            this.lastSequence = result.lastSequence;
            this.reconnectAttempts = 0;
            return result;
        } catch (error) {
            if (this.isNetworkError(error) && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                await this.resumeChat();
            } else {
                throw error;
            }
        }
    }

    async resumeChat() {
        if (!this.currentMessageId) return;

        await resumeChat(this.currentMessageId, this.lastSequence);
    }

    isNetworkError(error) {
        return error.name === 'TypeError' || error.message.includes('fetch');
    }
}
```

## 错误处理

所有 Agent 抛出的异常都会被自动转换为 SSE 错误事件：

```javascript
data: {
    "event": "error",
    "data": {
        "content": "ValueError: chunk_size must be positive",
        "metadata": {
            "error_type": "ValueError",
            "error_details": "ValueError: chunk_size must be positive"
        },
        "timestamp": "2026-02-07T12:34:56"
    }
}
```

前端可以统一处理：

```javascript
function handleEvent(event) {
    if (event.event === 'error') {
        const errorType = event.data.metadata?.error_type;
        const errorMessage = event.data.content;

        console.error(`[${errorType}] ${errorMessage}`);

        // 显示错误给用户
        showError(errorMessage);

        // 如果是特定错误，可以尝试恢复
        if (errorType === 'TimeoutError') {
            // 重试或提示用户
        }
    }
}
```

## 配置选项

### StreamResponseGenerator 配置

```python
from utils.stream_manager import get_stream_response_generator

generator = get_stream_response_generator()

# 可配置项
generator.enable_cache = True           # 是否启用缓存
generator.heartbeat_interval = 30      # 心跳间隔（秒）
generator.session_manager.MAX_CACHE_SIZE = 50  # 缓存大小
generator.session_manager.CACHE_TTL = 3600       # 缓存过期时间
```

## 监控和调试

### 检查消息状态

```bash
curl http://localhost:8000/juben/chat/message/msg_xxx
```

### Redis 命令

```bash
# 查看缓存的事件
redis-cli LRANGE "stream:cache:msg_xxx" 0 -1

# 查看消息元数据
redis-cli GET "stream:meta:msg_xxx"

# 清除缓存
redis-cli DEL "stream:cache:msg_xxx"
```

## 性能优化建议

1. **调整缓存大小**：根据实际 token 生成速度调整 `MAX_CACHE_SIZE`
2. **心跳间隔**：网络不稳定时缩短心跳间隔
3. **连接超时**：前端设置合理的 EventSource 重连策略
4. **Redis 持久化**：生产环境启用 Redis AOF 保证数据不丢失

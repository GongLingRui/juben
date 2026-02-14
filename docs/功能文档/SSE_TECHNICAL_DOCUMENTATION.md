# SSE 流式响应技术文档

## 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [前端实现](#前端实现)
- [后端实现](#后端实现)
- [数据格式](#数据格式)
- [交互流程](#交互流程)
- [高级特性](#高级特性)
- [错误处理](#错误处理)
- [性能优化](#性能优化)

## 概述

本系统使用 **Server-Sent Events (SSE)** 技术实现流式响应，为用户提供实时的 AI 交互体验。SSE 是一种基于 HTTP 的单向推送技术，允许服务器向客户端持续推送数据。

### 为什么选择 SSE 而不是 WebSocket？

1. **基于 HTTP**: 无需额外的协议升级，天然兼容防火墙和代理
2. **单向推送**: AI 响应场景下，只需要服务器向客户端推送
3. **自动重连**: 支持断点续传，提升用户体验
4. **简单可靠**: 实现简单，调试方便

### 核心特性

- ✅ **实时流式输出**: LLM Token 级别推送，打字机效果
- ✅ **断点续传**: 网络中断后可从断点恢复
- ✅ **事件缓存**: Redis 缓存最近 50 个事件，重连后自动恢复
- ✅ **心跳机制**: 30 秒心跳检测连接活性
- ✅ **自动重连**: 最多 3 次重试，延迟 2 秒
- ✅ **多事件类型**: 支持 9 种事件类型，40+ 种内容类型

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                        SSE 架构                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  前端 (React + TypeScript)                            │
│  ┌──────────────────────────────────────────────┐      │
│  │  useChat.ts (主 Hook)                      │      │
│  │  useStream.ts (SSE Hook)                   │      │
│  │  ChatSessionManager (会话管理)          │      │
│  │  RobustSSEClient (SSE 客户端)            │      │
│  └──────────────────────────────────────────────┘      │
│           │                                  │          │
│           ▼                                  │          │
│  ┌──────────────────────────────────────────────┐      │
│  │         SSE 连接 (text/event-stream)    │◄─────┤
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  后端 (FastAPI + Python)                               │
│  ┌──────────────────────────────────────────────┐      │
│  │  /juben/chat (主端点)                   │      │
│  │  /juben/chat/resume (恢复端点)        │      │
│  │  StreamResponseGenerator (流生成器)     │      │
│  │  StreamSessionManager (会话管理)       │      │
│  │  Redis (事件缓存)                      │      │
│  └──────────────────────────────────────────────┘      │
│           │                                  │          │
│           ▼                                  │          │
│  ┌──────────────────────────────────────────────┐      │
│  │         Agent (AI 处理)                 │      │
│  │  - process_request()                   │      │
│  │  - emit_juben_event()                  │      │
│  │  - yield StreamEvent                   │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 前端实现

### 1. 核心组件

#### 1.1 RobustSSEClient (`frontend/src/services/sseClient.ts`)

健壮的 SSE 客户端，提供断点续传、自动重连、心跳检测等高级功能。

```typescript
class RobustSSEClient {
    // 配置选项
    interface SSEClientConfig {
        endpoint?: string;           // SSE 端点
        maxReconnectAttempts?: number; // 最大重连次数
        reconnectDelay?: number;        // 重连延迟
        heartbeatInterval?: number;    // 心跳间隔
        enableCache?: boolean;         // 启用缓存
        cacheMaxSize?: number;         // 缓存大小
    }

    // 客户端状态
    interface SSEClientState {
        isConnected: boolean;
        currentMessageId?: string;
        currentSessionId?: string;
        lastSequence: number;
        reconnectAttempts: number;
        eventCache: Map<number, any>;
    }
}
```

**核心功能**:
- ✅ 自动重连机制（最多 3 次，延迟 2 秒）
- ✅ 心跳检测（30 秒无数据自动重连）
- ✅ 事件缓存（Map 结构，最多 50 个）
- ✅ 断点续传（记录 lastSequence）
- ✅ 网络错误判断（TypeError/fetch 失败可重试）

#### 1.2 ChatSessionManager (`frontend/src/services/chatService.ts`)

聊天会话管理器，封装 SSE 客户端，提供高层 API。

```typescript
class ChatSessionManager {
    private sseClient: RobustSSEClient | null = null;
    private currentRequest: ChatRequest | null = null;

    // 发送消息
    async sendMessage(request: ChatRequest): Promise<void>;

    // 断点续传
    async resume(fromSequence?: number): Promise<boolean>;

    // 断开连接
    disconnect(): void;

    // 订阅事件
    on(event: string, handler: Function): () => void;

    // 获取状态
    getState(): SSEClientState;
}
```

#### 1.3 useChat Hook (`frontend/src/hooks/useChat.ts`)

React Hook，提供完整的聊天功能。

```typescript
export function useChat() {
    const {
        messages,
        isStreaming,
        streamingMessageId,
        addMessage,
        updateMessage,
        deleteMessage,
        setStreamingMessageId,
        setIsStreaming,
        appendToMessage,
        setMessageStatus,
    } = useChatStore();

    // 发送消息（带重试机制）
    const sendMessage = useCallback(
        async (content: string, agentId?: string, retryCount: number = 0) => {
            // 添加用户消息
            const userMessage: Message = {
                id: `user-${Date.now()}-${retryCount}`,
                role: 'user',
                content,
                timestamp: new Date().toISOString(),
            };
            addMessage(userMessage);

            // 创建 AI 消息占位符
            const aiMessageId = `ai-${Date.now()}-${retryCount}`;
            const aiMessage: Message = {
                id: aiMessageId,
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
                status: 'streaming',
            };
            addMessage(aiMessage);

            // 构建请求
            const request: ChatRequest = {
                input: content,
                user_id: 'default-user',
                session_id: currentSession || undefined,
                project_id: localStorage.getItem('projectId') || undefined,
                model_provider: modelProvider,
                model: model,
                agent_id: agentId || activeAgent,
            };

            // 使用重试机制
            result = await retryWithBackoff(
                async () => {
                    // 流式响应
                    let fullContent = '';
                    const close = streamMessage(
                        request,
                        (chunk) => {
                            fullContent += chunk;
                            appendToMessage(aiMessageId, chunk);
                        },
                        (event) => {
                            // 处理各种事件类型
                            if (event.event === 'system') {
                                updateMessageMetadata(aiMessageId, () => ({
                                    systemEvents: [{ content: event.data.content }]
                                }));
                            }
                            // ... 其他事件处理
                        },
                        () => {
                            setIsStreaming(false);
                        },
                        (error) => {
                            // 错误处理
                        }
                    );
                },
                {
                    maxRetries: enableRetryOnError ? maxRetries : 0,
                    isRetriable: (error) => {
                        // 网络错误、超时、限流可重试
                        const errorMessage = error.message.toLowerCase();
                        return (
                            errorMessage.includes('network') ||
                            errorMessage.includes('timeout') ||
                            errorMessage.includes('rate limit')
                        );
                    },
                }
            );
        },
        [messages, sendMessage, deleteMessage]
    );

    return {
        messages,
        isStreaming,
        streamingMessageId,
        sendMessage,
        regenerateMessage,
        editMessage,
        stopStreaming,
        clearMessages,
        createBranch,
        setActiveAgent,
        deleteMessage,
    };
}
```

### 2. 前端 SSE 连接流程

```
┌───────────────────────────────────────────────────┐
│              前端 SSE 连接流程                   │
├───────────────────────────────────────────────────┤
│                                                         │
│  1. 用户发送消息                                     │
│     │                                               │
│     ▼                                               │
│  [创建 ChatRequest]                                 │
│     │                                               │
│     ▼                                               │
│  [调用 ChatSessionManager.sendMessage()]                │
│     │                                               │
│     ▼                                               │
│  [创建 RobustSSEClient]                            │
│     │                                               │
│     ▼                                               │
│  [POST /juben/chat]                                │
│     │    Headers:                                    │
│     │    Content-Type: application/json            │
│     │    Body: JSON.stringify(request)              │
│     │                                               │
│     ▼                                               │
│  [等待响应]                                         │
│     │    ← Response Headers:                       │
│     │    - X-Message-ID: msg_xxx                     │
│     │    - X-Session-ID: session_xxx                  │
│     │    - Content-Type: text/event-stream            │
│     │                                               │
│     ▼                                               │
│  [获取 reader]                                       │
│     reader = response.body.getReader()                  │
│     │                                               │
│     ▼                                               │
│  [读取流]                                           │
│     while (!aborted) {                                │
│         const { done, value } = await reader.read();    │
│         if (done) break;                               │
│         const chunk = decoder.decode(value);            │
│         buffer += chunk;                                 │
│         // 解析 SSE 格式                                 │
│         const lines = buffer.split('\n');              │
│         buffer = lines.pop() || '';                       │
│         for (const line of lines) {                       │
│             if (line.startsWith('data: ')) {          │
│                 const data = line.slice(6).trim();     │
│                 if (data) {                             │
│                     await handleSSEEvent(data);     │
│                 }                                      │
│             }                                          │
│         }                                              │
│     }                                                  │
│                                                         │
└───────────────────────────────────────────────────┘
```

## 后端实现

### 1. 核心组件

#### 1.1 StreamResponseGenerator (`utils/stream_manager.py`)

流式响应生成器，管理 Agent 事件流和心跳。

```python
class StreamResponseGenerator:
    """
    流式响应生成器

    提供：
    1. 事件缓存（Redis 缓存最后 50 个 token）
    2. 断点续传支持
    3. 异常处理和 SSE 错误事件
    4. Message ID 生成和追踪
    """

    def __init__(
        self,
        session_manager: StreamSessionManager = None,
        enable_cache: bool = True,
        heartbeat_interval: int = 30
    ):
        self.session_manager = session_manager or StreamSessionManager()
        self.enable_cache = enable_cache
        self.heartbeat_interval = heartbeat_interval

    async def generate(
        self,
        agent_generator: AsyncGenerator[Dict[str, Any], None],
        session_id: str,
        user_id: str,
        message_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        生成流式响应

        Yields:
            str: SSE 格式的事件
        """
        # 生成 message_id
        if not message_id:
            message_id = self.session_manager.generate_message_id(session_id, user_id)

        # 创建事件队列（合并 agent 事件和心跳）
        event_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        # Agent 事件处理任务
        async def process_agent_events():
            try:
                async for agent_event in agent_generator:
                    # 转换为 StreamEvent
                    stream_event = self._convert_agent_event(
                        agent_event,
                        message_id,
                        sequence
                    )

                    # 缓存事件
                    if self.enable_cache:
                        await self.session_manager.save_event(message_id, stream_event)

                    # 加入队列
                    await event_queue.put(("event", stream_event))

                # 发送完成信号
                await event_queue.put(("done", None))

            except Exception as e:
                # 发送错误事件
                error_event = StreamEvent(
                    event_type=StreamEventType.ERROR,
                    content=str(e),
                    message_id=message_id,
                    sequence=sequence + 1
                )
                await event_queue.put(("event", error_event))
                await event_queue.put(("done", None))

        # 心跳任务
        async def heartbeat_task():
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                # 只在没有新事件时发送心跳
                if time_since_last_event >= self.heartbeat_interval:
                    heartbeat_event = StreamEvent(
                        event_type=StreamEventType.HEARTBEAT,
                        content="ping",
                        message_id=message_id,
                        sequence=sequence
                    )
                    await event_queue.put(("heartbeat", heartbeat_event))

        # 启动任务
        agent_task = asyncio.create_task(process_agent_events())
        heartbeat_task_obj = asyncio.create_task(heartbeat_task())

        try:
            # 处理队列中的事件
            while True:
                event_type, event = await event_queue.get()

                if event_type == "done":
                    break

                if event_type == "event":
                    # 发送事件
                    try:
                        yield event.to_sse()
                    except Exception as e:
                        # 发送失败，更新状态为错误
                        await self.session_manager.save_message_meta(
                            message_id, session_id, user_id,
                            {"status": "error", "error": str(e)}
                        )
                        break

                # 检查是否完成事件
                if event.event_type == StreamEventType.COMPLETE:
                    # 更新元数据
                    await self.session_manager.save_message_meta(
                        message_id, session_id, user_id,
                        {"status": "completed", "total_events": sequence}
                    )
                    break

                # 检查是否错误事件
                if event.event_type == StreamEventType.ERROR:
                    # 更新元数据
                    await self.session_manager.save_message_meta(
                        message_id, session_id, user_id,
                        {"status": "error", "error": event.content}
                    )
                    break

                elif event_type == "heartbeat":
                    # 心跳不缓存，直接发送
                    try:
                        yield event.to_sse()
                    except Exception as e:
                        # 心跳发送失败，认为连接断开
                        break

        finally:
            # 取消任务
            agent_task.cancel()
            heartbeat_task_obj.cancel()
```

#### 1.2 StreamSessionManager (`utils/stream_manager.py`)

流式会话管理器，负责事件缓存和会话恢复。

```python
class StreamSessionManager:
    """
    流式会话管理器

    负责：
    1. 生成唯一 message_id
    2. 缓存流式事件到 Redis
    3. 支持断点续传
    """

    # Redis 键前缀
    STREAM_CACHE_PREFIX = "stream:cache:"
    STREAM_META_PREFIX = "stream:meta:"

    # 配置
    MAX_CACHE_SIZE = int(os.getenv("STREAM_CACHE_SIZE", "200"))  # 默认缓存 200 个事件
    CACHE_TTL = 3600  # 缓存过期时间（秒）

    async def save_event(
        self,
        message_id: str,
        event: StreamEvent
    ) -> bool:
        """
        保存事件到 Redis

        Args:
            message_id: 消息 ID
            event: 流式事件

        Returns:
            bool: 是否保存成功
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False

            # 缓存键
            cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"

            # 事件数据
            event_data = json.dumps(event.to_dict())

            # 使用 Redis List 存储事件
            await redis.rpush(cache_key, event_data)

            # 限制缓存大小
            await redis.ltrim(cache_key, 0, self.MAX_CACHE_SIZE - 1)

            # 设置过期时间
            await redis.expire(cache_key, self.CACHE_TTL)

            return True

        except Exception as e:
            self.logger.error(f"保存事件失败: {e}")
            return False

    async def get_cached_events(
        self,
        message_id: str,
        from_sequence: int = 0
    ) -> List[StreamEvent]:
        """
        获取缓存的事件

        Args:
            message_id: 消息 ID
            from_sequence: 从哪个序列号开始获取

        Returns:
            List[StreamEvent]: 事件列表
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return []

            cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"

            # 获取所有缓存事件
            cached_data = await redis.lrange(cache_key, 0, -1)

            events = []
            for data in cached_data:
                try:
                    event_dict = json.loads(data)
                    event = StreamEvent(
                        event_type=StreamEventType(event_dict["event_type"]),
                        content=event_dict["content"],
                        metadata=event_dict.get("metadata", {}),
                        timestamp=event_dict.get("timestamp", ""),
                        message_id=event_dict.get("message_id", ""),
                        sequence=event_dict.get("sequence", 0)
                    )
                    # 只返回序列号大于 from_sequence 的事件
                    if event.sequence > from_sequence:
                        events.append(event)
                except Exception as e:
                    self.logger.warning(f"解析缓存事件失败: {e}")

            return events

        except Exception as e:
            self.logger.error(f"获取缓存事件失败: {e}")
            return []

    async def resume(
        self,
        message_id: str,
        from_sequence: int = 0
    ) -> AsyncGenerator[str, None]:
        """
        断点续传

        Args:
            message_id: 消息 ID
            from_sequence: 从哪个序列号开始恢复

        Yields:
            str: SSE 格式的事件
        """
        # 获取缓存的事件
        cached_events = await self.get_cached_events(message_id, from_sequence)

        if not cached_events:
            # 没有缓存数据
            no_data_event = StreamEvent(
                event_type=StreamEventType.ERROR,
                content="没有找到可恢复的缓存数据",
                message_id=message_id,
                sequence=0
            )
            yield no_data_event.to_sse()
            return

        # 发送缓存的事件
        for event in cached_events:
            yield event.to_sse()

        # 检查是否已完成
        last_event = cached_events[-1]
        if last_event.event_type == StreamEventType.COMPLETE:
            # 已经完成，不需要继续
            return

        # 如果未完成，通知前端需要重新请求
        resume_info_event = StreamEvent(
            event_type=StreamEventType.PROGRESS,
            content=f"已恢复到序列 {last_event.sequence}，请重新发起请求以继续",
            metadata={
                "message_id": message_id,
                "last_sequence": last_event.sequence,
                "need_restart": True
            },
            message_id=message_id,
            sequence=last_event.sequence + 1
        )
        yield resume_info_event.to_sse()
```

### 2. API 端点 (`apis/core/chat_routes.py`)

```python
@router.post("")
async def chat_handler(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """
    处理聊天请求 - 支持流式输出

    Args:
        request: 聊天请求
        background_tasks: 后台任务
        http_request: HTTP 请求对象

    Returns:
        StreamingResponse: 流式响应
    """
    try:
        logger.info(f"收到聊天请求: user_id={request.user_id}, session_id={request.session_id}")

        # 解析引用
        resolved_input, reference_trace = await resolve_references(request)

        # 构建请求数据
        request_data = {
            "input": resolved_input,
            "query": resolved_input,
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{hash(resolved_input)}",
            "project_id": request.project_id,
            "file_ids": request.file_ids or [],
            "auto_mode": request.auto_mode,
            "user_selections": request.user_selections or [],
            "reference_trace": reference_trace,
            "original_input": request.input,
            "stream_mode": True,
            "context": http_request.url.path
        }

        # 解析并加载 Agent
        agent_id = request.agent_id or "short_drama_planner"
        module_path, class_name = _resolve_agent_import(agent_id)

        try:
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            agent = agent_class()
        except Exception as agent_error:
            raise HTTPException(status_code=404, detail=f"未找到可用Agent: {agent_id}")

        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "project_id": request.project_id,
            "request_path": http_request.url.path,
            "http_request": http_request,
            "background_tasks": background_tasks
        }

        # 获取 Agent 生成器
        agent_generator = build_agent_generator(agent, request_data, context)

        # 创建流式响应
        session_id = request.session_id or f"session_{hash(resolved_input)}"
        user_id = request.user_id or "default_user"
        stream_generator = get_stream_response_generator()

        return StreamingResponse(
            stream_generator.generate(
                agent_generator=agent_generator,
                session_id=session_id,
                user_id=user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        error_result = await handle_error(e, "chat_processing", {
            "user_id": getattr(request, 'user_id', 'unknown'),
            "session_id": getattr(request, 'session_id', 'unknown')
        })
        raise HTTPException(status_code=500, detail=error_result.get("message", "处理失败"))

@router.post("/resume")
async def resume_chat(request: Request):
    """
    恢复中断的聊天会话

    Args:
        request: HTTP 请求对象

    Returns:
        StreamingResponse: 从断点继续的流式响应
    """
    try:
        # 从请求体获取恢复参数
        request_data = await request.json()
        session_id = request_data.get("session_id")
        message_id = request_data.get("message_id")
        from_sequence = request_data.get("from_sequence", 0)

        if not session_id or not message_id:
            raise HTTPException(status_code=400, detail="缺少必要参数")

        logger.info(f"恢复会话: session_id={session_id}, message_id={message_id}, from_sequence={from_sequence}")

        # 获取流式会话管理器
        session_manager = get_stream_session_manager()

        # 恢复会话
        stream_generator = session_manager.resume_session(
            session_id=session_id,
            message_id=message_id,
            from_sequence=from_sequence
        )

        if not stream_generator:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")

        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="恢复失败")
```

## 数据格式

### 1. SSE 事件格式

所有 SSE 事件遵循统一格式：

```
data: {"event_type":"message","content":"...","metadata":{...},"timestamp":"...","message_id":"...","sequence":1}

```

**字段说明**：
- `event_type`: 事件类型（message, thinking, progress, error, complete, heartbeat 等）
- `content`: 事件内容
- `metadata`: 元数据（可选）
- `timestamp`: 时间戳（ISO 8601 格式）
- `message_id`: 消息 ID
- `sequence`: 序列号

### 2. 事件类型 (`apis/core/schemas.py`)

```python
class EventType(str, Enum):
    """事件类型枚举"""
    MESSAGE = "message"           # 普通消息
    LLM_CHUNK = "llm_chunk"       # LLM内容片段
    THOUGHT = "thought"           # 思考过程
    TOOL_CALL = "tool_call"       # 工具调用开始
    TOOL_RETURN = "tool_return"   # 工具调用返回
    TOOL_PROCESSING = "tool_processing"  # 工具处理中
    ERROR = "error"               # 错误事件
    DONE = "done"                 # 完成信号
    BILLING = "billing"           # 计费信息
    PROGRESS = "progress"         # 进度更新
    SYSTEM = "system"             # 系统消息
```

### 3. 内容类型 (`apis/core/schemas.py`)

```python
class StreamContentType(str, Enum):
    """流式内容类型枚举 - juben剧本创作专用"""

    # 基础类型
    TEXT = "text"                    # 普通文本
    MARKDOWN = "markdown"            # Markdown格式内容
    JSON = "json"                    # JSON结构化数据

    # 思考和分析类
    THOUGHT = "thought"              # Agent的内心思考过程
    PLAN_STEP = "plan_step"            # 执行计划步骤
    INSIGHT = "insight"              # 洞察分析

    # 人物相关
    CHARACTER_PROFILE = "character_profile"       # 人物画像/小传
    CHARACTER_RELATIONSHIP = "character_relationship" # 人物关系分析

    # 故事结构相关
    STORY_SUMMARY = "story_summary"              # 故事梗概/总结
    STORY_OUTLINE = "story_outline"              # 故事大纲
    STORY_TYPE = "story_type"                    # 故事类型分析
    FIVE_ELEMENTS = "five_elements"              # 故事五元素分析
    SERIES_INFO = "series_info"                  # 系列信息
    SERIES_ANALYSIS = "series_analysis"          # 系列分析

    # 情节相关
    MAJOR_PLOT = "major_plot"                    # 大情节点
    DETAILED_PLOT = "detailed_plot"              # 详细情节点
    DRAMA_ANALYSIS = "drama_analysis"            # 剧本功能分析
    PLOT_ANALYSIS = "plot_analysis"              # 情节分析

    # 创作相关
    SCRIPT = "script"                            # 剧本内容
    DRAMA_PLAN = "drama_plan"                    # 剧本策划
    PROPOSAL = "proposal"                        # 内容提案

    # 可视化
    MIND_MAP = "mind_map"                        # 思维导图

    # 评估相关
    EVALUATION = "evaluation"                    # 综合评估结果
    SCRIPT_EVALUATION = "script_evaluation"      # 剧本评估
    STORY_EVALUATION = "story_evaluation"        # 故事评估
    OUTLINE_EVALUATION = "outline_evaluation"    # 大纲评估
    IP_EVALUATION = "ip_evaluation"              # IP评估
    NOVEL_SCREENING = "novel_screening"          # 小说筛选
    SCORE_ANALYSIS = "score_analysis"            # 评分分析

    # 工具相关
    SEARCH_RESULT = "search_result"              # 搜索结果（百度/网络）
    KNOWLEDGE_RESULT = "knowledge_result"        # 知识库检索结果
    REFERENCE_RESULT = "reference_result"        # 参考文献结果
    DOCUMENT = "document"                        # 文档生成
    FORMATTED_CONTENT = "formatted_content"      # 格式化输出

    # 系统相关
    SYSTEM_PROGRESS = "system_progress"          # 系统进度提示
    TOOL_RESULT = "tool_result"                  # 工具执行结果
    WORKFLOW_PROGRESS = "workflow_progress"      # 工作流进度
    RESULT_INTEGRATION = "result_integration"    # 结果整合
    TEXT_OPERATION = "text_operation"            # 文本操作
    BATCH_PROGRESS = "batch_progress"            # 批处理进度

    # 其他
    FINAL_ANSWER = "final_answer"                # 最终整合答案
    ERROR = "error_content"                      # 错误内容
```

## 交互流程

### 1. 完整的流式响应流程

```
┌──────────────────────────────────────────────────────────┐
│            Agent 输出完整流程                   │
├──────────────────────────────────────────────────────────┤
│                                                         │
│  1. 用户输入                                        │
│     "帮我创作一个现代都市爱情短剧"                  │
│     │                                               │
│     ▼                                               │
│  [前端] 发送 POST /juben/chat                        │
│     Body: {                                         │
│       "input": "帮我创作一个现代都市爱情短剧",        │
│       "user_id": "user_123",                       │
│       "session_id": "session_456",                   │
│       "agent_id": "short_drama_creator",             │
│       "stream_mode": true                             │
│     }                                                │
│     │                                               │
│     ▼                                               │
│  [后端] FastAPI 处理                              │
│     - 解析 agent_id                                  │
│     - 加载 Agent 类                                 │
│     - 构建上下文                                    │
│     - 调用 agent.process_request()               │
│     │                                               │
│     ▼                                               │
│  [Agent] process_request()                         │
│     async def process_request(                       │
│         self, request_data, context                  │
│     ) -> AsyncGenerator[Dict, None]:                │
│         # 开始处理                                   │
│         yield {                                       │
│             "event_type": "thinking",               │
│             "content": "正在分析您的需求...",         │
│         }                                              │
│                                                         │
│         # 调用 LLM                                     │
│         async for chunk in self._call_llm(...):    │
│             yield {                                       │
│                 "event_type": "message",               │
│                 "content": chunk,                       │
│                 "metadata": {                            │
│                     "content_type": "text"            │
│                 }                                          │
│             }                                              │
│                                                         │
│         # 生成结果                                     │
│         yield {                                       │
│             "event_type": "message",               │
│             "content": "【第一场】\n场景：...",      │
│             "metadata": {                            │
│                 "content_type": "script"            │
│             }                                          │
│         }                                              │
│                                                         │
│         # 完成                                         │
│         yield {                                       │
│             "event_type": "complete"               │
│             "data": {                                   │
│                 "total_events": 45                 │
│             }                                          │
│         }                                              │
│                                                         │
│     ▼                                               │
│  [StreamResponseGenerator] 格式化                   │
│     - 添加 timestamp                                  │
│     - 添加 message_id                                │
│     - 添加 sequence                                   │
│     - 转换为 SSE 格式                                │
│     - 发送到前端                                     │
│                                                         │
│     ▼                                               │
│  [前端] 接收并处理                               │
│     - 解析 SSE 格式                                  │
│     - 更新消息内容                                   │
│     - 触发事件回调                                   │
│     - 更新 UI 状态                                   │
│                                                         │
└──────────────────────────────────────────────────────────┘
```

### 2. 断点续传流程

```
┌──────────────────────────────────────────────────────────┐
│              断点续传流程                         │
├──────────────────────────────────────────────────────────┤
│                                                         │
│  1. 网络中断                                         │
│     [连接丢失]                                        │
│     │                                               │
│     ▼                                               │
│  [前端] 检测到连接断开                            │
│     - 3 秒无心跳                                    │
│     - fetch/read 失败                                │
│     │                                               │
│     ▼                                               │
│  [自动重连]                                         │
│     maxReconnectAttempts = 3                         │
│     reconnectDelay = 2000ms                           │
│     │                                               │
│     ▼                                               │
│  [POST /juben/chat/resume]                         │
│     Body: {                                         │
│       "message_id": "msg_xxx",                      │
│       "session_id": "session_xxx",                  │
│       "from_sequence": 23                           │
│     }                                                │
│     │                                               │
│     ▼                                               │
│  [后端] 从 Redis 缓存读取                         │
│     cached_events = await redis.lrange(               │
│         "stream:cache:msg_xxx",                       │
│         0, -1                                         │
│     )                                                │
│     │                                               │
│     ▼                                               │
│  [过滤出序列号 > 23 的事件]                       │
│     for event in cached_events:                     │
│         if event.sequence > 23:                  │
│             yield event.to_sse()                    │
│                                                         │
│     ▼                                               │
│  [前端] 接收缓存事件                               │
│     - 追加到消息内容                                 │
│     - 更新 UI 状态                                    │
│     - 继续等待新事件                                   │
│                                                         │
│     ▼                                               │
│  [检查最后事件状态]                                │
│     if last_event.type == "complete":               │
│         # 已完成，停止恢复                          │
│     else:                                            │
│         # 未完成，通知前端重新请求               │
│         yield {                                       │
│             "event_type": "progress",              │
│             "content": "请重新发起请求以继续",      │
│             "metadata": {                            │
│                 "need_restart": true                  │
│             }                                          │
│         }                                              │
│                                                         │
└──────────────────────────────────────────────────────────┘
```

## 高级特性

### 1. 心跳机制

**目的**: 检测连接活性，及时发现断连

```python
# 后端心跳发送（30 秒间隔）
async def heartbeat_task():
    while True:
        await asyncio.sleep(30)  # 30 秒间隔

        # 只在没有新事件时发送心跳
        time_since_last_event = current_time - last_event_time

        if time_since_last_event >= 30:
            heartbeat_event = StreamEvent(
                event_type=StreamEventType.HEARTBEAT,
                content="ping",
                message_id=message_id,
                sequence=sequence
            )
            await event_queue.put(("heartbeat", heartbeat_event))
```

```typescript
// 前端心跳检测（30 + 5 秒容差）
this.heartbeatTimer = window.setTimeout(() => {
    if (!this.state.isConnected) {
        console.warn('[SSE] Connection lost, no heartbeat received');
        this._handleConnectionLost();
    } else {
        // 重新启动心跳
        this._startHeartbeat();
    }
}, this.config.heartbeatInterval + 5000); // 额外 5 秒容差
```

### 2. 事件缓存

**目的**: 断点续传时恢复历史事件

```python
# Redis List 结构
# Key: stream:cache:{message_id}
# Value: ["{event_1}", "{event_2}", ..., "{event_n}"]
# TTL: 3600 秒（1 小时）
# Max: 200 个事件

async def save_event(self, message_id: str, event: StreamEvent):
    redis = await self._get_redis()
    cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"

    # 使用 RPUSH 添加到列表头部
    await redis.rpush(cache_key, event_data)

    # 限制列表大小（保留最近 200 个）
    await redis.ltrim(cache_key, 0, self.MAX_CACHE_SIZE - 1)

    # 设置过期时间
    await redis.expire(cache_key, self.CACHE_TTL)
```

### 3. 自动重连

**策略**:
- 最多重试 3 次
- 每次延迟 2 秒
- 只在网络错误时重连（TypeError, fetch error）
- AbortError 不重连（用户主动取消）

```typescript
private async _reconnect(): Promise<void> {
    if (!this.currentRequest) {
        console.error('[SSE] No request available for reconnect');
        return;
    }

    if (this.state.reconnectAttempts >= this.config.maxReconnectAttempts) {
        console.error('[SSE] Max reconnect attempts reached');
        return;
    }

    this.state.reconnectAttempts++;

    await new Promise(resolve => setTimeout(resolve, this.config.reconnectDelay));

    try:
        await this.connect(this.currentRequest);
    } catch (error) {
        // 重连失败，已经在 connect 方法中处理
    }
}
```

### 4. 消息 ID 追踪

**格式**: `msg_{user_id}_{session_id}_{timestamp}_{unique}`

```python
def generate_message_id(self, session_id: str, user_id: str) -> str:
    """生成唯一消息 ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"msg_{user_id}_{session_id}_{timestamp}_{unique}"
```

**作用**:
- 唯一标识每次会话
- 支持断点续传时恢复上下文
- 追踪用户多轮对话历史

### 5. 序列号管理

**目的**: 保证事件顺序，支持断点续传

```python
sequence = 0
last_event_time = asyncio.get_event_loop().time()

async def process_agent_events():
    nonlocal sequence, last_event_time
    try:
        async for agent_event in agent_generator:
            sequence += 1
            last_event_time = asyncio.get_event_loop().time()

            # 转换为 StreamEvent，包含序列号
            stream_event = self._convert_agent_event(
                agent_event,
                message_id,
                sequence  # 递增序列号
            )

            # 缓存事件（包含序列号）
            await self.session_manager.save_event(message_id, stream_event)

            # 发送到前端
            yield stream_event.to_sse()
```

## 错误处理

### 1. 网络错误

**可重试的错误**:
- `TypeError`: 网络类型错误
- `fetch` 失败: 网络请求失败
- `timeout`: 请求超时

**不可重试的错误**:
- `AbortError`: 用户主动取消
- HTTP 4xx 错误: 客户端错误（重试无意义）
- HTTP 404: 资源不存在

```typescript
private _shouldReconnect(error: any): boolean {
    // 网络错误
    if (error?.name === 'TypeError' || error?.message?.includes('fetch')) {
        return this.state.reconnectAttempts < this.config.maxReconnectAttempts;
    }

    // AbortError 不重连
    if (error?.name === 'AbortError') {
        return false;
    }

    return false;
}
```

### 2. Agent 错误

**处理流程**:
1. 捕获 Agent 异常
2. 转换为错误事件
3. 更新消息状态为错误
4. 停止流式输出

```python
try:
    async for agent_event in agent_generator:
        # 处理事件
        ...
except Exception as e:
    # 发送错误事件
    error_event = StreamEvent(
        event_type=StreamEventType.ERROR,
        content=str(e),
        message_id=message_id,
        sequence=sequence + 1
    )
    await event_queue.put(("event", error_event))
    await event_queue.put(("done", None))
```

### 3. 前端错误处理

```typescript
// SSE 事件处理错误
try {
    const data = JSON.parse(event.data);
    // ... 处理事件
} catch (error) {
    console.error('[SSE] Error parsing event:', error, event.data);
}

// 连接错误
this.onError((error) => {
    console.error('[ChatSessionManager] SSE error:', error);

    // 检查是否需要重连
    if (this._isNetworkError(error)) {
        const state = this.sseClient!.getState();
        if (state.reconnectAttempts < 3) {
            console.log('[ChatSessionManager] Initiating reconnection...');
            this._emit('reconnecting', state.reconnectAttempts + 1);
        }
    }

    // 通知 UI
    this._emit('error', error);
});
```

## 性能优化

### 1. 事件队列

**问题**: Agent 生成事件速度快，网络发送慢

**解决**: 使用 `asyncio.Queue` 缓冲

```python
# 创建事件队列（200 大小）
event_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

# Agent 事件处理任务（快速消费者）
async def process_agent_events():
    async for agent_event in agent_generator:
        # 快速处理并加入队列
        await event_queue.put(("event", stream_event))

# 心跳任务（定时生产者）
async def heartbeat_task():
    while True:
        await asyncio.sleep(30)
        await event_queue.put(("heartbeat", heartbeat_event))

# 主循环（慢速消费者）
while True:
    event_type, event = await event_queue.get()

    if event_type == "done":
        break

    # 发送事件（网络 IO，慢速操作）
    yield event.to_sse()
```

### 2. Redis 缓存优化

**批量操作**: 使用 Pipeline 减少网络往返

```python
async def save_events_batch(self, events: List[StreamEvent]) -> bool:
    """批量保存事件"""
    try:
        redis = await self._get_redis()
        pipe = redis.pipeline()

        for event in events:
            cache_key = f"{self.STREAM_CACHE_PREFIX}{event.message_id}"
            event_data = json.dumps(event.to_dict())
            pipe.rpush(cache_key, event_data)
            pipe.ltrim(cache_key, 0, self.MAX_CACHE_SIZE - 1)
            pipe.expire(cache_key, self.CACHE_TTL)

        await pipe.execute()
        return True

    except Exception as e:
        self.logger.error(f"批量保存事件失败: {e}")
        return False
```

### 3. 前端渲染优化

**虚拟滚动**: 只渲染可见部分

```typescript
import { useVirtualizer } from '@tanstack/virtual-list';

// 虚拟滚动 10000 条消息
const rowVirtualizer = useVirtualizer({
    estimateSize: _estimateSize,         // 估算每项高度
    overscan: 10,                      // 额外渲染项数
    scrollBehavior: 'smooth',          // 平滑滚动
});
```

**Markdown 缓存**: 缓存渲染结果

```typescript
// 缓存 Markdown 渲染结果
const cachedMarkdown = new Map<string, ReactNode>();

// 使用 React.memo 优化组件
const MemoizedMarkdown = React.memo(({ content }) => {
    const rendered = cachedMarkdown.get(content);
    if (rendered) {
        return rendered;
    }

    const node = renderMarkdown(content);
    cachedMarkdown.set(content, node);
    return node;
});
```

### 4. 连接池管理

```python
# 使用连接池复用 Redis 连接
class ConnectionPoolManager:
    def __init__(self):
        self._redis_pools: Dict[str, Any] = {}
        self._pool_configs = {
            'high_priority': {'max_connections': 200},  # 主业务操作
            'normal': {'max_connections': 100},        # 一般操作
            'background': {'max_connections': 50},     # 后台任务
        }

    async def get_redis_client(self, pool_type: str = 'high_priority'):
        """获取 Redis 客户端"""
        if pool_type in self._redis_pools:
            return self._redis_pools[pool_type]

        # 创建新连接池
        pool = aioredis.ConnectionPool.from_url(
            redis_url,
            max_connections=self._pool_configs[pool_type]['max_connections'],
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        self._redis_pools[pool_type] = pool
        return aioredis.Redis(connection_pool=pool)
```

## 安全考虑

### 1. 输入验证

```python
from pydantic import BaseModel, Field, validator

class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=5000)
    user_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    session_id: Optional[str] = Field(None, min_length=1, max_length=100)
    agent_id: Optional[str] = Field(None, min_length=1, max_length=100)

    @validator('input')
    def validate_input(cls, v):
        # 防止注入攻击
        if '<script>' in v.lower():
            raise ValueError('Invalid input: script tag detected')
        return v
```

### 2. 速率限制

```python
from slowapi import Limiter

# 全局限流器
limiter = Limiter(resource="http")

# API 限流
@router.post("", dependencies=[Depends(limiter)])
async def chat_handler(request: ChatRequest):
    ...
```

### 3. 用户隔离

```python
# 每个用户独立的 session_id 和 message_id
session_id: str = f"session_{hash(input)}_{timestamp}"
message_id: str = f"msg_{user_id}_{session_id}_{timestamp}_{unique}"

# Redis 缓存键隔离
cache_key = f"{self.STREAM_CACHE_PREFIX}{message_id}"

# 用户只能访问自己的缓存
# 在 API 层面验证用户权限
```

### 4. CORS 配置

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
)
```

## 监控和日志

### 1. 关键日志点

```python
logger.info(f"收到聊天请求: user_id={request.user_id}, session_id={request.session_id}")
logger.debug(f"请求内容: {request.input[:100]}")
logger.info(f"SSE 连接建立: message_id={message_id}")
logger.debug(f"发送事件: type={event.event_type}, sequence={event.sequence}")
logger.warning(f"SSE 心跳超时: {message_id}")
logger.error(f"SSE 发送失败: {error}")
```

### 2. 性能指标

```python
# 记录关键性能指标
- 请求处理时间
- LLM 响应时间
- SSE 事件发送速率
- 网络错误率
- 重连次数

# 示例代码
import time
start_time = time.time()

# ... 处理请求

duration = time.time() - start_time
logger.info(f"请求处理完成: 耗时 {duration:.2f}秒")
```

### 3. 错误告警

```python
# 错误率超过阈值时告警
error_rate = errors / total_requests
if error_rate > 0.05:  # 5% 错误率
    logger.error(f"错误率过高: {error_rate:.2%}")
    # 发送告警通知
```

## 最佳实践

### 1. 前端

- ✅ 使用 `AbortController` 支持请求取消
- ✅ 实现自动重连机制
- ✅ 监听连接状态变化
- ✅ 处理网络错误超时
- ✅ 优化大量消息渲染（虚拟滚动）
- ✅ 缓存 Markdown 渲染结果

### 2. 后端

- ✅ 使用事件队列解耦生产和消费
- ✅ 实现 Redis 事件缓存
- ✅ 发送心跳检测连接活性
- ✅ 记录详细的日志便于调试
- ✅ 实现输入验证和速率限制
- ✅ 使用连接池复用数据库连接

### 3. 测试

- ✅ 测试网络中断恢复
- ✅ 测试长时间请求超时
- ✅ 测试并发请求处理
- ✅ 测试缓存命中率和失效
- ✅ 测试重连机制

---

**最后更新**: 2026-02-14
**维护者**: 宫灵瑞
**版本**: v1.0

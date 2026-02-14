# 分布式锁使用说明

## 概述

分布式锁用于解决高并发场景下同一 `session_id` 的上下文竞争问题，确保同一会话的请求串行处理，避免对话串词或 Token 计算错误。

## 文件结构

```
utils/
├── distributed_lock.py              # 分布式锁核心实现
└── ...

apis/
├── core/
│   ├── api_routes.py               # 集成了分布式锁的 API 路由
│   └── distributed_lock_dependencies.py  # FastAPI 依赖和异常处理
└── ...

main.py                             # 应用入口（已注册异常处理器）
```

## 核心特性

### 1. Redis 分布式锁

- **锁格式**: `lock:session:{user_id}:{session_id}`
- **实现方式**: 使用 Redis `SET NX EX` 命令
- **默认超时**: 300 秒（5 分钟）
- **自动释放**: 即使异常退出也能自动释放

### 2. 防止死锁

- 设置合理的超时时间
- 使用 Lua 脚本确保只释放自己的锁
- 支持锁续期（长时间任务）

### 3. FastAPI 集成

- 自动返回 429 状态码
- 友好的错误消息："AI 正在思考中，请稍后再试"
- 异常处理器全局生效

## 使用方式

### 方式一：在 Agent 的 process_request 方法使用装饰器

```python
from utils.distributed_lock import with_session_lock

class MyAgent(BaseJubenAgent):
    @with_session_lock(lock_timeout=300)
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # 处理请求
        async for event in ...:
            yield event
```

### 方式二：使用上下文管理器

```python
from utils.distributed_lock import SessionLockContext

async def my_handler(request_data: dict, context: dict):
    session_id = context.get("session_id", "unknown")
    user_id = context.get("user_id", "unknown")

    async with SessionLockContext(session_id, user_id, lock_timeout=300) as lock:
        # 处理请求
        pass
```

### 方式三：在 FastAPI 路由中使用（已实现）

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or f"session_{hash(request.input)}"
    user_id = request.user_id or "unknown"

    async with SessionLockContext(session_id, user_id, lock_timeout=300):
        # 处理请求
        pass
```

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lock_timeout` | int | 300 | 锁超时时间（秒） |
| `blocking` | bool | False | 是否阻塞等待 |
| `blocking_timeout` | float | None | 阻塞等待的最大时间（秒） |
| `extend_lock_interval` | int | None | 锁续期间隔（秒） |

## 错误处理

当获取锁失败时，系统返回：

```json
{
    "success": false,
    "error": "AI 正在思考中，请稍后再试",
    "detail": "[lock:session:user:session_123] 锁已被占用",
    "status_code": 429
}
```

## 监控和调试

### 检查锁状态

```python
from utils.distributed_lock import is_session_locked

is_locked = await is_session_locked(session_id, user_id)
print(f"Session {session_id} is locked: {is_locked}")
```

### 强制释放锁（紧急情况）

```python
from utils.distributed_lock import get_distributed_lock

lock_manager = await get_distributed_lock()
await lock_manager.force_release(f"{user_id}:{session_id}")
```

## 注意事项

1. **锁超时设置**: 根据实际任务耗时设置，避免任务未完成锁就过期
2. **长时间任务**: 考虑使用锁续期机制 (`extend_lock_interval`)
3. **阻塞模式**: 生产环境建议使用 `blocking=False` 避免请求堆积
4. **Redis 可用性**: 确保Redis服务稳定运行

## 与现有功能的兼容性

- ✅ 与 `stop_manager` 停止管理器兼容
- ✅ 与 `connection_pool_manager` 连接池管理器兼容
- ✅ 与 `base_juben_agent` 的 Token 累加器兼容
- ✅ 与流式输出 (`StreamingResponse`) 兼容

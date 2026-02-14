"""
FastAPI 分布式锁集成
提供 FastAPI 依赖和异常处理，用于处理 session 锁

代码作者：宫灵瑞
创建时间：2026年2月7日
"""
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import logging

try:
    from ...utils.distributed_lock import (
        LockAcquisitionError,
        SessionLockContext,
        acquire_session_lock,
        release_session_lock,
        is_session_locked
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from utils.distributed_lock import (
        LockAcquisitionError,
        SessionLockContext,
        acquire_session_lock,
        release_session_lock,
        is_session_locked
    )

logger = logging.getLogger("FastAPIDistributedLock")


# ==================== 异常处理器 ====================

async def lock_acquisition_exception_handler(
    request: Request,
    exc: LockAcquisitionError
) -> JSONResponse:
    """
    处理锁获取失败异常

    返回 429 状态码和友好的错误消息
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": "AI 正在思考中，请稍后再试",
            "detail": str(exc),
            "status_code": 429
        }
    )


# ==================== FastAPI 依赖 ====================

class SessionLockDependency:
    """
    Session 锁依赖

    用法：
    ```python
    @router.post("/chat")
    async def chat_endpoint(
        request_data: ChatRequest,
        session_lock: SessionLockDependency = Depends()
    ):
        # 锁已自动获取
        # 处理请求...
        pass
    # 锁自动释放
    ```
    """

    def __init__(
        self,
        lock_timeout: int = 300,
        blocking: bool = False,
        error_message: str = "AI 正在思考中，请稍后再试"
    ):
        self.lock_timeout = lock_timeout
        self.blocking = blocking
        self.error_message = error_message

    async def __call__(
        self,
        request_data: Dict[str, Any],
        session_id: str,
        user_id: str = None
    ) -> SessionLockContext:
        """
        获取锁并返回上下文管理器

        注意：这里只验证锁是否可获取，实际的锁管理
        应该在路由处理函数中使用 async with
        """
        # 检查锁是否已被占用
        is_locked = await is_session_locked(session_id, user_id)

        if is_locked and not self.blocking:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=self.error_message
            )

        # 返回锁上下文管理器
        return SessionLockContext(
            session_id=session_id,
            user_id=user_id,
            lock_timeout=self.lock_timeout,
            blocking=self.blocking
        )


def get_session_lock(
    lock_timeout: int = 300,
    blocking: bool = False,
    error_message: str = "AI 正在思考中，请稍后再试"
):
    """
    获取 session 锁依赖（便捷函数）

    用法：
    ```python
    @router.post("/chat")
    async def chat_endpoint(
        request_data: ChatRequest,
        lock_ctx: SessionLockContext = Depends(get_session_lock())
    ):
        async with lock_ctx as lock:
            # 处理请求
            pass
    ```

    Args:
        lock_timeout: 锁超时时间（秒）
        blocking: 是否阻塞等待
        error_message: 获取锁失败时的错误消息

    Returns:
        FastAPI 依赖函数
    """

    async def dependency(
        session_id: str,
        user_id: str = None
    ) -> SessionLockContext:
        is_locked = await is_session_locked(session_id, user_id)

        if is_locked and not blocking:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message
            )

        return SessionLockContext(
            session_id=session_id,
            user_id=user_id,
            lock_timeout=lock_timeout,
            blocking=blocking
        )

    return dependency


# ==================== 装饰器版本 ====================

def locked_endpoint(
    lock_timeout: int = 300,
    blocking: bool = False,
    error_message: str = "AI 正在思考中，请稍后再试"
):
    """
    端点锁装饰器

    用法：
    ```python
    @router.post("/chat")
    @locked_endpoint(lock_timeout=300)
    async def chat_endpoint(request_data: ChatRequest):
        # 自动从 request_data 中提取 session_id 和 user_id
        # 自动获取锁和释放锁
        pass
    ```

    Args:
        lock_timeout: 锁超时时间（秒）
        blocking: 是否阻塞等待
        error_message: 获取锁失败时的错误消息
    """

    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中提取 session_id 和 user_id
            session_id = None
            user_id = None

            # 检查 kwargs
            session_id = kwargs.get('session_id')
            user_id = kwargs.get('user_id')

            # 检查 request_data
            if not session_id:
                for arg in args:
                    if isinstance(arg, dict):
                        session_id = arg.get('session_id')
                        user_id = user_id or arg.get('user_id')
                        break

            if not session_id:
                logger.warning("⚠️ 未找到 session_id，跳过分布式锁")
                return await func(*args, **kwargs)

            # 检查锁状态
            is_locked = await is_session_locked(session_id, user_id)

            if is_locked and not blocking:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_message
                )

            # 获取锁
            lock_value = await acquire_session_lock(session_id, user_id, lock_timeout)

            if lock_value is None:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_message
                )

            try:
                # 执行原函数
                return await func(*args, **kwargs)
            finally:
                # 释放锁
                await release_session_lock(session_id, user_id, lock_value)

        return wrapper

    return decorator


# ==================== 工具函数 ====================

async def check_session_lock_status(
    session_id: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    检查 session 锁状态

    Args:
        session_id: 会话ID
        user_id: 用户ID

    Returns:
        Dict: 锁状态信息
    """
    is_locked = await is_session_locked(session_id, user_id)

    return {
        "session_id": session_id,
        "user_id": user_id,
        "is_locked": is_locked,
        "message": "会话正在进行中" if is_locked else "会话空闲"
    }


# ==================== FastAPI 路由集成示例 ====================

"""
在 FastAPI 应用中使用分布式锁的几种方式：

## 方式1: 使用异常处理器（推荐）

```python
from fastapi import FastAPI, APIRouter, Depends
from utils.distributed_lock import with_session_lock, SessionLockContext
from apis.core.distributed_lock_dependencies import (
    lock_acquisition_exception_handler,
    get_session_lock
)

app = FastAPI()
router = APIRouter()

# 添加异常处理器
app.add_exception_handler(
    LockAcquisitionError,
    lock_acquisition_exception_handler
)

# 在路由中使用装饰器
@router.post("/chat")
@with_session_lock(lock_timeout=300)
async def chat_endpoint(request_data: dict, context: dict):
    # 处理请求...
    pass

# 或者使用上下文管理器
@router.post("/chat")
async def chat_endpoint(
    request_data: dict,
    context: dict,
    lock_ctx: SessionLockContext = Depends(get_session_lock())
):
    async with lock_ctx:
        # 处理请求...
        pass
```

## 方式2: 手动处理

```python
from fastapi import HTTPException, status
from utils.distributed_lock import SessionLockContext

@router.post("/chat")
async def chat_endpoint(request_data: dict, context: dict):
    session_id = context.get("session_id", "unknown")
    user_id = context.get("user_id", "unknown")

    async with SessionLockContext(session_id, user_id, lock_timeout=300) as lock:
        # 处理请求...
        pass
```

## 方式3: 使用端点装饰器

```python
from apis.core.distributed_lock_dependencies import locked_endpoint

@router.post("/chat")
@locked_endpoint(lock_timeout=300)
async def chat_endpoint(request_data: dict, context: dict):
    # 处理请求...
    pass
```
"""

"""
限流依赖项
为 FastAPI 路由提供限流功能的依赖注入
"""
from fastapi import Request, HTTPException, Depends
from typing import Optional
from utils.rate_limiter import get_rate_limiter, check_rate_limit
from utils.logger import get_logger
from utils.exceptions import RateLimitException

logger = get_logger("rate_limit_dependency")


class RateLimitDepends:
    """限流依赖类"""

    def __init__(
        self,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        key_func: Optional[callable] = None
    ):
        """
        初始化限流依赖

        Args:
            limit: 限制次数，None 则使用全局配置
            window_seconds: 时间窗口（秒），None 则使用全局配置
            key_func: 用于提取限流键的函数，接收 Request 返回 str
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """默认的键提取函数 - 使用用户ID或IP"""
        # 尝试从请求中获取用户ID
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"user:{user_id}"

        # 尝试从查询参数获取用户ID
        if hasattr(request, "query") and "user_id" in request.query:
            return f"user:{request.query['user_id']}"

        # 使用客户端IP作为fallback
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def __call__(self, request: Request) -> None:
        """
        执行限流检查

        Raises:
            HTTPException: 当超过限流阈值时
        """
        # 提取限流键
        identifier = self.key_func(request)

        # 检查限流
        allowed, info = await check_rate_limit(
            identifier=identifier,
            limit=self.limit,
            window_seconds=self.window_seconds
        )

        # 添加限流信息到请求状态（供后续使用）
        if not hasattr(request.state, "_rate_limit_info"):
            request.state._rate_limit_info = {}
        request.state._rate_limit_info = info

        # 如果超过限制，抛出异常
        if not allowed:
            logger.warning(f"限流触发: {identifier}, 当前: {info['current_count']}/{info['limit']}")

            raise RateLimitException(
                message="请求过于频繁，请稍后再试",
                retry_after=info.get("reset_time", 0) - int(__import__("time").time()),
                details={
                    "current": info["current_count"],
                    "limit": info["limit"],
                    "window": info["window_seconds"],
                    "reset_at": info.get("reset_time")
                }
            )


# ==================== 预定义的限流依赖 ====================

async def rate_limit_auth(request: Request) -> None:
    """
    认证用户的限流依赖（较宽松）
    限制: 100 次/分钟
    """
    key = f"user:{request.headers.get('X-User-ID', 'anonymous')}"
    allowed, info = await check_rate_limit(identifier=key, limit=100, window_seconds=60)

    if not allowed:
        raise RateLimitException(
            message="请求过于频繁，请稍后再试",
            retry_after=info.get("reset_time", 0) - int(__import__("time").time()),
            details={"limit": 100, "window": 60}
        )


async def rate_limit_anon(request: Request) -> None:
    """
    匿名用户的限流依赖（较严格）
    限制: 20 次/分钟
    """
    client_host = request.client.host if request.client else "unknown"
    key = f"ip:{client_host}"
    allowed, info = await check_rate_limit(identifier=key, limit=20, window_seconds=60)

    if not allowed:
        raise RateLimitException(
            message="请求过于频繁，请稍后再试",
            retry_after=info.get("reset_time", 0) - int(__import__("time").time()),
            details={"limit": 20, "window": 60}
        )


async def rate_limit_chat(request: Request) -> None:
    """
    聊天接口的限流依赖（中等）
    限制: 60 次/分钟
    """
    key = f"chat:{request.headers.get('X-User-ID', request.client.host if request.client else 'unknown')}"
    allowed, info = await check_rate_limit(identifier=key, limit=60, window_seconds=60)

    if not allowed:
        raise RateLimitException(
            message="聊天请求过于频繁，请稍后再试",
            retry_after=info.get("reset_time", 0) - int(__import__("time").time()),
            details={"limit": 60, "window": 60}
        )


async def rate_limit_search(request: Request) -> None:
    """
    搜索接口的限流依赖（较严格）
    限制: 30 次/分钟
    """
    key = f"search:{request.headers.get('X-User-ID', request.client.host if request.client else 'unknown')}"
    allowed, info = await check_rate_limit(identifier=key, limit=30, window_seconds=60)

    if not allowed:
        raise RateLimitException(
            message="搜索请求过于频繁，请稍后再试",
            retry_after=info.get("reset_time", 0) - int(__import__("time").time()),
            details={"limit": 30, "window": 60}
        )


# ==================== 辅助函数 ====================

def get_rate_limit_info(request: Request) -> dict:
    """
    从请求状态中获取限流信息

    Args:
        request: FastAPI 请求对象

    Returns:
        限流信息字典
    """
    return getattr(request.state, "_rate_limit_info", {
        "current_count": 0,
        "limit": 0,
        "window_seconds": 60,
        "enabled": False
    })

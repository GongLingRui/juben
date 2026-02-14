"""
增强的速率限制中间件
支持 Redis 后端和分层限流（用户级别、IP 级别、API 级别）
"""
import asyncio
import time
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

try:
    import redis
    from redis import asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimitConfig:
    """速率限制配置"""

    # 默认限制（每分钟请求数）
    DEFAULT_LIMITS = {
        "global": 120,          # 全局限制
        "per_ip": 60,           # 每个 IP
        "per_user": 100,        # 每个用户
        "per_endpoint": {       # 每个端点
            "/juben/chat": 30,
            "/juben/creator/chat": 30,
            "/juben/evaluation/chat": 30,
            "/auth/login": 10,
            "/auth/register": 5,
        }
    }

    # 严格模式的限制（生产环境）
    STRICT_LIMITS = {
        "global": 60,
        "per_ip": 30,
        "per_user": 50,
        "per_endpoint": {
            "/juben/chat": 15,
            "/juben/creator/chat": 15,
            "/juben/evaluation/chat": 15,
            "/auth/login": 5,
            "/auth/register": 3,
        }
    }

    @classmethod
    def get_limits(cls, strict: bool = False) -> Dict[str, Any]:
        """获取当前环境的限制配置"""
        app_env = os.getenv("APP_ENV", "development")
        use_strict = strict or app_env == "production"
        return cls.STRICT_LIMITS if use_strict else cls.DEFAULT_LIMITS


import os


class InMemoryRateLimiter:
    """内存速率限制器（用于开发和测试）"""

    def __init__(self):
        self._requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查是否允许请求

        Args:
            key: 限制键（如 user:123, ip:1.2.3.4）
            limit: 时间窗口内允许的最大请求数
            window: 时间窗口（秒）

        Returns:
            (是否允许, 限制信息)
        """
        now = time.time()
        window_start = now - window

        async with self._lock:
            # 获取该键的请求记录
            requests = self._requests.get(key, [])

            # 清理过期的请求记录
            requests = [req_time for req_time in requests if req_time > window_start]

            # 检查是否超过限制
            if len(requests) >= limit:
                # 计算重置时间
                oldest_request = min(requests)
                reset_time = oldest_request + window
                retry_after = int(reset_time - now)

                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": int(reset_time),
                    "retry_after": retry_after
                }

            # 记录当前请求
            requests.append(now)
            self._requests[key] = requests

            return True, {
                "limit": limit,
                "remaining": limit - len(requests),
                "reset": int(now + window)
            }

    async def reset(self, key: str):
        """重置指定键的限制"""
        async with self._lock:
            if key in self._requests:
                del self._requests[key]


class RedisRateLimiter:
    """Redis 速率限制器（用于生产环境）"""

    def __init__(self, redis_url: str):
        if not REDIS_AVAILABLE:
            raise ImportError("redis 包未安装")

        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        """获取 Redis 连接"""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        使用 Redis 滑动窗口算法检查速率限制

        Args:
            key: 限制键
            limit: 时间窗口内允许的最大请求数
            window: 时间窗口（秒）

        Returns:
            (是否允许, 限制信息)
        """
        redis = await self._get_redis()
        now = time.time()
        window_start = now - window

        try:
            pipe = redis.pipeline()

            # 使用有序集合存储请求时间戳
            rate_key = f"ratelimit:{key}"

            # 移除窗口外的记录
            pipe.zremrangebyscore(rate_key, 0, window_start)

            # 获取当前计数
            pipe.zcard(rate_key)

            # 添加当前请求
            pipe.zadd(rate_key, {str(now): now})

            # 设置过期时间
            pipe.expire(rate_key, window + 1)

            results = await pipe.execute()

            current_count = results[1]

            if current_count >= limit:
                # 计算重置时间
                oldest = await redis.zrange(rate_key, 0, 0, withscores=True)
                if oldest:
                    reset_time = oldest[0][1] + window
                    retry_after = int(reset_time - now)
                else:
                    reset_time = now + window
                    retry_after = window

                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": int(reset_time),
                    "retry_after": retry_after
                }

            return True, {
                "limit": limit,
                "remaining": limit - current_count,
                "reset": int(now + window)
            }

        except Exception as e:
            # Redis 出错时降级到允许请求
            logger.warning(f"⚠️ Redis 速率限制错误: {e}")
            return True, {"limit": limit, "remaining": limit, "reset": int(now + window)}

    async def reset(self, key: str):
        """重置指定键的限制"""
        try:
            redis = await self._get_redis()
            await redis.delete(f"ratelimit:{key}")
        except Exception as e:
            logger.warning(f"⚠️ Redis 重置限制失败: {e}")


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """增强的速率限制中间件"""

    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)

        self.config = RateLimitConfig.get_limits()
        self.window = 60  # 60秒窗口

        # 选择限流器实现
        if redis_url and REDIS_AVAILABLE:
            self.limiter = RedisRateLimiter(redis_url)
            self.backend = "redis"
        else:
            self.limiter = InMemoryRateLimiter()
            self.backend = "memory"
            if redis_url and not REDIS_AVAILABLE:
                logger.warning("⚠️ Redis 不可用，使用内存限流器")

    async def dispatch(self, request: Request, call_next):
        """处理请求"""

        # 跳过健康检查和监控端点
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # 获取客户端标识
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        # 检查多层限制
        limits_to_check = []

        # 1. 全局限制
        limits_to_check.append(("global", f"global", self.config["global"]))

        # 2. IP 限制
        limits_to_check.append(("ip", f"ip:{client_ip}", self.config["per_ip"]))

        # 3. 用户限制（如果已认证）
        if user_id:
            limits_to_check.append(("user", f"user:{user_id}", self.config["per_user"]))

        # 4. 端点限制
        endpoint_limits = self.config.get("per_endpoint", {})
        for path, limit in endpoint_limits.items():
            if request.url.path.startswith(path):
                # 未认证用户使用 IP，已认证用户使用用户ID
                key = f"endpoint:{path}:{user_id or client_ip}"
                limits_to_check.append(("endpoint", key, limit))
                break

        # 检查所有限制
        for limit_type, key, limit in limits_to_check:
            allowed, info = await self.limiter.is_allowed(key, limit, self.window)

            if not allowed:
                # 返回 429 状态码
                headers = {
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-RateLimit-Backend": self.backend
                }

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Too many requests",
                        "message": f"Rate limit exceeded for {limit_type}",
                        "limit_info": info
                    },
                    headers=headers
                )

        # 添加速率限制头到响应
        response = await call_next(request)

        # 添加最后一项限制的信息到响应头
        if limits_to_check:
            _, key, limit = limits_to_check[-1]
            _, info = await self.limiter.is_allowed(key, limit, self.window)

            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
            response.headers["X-RateLimit-Backend"] = self.backend

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 检查代理头
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 回退到直接连接的 IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """从请求中获取用户 ID"""
        # 从 Authorization 头获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # 这里可以解析 JWT 获取用户 ID
            # 为简单起见，我们使用令牌哈希
            token = auth_header[7:]
            return hashlib.sha256(token.encode()).hexdigest()[:16]

        return None


def create_rate_limit_middleware(
    redis_url: Optional[str] = None,
    strict: bool = False
) -> EnhancedRateLimitMiddleware:
    """
    创建速率限制中间件

    Args:
        redis_url: Redis 连接 URL（可选）
        strict: 是否使用严格限制

    Returns:
        速率限制中间件实例
    """
    # 如果没有提供 Redis URL，尝试从环境变量获取
    if not redis_url:
        redis_url = os.getenv("REDIS_URL")

    return lambda app: EnhancedRateLimitMiddleware(app, redis_url)


# 便捷函数
def get_rate_limit_config() -> Dict[str, Any]:
    """获取当前速率限制配置"""
    return RateLimitConfig.get_limits()


async def reset_rate_limit(key: str, redis_url: Optional[str] = None):
    """重置指定键的速率限制"""
    if redis_url and REDIS_AVAILABLE:
        limiter = RedisRateLimiter(redis_url)
    else:
        limiter = InMemoryRateLimiter()

    await limiter.reset(key)

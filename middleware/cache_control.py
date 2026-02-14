"""
缓存控制中间件
为 API 响应添加适当的缓存控制头
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Dict, Optional, Pattern
import re

from utils.logger import get_logger

logger = get_logger("CacheControl")


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    缓存控制中间件

    为 API 响应添加缓存控制头，支持：
    - 基于路径模式的缓存策略
    - 公共/私有缓存控制
    - 最大缓存时间设置
    - 动态内容的禁用缓存
    """

    def __init__(
        self,
        app: ASGIApp,
        default_max_age: int = 300,  # 默认 5 分钟
        public_paths: Optional[list] = None,
        private_paths: Optional[list] = None,
        no_cache_paths: Optional[list] = None
    ):
        """
        初始化缓存控制中间件

        Args:
            app: ASGI 应用
            default_max_age: 默认最大缓存时间（秒）
            public_paths: 可以被公共缓存的路径模式列表
            private_paths: 只能被私有缓存的路径模式列表
            no_cache_paths: 禁用缓存的路径模式列表
        """
        super().__init__(app)
        self.default_max_age = default_max_age

        # 编译路径模式为正则表达式
        self.public_patterns = [re.compile(pattern) for pattern in (public_paths or [])]
        self.private_patterns = [re.compile(pattern) for pattern in (private_paths or [])]
        self.no_cache_patterns = [re.compile(pattern) for pattern in (no_cache_paths or [])]

        # 默认的缓存策略配置
        self.default_public_paths = [
            r"/juben/agents$",
            r"/juben/agents/list$",
            r"/juben/health$",
            r"/juben/models$",
            r"/juben/config$",
        ]

        self.default_private_paths = [
            r"/juben/chat$",
            r"/juben/sessions/.*",
            r"/juben/notes/.*",
            r"/juben/projects/.*",
        ]

        self.default_no_cache_paths = [
            r"/juben/.*$",
            r"/auth/.*$",
            r"/juben/stop/.*$",
            r"/juben/stream/.*$",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，添加缓存控制头

        Args:
            request: 传入请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 带缓存控制头的响应
        """
        response = await call_next(request)

        # 跳过 StreamingResponse
        if hasattr(response, 'body_iterator'):
            return response

        # 跳过已经有 Cache-Control 的响应
        if 'cache-control' in response.headers:
            return response

        # 根据路径确定缓存策略
        cache_policy = self._get_cache_policy(request.url.path)

        # 添加缓存控制头
        if cache_policy:
            response.headers["Cache-Control"] = cache_policy

        return response

    def _get_cache_policy(self, path: str) -> Optional[str]:
        """
        根据路径获取缓存策略

        Args:
            path: 请求路径

        Returns:
            str: Cache-Control 头值，如果不缓存返回 None
        """
        # 检查禁用缓存的模式
        for pattern in self.no_cache_patterns:
            if pattern.search(path):
                return "no-store, no-cache, must-revalidate, max-age=0"

        # 检查私有缓存模式
        for pattern in self.private_patterns:
            if pattern.search(path):
                return f"private, max-age={self.default_max_age}, must-revalidate"

        # 检查公共缓存模式
        for pattern in self.public_patterns:
            if pattern.search(path):
                return f"public, max-age={self.default_max_age}, s-maxage={self.default_max_age * 2}"

        # 静态资源路径
        if path.startswith("/static/") or path.startswith("/assets/"):
            return "public, max-age=86400, immutable"  # 24 小时

        # API 文档路径
        if path in ["/docs", "/redoc", "/openapi.json"]:
            return "public, max-age=3600"  # 1 小时

        # 默认策略：短时间缓存
        if path.startswith("/juben/"):
            return f"private, max-age=60, must-revalidate"  # 1 分钟

        # 其他路径：禁用缓存
        return "no-store, no-cache, must-revalidate"


class CacheControlConfig:
    """缓存控制配置类"""

    # 预定义的缓存策略
    NO_CACHE = "no-store, no-cache, must-revalidate, max-age=0"
    PRIVATE_SHORT = "private, max-age=60, must-revalidate"
    PRIVATE_MEDIUM = "private, max-age=300, must-revalidate"
    PRIVATE_LONG = "private, max-age=3600, must-revalidate"
    PUBLIC_SHORT = "public, max-age=60, s-maxage=120"
    PUBLIC_MEDIUM = "public, max-age=300, s-maxage=600"
    PUBLIC_LONG = "public, max-age=3600, s-maxage=7200"
    STATIC = "public, max-age=86400, immutable"  # 24 小时

    @staticmethod
    def create_custom(
        max_age: int,
        private: bool = False,
        must_revalidate: bool = True,
        s_maxage: Optional[int] = None
    ) -> str:
        """
        创建自定义缓存策略

        Args:
            max_age: 最大缓存时间（秒）
            private: 是否为私有缓存
            must_revalidate: 是否必须重新验证
            s_maxage: 共享缓存的最大时间（秒）

        Returns:
            str: Cache-Control 头值
        """
        parts = []

        if private:
            parts.append("private")
        else:
            parts.append("public")

        parts.append(f"max-age={max_age}")

        if s_maxage:
            parts.append(f"s-maxage={s_maxage}")

        if must_revalidate:
            parts.append("must-revalidate")

        return ", ".join(parts)


# 预配置的中间件实例
def create_cache_control_middleware(
    enable_compression_cache: bool = True,
    default_max_age: int = 300
) -> CacheControlMiddleware:
    """
    创建缓存控制中间件的工厂函数

    Args:
        enable_compression_cache: 是否启用压缩数据的缓存
        default_max_age: 默认最大缓存时间

    Returns:
        CacheControlMiddleware: 中间件实例
    """
    public_paths = [
        r"/juben/agents$",
        r"/juben/agents/list$",
        r"/juben/health$",
        r"/juben/models$",
        r"/juben/config$",
    ]

    private_paths = [
        r"/juben/chat$",
        r"/juben/sessions/",
        r"/juben/notes/",
        r"/juben/projects/",
    ]

    no_cache_paths = [
        r"/juben/.*",  # 流式响应
        r"/auth/",
        r"/juben/stop/",
        r"/juben/stream/",
    ]

    return lambda app: CacheControlMiddleware(
        app,
        default_max_age=default_max_age,
        public_paths=public_paths,
        private_paths=private_paths,
        no_cache_paths=no_cache_paths
    )

"""
请求追踪中间件
为每个请求添加唯一ID，支持链路追踪
"""
import uuid
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from utils.logger import get_logger

logger = get_logger("request_tracking")


class RequestContext:
    """请求上下文，存储请求相关信息"""

    def __init__(self, request_id: str, request: Request):
        self.request_id = request_id
        self.request = request
        self.start_time = datetime.utcnow()
        self.metadata = {}

    def elapsed_ms(self) -> float:
        """获取已耗时（毫秒）"""
        return (datetime.utcnow() - self.start_time).total_seconds() * 1000


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())

        # 尝试从头部获取追踪ID（用于分布式追踪）
        trace_id = request.headers.get("X-Trace-ID", request_id)
        parent_span_id = request.headers.get("X-Parent-Span-ID", "")

        # 创建请求上下文
        context = RequestContext(request_id, request)
        context.metadata["trace_id"] = trace_id
        context.metadata["parent_span_id"] = parent_span_id
        context.metadata["client_ip"] = request.client.host if request.client else "unknown"
        context.metadata["user_agent"] = request.headers.get("user-agent", "unknown")
        context.metadata["method"] = request.method
        context.metadata["path"] = request.url.path

        # 将上下文存储到 request.state
        request.state.request_context = context

        # 添加请求ID到请求头（传递给下游服务）
        request.headers.__dict__["_list"].append(
            ("x-request-id", request_id.encode())
        )
        request.headers.__dict__["_list"].append(
            ("x-trace-id", trace_id.encode())
        )

        # 记录请求开始
        logger.info(
            f"➡️  [{request_id[:8]}] {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": context.metadata["client_ip"]
            }
        )

        try:
            # 处理请求
            response = await call_next(request)

            # 记录请求完成
            elapsed = context.elapsed_ms()
            logger.info(
                f"✅ [{request_id[:8]}] {request.method} {request.url.path} - {response.status_code} ({elapsed:.0f}ms)",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed
                }
            )

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id

            return response

        except Exception as e:
            # 记录请求失败
            elapsed = context.elapsed_ms()
            logger.error(
                f"❌ [{request_id[:8]}] {request.method} {request.url.path} - ERROR ({elapsed:.0f}ms)",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "error": str(e),
                    "elapsed_ms": elapsed
                },
                exc_info=True
            )
            raise


def get_request_context(request: Request) -> RequestContext:
    """从请求中获取上下文"""
    return getattr(request.state, "request_context", None)


def get_request_id(request: Request) -> str:
    """从请求中获取请求ID"""
    context = get_request_context(request)
    return context.request_id if context else "unknown"


class Span:
    """用于追踪子操作的Span"""

    def __init__(self, name: str, request: Request, metadata: dict = None):
        self.name = name
        self.request = request
        self.metadata = metadata or {}
        self.start_time = datetime.utcnow()
        self.context = get_request_context(request)
        self.span_id = str(uuid.uuid4())[:8]

    def __enter__(self):
        logger.debug(
            f"→ [{self.context.request_id[:8]}] {self.name} started",
            extra={
                "request_id": self.context.request_id,
                "span_id": self.span_id,
                "span_name": self.name
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        if exc_type:
            logger.error(
                f"← [{self.context.request_id[:8]}] {self.name} failed ({elapsed:.0f}ms)",
                extra={
                    "request_id": self.context.request_id,
                    "span_id": self.span_id,
                    "span_name": self.name,
                    "elapsed_ms": elapsed,
                    "error": str(exc_val)
                }
            )
        else:
            logger.debug(
                f"← [{self.context.request_id[:8]}] {self.name} completed ({elapsed:.0f}ms)",
                extra={
                    "request_id": self.context.request_id,
                    "span_id": self.span_id,
                    "span_name": self.name,
                    "elapsed_ms": elapsed
                }
            )

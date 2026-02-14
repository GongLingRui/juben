"""
请求体大小限制中间件
防止大文件上传和 DoS 攻击
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive
from typing import Callable, Optional
from fastapi.responses import JSONResponse

from utils.logger import get_logger
from utils.constants import HTTPConstants

logger = get_logger("RequestSizeLimit")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    请求体大小限制中间件

    特性：
    - 全局请求体大小限制
    - 按路径模式的定制限制
    - 上传文件路径的特殊处理
    - 详细的大小限制日志
    """

    def __init__(
        self,
        app: ASGIApp,
        max_request_size: int = None,
        max_upload_size: int = None,
        excluded_paths: Optional[list] = None
    ):
        """
        初始化请求大小限制中间件

        Args:
            app: ASGI 应用
            max_request_size: 最大请求体大小（字节）
            max_upload_size: 最大上传文件大小（字节）
            excluded_paths: 排除大小限制的路径模式列表
        """
        super().__init__(app)

        # 从常量读取默认值
        self.max_request_size = max_request_size or HTTPConstants.MAX_REQUEST_SIZE
        self.max_upload_size = max_upload_size or HTTPConstants.MAX_UPLOAD_SIZE

        # 上传相关路径
        self.upload_paths = [
            "/upload",
            "/file/upload",
            "/files/upload",
            "/images/upload",
            "/documents/upload",
        ]

        # 编译排除路径
        self.excluded_patterns = excluded_paths or []

        # 统计
        self._blocked_count = 0
        self._allowed_count = 0

        logger.info(
            f"✅ 请求大小限制中间件初始化: "
            f"max_request={self.max_request_size}, "
            f"max_upload={self.max_upload_size}"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，检查请求体大小

        Args:
            request: 传入请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应或错误响应
        """
        # 获取内容长度
        content_length = request.headers.get("content-length")

        # 如果没有 content-length，需要读取请求体来确定大小
        if content_length is None:
            # 对于没有 content-length 的请求，我们使用流式处理
            return await self._handle_streaming_request(request, call_next)

        content_length = int(content_length)

        # 确定此路径的大小限制
        limit = self._get_limit_for_path(request.url.path)

        # 检查大小
        if content_length > limit:
            self._blocked_count += 1
            logger.warning(
                f"⚠️ 请求体过大: {request.url.path} "
                f"({content_length} > {limit} bytes)"
            )

            return JSONResponse(
                status_code=413,  # Payload Too Large
                content={
                    "success": False,
                    "message": f"请求体过大。最大允许 {limit} 字节，当前 {content_length} 字节",
                    "error_code": "REQUEST_TOO_LARGE"
                }
            )

        # 允许请求通过
        self._allowed_count += 1
        return await call_next(request)

    async def _handle_streaming_request(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        处理没有 content-length 的流式请求

        Args:
            request: 传入请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应
        """
        # 获取大小限制
        limit = self._get_limit_for_path(request.url.path)

        # 读取请求体（带限制）
        body = b""
        size = 0

        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                self._blocked_count += 1
                logger.warning(
                    f"⚠️ 流式请求体过大: {request.url.path} "
                    f"({size} > {limit} bytes)"
                )

                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "message": f"请求体过大。最大允许 {limit} 字节",
                        "error_code": "REQUEST_TOO_LARGE"
                    }
                )

            body += chunk

        # 重建请求（可选，如果后续中间件需要请求体）
        # 这里我们直接调用下一个处理器，让 FastAPI 处理请求体

        return await call_next(request)

    def _get_limit_for_path(self, path: str) -> int:
        """
        根据路径获取大小限制

        Args:
            path: 请求路径

        Returns:
            int: 大小限制（字节）
        """
        # 上传路径使用更大的限制
        for upload_path in self.upload_paths:
            if upload_path in path:
                return self.max_upload_size

        # 其他路径使用默认限制
        return self.max_request_size

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "blocked_count": self._blocked_count,
            "allowed_count": self._allowed_count,
            "max_request_size": self.max_request_size,
            "max_upload_size": self.max_upload_size,
            "block_rate": (
                self._blocked_count / (self._blocked_count + self._allowed_count)
                if (self._blocked_count + self._allowed_count) > 0
                else 0
            )
        }

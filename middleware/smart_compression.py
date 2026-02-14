"""
智能压缩中间件
只为非流式响应启用 GZip 压缩，避免影响流式传输
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import StreamingResponse
import gzip
import io
from typing import Callable, Optional

from utils.logger import get_logger

logger = get_logger("SmartCompression")


class SmartCompressionMiddleware(BaseHTTPMiddleware):
    """
    智能压缩中间件

    特性：
    - 只压缩非流式响应
    - 可配置的最小压缩大小
    - 支持 gzip 编码协商
    - 自动处理 Content-Type 和 Content-Encoding
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1000,  # 小于此值不压缩
        compresslevel: int = 6,  # 压缩级别 (0-9)
        excluded_types: Optional[list] = None
    ):
        """
        初始化压缩中间件

        Args:
            app: ASGI 应用
            minimum_size: 最小压缩大小（字节）
            compresslevel: 压缩级别 (0-9, 默认6)
            excluded_types: 排除的 Content-Type 列表
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

        # 默认排除的 Content-Type（通常已经压缩的格式）
        self.excluded_types = excluded_types or [
            "application/gzip",
            "application/zip",
            "application/x-gzip",
            "application/x-compressed",
            "application/x-zip-compressed",
            "image/",  # 所有图片类型
            "video/",  # 所有视频类型
            "audio/",  # 所有音频类型
            "application/octet-stream",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，对响应进行压缩

        Args:
            request: 传入请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 压缩后的响应（如果适用）
        """
        # 调用下一个处理器
        response = await call_next(request)

        # 检查是否应该压缩
        if not self._should_compress(request, response):
            return response

        # 对于 StreamingResponse，不进行压缩
        if isinstance(response, StreamingResponse):
            return response

        # 处理普通响应
        return await self._compress_response(request, response)

    def _should_compress(self, request: Request, response: Response) -> bool:
        """
        检查响应是否应该被压缩

        Args:
            request: 传入请求
            response: 响应对象

        Returns:
            bool: 是否应该压缩
        """
        # 检查客户端是否支持 gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return False

        # 检查响应是否已经有 Content-Encoding
        if response.headers.get("content-encoding"):
            return False

        # 检查响应状态码
        # 只压缩成功响应
        if response.status_code < 200 or response.status_code >= 300:
            return False

        # 检查 Content-Type
        content_type = response.headers.get("content-type", "")
        if any(excluded in content_type for excluded in self.excluded_types):
            return False

        # 检查 Content-Length
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) < self.minimum_size:
                    return False
            except ValueError:
                pass

        return True

    async def _compress_response(self, request: Request, response: Response) -> Response:
        """
        压缩响应体

        Args:
            request: 传入请求
            response: 原始响应

        Returns:
            Response: 压缩后的响应
        """
        try:
            # 获取响应体
            body = await self._get_response_body(response)

            # 检查大小
            if len(body) < self.minimum_size:
                return response

            # 压缩
            compressed_body = self._gzip_compress(body)

            # 如果压缩后反而更大，不使用压缩
            if len(compressed_body) >= len(body):
                return response

            # 创建新响应
            headers = dict(response.headers)
            headers["content-encoding"] = "gzip"
            headers["content-length"] = str(len(compressed_body))

            # 添加压缩信息头
            headers["x-original-size"] = str(len(body))
            headers["x-compressed-size"] = str(len(compressed_body))
            compression_ratio = (1 - len(compressed_body) / len(body)) * 100
            headers["x-compression-ratio"] = f"{compression_ratio:.1f}%"

            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )

        except Exception as e:
            logger.warning(f"⚠️ 响应压缩失败: {e}")
            return response

    async def _get_response_body(self, response: Response) -> bytes:
        """
        获取响应体

        Args:
            response: 响应对象

        Returns:
            bytes: 响应体
        """
        # 某些 Streaming / 特殊响应对象没有 .body 属性，直接访问会抛 AttributeError
        try:
            raw_body = getattr(response, "body", None)
        except Exception:
            raw_body = None

        # 如果响应体已经是 bytes
        if isinstance(raw_body, bytes):
            return raw_body

        # 如果是字符串，编码为 bytes
        if isinstance(raw_body, str):
            return raw_body.encode("utf-8")

        # 其他情况，尝试从 body_iterator 读取
        body = b""
        iterator = getattr(response, "body_iterator", None)
        if iterator is not None:
            async for chunk in iterator:
                if isinstance(chunk, str):
                    body += chunk.encode("utf-8")
                else:
                    body += chunk

        return body

    def _gzip_compress(self, data: bytes) -> bytes:
        """
        使用 gzip 压缩数据

        Args:
            data: 要压缩的数据

        Returns:
            bytes: 压缩后的数据
        """
        buf = io.BytesIO()
        with gzip.GzipFile(
            fileobj=buf,
            mode="wb",
            compresslevel=self.compresslevel
        ) as f:
            f.write(data)
        return buf.getvalue()


def create_smart_compression_middleware(
    minimum_size: int = 1000,
    compresslevel: int = 6
) -> SmartCompressionMiddleware:
    """
    创建智能压缩中间件的工厂函数

    Args:
        minimum_size: 最小压缩大小
        compresslevel: 压缩级别

    Returns:
        SmartCompressionMiddleware: 中间件实例
    """
    return lambda app: SmartCompressionMiddleware(
        app,
        minimum_size=minimum_size,
        compresslevel=compresslevel
    )

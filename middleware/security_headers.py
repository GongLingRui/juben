"""
安全响应头中间件
添加安全相关的 HTTP 响应头以增强应用安全性
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Dict, Optional

from utils.logger import get_logger
import os

logger = get_logger("SecurityHeaders")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全响应头中间件

    添加以下安全头：
    - X-Content-Type-Options: 防止 MIME 类型嗅探
    - X-Frame-Options: 防止点击劫持
    - X-XSS-Protection: XSS 保护
    - Strict-Transport-Security: 强制 HTTPS
    - Content-Security-Policy: 内容安全策略
    - Referrer-Policy: 控制引用信息泄露
    - Permissions-Policy: 控制浏览器功能
    """

    def __init__(
        self,
        app: ASGIApp,
        hsts_enabled: bool = True,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp_enabled: bool = True,
        frame_options: str = "DENY",
        ssl_redirect: bool = False
    ):
        """
        初始化安全头中间件

        Args:
            app: ASGI 应用
            hsts_enabled: 是否启用 HSTS
            hsts_max_age: HSTS 最大时间（秒）
            hsts_include_subdomains: 是否包含子域名
            hsts_preload: 是否启用 HSTS 预加载
            csp_enabled: 是否启用 CSP
            frame_options: X-Frame-Options 值
            ssl_redirect: 是否重定向到 HTTPS
        """
        super().__init__(app)

        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.csp_enabled = csp_enabled
        self.frame_options = frame_options
        self.ssl_redirect = ssl_redirect

        # 检测是否在生产环境
        self.is_production = os.getenv("APP_ENV", "development") == "production"

        logger.info("✅ 安全响应头中间件初始化完成")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求，添加安全响应头

        Args:
            request: 传入请求
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 带安全头的响应
        """
        # HTTPS 重定向（仅在生产环境启用）
        if self.ssl_redirect and self.is_production:
            if request.url.scheme != "https":
                from fastapi.responses import RedirectResponse
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=301)

        # 调用下一个处理器
        response = await call_next(request)

        # 添加安全头
        self._add_security_headers(request, response)

        return response

    def _add_security_headers(self, request: Request, response: Response):
        """
        添加安全响应头

        Args:
            request: 传入请求
            response: 响应对象
        """
        # X-Content-Type-Options: 防止 MIME 类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: 防止点击劫持
        response.headers["X-Frame-Options"] = self.frame_options

        # X-XSS-Protection: XSS 保护
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: 控制引用信息泄露
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: 控制浏览器功能
        response.headers["Permissions-Policy"] = self._get_permissions_policy()

        # Content-Security-Policy: 内容安全策略
        if self.csp_enabled:
            response.headers["Content-Security-Policy"] = self._get_csp(request)

        # Strict-Transport-Security: 仅在 HTTPS 下添加
        if self.hsts_enabled and request.url.scheme == "https":
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # 移除可能泄露信息的服务器头
        if "Server" in response.headers:
            del response.headers["Server"]

        # 自定义服务器头（隐藏具体版本）
        response.headers["X-Powered-By"] = "Juben Platform"

    def _get_csp(self, request: Request) -> str:
        """
        生成内容安全策略

        Args:
            request: 传入请求

        Returns:
            str: CSP 头值
        """
        # 基础 CSP 策略
        csp_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # 允许内联脚本（开发需要）
            "style-src 'self' 'unsafe-inline'",  # 允许内联样式
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",  # 防止被嵌入到 iframe
            "base-uri 'self'",
            "form-action 'self'",
        ]

        # 如果是开发环境，放宽限制
        if not self.is_production:
            csp_parts.extend([
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:5173 localhost:3000",
                "connect-src 'self' ws://localhost:* wss://localhost:* http://localhost:*",
            ])

        return "; ".join(csp_parts)

    def _get_permissions_policy(self) -> str:
        """
        生成 Permissions-Policy 头

        Returns:
            str: Permissions-Policy 头值
        """
        # 控制浏览器功能的使用权限
        policies = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]

        # 生产环境禁用更多功能
        if self.is_production:
            policies.extend([
                "interest-cohort=()",
                "browsing-topics=()",
            ])

        return ", ".join(policies)


def create_security_headers_middleware(
    hsts_enabled: bool = True,
    csp_enabled: bool = True,
    frame_options: str = "DENY"
) -> SecurityHeadersMiddleware:
    """
    创建安全头中间件的工厂函数

    Args:
        hsts_enabled: 是否启用 HSTS
        csp_enabled: 是否启用 CSP
        frame_options: X-Frame-Options 值

    Returns:
        SecurityHeadersMiddleware: 中间件实例
    """
    return lambda app: SecurityHeadersMiddleware(
        app,
        hsts_enabled=hsts_enabled,
        csp_enabled=csp_enabled,
        frame_options=frame_options
    )

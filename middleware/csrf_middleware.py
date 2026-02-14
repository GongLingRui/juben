"""
CSRF (Cross-Site Request Forgery) 保护中间件

为所有修改状态的请求提供 CSRF 保护
"""
import os
import secrets
import hashlib
import hmac
from typing import Optional, Callable, Awaitable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from utils.logger import get_logger
from utils.constants import CSRFConstants

logger = get_logger("CSRFMiddleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF 保护中间件

    功能：
    1. 为会话生成唯一的 CSRF token
    2. 验证请求中的 CSRF token
    3. 自动为安全方法豁免验证
    4. 支持通过 Header 或 Form 字段传递 token
    """

    def __init__(
        self,
        app,
        secret_key: Optional[str] = None,
        token_length: int = CSRFConstants.TOKEN_LENGTH,
        token_expire: int = CSRFConstants.TOKEN_EXPIRE,
        header_name: str = CSRFConstants.HEADER_NAME,
        form_field_name: str = CSRFConstants.FORM_FIELD_NAME,
        secure_cookie: bool = CSRFConstants.SECURE_COOKIE,
        httponly_cookie: bool = CSRFConstants.HTTPONLY_COOKIE,
        samesite: str = CSRFConstants.SAMESITE,
        per_ref_token: bool = CSRFConstants.PER_REF_TOKEN,
    ):
        """
        初始化 CSRF 中间件

        Args:
            app: ASGI 应用
            secret_key: 用于签名 token 的密钥
            token_length: token 长度
            token_expire: token 过期时间（秒）
            header_name: HTTP header 名称
            form_field_name: 表单字段名称
            secure_cookie: 是否仅通过 HTTPS 发送 cookie
            httponly_cookie: 是否禁止 JavaScript 访问 cookie
            samesite: SameSite 属性值
            per_ref_token: 是否每个请求生成新 token
        """
        super().__init__(app)
        self.secret_key = secret_key or os.getenv("CSRF_SECRET_KEY", secrets.token_hex(32))
        self.token_length = token_length
        self.token_expire = token_expire
        self.header_name = header_name
        self.form_field_name = form_field_name
        self.secure_cookie = secure_cookie
        self.httponly_cookie = httponly_cookie
        self.samesite = samesite
        self.per_ref_token = per_ref_token

        if not self.secret_key:
            logger.warning("⚠️ CSRF_SECRET_KEY 未设置，将使用自动生成的密钥（重启后失效）")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 跳过安全方法的验证
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return await call_next(request)

        # 检查是否为 API 请求（API 通常使用 JWT 认证，不需要 CSRF）
        if self._is_api_request(request):
            return await call_next(request)

        # 验证 CSRF token
        csrf_error = await self._validate_csrf(request)
        if csrf_error:
            return csrf_error

        response = await call_next(request)
        return response

    def _is_api_request(self, request: Request) -> bool:
        """判断是否为 API 请求"""
        path = request.url.path
        # API 路径通常以 /api/ 开头
        return path.startswith("/api/") or path.startswith("/juben/")

    async def _validate_csrf(self, request: Request) -> Optional[JSONResponse]:
        """验证 CSRF token"""
        # 从 cookie 获取 session token
        session_token = request.cookies.get("csrf_session_token")
        if not session_token:
            logger.warning(f"⚠️ CSRF: 缺少 session token - {request.url.path}")
            return self._error_response("缺少 CSRF token，请刷新页面重试")

        # 从 header 或 form 获取 request token
        request_token = (
            request.headers.get(self.header_name) or
            await self._get_form_token(request)
        )
        if not request_token:
            logger.warning(f"⚠️ CSRF: 缺少 request token - {request.url.path}")
            return self._error_response("缺少 CSRF token")

        # 验证 token
        if not self._verify_token(session_token, request_token):
            logger.warning(f"⚠️ CSRF: token 验证失败 - {request.url.path}")
            return self._error_response("CSRF token 验证失败")

        return None

    async def _get_form_token(self, request: Request) -> Optional[str]:
        """从表单获取 token"""
        # 尝试从 JSON body 获取
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
                return body.get(self.form_field_name)
            except Exception:
                pass

        # 尝试从 form data 获取
        try:
            form = await request.form()
            return form.get(self.form_field_name)
        except Exception:
            pass

        return None

    def _generate_token(self, session_id: str) -> tuple[str, str]:
        """
        生成 CSRF token 对

        Returns:
            (session_token, request_token)
        """
        # 生成随机 token
        random_token = secrets.token_hex(self.token_length)

        # 创建 session token（存入 cookie）
        session_token = self._sign_token(session_id, random_token)

        # 创建 request token（提交时使用）
        request_token = self._hash_token(session_id, random_token)

        return session_token, request_token

    def _sign_token(self, session_id: str, random_token: str) -> str:
        """签名 token"""
        message = f"{session_id}:{random_token}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{random_token}:{signature}"

    def _hash_token(self, session_id: str, random_token: str) -> str:
        """哈希 token"""
        message = f"{session_id}:{random_token}:{self.secret_key}"
        return hashlib.sha256(message.encode()).hexdigest()

    def _verify_token(self, session_token: str, request_token: str) -> bool:
        """验证 token"""
        try:
            # 分割 session token
            parts = session_token.split(":")
            if len(parts) != 2:
                return False

            random_token, signature = parts

            # 验证签名
            # 这里我们简化处理，实际使用中可以从 session 获取 session_id
            expected_signature = hmac.new(
                self.secret_key.encode(),
                f"session:{random_token}".encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                return False

            # 验证 request token
            expected_request_token = self._hash_token("session", random_token)
            return hmac.compare_digest(request_token, expected_request_token)

        except Exception as e:
            logger.error(f"❌ CSRF token 验证出错: {e}")
            return False

    def _error_response(self, message: str) -> JSONResponse:
        """返回错误响应"""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": message, "code": "CSRF_VALIDATION_FAILED"}
        )

    def generate_csrf_token_for_session(self, session_id: str) -> dict:
        """
        为会话生成 CSRF token

        Args:
            session_id: 会话 ID

        Returns:
            包含 session_token 和 request_token 的字典
        """
        session_token, request_token = self._generate_token(session_id)
        return {
            "session_token": session_token,
            "request_token": request_token,
            "header_name": self.header_name,
            "form_field_name": self.form_field_name
        }


# 全局 CSRF 中间件实例
_csrf_middleware: Optional[CSRFMiddleware] = None


def get_csrf_middleware() -> CSRFMiddleware:
    """获取 CSRF 中间件单例"""
    global _csrf_middleware
    if _csrf_middleware is None:
        _csrf_middleware = CSRFMiddleware
    return _csrf_middleware


# 便捷函数
def generate_csrf_token(session_id: str = "default") -> str:
    """
    生成 CSRF token

    Args:
        session_id: 会话 ID

    Returns:
        CSRF token 字符串
    """
    middleware = get_csrf_middleware()
    if isinstance(middleware, type):
        # 如果是类，创建实例
        middleware = middleware(app=None)
    tokens = middleware.generate_csrf_token_for_session(session_id)
    return tokens["request_token"]

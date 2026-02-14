"""
基于 Cookie 的认证工具
提供 httpOnly Cookie 支持，替代 localStorage 存储 token
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Response, Request, HTTPException, status
from fastapi.responses import JSONResponse
import jwt
import secrets


class CookieAuthManager:
    """Cookie 认证管理器"""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY 必须设置")

        self.access_token_expire = timedelta(minutes=30)
        self.refresh_token_expire = timedelta(days=7)

        # Cookie 配置
        self.cookie_domain = os.getenv("COOKIE_DOMAIN", None)
        self.cookie_secure = os.getenv("APP_ENV", "development") == "production"
        self.cookie_samesite = "lax" if not self.cookie_secure else "strict"

    def generate_tokens(self, user_data: Dict[str, Any]) -> tuple[str, str]:
        """
        生成访问令牌和刷新令牌

        Args:
            user_data: 用户数据

        Returns:
            (access_token, refresh_token)
        """
        now = datetime.utcnow()

        # 访问令牌（短期，存内存）
        access_payload = {
            "user_id": user_data.get("id"),
            "username": user_data.get("username"),
            "roles": user_data.get("roles", []),
            "permissions": user_data.get("permissions", []),
            "type": "access",
            "iat": now,
            "exp": now + self.access_token_expire,
            "jti": secrets.token_urlsafe(16)  # JWT ID
        }

        # 刷新令牌（长期，存 httpOnly cookie）
        refresh_payload = {
            "user_id": user_data.get("id"),
            "type": "refresh",
            "iat": now,
            "exp": now + self.refresh_token_expire,
            "jti": secrets.token_urlsafe(16)
        }

        access_token = jwt.encode(access_payload, self.secret_key, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm="HS256")

        return access_token, refresh_token

    def set_auth_cookies(
        self,
        response: Response,
        access_token: str,
        refresh_token: str,
        remember_me: bool = False
    ) -> Response:
        """
        设置认证 Cookie

        Args:
            response: FastAPI 响应对象
            access_token: 访问令牌
            refresh_token: 刷新令牌
            remember_me: 是否记住登录

        Returns:
            修改后的响应对象
        """
        # 访问令牌 cookie（会话级或短期）
        max_age = 7 * 24 * 60 * 60 if remember_me else None

        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=max_age or 30 * 60,  # 默认 30 分钟
            expires=None if not remember_me else datetime.utcnow() + timedelta(days=7),
            path="/",
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=True,  # 关键：防止 XSS 窃取
            samesite=self.cookie_samesite
        )

        # 刷新令牌 cookie（长期，用于获取新访问令牌）
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=7 * 24 * 60 * 60,  # 7 天
            expires=datetime.utcnow() + timedelta(days=7),
            path="/",
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=True,
            samesite=self.cookie_samesite
        )

        # 设置用户标识 cookie（非敏感，用于前端显示）
        response.set_cookie(
            key="logged_in",
            value="true",
            max_age=7 * 24 * 60 * 60,
            path="/",
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=False,  # 允许 JavaScript 访问
            samesite=self.cookie_samesite
        )

        return response

    def clear_auth_cookies(self, response: Response) -> Response:
        """
        清除认证 Cookie

        Args:
            response: FastAPI 响应对象

        Returns:
            修改后的响应对象
        """
        for cookie_name in ["access_token", "refresh_token", "logged_in"]:
            response.delete_cookie(
                key=cookie_name,
                path="/",
                domain=self.cookie_domain
            )

        return response

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证访问令牌

        Args:
            token: JWT 令牌

        Returns:
            解码后的用户数据，验证失败返回 None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "iat", "type"]}
            )

            if payload.get("type") != "access":
                return None

            return payload

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证刷新令牌

        Args:
            token: JWT 令牌

        Returns:
            解码后的用户数据，验证失败返回 None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "iat", "type"]}
            )

            if payload.get("type") != "refresh":
                return None

            return payload

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_token_from_cookie(self, request: Request, token_type: str = "access") -> Optional[str]:
        """
        从 Cookie 中获取令牌

        Args:
            request: FastAPI 请求对象
            token_type: 令牌类型 (access 或 refresh)

        Returns:
            令牌字符串，不存在返回 None
        """
        cookie_name = f"{token_type}_token"
        return request.cookies.get(cookie_name)

    async def refresh_access_token(self, request: Request) -> Optional[str]:
        """
        使用刷新令牌获取新的访问令牌

        Args:
            request: FastAPI 请求对象

        Returns:
            新的访问令牌，失败返回 None
        """
        refresh_token = self.get_token_from_cookie(request, "refresh")
        if not refresh_token:
            return None

        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None

        # 生成新的访问令牌
        user_data = {
            "id": payload.get("user_id"),
            "username": payload.get("username"),
        }

        # 这里需要从数据库获取完整的用户信息
        # 简化实现：直接使用 token 中的信息
        access_token, _ = self.generate_tokens(user_data)

        return access_token


# 全局实例
cookie_auth_manager = CookieAuthManager()


def get_cookie_auth_manager() -> CookieAuthManager:
    """获取 Cookie 认证管理器实例"""
    return cookie_auth_manager


# FastAPI 依赖项
async def get_current_user_from_cookie(request: Request) -> Optional[Dict[str, Any]]:
    """
    从 Cookie 获取当前用户（FastAPI 依赖项）

    Args:
        request: FastAPI 请求对象

    Returns:
        用户数据，未认证返回 None

    Raises:
        HTTPException: 令牌无效时抛出 401
    """
    auth_manager = get_cookie_auth_manager()

    # 首先尝试从 Cookie 获取
    access_token = auth_manager.get_token_from_cookie(request, "access")

    if access_token:
        payload = auth_manager.verify_access_token(access_token)
        if payload:
            return {
                "id": payload.get("user_id"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "auth_method": "cookie"
            }

    # 如果 Cookie 中的令牌过期，尝试用刷新令牌
    new_token = await auth_manager.refresh_access_token(request)
    if new_token:
        payload = auth_manager.verify_access_token(new_token)
        if payload:
            # 返回用户数据，调用方需要设置新的 Cookie
            return {
                "id": payload.get("user_id"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "auth_method": "cookie",
                "new_access_token": new_token  # 需要设置到响应中
            }

    # 未认证
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Cookie"},
    )


class CookieAuthMiddleware:
    """Cookie 认证中间件 - 为现有代码提供兼容层"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 创建请求对象
        request = Request(scope, receive)

        # 检查 Cookie 中的令牌
        access_token = request.cookies.get("access_token")
        if access_token:
            # 验证令牌并添加到请求状态
            try:
                auth_manager = get_cookie_auth_manager()
                payload = auth_manager.verify_access_token(access_token)
                if payload:
                    # 将用户信息添加到请求 scope，供后续使用
                    scope["user"] = {
                        "id": payload.get("user_id"),
                        "username": payload.get("username"),
                        "roles": payload.get("roles", []),
                        "permissions": payload.get("permissions", []),
                    }
            except Exception:
                pass  # 令牌无效，继续处理

        await self.app(scope, receive, send)

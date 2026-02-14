"""
基于 Cookie 的认证 API 路由
提供更安全的登录/登出功能
"""
import os
from typing import Optional
from fastapi import APIRouter, Response, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from utils.cookie_auth import get_cookie_auth_manager, CookieAuthManager
from utils.jwt_auth import get_password_hash, verify_password
from utils.user_store import UserStore
from utils.rbac import Role

router = APIRouter(prefix="/auth/cookie", tags=["cookie-auth"])


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: EmailStr
    display_name: Optional[str] = None


# 管理员用户信息（不含密码哈希）
_admin_user_info = None


def _get_admin_user() -> dict:
    """获取管理员用户信息 - 密码哈希每次重新生成"""
    global _admin_user_info

    username = os.getenv("ADMIN_USERNAME")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH")
    password_plain = os.getenv("ADMIN_PASSWORD")
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    if not username or (not password_hash and not password_plain):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials not configured"
        )

    # 首次加载：缓存不含密码的用户信息
    if not _admin_user_info:
        _admin_user_info = {
            "id": "admin",
            "username": username,
            "email": email,
            "displayName": "管理员",
            "roles": [Role.ADMIN],
            "permissions": ["*"],
            "createdAt": None,
        }

    # 每次都重新计算密码哈希（不缓存）
    if not password_hash and password_plain:
        password_hash = get_password_hash(password_plain)

    # 返回缓存的用户信息 + 密码哈希
    return {
        **_admin_user_info,
        "password_hash": password_hash
    }


def _get_user_by_username(username: str) -> Optional[dict]:
    """根据用户名获取用户"""
    admin = _get_admin_user()
    if admin["username"] == username:
        return admin

    user_store = UserStore()
    return user_store.get_by_username(username)


@router.post("/login")
async def cookie_login(
    request: LoginRequest,
    response: Response
):
    """
    Cookie 登录端点 - 使用 httpOnly Cookie 存储令牌

    Args:
        request: 登录请求
        response: FastAPI 响应对象

    Returns:
        登录结果
    """
    # 获取用户
    user = _get_user_by_username(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 生成令牌
    auth_manager = get_cookie_auth_manager()
    user_data = {
        "id": user["id"],
        "username": user["username"],
        "roles": user.get("roles", []),
        "permissions": user.get("permissions", []),
    }

    access_token, refresh_token = auth_manager.generate_tokens(user_data)

    # 设置 Cookie
    auth_manager.set_auth_cookies(
        response,
        access_token,
        refresh_token,
        request.remember_me
    )

    return {
        "success": True,
        "message": "登录成功",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email"),
            "displayName": user.get("displayName"),
            "roles": user.get("roles", []),
        }
    }


@router.post("/logout")
async def cookie_logout(response: Response):
    """
    Cookie 登出端点 - 清除 httpOnly Cookie

    Args:
        response: FastAPI 响应对象

    Returns:
        登出结果
    """
    auth_manager = get_cookie_auth_manager()
    auth_manager.clear_auth_cookies(response)

    return {
        "success": True,
        "message": "登出成功"
    }


@router.post("/refresh")
async def cookie_refresh(request: Request):
    """
    刷新访问令牌

    Args:
        request: FastAPI 请求对象

    Returns:
        新的令牌信息
    """
    auth_manager = get_cookie_auth_manager()
    new_token = await auth_manager.refresh_access_token(request)

    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期"
        )

    return {
        "success": True,
        "access_token": new_token
    }


@router.get("/me")
async def get_current_user(request: Request):
    """
    获取当前登录用户信息

    Args:
        request: FastAPI 请求对象

    Returns:
        当前用户信息
    """
    auth_manager = get_cookie_auth_manager()
    access_token = auth_manager.get_token_from_cookie(request, "access")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录"
        )

    payload = auth_manager.verify_access_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期"
        )

    # 获取完整用户信息
    user = _get_user_by_username(payload.get("username"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "displayName": user.get("displayName"),
        "roles": user.get("roles", []),
        "permissions": user.get("permissions", []),
    }


@router.post("/verify")
async def verify_auth(request: Request):
    """
    验证当前认证状态

    Args:
        request: FastAPI 请求对象

    Returns:
        认证状态
    """
    auth_manager = get_cookie_auth_manager()

    # 检查是否有 Cookie
    has_cookie = bool(auth_manager.get_token_from_cookie(request, "access"))

    if not has_cookie:
        return {
            "authenticated": False,
            "message": "未登录"
        }

    # 验证令牌
    access_token = auth_manager.get_token_from_cookie(request, "access")
    payload = auth_manager.verify_access_token(access_token) if access_token else None

    if not payload:
        return {
            "authenticated": False,
            "message": "令牌无效或已过期"
        }

    return {
        "authenticated": True,
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
    }

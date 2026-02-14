"""
认证 API 路由
提供登录、刷新 Token 等基础认证能力
增强版：支持用户管理、RBAC
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from utils.jwt_auth import (
    LoginRequest,
    RefreshTokenRequest,
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token_type,
    get_current_user,
    UserAuthInfo,
    logout_current_user,
)
from utils.user_store import UserStore

from utils.rbac import (
    Role,
    Permission,
    RBACChecker,
)
from utils.jwt_auth import require_permissions

router = APIRouter(prefix="/auth", tags=["auth"])

# ==================== 数据模型 ====================

# 管理员用户信息（不含密码哈希）
_admin_user_info = None
user_store = UserStore()


class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str
    password: str
    email: EmailStr
    display_name: Optional[str] = None
    roles: List[Role] = [Role.USER]


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    roles: Optional[List[Role]] = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: EmailStr


# ==================== 内部函数 ====================

def _get_admin_user() -> Dict[str, Any]:
    """获取管理员用户信息 - 密码哈希每次重新生成"""
    global _admin_user_info

    username = os.getenv("ADMIN_USERNAME")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH")
    password_plain = os.getenv("ADMIN_PASSWORD")
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    if not username or (not password_hash and not password_plain):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD or ADMIN_PASSWORD_HASH.",
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
            "createdAt": datetime.utcnow().isoformat(),
        }

    # 每次都重新计算密码哈希（不缓存）
    if not password_hash and password_plain:
        password_hash = get_password_hash(password_plain)

    # 返回缓存的用户信息 + 密码哈希
    return {
        **_admin_user_info,
        "password_hash": password_hash
    }


def _get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """根据用户名获取用户"""
    admin = _get_admin_user()
    if admin["username"] == username:
        return admin
    return user_store.get_by_username(username)


def _get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """根据ID获取用户"""
    admin = _get_admin_user()
    if admin["id"] == user_id:
        return admin
    return user_store.get_by_id(user_id)


# ==================== 端点 ====================

@router.post("/register")
async def register(request: UserCreateRequest):
    """用户注册"""
    # 检查用户是否已存在
    existing_user = user_store.get_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    existing_email = user_store.get_by_email(request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册"
        )

    # 创建新用户
    password_hash = get_password_hash(request.password)
    new_user = {
        "id": str(uuid.uuid4()),
        "username": request.username,
        "email": request.email,
        "password_hash": password_hash,
        "displayName": request.display_name or request.username,
        "roles": [r.value if isinstance(r, Role) else r for r in request.roles],
        "permissions": [],
        "createdAt": datetime.utcnow().isoformat(),
    }

    # 保存用户
    user_store.create_user(new_user)

    # 返回用户信息（不含密码）
    return {
        "id": new_user["id"],
        "username": new_user["username"],
        "email": new_user["email"],
        "displayName": new_user.get("displayName", new_user["username"]),
        "roles": new_user.get("roles", ["user"]),
        "permissions": new_user.get("permissions", []),
        "createdAt": new_user.get("createdAt"),
    }


@router.post("/login")
async def login(request: LoginRequest):
    """用户登录"""
    user = _get_user_by_username(request.username)

    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 获取用户权限
    if isinstance(user.get("roles"), list):
        roles = [r if isinstance(r, Role) else Role(r) for r in user["roles"]]
        permissions = RBACChecker.get_permissions_for_roles(roles)
        user["permissions"] = [p.value for p in permissions]
        user["roles"] = [r.value for r in roles]

    access_token = create_access_token(
        user_id=user["id"],
        permissions=user.get("permissions", []),
        additional_claims={
            "role": user.get("roles", ["user"])[0] if user.get("roles") else "user",
            "username": user["username"]
        },
    )
    refresh_token = create_refresh_token(user_id=user["id"])

    expires_at = int((datetime.utcnow() + timedelta(minutes=30)).timestamp() * 1000)

    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "displayName": user.get("displayName", user["username"]),
            "roles": user.get("roles", ["user"]),
            "permissions": user.get("permissions", []),
            "createdAt": user.get("createdAt", datetime.utcnow().isoformat()),
            "lastLoginAt": datetime.utcnow().isoformat(),
        },
        "tokens": {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at,
        },
    }


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """刷新访问令牌"""
    payload = verify_token_type(request.refresh_token, "refresh")
    user = _get_user_by_id(payload.sub)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 获取用户权限
    if isinstance(user.get("roles"), list):
        roles = [r if isinstance(r, Role) else Role(r) for r in user["roles"]]
        permissions = RBACChecker.get_permissions_for_roles(roles)
        user["permissions"] = [p.value for p in permissions]

    access_token = create_access_token(
        user_id=payload.sub,
        permissions=user.get("permissions", []),
    )
    new_refresh = create_refresh_token(user_id=payload.sub)
    expires_at = int((datetime.utcnow() + timedelta(minutes=30)).timestamp() * 1000)

    return {
        "accessToken": access_token,
        "refreshToken": new_refresh,
        "expiresAt": expires_at,
    }


@router.post("/logout")
async def logout(current_user: Dict = Depends(logout_current_user)):
    """登出"""
    return {"success": True, "message": "登出成功"}


@router.get("/me")
async def get_current_user_info(current_user: UserAuthInfo = Depends(get_current_user)):
    """获取当前用户信息"""
    user = _get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "displayName": user.get("displayName", user["username"]),
        "roles": user.get("roles", ["user"]),
        "permissions": user.get("permissions", []),
        "createdAt": user.get("createdAt"),
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserAuthInfo = Depends(get_current_user)
):
    """修改当前用户密码"""
    user = _get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 验证当前密码
    if not verify_password(request.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )

    # 更新密码
    user["password_hash"] = get_password_hash(request.new_password)
    user["passwordChangedAt"] = datetime.utcnow().isoformat()
    user_store.update_user(user["id"], {"password_hash": user["password_hash"]})

    return {"success": True, "message": "密码修改成功"}


# ==================== 管理端点（需要管理员权限）====================

@router.get("/users")
async def list_users(current_user: UserAuthInfo = Depends(get_current_user)):
    """列出所有用户（需要管理员权限）"""
    # 检查权限 - 使用 Permission 枚举
    required_permissions = [Permission.SYSTEM_ADMIN, Permission.USER_READ]
    user_permissions = [Permission(p) if isinstance(p, str) else p for p in current_user.permissions]

    # 检查是否拥有任一所需权限
    if not any(perm in user_permissions for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足。需要以下权限之一: {[p.value for p in required_permissions]}"
        )

    admin = _get_admin_user()
    users = [
        {
            "id": admin["id"],
            "username": admin["username"],
            "email": admin["email"],
            "displayName": admin["displayName"],
            "roles": [Role.ADMIN.value],
            "createdAt": admin["createdAt"],
            "isActive": True,
        }
    ] + [
        {
            "id": u["id"],
            "username": u["username"],
            "email": u["email"],
            "displayName": u.get("displayName", u["username"]),
            "roles": [r.value if isinstance(r, Role) else r for r in u.get("roles", [Role.USER])],
            "createdAt": u.get("createdAt"),
            "isActive": u.get("isActive", True),
        }
        for u in user_store.list_users()
    ]

    return {"users": users}


@router.post("/users")
async def create_user(
    request: UserCreateRequest,
    current_user: UserAuthInfo = Depends(get_current_user)
):
    """创建新用户（需要管理员权限）"""
    # 检查权限 - 使用 Permission 枚举
    required_permissions = [Permission.SYSTEM_ADMIN, Permission.USER_CREATE]
    user_permissions = [Permission(p) if isinstance(p, str) else p for p in current_user.permissions]

    if not any(perm in user_permissions for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足。需要以下权限之一: {[p.value for p in required_permissions]}"
        )

    # 检查用户名是否已存在
    if _get_user_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 创建用户
    role_values = [r.value if isinstance(r, Role) else r for r in request.roles]
    new_user = {
        "id": str(uuid.uuid4()),
        "username": request.username,
        "email": request.email,
        "displayName": request.display_name or request.username,
        "roles": role_values,
        "password_hash": get_password_hash(request.password),
        "createdAt": datetime.utcnow().isoformat(),
        "isActive": True,
    }

    # 获取权限
    permissions = RBACChecker.get_permissions_for_roles([Role(r) for r in role_values])
    new_user["permissions"] = [p.value for p in permissions]
    user_store.create_user(new_user)

    return {
        "id": new_user["id"],
        "username": new_user["username"],
        "email": new_user["email"],
        "displayName": new_user["displayName"],
        "roles": [r.value for r in new_user["roles"]],
        "createdAt": new_user["createdAt"],
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: UserAuthInfo = Depends(get_current_user)
):
    """更新用户信息（需要管理员权限）"""
    # 检查权限 - 使用 Permission 枚举
    required_permissions = [Permission.SYSTEM_ADMIN, Permission.USER_UPDATE]
    user_permissions = [Permission(p) if isinstance(p, str) else p for p in current_user.permissions]

    if not any(perm in user_permissions for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足。需要以下权限之一: {[p.value for p in required_permissions]}"
        )

    # 不允许修改管理员
    if user_id == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改管理员账户"
        )

    # 查找用户
    user = user_store.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新字段
    updates = {}
    if request.email is not None:
        user["email"] = request.email
        updates["email"] = request.email
    if request.display_name is not None:
        user["displayName"] = request.display_name
        updates["displayName"] = request.display_name
    if request.roles is not None:
        role_values = [r.value if isinstance(r, Role) else r for r in request.roles]
        user["roles"] = role_values
        permissions = RBACChecker.get_permissions_for_roles([Role(r) for r in role_values])
        user["permissions"] = [p.value for p in permissions]
        updates["roles"] = role_values
        updates["permissions"] = user["permissions"]

    if updates:
        user_store.update_user(user_id, updates)

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "displayName": user.get("displayName", user["username"]),
        "roles": [r.value for r in user["roles"]],
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserAuthInfo = Depends(get_current_user)
):
    """删除用户（需要管理员权限）"""
    # 检查权限 - 使用 Permission 枚举
    required_permissions = [Permission.SYSTEM_ADMIN, Permission.USER_DELETE]
    user_permissions = [Permission(p) if isinstance(p, str) else p for p in current_user.permissions]

    if not any(perm in user_permissions for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足。需要以下权限之一: {[p.value for p in required_permissions]}"
        )

    # 不允许删除管理员
    if user_id == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除管理员账户"
        )

    # 查找并删除用户
    deleted = user_store.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return {"success": True, "message": "用户已删除"}


# ==================== RBAC相关端点 ====================

@router.get("/roles")
async def list_roles(current_user: UserAuthInfo = Depends(get_current_user)):
    """列出所有角色"""
    return {"roles": RBACChecker.list_all_roles()}


@router.get("/roles/{role_name}")
async def get_role_info(
    role_name: str,
    current_user: UserAuthInfo = Depends(get_current_user)
):
    """获取角色详情"""
    try:
        role = Role(role_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    role_def = RBACChecker.get_role_definition(role)
    if not role_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    return {
        "name": role_def.name.value,
        "displayName": role_def.display_name,
        "description": role_def.description,
        "permissions": [p.value for p in role_def.permissions],
        "isSystemRole": role_def.is_system_role,
    }

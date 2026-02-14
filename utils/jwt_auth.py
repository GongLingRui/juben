"""
JWT Authentication Module for Juben Project

Provides JWT-based authentication and authorization functionality:
- JWT token generation and validation
- Password hashing and verification
- Authentication dependencies for FastAPI
- User session management
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Import logger
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import JubenLogger
from utils.redis_client import JubenRedisClient

logger = JubenLogger("jwt_auth")


# Configuration
class JWTConfig:
    """JWT configuration settings"""

    # Secret key - should be loaded from environment
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")

    # Algorithm
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Token expiration times
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Issuer
    ISSUER: str = os.getenv("JWT_ISSUER", "juben-api")

    @classmethod
    def validate(cls):
        """Validate JWT configuration"""
        if len(cls.SECRET_KEY) < 32:
            logger.warning("⚠️ JWT_SECRET_KEY is too short. Use at least 32 characters in production.")
        return True


# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer scheme for FastAPI
security = HTTPBearer(auto_error=False)


# Pydantic models
class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Token payload model"""
    sub: str  # Subject (user_id)
    exp: int  # Expiration time
    iat: int  # Issued at
    iss: str  # Issuer
    type: str = "access"  # Token type
    permissions: list = []


class UserAuthInfo(BaseModel):
    """User authentication info"""
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"
    permissions: list = []


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError) as e:
        # bcrypt 有 72 字节限制
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    # bcrypt 有 72 字节限制
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)


# JWT token utilities
def create_access_token(
    user_id: str,
    permissions: list = None,
    additional_claims: Dict[str, Any] = None
) -> str:
    """
    Create a JWT access token

    Args:
        user_id: User ID
        permissions: List of user permissions
        additional_claims: Additional claims to include

    Returns:
        str: Encoded JWT token
    """
    JWTConfig.validate()

    now = datetime.utcnow()
    expires = now + timedelta(minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "exp": expires,
        "iat": now,
        "iss": JWTConfig.ISSUER,
        "type": "access",
        "permissions": permissions or []
    }

    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, JWTConfig.SECRET_KEY, algorithm=JWTConfig.ALGORITHM)

    logger.info(f"✅ Created access token for user: {user_id}")
    return token


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token

    Args:
        user_id: User ID

    Returns:
        str: Encoded JWT refresh token
    """
    JWTConfig.validate()

    now = datetime.utcnow()
    expires = now + timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "exp": expires,
        "iat": now,
        "iss": JWTConfig.ISSUER,
        "type": "refresh"
    }

    token = jwt.encode(payload, JWTConfig.SECRET_KEY, algorithm=JWTConfig.ALGORITHM)

    logger.info(f"✅ Created refresh token for user: {user_id}")
    return token


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        TokenPayload: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            JWTConfig.SECRET_KEY,
            algorithms=[JWTConfig.ALGORITHM],
            issuer=JWTConfig.ISSUER
        )

        return TokenPayload(**payload)

    except jwt.ExpiredSignatureError:
        logger.warning("⚠️ Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )

    except jwt.InvalidTokenError as e:
        logger.warning(f"⚠️ Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def verify_token_type(token: str, expected_type: str) -> TokenPayload:
    """
    Verify token type

    Args:
        token: JWT token string
        expected_type: Expected token type (access/refresh)

    Returns:
        TokenPayload: Decoded token payload

    Raises:
        HTTPException: If token type doesn't match
    """
    payload = decode_token(token)

    if payload.type != expected_type:
        logger.warning(f"⚠️ Expected {expected_type} token, got {payload.type}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type. Expected {expected_type}",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload


# FastAPI dependencies
async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UserAuthInfo]:
    """
    Get current user from token (optional - no error if no token)

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        UserAuthInfo: User info or None
    """
    if credentials is None:
        return None

    try:
        payload = verify_token_type(credentials.credentials, "access")

        return UserAuthInfo(
            user_id=payload.sub,
            permissions=payload.permissions
        )

    except HTTPException:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserAuthInfo:
    """
    Get current user from token (required)

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        UserAuthInfo: User info

    Raises:
        HTTPException: If no token or invalid token
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = verify_token_type(credentials.credentials, "access")

    logger.debug(f"✅ Authenticated user: {payload.sub}")

    return UserAuthInfo(
        user_id=payload.sub,
        permissions=payload.permissions
    )


async def require_permissions(required_permissions: list):
    """
    Dependency factory to require specific permissions

    Args:
        required_permissions: List of required permissions

    Returns:
        Dependency function
    """
    async def permission_checker(
        current_user: UserAuthInfo = Depends(get_current_user)
    ) -> UserAuthInfo:
        """Check if user has required permissions"""
        user_permissions = set(current_user.permissions)
        required = set(required_permissions)

        if not required.issubset(user_permissions):
            logger.warning(
                f"⚠️ User {current_user.user_id} missing permissions: {required - user_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permissions}"
            )

        return current_user

    return permission_checker


# Token refresh
def refresh_access_token(refresh_token: str) -> Token:
    """
    Create new access token from refresh token

    Args:
        refresh_token: Valid refresh token

    Returns:
        Token: New token pair

    Raises:
        HTTPException: If refresh token is invalid
    """
    payload = verify_token_type(refresh_token, "refresh")

    # Create new tokens
    access_token = create_access_token(
        user_id=payload.sub,
        permissions=[]
    )
    new_refresh_token = create_refresh_token(payload.sub)

    logger.info(f"✅ Refreshed tokens for user: {payload.sub}")

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

async def logout_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Logout current user by blacklisting token

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Dict: Logout confirmation
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    token = credentials.credentials
    payload = decode_token(token)

    # 使用带缓存的黑名单管理器
    from utils.token_blacklist_manager import get_token_blacklist_manager
    blacklist_manager = await get_token_blacklist_manager()

    # 计算 token 剩余有效期
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    exp_time = datetime.fromtimestamp(payload.exp, tz=timezone.utc)
    ttl = int((exp_time - now).total_seconds()) if exp_time > now else 3600

    # 添加到黑名单
    await blacklist_manager.add_to_blacklist(token, ttl=ttl)

    logger.info(f"✅ Logged out user: {payload.sub}")

    return {
        "message": "Successfully logged out",
        "user_id": payload.sub
    }


# Session management (in-memory for now, can be replaced with Redis)
_sessions: Dict[str, Dict[str, Any]] = {}


def create_session(user_id: str, session_data: Dict[str, Any] = None) -> str:
    """
    Create a user session

    Args:
        user_id: User ID
        session_data: Additional session data

    Returns:
        str: Session ID
    """
    import uuid
    session_id = str(uuid.uuid4())

    _sessions[session_id] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "data": session_data or {}
    }

    logger.info(f"✅ Created session {session_id} for user {user_id}")
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get session data

    Args:
        session_id: Session ID

    Returns:
        Dict: Session data or None
    """
    return _sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """
    Delete a session

    Args:
        session_id: Session ID

    Returns:
        bool: True if deleted
    """
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info(f"✅ Deleted session {session_id}")
        return True
    return False


# Helper function to create token response
def create_token_response(user_id: str, permissions: list = None) -> Token:
    """
    Create a complete token response

    Args:
        user_id: User ID
        permissions: User permissions

    Returns:
        Token: Token response
    """
    access_token = create_access_token(user_id, permissions)
    refresh_token = create_refresh_token(user_id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# Initialize
def init_jwt_auth():
    """Initialize JWT authentication"""
    JWTConfig.validate()
    logger.info("✅ JWT Authentication initialized")
    logger.info(f"   Algorithm: {JWTConfig.ALGORITHM}")
    logger.info(f"   Access token expires: {JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    logger.info(f"   Refresh token expires: {JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS} days")

"""
自定义异常类和错误处理框架
提供统一的错误类型定义和处理机制
"""
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime
import traceback


class ErrorCode(str, Enum):
    """标准错误码定义"""

    # 通用错误 (1xxx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"

    # 认证/授权错误 (2xxx)
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # 输入验证错误 (3xxx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    OUT_OF_RANGE = "OUT_OF_RANGE"

    # 资源错误 (4xxx)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # 业务逻辑错误 (5xxx)
    BUSINESS_ERROR = "BUSINESS_ERROR"
    OPERATION_FAILED = "OPERATION_FAILED"
    INVALID_STATE = "INVALID_STATE"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"

    # 外部服务错误 (6xxx)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    VECTOR_DB_ERROR = "VECTOR_DB_ERROR"
    LLM_API_ERROR = "LLM_API_ERROR"
    SEARCH_API_ERROR = "SEARCH_API_ERROR"

    # 并发/性能错误 (7xxx)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    TIMEOUT = "TIMEOUT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"          # 轻微错误，不影响主要功能
    MEDIUM = "medium"    # 中等错误，影响部分功能
    HIGH = "high"        # 严重错误，影响核心功能
    CRITICAL = "critical" # 致命错误，系统无法运行


class BaseAppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.severity = severity
        self.http_status = http_status
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat()
        }


# ==================== 认证/授权异常 ====================

class AuthenticationException(BaseAppException):
    """认证异常"""

    def __init__(
        self,
        message: str = "认证失败",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.UNAUTHORIZED,
            details=details,
            http_status=status.HTTP_401_UNAUTHORIZED
        )


class TokenExpiredException(AuthenticationException):
    """令牌过期异常"""

    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="令牌已过期",
            details=details
        )
        self.code = ErrorCode.TOKEN_EXPIRED


class AuthorizationException(BaseAppException):
    """授权异常"""

    def __init__(
        self,
        message: str = "权限不足",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            details=details,
            http_status=status.HTTP_403_FORBIDDEN
        )


# ==================== 输入验证异常 ====================

class ValidationException(BaseAppException):
    """输入验证异常"""

    def __init__(
        self,
        message: str = "输入验证失败",
        field_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        merged_details = {**(details or {})}
        if field_errors:
            merged_details["field_errors"] = field_errors
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details=merged_details,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class InvalidInputException(ValidationException):
    """无效输入异常"""

    def __init__(
        self,
        field_name: str,
        message: Optional[str] = None
    ):
        super().__init__(
            message=message or f"无效的输入: {field_name}",
            details={"field": field_name}
        )
        self.code = ErrorCode.INVALID_INPUT


# ==================== 资源异常 ====================

class ResourceNotFoundException(BaseAppException):
    """资源未找到异常"""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"{resource_type} 未找到"
        if resource_id:
            message += f": {resource_id}"

        merged_details = {
            "resource_type": resource_type,
            **(details or {})
        }
        if resource_id:
            merged_details["resource_id"] = resource_id

        super().__init__(
            message=message,
            code=ErrorCode.RESOURCE_NOT_FOUND,
            details=merged_details,
            http_status=status.HTTP_404_NOT_FOUND
        )


class ResourceConflictException(BaseAppException):
    """资源冲突异常"""

    def __init__(
        self,
        message: str = "资源冲突",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=ErrorCode.RESOURCE_CONFLICT,
            details=details,
            http_status=status.HTTP_409_CONFLICT
        )


# ==================== 业务逻辑异常 ====================

class BusinessException(BaseAppException):
    """业务逻辑异常"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        super().__init__(
            message=message,
            code=ErrorCode.BUSINESS_ERROR,
            details=details,
            severity=severity,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class InvalidStateException(BusinessException):
    """无效状态异常"""

    def __init__(
        self,
        message: str = "操作在当前状态下无效",
        current_state: Optional[str] = None,
        expected_state: Optional[str] = None
    ):
        details = {}
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state

        super().__init__(
            message=message,
            details=details
        )
        self.code = ErrorCode.INVALID_STATE


# ==================== 外部服务异常 ====================

class ExternalServiceException(BaseAppException):
    """外部服务异常"""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        full_message = message or f"{service_name} 服务错误"
        merged_details = {
            "service": service_name,
            **(details or {})
        }
        if original_error:
            merged_details["original_error"] = str(original_error)

        super().__init__(
            message=full_message,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=merged_details,
            severity=ErrorSeverity.HIGH
        )


class DatabaseException(ExternalServiceException):
    """数据库异常"""

    def __init__(
        self,
        message: str = "数据库操作失败",
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service_name="Database",
            message=message,
            details=details,
            original_error=original_error
        )
        self.code = ErrorCode.DATABASE_ERROR


class VectorDBException(ExternalServiceException):
    """向量数据库异常"""

    def __init__(
        self,
        message: str = "向量数据库操作失败",
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service_name="VectorDB",
            message=message,
            details=details,
            original_error=original_error
        )
        self.code = ErrorCode.VECTOR_DB_ERROR


class LLMApiException(ExternalServiceException):
    """LLM API 异常"""

    def __init__(
        self,
        message: str = "LLM API 调用失败",
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service_name="LLM",
            message=message,
            details=details,
            original_error=original_error
        )
        self.code = ErrorCode.LLM_API_ERROR


# ==================== 并发/性能异常 ====================

class RateLimitException(BaseAppException):
    """速率限制异常"""

    def __init__(
        self,
        message: str = "请求频率过高",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        merged_details = {**(details or {})}
        if retry_after is not None:
            merged_details["retry_after"] = retry_after

        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details=merged_details,
            http_status=status.HTTP_429_TOO_MANY_REQUESTS
        )


class TimeoutException(BaseAppException):
    """超时异常"""

    def __init__(
        self,
        operation: str,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"操作超时: {operation}"
        merged_details = {"operation": operation, **(details or {})}
        if timeout_seconds:
            merged_details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            code=ErrorCode.TIMEOUT,
            details=merged_details,
            severity=ErrorSeverity.HIGH,
            http_status=status.HTTP_504_GATEWAY_TIMEOUT
        )


class ServiceUnavailableException(BaseAppException):
    """服务不可用异常"""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        full_message = message or f"{service_name} 服务暂时不可用"
        merged_details = {
            "service": service_name,
            **(details or {})
        }

        super().__init__(
            message=full_message,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            details=merged_details,
            severity=ErrorSeverity.HIGH,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# ==================== FastAPI 错误处理器 ====================

async def base_app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """处理 BaseAppException"""
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "success": False,
            "error": exc.to_dict()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有其他异常"""
    logger = __import__("utils.logger", fromlist=["get_logger"]).get_logger("error_handler")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "内部服务器错误",
                "details": {
                    "type": type(exc).__name__,
                    "message": str(exc)
                } if logger.logger.level <= 10 else {},  # Only in debug mode
                "severity": ErrorSeverity.HIGH.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR.value,
                "message": exc.detail,
                "details": {},
                "severity": ErrorSeverity.MEDIUM.value if exc.status_code < 500 else ErrorSeverity.HIGH.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


# ==================== 错误响应工具函数 ====================

def create_error_response(
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> JSONResponse:
    """创建错误响应"""
    error = BaseAppException(
        message=message,
        code=code,
        details=details,
        severity=severity,
        http_status=http_status
    )
    return JSONResponse(
        status_code=http_status,
        content={
            "success": False,
            "error": error.to_dict()
        }
    )


def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应"""
    return {
        "success": True,
        "message": message,
        "data": data
    }

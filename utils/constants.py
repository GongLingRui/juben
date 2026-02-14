"""
项目常量定义
集中管理所有魔法数字、字符串和配置值
"""
from enum import Enum
from typing import Tuple


# ==================== 环境常量 ====================

class Environment(str, Enum):
    """环境类型"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"


# ==================== 认证相关常量 ====================

class AuthConstants:
    """认证相关常量"""

    # Token 过期时间（秒）
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    # Token 算法
    ALGORITHM = "HS256"

    # 登录尝试
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW_MINUTES = 15

    # 密码要求
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128


# ==================== 缓存常量 ====================

class CacheConstants:
    """缓存相关常量"""

    # 缓存时间（秒）
    SHORT = 60
    MEDIUM = 300
    LONG = 3600
    VERY_LONG = 86400  # 24 小时

    # LRU 缓存大小
    LRU_CACHE_SIZE = 1000

    # Token 黑名单缓存
    TOKEN_BLACKLIST_CACHE_SIZE = 10000
    TOKEN_BLACKLIST_TTL = 300


# ==================== HTTP 相关常量 ====================

class HTTPConstants:
    """HTTP 相关常量"""

    # 状态码
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503

    # 请求大小限制
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB


# ==================== 压缩相关常量 ====================

class CompressionConstants:
    """压缩相关常量"""

    # GZip 压缩级别 (0-9)
    COMPRESSION_LEVEL = 6

    # 最小压缩大小（字节）
    MIN_COMPRESSION_SIZE = 1000


# ==================== 速率限制常量 ====================

class RateLimitConstants:
    """速率限制常量"""

    # 每分钟请求数
    DEFAULT_RPM = 120
    BURST_SIZE = 20

    # API 端点特定限制
    CHAT_RPM = 60
    UPLOAD_RPM = 30
    AUTH_RPM = 10


# ==================== 文件相关常量 ====================

class FileConstants:
    """文件相关常量"""

    # 文件大小限制（字节）
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB

    # 文件数量限制
    MAX_FILES_PER_REQUEST = 20
    MAX_FILES_TOTAL = 1000

    # 支持的文件类型
    ALLOWED_IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_DOCUMENT_TYPES = [".pdf", ".doc", ".docx", ".txt", ".md"]
    ALLOWED_VIDEO_TYPES = [".mp4", ".mov", ".avi", ".mkv"]


# ==================== LLM 相关常量 ====================

class LLMConstants:
    """LLM 调用相关常量"""

    # 超时时间（秒）
    DEFAULT_TIMEOUT = 180
    SHORT_TIMEOUT = 60
    LONG_TIMEOUT = 300

    # 重试配置
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # 指数退避基数
    RETRY_JITTER_RANGE = (0, 1)  # 随机抖动范围

    # Token 限制
    MAX_CONTEXT_TOKENS = 128000
    MAX_RESPONSE_TOKENS = 4096

    # 温度参数
    DEFAULT_TEMPERATURE = 0.7
    MIN_TEMPERATURE = 0.0
    MAX_TEMPERATURE = 2.0


# ==================== 分页相关常量 ====================

class PaginationConstants:
    """分页相关常量"""

    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1


# ==================== 数据库相关常量 ====================

class DatabaseConstants:
    """数据库相关常量"""

    # 连接池大小
    MIN_CONNECTIONS = 5
    MAX_CONNECTIONS = 20
    CONNECTION_TIMEOUT = 30
    IDLE_TIMEOUT = 600

    # 查询超时（秒）
    QUERY_TIMEOUT = 30

    # 事务隔离级别
    ISOLATION_LEVEL = "READ_COMMITTED"


# ==================== 日志相关常量 ====================

class LogConstants:
    """日志相关常量"""

    # 日志级别
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    # 日志保留时间（天）
    LOG_RETENTION_DAYS = 30

    # 日志文件大小（MB）
    MAX_LOG_SIZE_MB = 100


# ==================== 用户界面相关常量 ====================

class UIConstants:
    """用户界面相关常量"""

    # 分页
    DEFAULT_ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100

    # 输入限制
    MAX_INPUT_LENGTH = 10000
    MAX_COMMENT_LENGTH = 5000

    # 超时设置（毫秒）
    TOAST_DURATION = 3000
    MODAL_ANIMATION_DURATION = 200


# ==================== WebSocket 相关常量 ====================

class WebSocketConstants:
    """WebSocket 相关常量"""

    # 心跳间隔（秒）
    HEARTBEAT_INTERVAL = 30

    # 连接超时（秒）
    CONNECTION_TIMEOUT = 60

    # 消息大小限制（字节）
    MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MB


# ==================== 监控相关常量 ====================

class MonitoringConstants:
    """监控相关常量"""

    # 性能监控采样率
    PERFORMANCE_SAMPLE_RATE = 0.1  # 10%

    # 慢查询阈值（毫秒）
    SLOW_QUERY_THRESHOLD = 1000

    # 内存使用阈值（百分比）
    MEMORY_WARNING_THRESHOLD = 80
    MEMORY_CRITICAL_THRESHOLD = 90


# ==================== 时间相关常量 ====================

class TimeConstants:
    """时间相关常量"""

    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    MONTH = 2592000
    YEAR = 31536000


# ==================== 会话相关常量 ====================

class SessionConstants:
    """会话管理相关常量"""

    # 会话超时时间（秒）
    DEFAULT_SESSION_TIMEOUT = 3600  # 1小时
    EXTENDED_SESSION_TIMEOUT = 86400  # 24小时
    REMEMBER_ME_TIMEOUT = 2592000  # 30天

    # 会话清理
    SESSION_CLEANUP_INTERVAL = 3600  # 每小时清理一次过期会话
    MAX_SESSIONS_PER_USER = 10  # 每个用户最多同时拥有的会话数

    # 活动检测
    ACTIVITY_UPDATE_INTERVAL = 300  # 5分钟更新一次活动时间
    SESSION_GRACE_PERIOD = 300  # 会话过期后5分钟宽限期


# ==================== 密码策略常量 ====================

class PasswordPolicyConstants:
    """密码策略相关常量"""

    # 长度要求
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    RECOMMENDED_PASSWORD_LENGTH = 12

    # 复杂度要求
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL_CHAR = True

    # 特殊字符集合
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # 密码历史
    PASSWORD_HISTORY_COUNT = 5  # 记住最近5个密码
    PASSWORD_REUSE_DAYS = 90  # 90天内不能重复使用旧密码

    # 密码过期
    PASSWORD_EXPIRE_DAYS = 90  # 密码每90天过期
    PASSWORD_EXPIRE_WARNING_DAYS = 7  # 过期前7天警告

    # 密码重置
    RESET_TOKEN_EXPIRE_HOURS = 1  # 重置令牌1小时过期
    MAX_RESET_ATTEMPTS = 3  # 最多3次重置尝试


# ==================== CSRF 保护常量 ====================

class CSRFConstants:
    """CSRF 保护相关常量"""

    # Token 长度
    TOKEN_LENGTH = 32

    # Token 过期时间（秒）
    TOKEN_EXPIRE = 3600  # 1小时

    # Token 名称
    HEADER_NAME = "X-CSRF-Token"
    FORM_FIELD_NAME = "csrf_token"

    # 安全设置
    PER_REF_TOKEN = False  # 每次请求生成新令牌
    SECURE_COOKIE = True  # 仅HTTPS
    HTTPONLY_COOKIE = False  # 允许JavaScript访问
    SAMESITE = "Lax"  # SameSite属性


# ==================== 审计日志常量 ====================

class AuditConstants:
    """审计日志相关常量"""

    # 日志级别
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"
    LEVEL_CRITICAL = "critical"

    # 事件类型
    # 认证事件
    EVENT_LOGIN = "user.login"
    EVENT_LOGOUT = "user.logout"
    EVENT_LOGIN_FAILED = "user.login_failed"
    EVENT_PASSWORD_CHANGE = "user.password_change"
    EVENT_PASSWORD_RESET = "user.password_reset"

    # 数据事件
    EVENT_CREATE = "data.create"
    EVENT_READ = "data.read"
    EVENT_UPDATE = "data.update"
    EVENT_DELETE = "data.delete"

    # 权限事件
    EVENT_GRANT = "permission.grant"
    EVENT_REVOKE = "permission.revoke"
    EVENT_ESCALATE = "permission.escalate"

    # 系统事件
    EVENT_CONFIG_CHANGE = "system.config_change"
    EVENT_STARTUP = "system.startup"
    EVENT_SHUTDOWN = "system.shutdown"

    # 保留时间（天）
    LOG_RETENTION_DAYS = 365  # 审计日志保留1年
    ARCHIVE_AFTER_DAYS = 30  # 30天后归档

    # 批量写入
    BATCH_SIZE = 100
    FLUSH_INTERVAL = 60  # 秒


# ==================== IP 白名单常量 ====================

class IPWhitelistConstants:
    """IP 白名单相关常量"""

    # 默认白名单（本地访问）
    DEFAULT_WHITELIST = [
        "127.0.0.1",
        "::1",
        "localhost"
    ]

    # 私有IP范围
    PRIVATE_IP_RANGES = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16"
    ]

    # 白名单检查模式
    MODE_ALLOW = "allow"  # 仅允许白名单
    MODE_DENY = "deny"  # 仅拒绝黑名单
    MODE_HYBRID = "hybrid"  # 混合模式

    # 缓存时间（秒）
    CACHE_TTL = 300  # 5分钟


# ==================== API 版本控制常量 ====================

class APIVersionConstants:
    """API 版本控制相关常量"""

    # 当前版本
    CURRENT_VERSION = "v1"
    SUPPORTED_VERSIONS = ["v1", "v2"]

    # 版本弃用
    DEPRECATED_VERSIONS = {
        "v1": "2025-12-31"  # v1版本将在2025年12月31日弃用
    }

    # 版本策略
    VERSION_HEADER = "X-API-Version"
    VERSION_QUERY_PARAM = "api_version"

    # 响应头
    API_VERSION_HEADER = "X-API-Version"
    API_DEPRECATED_HEADER = "X-API-Deprecated"


# ==================== 断路器常量 ====================

class CircuitBreakerConstants:
    """断路器模式相关常量"""

    # 默认阈值
    DEFAULT_FAILURE_THRESHOLD = 5  # 失败次数阈值
    DEFAULT_SUCCESS_THRESHOLD = 2  # 半开状态成功阈值
    DEFAULT_TIMEOUT = 60  # 熔断超时时间（秒）
    DEFAULT_HALF_OPEN_MAX_CALLS = 3  # 半开状态最大调用次数

    # 滑动窗口
    SLIDING_WINDOW_SIZE = 100  # 滑动窗口大小
    MIN_CALLS_THRESHOLD = 10  # 最小调用次数阈值

    # 超时设置
    DEFAULT_CALL_TIMEOUT = 30  # 调用超时（秒）

    # 恢复时间
    RECOVERY_TIMEOUT = 60  # 恢复超时（秒）
    HALF_OPEN_TIMEOUT = 30  # 半开状态超时（秒）


# ==================== 双因素认证常量 ====================

class TwoFactorAuthConstants:
    """双因素认证相关常量"""

    # TOTP 设置
    TOTP_ISSUER = "JubenAI"
    TOTP_DIGITS = 6
    TOTP_PERIOD = 30  # 秒
    TOTP_ALGORITHM = "SHA1"

    # 备份码
    BACKUP_CODES_COUNT = 10
    BACKUP_CODE_LENGTH = 8

    # 验证码
    CODE_EXPIRE_SECONDS = 300  # 5分钟
    MAX_VERIFY_ATTEMPTS = 3
    RESEND_COOLDOWN = 60  # 重发冷却时间（秒）

    # 信任设备
    TRUSTED_DEVICE_DAYS = 30  # 信任设备30天


# ==================== 导出所有常量 ====================

__all__ = [
    # 环境常量
    "Environment",
    # 认证常量
    "AuthConstants",
    # 缓存常量
    "CacheConstants",
    # HTTP 常量
    "HTTPConstants",
    # 压缩常量
    "CompressionConstants",
    # 速率限制常量
    "RateLimitConstants",
    # 文件常量
    "FileConstants",
    # LLM 常量
    "LLMConstants",
    # 分页常量
    "PaginationConstants",
    # 数据库常量
    "DatabaseConstants",
    # 日志常量
    "LogConstants",
    # UI 常量
    "UIConstants",
    # WebSocket 常量
    "WebSocketConstants",
    # 监控常量
    "MonitoringConstants",
    # 时间常量
    "TimeConstants",
    # 会话常量
    "SessionConstants",
    # 密码策略常量
    "PasswordPolicyConstants",
    # CSRF 常量
    "CSRFConstants",
    # 审计日志常量
    "AuditConstants",
    # IP 白名单常量
    "IPWhitelistConstants",
    # API 版本控制常量
    "APIVersionConstants",
    # 断路器常量
    "CircuitBreakerConstants",
    # 双因素认证常量
    "TwoFactorAuthConstants",
]

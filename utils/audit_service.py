"""
审计日志服务

记录所有关键操作用于安全审计和合规性要求
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import deque

from utils.logger import get_logger
from utils.constants import AuditConstants

logger = get_logger("AuditService")


class AuditLevel(str, Enum):
    """审计日志级别"""
    INFO = AuditConstants.LEVEL_INFO
    WARNING = AuditConstants.LEVEL_WARNING
    ERROR = AuditConstants.LEVEL_ERROR
    CRITICAL = AuditConstants.LEVEL_CRITICAL


class AuditEventType(str, Enum):
    """审计事件类型"""

    # 认证事件
    LOGIN = AuditConstants.EVENT_LOGIN
    LOGOUT = AuditConstants.EVENT_LOGOUT
    LOGIN_FAILED = AuditConstants.EVENT_LOGIN_FAILED
    PASSWORD_CHANGE = AuditConstants.EVENT_PASSWORD_CHANGE
    PASSWORD_RESET = AuditConstants.EVENT_PASSWORD_RESET

    # 数据事件
    CREATE = AuditConstants.EVENT_CREATE
    READ = AuditConstants.EVENT_READ
    UPDATE = AuditConstants.EVENT_UPDATE
    DELETE = AuditConstants.EVENT_DELETE

    # 权限事件
    GRANT = AuditConstants.EVENT_GRANT
    REVOKE = AuditConstants.EVENT_REVOKE
    ESCALATE = AuditConstants.EVENT_ESCALATE

    # 系统事件
    CONFIG_CHANGE = AuditConstants.EVENT_CONFIG_CHANGE
    STARTUP = AuditConstants.EVENT_STARTUP
    SHUTDOWN = AuditConstants.EVENT_SHUTDOWN


@dataclass
class AuditEvent:
    """审计事件数据结构"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    level: str = AuditLevel.INFO
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换 datetime 为 ISO 字符串
        if isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        if isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        return data


class AuditLogger:
    """
    审计日志记录器

    功能：
    1. 记录所有关键操作
    2. 支持批量写入
    3. 支持异步处理
    4. 支持日志归档
    """

    def __init__(self):
        self._buffer: deque[AuditEvent] = deque(maxlen=AuditConstants.BATCH_SIZE)
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._storage_backend = self._get_storage_backend()

    def _get_storage_backend(self) -> str:
        """获取存储后端"""
        import os
        return os.getenv("AUDIT_STORAGE_BACKEND", "file")  # file, database, or hybrid

    async def start(self):
        """启动审计日志服务"""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("✅ 审计日志服务已启动")

    async def stop(self):
        """停止审计日志服务"""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 刷新剩余的日志
        await self._flush()

        logger.info("✅ 审计日志服务已停止")

    async def _flush_loop(self):
        """定期刷新日志"""
        while self._running:
            try:
                await asyncio.sleep(AuditConstants.FLUSH_INTERVAL)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 刷新审计日志失败: {e}")

    async def _flush(self):
        """刷新日志到存储"""
        if not self._buffer:
            return

        events = list(self._buffer)
        self._buffer.clear()

        try:
            if self._storage_backend in ("database", "hybrid"):
                await self._write_to_database(events)
            if self._storage_backend in ("file", "hybrid"):
                await self._write_to_file(events)
        except Exception as e:
            logger.error(f"❌ 写入审计日志失败: {e}")

    async def _write_to_database(self, events: List[AuditEvent]):
        """写入数据库"""
        try:
            from utils.database_client import execute

            for event in events:
                await execute(
                    """
                    INSERT INTO audit_logs (
                        event_id, event_type, severity, timestamp, user_id, session_id,
                        ip_address, user_agent, action, resource_type, resource_id,
                        details, success, error_message, correlation_id, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    event.event_id,
                    event.event_type,
                    event.level,
                    event.timestamp,
                    event.user_id,
                    event.session_id,
                    event.ip_address,
                    event.user_agent,
                    event.action,
                    event.resource_type,
                    event.resource_id,
                    json.dumps(event.details),
                    event.success,
                    event.error_message,
                    event.correlation_id,
                    event.created_at
                )
        except Exception as e:
            logger.error(f"❌ 写入数据库审计日志失败: {e}")

    async def _write_to_file(self, events: List[AuditEvent]):
        """写入文件"""
        try:
            from pathlib import Path
            import os

            log_dir = Path(os.getenv("AUDIT_LOG_DIR", "logs/audit"))
            log_dir.mkdir(parents=True, exist_ok=True)

            # 按日期分割文件
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = log_dir / f"audit_{date_str}.log"

            with open(log_file, "a", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

        except Exception as e:
            logger.error(f"❌ 写入文件审计日志失败: {e}")

    def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        level: AuditLevel = AuditLevel.INFO,
        request: Optional[Any] = None,
    ) -> str:
        """
        记录审计事件

        Args:
            event_type: 事件类型
            user_id: 用户 ID
            session_id: 会话 ID
            action: 操作动作
            resource_type: 资源类型
            resource_id: 资源 ID
            details: 详细信息
            success: 是否成功
            error_message: 错误消息
            level: 日志级别
            request: FastAPI 请求对象（用于提取 IP 和 User-Agent）

        Returns:
            事件 ID
        """
        # 从请求中提取信息
        ip_address = None
        user_agent = None
        correlation_id = None

        if request:
            ip_address = self._extract_ip(request)
            user_agent = request.headers.get("user-agent")
            correlation_id = request.headers.get("x-correlation-id")

        # 创建事件
        event = AuditEvent(
            event_type=event_type.value,
            level=level.value,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            success=success,
            error_message=error_message,
            correlation_id=correlation_id
        )

        # 添加到缓冲区
        self._buffer.append(event)

        # 如果缓冲区满了，立即刷新
        if len(self._buffer) >= AuditConstants.BATCH_SIZE:
            asyncio.create_task(self._flush())

        return event.event_id

    def _extract_ip(self, request: Any) -> Optional[str]:
        """从请求中提取 IP 地址"""
        # 尝试从各种 header 中获取真实 IP
        headers_to_check = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",
            "x-client-ip"
        ]

        for header in headers_to_check:
            ip = request.headers.get(header)
            if ip:
                # x-forwarded-for 可能包含多个 IP
                if "," in ip:
                    ip = ip.split(",")[0].strip()
                return ip

        # 回退到直接连接的 IP
        if hasattr(request, "client"):
            return request.client.host if request.client else None

        return None

    # 便捷方法
    def login(
        self,
        user_id: str,
        success: bool = True,
        request: Optional[Any] = None
    ) -> str:
        """记录登录事件"""
        return self.log(
            event_type=AuditEventType.LOGIN,
            user_id=user_id,
            action="user_login",
            success=success,
            error_message=None if success else "登录失败",
            request=request
        )

    def logout(
        self,
        user_id: str,
        request: Optional[Any] = None
    ) -> str:
        """记录登出事件"""
        return self.log(
            event_type=AuditEventType.LOGOUT,
            user_id=user_id,
            action="user_logout",
            request=request
        )

    def data_access(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        request: Optional[Any] = None
    ) -> str:
        """记录数据访问事件"""
        event_type = AuditEventType.READ
        if action.startswith("create"):
            event_type = AuditEventType.CREATE
        elif action.startswith("update"):
            event_type = AuditEventType.UPDATE
        elif action.startswith("delete"):
            event_type = AuditEventType.DELETE

        return self.log(
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request=request
        )

    def permission_change(
        self,
        admin_id: str,
        target_user_id: str,
        action: str,
        permissions: List[str],
        request: Optional[Any] = None
    ) -> str:
        """记录权限变更事件"""
        return self.log(
            event_type=AuditEventType.GANT if action == "grant" else AuditEventType.REVOKE,
            user_id=admin_id,
            action=f"permission_{action}",
            resource_type="user_permission",
            resource_id=target_user_id,
            details={"permissions": permissions},
            request=request
        )

    def system_event(
        self,
        event_type: AuditEventType,
        details: Dict[str, Any],
        level: AuditLevel = AuditLevel.INFO
    ) -> str:
        """记录系统事件"""
        return self.log(
            event_type=event_type,
            action=event_type.value,
            details=details,
            level=level
        )


# 全局审计日志记录器实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志记录器单例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

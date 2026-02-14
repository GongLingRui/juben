"""
会话管理器

提供会话超时、清理和管理功能
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from collections import OrderedDict
from dataclasses import dataclass, field

from utils.logger import get_logger
from utils.constants import SessionConstants

logger = get_logger("SessionManager")


@dataclass
class SessionData:
    """会话数据"""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_extended: bool = False  # 是否为延长会话（记住我）

    @property
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_within_grace_period(self) -> bool:
        """检查是否在宽限期内"""
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        grace_end = self.expires_at + timedelta(seconds=SessionConstants.SESSION_GRACE_PERIOD)
        return now < grace_end


class SessionManager:
    """
    会话管理器

    功能：
    1. 会话超时管理
    2. 会话清理
    3. 最大会话数限制
    4. 活动检测
    5. 延长会话（记住我）
    """

    def __init__(self):
        # 使用 OrderedDict 实现 LRU 缓存
        self._sessions: OrderedDict[str, SessionData] = OrderedDict()
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """启动会话管理器"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("✅ 会话管理器已启动")

    async def stop(self):
        """停止会话管理器"""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("✅ 会话管理器已停止")

    async def _cleanup_loop(self):
        """定期清理过期会话"""
        while self._running:
            try:
                await asyncio.sleep(SessionConstants.SESSION_CLEANUP_INTERVAL)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 清理会话失败: {e}")

    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now(timezone.utc)
        expired_sessions = []

        for session_id, session in self._sessions.items():
            if session.is_expired and not session.is_within_grace_period:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.remove_session(session_id)

        if expired_sessions:
            logger.info(f"🧹 清理了 {len(expired_sessions)} 个过期会话")

    def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        remember_me: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionData:
        """
        创建新会话

        Args:
            user_id: 用户 ID
            ip_address: IP 地址
            user_agent: User-Agent
            remember_me: 是否记住我（延长会话）
            metadata: 元数据

        Returns:
            会话数据
        """
        # 检查用户是否超过最大会话数
        self._enforce_max_sessions(user_id)

        # 创建会话
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # 计算过期时间
        if remember_me:
            expires_at = now + timedelta(seconds=SessionConstants.REMEMBER_ME_TIMEOUT)
        else:
            expires_at = now + timedelta(seconds=SessionConstants.DEFAULT_SESSION_TIMEOUT)

        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            is_extended=remember_me
        )

        # 添加到存储
        self._sessions[session_id] = session
        self._sessions.move_to_end(session_id)  # 标记为最近使用

        # 添加到用户会话列表
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        logger.info(f"✅ 创建会话: {session_id} for user {user_id}")
        return session

    def _enforce_max_sessions(self, user_id: str):
        """强制执行最大会话数限制"""
        user_sessions = self._user_sessions.get(user_id, [])

        if len(user_sessions) >= SessionConstants.MAX_SESSIONS_PER_USER:
            # 删除最旧的会话
            sessions_to_remove = len(user_sessions) - SessionConstants.MAX_SESSIONS_PER_USER + 1

            for _ in range(sessions_to_remove):
                if user_sessions:
                    oldest_session_id = user_sessions.pop(0)
                    self._remove_session_no_cleanup(oldest_session_id)

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """获取会话"""
        session = self._sessions.get(session_id)
        if session:
            # 更新 LRU
            self._sessions.move_to_end(session_id)
        return session

    def update_activity(self, session_id: str) -> bool:
        """
        更新会话活动时间

        Args:
            session_id: 会话 ID

        Returns:
            是否更新成功
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.last_activity_at = datetime.now(timezone.utc)
        return True

    def extend_session(self, session_id: str, remember_me: bool = False) -> bool:
        """
        延长会话过期时间

        Args:
            session_id: 会话 ID
            remember_me: 是否设置为延长会话

        Returns:
            是否延长成功
        """
        session = self.get_session(session_id)
        if not session:
            return False

        now = datetime.now(timezone.utc)
        if remember_me:
            session.expires_at = now + timedelta(seconds=SessionConstants.REMEMBER_ME_TIMEOUT)
        else:
            session.expires_at = now + timedelta(seconds=SessionConstants.EXTENDED_SESSION_TIMEOUT)

        session.is_extended = remember_me
        return True

    async def remove_session(self, session_id: str) -> bool:
        """移除会话"""
        return self._remove_session_no_cleanup(session_id)

    def _remove_session_no_cleanup(self, session_id: str) -> bool:
        """移除会话（不触发清理）"""
        session = self._sessions.pop(session_id, None)
        if not session:
            return False

        # 从用户会话列表中移除
        if session.user_id in self._user_sessions:
            user_sessions = self._user_sessions[session.user_id]
            if session_id in user_sessions:
                user_sessions.remove(session_id)

        logger.info(f"🗑️ 移除会话: {session_id}")
        return True

    async def remove_user_sessions(self, user_id: str) -> int:
        """移除用户的所有会话"""
        session_ids = self._user_sessions.get(user_id, []).copy()
        count = 0

        for session_id in session_ids:
            if await self.remove_session(session_id):
                count += 1

        return count

    def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """获取用户的所有活动会话"""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []

        for session_id in session_ids:
            session = self.get_session(session_id)
            if session and not session.is_expired:
                sessions.append(session)

        return sessions

    def get_active_session_count(self) -> int:
        """获取活动会话数量"""
        return len([s for s in self._sessions.values() if not s.is_expired])

    def validate_session(self, session_id: str) -> tuple[bool, Optional[str]]:
        """
        验证会话是否有效

        Returns:
            (是否有效, 错误消息)
        """
        session = self.get_session(session_id)

        if not session:
            return False, "会话不存在"

        if session.is_expired:
            if session.is_within_grace_period:
                # 在宽限期内，允许活动后延长
                return True, None
            return False, "会话已过期"

        return True, None

    async def cleanup_expired_sessions(self) -> int:
        """手动清理过期会话"""
        await self._cleanup_expired_sessions()
        return len([s for s in self._sessions.values() if s.is_expired])


# 全局会话管理器实例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

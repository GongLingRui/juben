"""
流式事件回放管理器
提供流式事件的数据库持久化、断网检测和事件回放功能

功能：
1. 用户心跳跟踪
2. 流式事件数据库持久化
3. 断网检测和时间窗口
4. 智能事件回放
5. 任务状态检查
6. 混合模式：回放+实时流


"""

import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

import logging

logger = logging.getLogger(__name__)


class ReplayReason(Enum):
    """回放原因"""
    NORMAL_REPLAY = "normal_replay"
    HAS_DISCONNECT_EVENTS = "has_disconnect_events"
    TOO_MANY_UNREPLAYED = "too_many_unreplayed"
    NO_EVENTS = "no_events"
    CHECK_FAILED = "check_failed"


@dataclass
class StreamEventRecord:
    """流式事件记录"""
    id: Optional[int] = None
    session_id: str = ""
    user_id: str = ""
    event_type: str = ""
    content_type: Optional[str] = None
    agent_source: str = ""
    event_data: Any = None
    event_metadata: Dict = None
    is_replayed: bool = False
    is_after_disconnect: bool = False
    is_session_complete: bool = False
    task_phase: Optional[str] = None
    created_at: Optional[str] = None
    user_last_seen: Optional[str] = None

    def __post_init__(self):
        if self.event_metadata is None:
            self.event_metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class StreamReplayManager:
    """
    流式事件回放管理器

    功能：
    1. 用户心跳跟踪 - 检测用户断网时间
    2. 流式事件持久化 - 数据库存储
    3. 断网检测 - 基于心跳时间窗口
    4. 智能回放 - 只回放断网后的事件
    5. 任务状态检查 - 判断任务是否完成
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._storage_manager = None

        # 心跳缓存（避免频繁数据库写入）
        self._heartbeat_cache: Dict[str, datetime] = {}
        self._heartbeat_cache_ttl = 5  # 5秒缓存

    async def _get_storage_manager(self):
        """获取存储管理器"""
        if self._storage_manager is None:
            from utils.storage_manager import get_storage
            self._storage_manager = get_storage()
        return self._storage_manager

    def _normalize_boolean(self, value: Any, default: bool = False) -> bool:
        """统一处理布尔值"""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 't')
        return bool(value)

    # ==================== 用户心跳跟踪 ====================

    async def update_user_heartbeat(self, user_id: str, session_id: str) -> bool:
        """
        更新用户心跳（带缓存优化）

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            bool: 是否成功
        """
        try:
            cache_key = f"{user_id}:{session_id}"
            now = datetime.now(timezone.utc)

            # 如果5秒内已经更新过，跳过（减少数据库写入）
            if cache_key in self._heartbeat_cache:
                last_update = self._heartbeat_cache[cache_key]
                if (now - last_update).total_seconds() < self._heartbeat_cache_ttl:
                    return True

            # 使用Redis存储心跳时间
            try:
                from utils.redis_client import get_redis_client
                redis_client = await get_redis_client()
                if redis_client:
                    heartbeat_key = f"juben:heartbeat:{user_id}:{session_id}"
                    await redis_client.setex(heartbeat_key, 3600, now.isoformat())
            except Exception as e:
                self.logger.warning(f"⚠️ Redis心跳更新失败: {e}")

            # 更新缓存
            self._heartbeat_cache[cache_key] = now

            return True

        except Exception as e:
            self.logger.error(f"❌ 更新心跳失败: {e}")
            return False

    async def get_last_heartbeat(self, user_id: str, session_id: str) -> Optional[datetime]:
        """
        获取用户最后心跳时间

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Optional[datetime]: 最后心跳时间（UTC）
        """
        try:
            cache_key = f"{user_id}:{session_id}"

            # 先查缓存
            if cache_key in self._heartbeat_cache:
                return self._heartbeat_cache[cache_key]

            # 从Redis获取
            try:
                from utils.redis_client import get_redis_client
                redis_client = await get_redis_client()
                if redis_client:
                    heartbeat_key = f"juben:heartbeat:{user_id}:{session_id}"
                    heartbeat_str = await redis_client.get(heartbeat_key)
                    if heartbeat_str:
                        heartbeat = datetime.fromisoformat(heartbeat_str)
                        self._heartbeat_cache[cache_key] = heartbeat
                        return heartbeat
            except Exception as e:
                self.logger.warning(f"⚠️ Redis心跳查询失败: {e}")

            return None

        except Exception as e:
            self.logger.error(f"❌ 获取最后心跳失败: {e}")
            return None

    # ==================== 流式事件持久化 ====================

    async def store_event(
        self,
        session_id: str,
        user_id: str,
        event_type: str,
        content_type: Optional[str],
        agent_source: str,
        event_data: Any,
        event_metadata: Dict = None,
        is_after_disconnect: bool = False,
        is_session_complete: bool = False,
        task_phase: Optional[str] = None
    ) -> bool:
        """
        存储流式事件

        Args:
            session_id: 会话ID
            user_id: 用户ID
            event_type: 事件类型
            content_type: 内容类型
            agent_source: Agent来源
            event_data: 事件数据
            event_metadata: 事件元数据
            is_after_disconnect: 是否在断网后
            is_session_complete: 会话是否完成
            task_phase: 任务阶段

        Returns:
            bool: 是否成功
        """
        try:
            # 使用Redis存储（简化版本）
            try:
                from utils.redis_client import get_redis_client
                redis_client = await get_redis_client()
                if redis_client:
                    event_key = f"juben:stream_event:{session_id}:{datetime.now(timezone.utc).timestamp()}"

                    event_record = StreamEventRecord(
                        session_id=session_id,
                        user_id=user_id,
                        event_type=event_type,
                        content_type=content_type,
                        agent_source=agent_source,
                        event_data=event_data,
                        event_metadata=event_metadata or {},
                        is_replayed=False,
                        is_after_disconnect=is_after_disconnect,
                        is_session_complete=is_session_complete,
                        task_phase=task_phase
                    )

                    # 存储到Redis（7天过期）
                    await redis_client.setex(
                        event_key,
                        7 * 24 * 3600,
                        json.dumps(event_record.to_dict(), ensure_ascii=False, default=str)
                    )

                    # 添加到会话事件列表
                    list_key = f"juben:stream_events:{session_id}"
                    await redis_client.rpush(list_key, event_key)
                    await redis_client.expire(list_key, 7 * 24 * 3600)

                    self.logger.debug(f"✅ 事件已存储: session_id={session_id}, type={event_type}")
                    return True

            except Exception as e:
                self.logger.warning(f"⚠️ Redis事件存储失败: {e}")

            return False

        except Exception as e:
            self.logger.error(f"❌ 存储事件失败: {e}")
            return False

    # ==================== 断网检测和回放检查 ====================

    async def check_need_replay(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        检查是否需要回放

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 回放信息
        """
        try:
            self.logger.info(f"🔍 检查是否需要回放: session_id={session_id}")

            # 获取用户最后心跳时间
            last_heartbeat = await self.get_last_heartbeat(user_id, session_id)

            # 获取所有未回放的事件
            unreplayed_events = await self._get_unreplayed_events(session_id)

            if not unreplayed_events:
                return {
                    'needs_replay': False,
                    'reason': ReplayReason.NO_EVENTS.value,
                    'events': []
                }

            # 如果有最后心跳时间，判断断网时间窗口
            if last_heartbeat:
                # 断网窗口开始时间 = 最后心跳时间 + 30秒
                disconnect_window_start = last_heartbeat + timedelta(seconds=30)

                # 过滤出断网窗口内的事件
                events_in_window = []
                for event in unreplayed_events:
                    try:
                        event_time = datetime.fromisoformat(event['created_at'])
                        if event_time >= disconnect_window_start:
                            events_in_window.append(event)
                    except Exception:
                        # 如果时间解析失败，保留该事件
                        events_in_window.append(event)

                unreplayed_events = events_in_window

            if not unreplayed_events:
                return {
                    'needs_replay': False,
                    'reason': ReplayReason.NO_EVENTS.value,
                    'events': []
                }

            # 检查是否有断网后的事件
            has_disconnect_events = any(
                self._normalize_boolean(e.get('is_after_disconnect', False))
                for e in unreplayed_events
            )

            reason = ReplayReason.NORMAL_REPLAY.value
            if has_disconnect_events:
                reason = ReplayReason.HAS_DISCONNECT_EVENTS.value
            elif len(unreplayed_events) > 10:
                reason = ReplayReason.TOO_MANY_UNREPLAYED.value

            self.logger.info(f"✅ 需要回放 {len(unreplayed_events)} 个事件，原因: {reason}")

            return {
                'needs_replay': True,
                'reason': reason,
                'events': unreplayed_events,
                'total_count': len(unreplayed_events)
            }

        except Exception as e:
            self.logger.error(f"❌ 检查回放需求失败: {e}")
            return {
                'needs_replay': False,
                'reason': ReplayReason.CHECK_FAILED.value,
                'events': []
            }

    async def _get_unreplayed_events(self, session_id: str) -> List[Dict[str, Any]]:
        """获取未回放的事件"""
        try:
            from utils.redis_client import get_redis_client
            redis_client = await get_redis_client()
            if not redis_client:
                return []

            list_key = f"juben:stream_events:{session_id}"
            event_keys = await redis_client.lrange(list_key, 0, -1)

            events = []
            for event_key in event_keys:
                try:
                    event_data = await redis_client.get(event_key)
                    if event_data:
                        event_dict = json.loads(event_data)
                        # 只返回未回放的事件
                        if not self._normalize_boolean(event_dict.get('is_replayed', False)):
                            events.append(event_dict)
                except Exception as e:
                    self.logger.warning(f"⚠️ 解析事件失败: {e}")

            return events

        except Exception as e:
            self.logger.error(f"❌ 获取未回放事件失败: {e}")
            return []

    # ==================== 任务状态检查 ====================

    async def check_task_status(self, session_id: str) -> Dict[str, Any]:
        """
        检查任务/会话的状态

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 任务状态
        """
        try:
            from utils.redis_client import get_redis_client
            redis_client = await get_redis_client()
            if not redis_client:
                return {"is_running": False, "reason": "redis_unavailable"}

            list_key = f"juben:stream_events:{session_id}"
            event_keys = await redis_client.lrange(list_key, -5)  # 获取最后5个事件

            if not event_keys:
                return {"is_running": False, "reason": "no_events_found"}

            events = []
            for event_key in event_keys:
                try:
                    event_data = await redis_client.get(event_key)
                    if event_data:
                        events.append(json.loads(event_data))
                except Exception:
                    pass

            if not events:
                return {"is_running": False, "reason": "no_valid_events"}

            # 获取最后事件
            last_event = events[-1]

            # 检查是否有完成标记
            completion_indicators = ['SESSION_COMPLETE', 'ORCHESTRATOR_DECLARATION']
            has_completion_signal = any(
                last_event.get('event_type') in completion_indicators or
                last_event.get('task_phase') == 'completed' or
                self._normalize_boolean(last_event.get('is_session_complete', False))
                for event in events
            )

            # 解析最后事件时间
            try:
                last_event_time_str = last_event['created_at']
                if last_event_time_str.endswith('Z'):
                    last_event_time_str = last_event_time_str.replace('Z', '+00:00')
                last_event_time = datetime.fromisoformat(last_event_time_str)
                last_event_utc = last_event_time.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                last_event_utc = datetime.now(timezone.utc)

            current_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            minutes_since_last = (current_utc - last_event_utc).total_seconds() / 60

            # 判断任务状态
            if has_completion_signal:
                is_running = False
                reason = "completion_signal_detected"
            elif minutes_since_last <= 2:
                is_running = True
                reason = "recent_activity_detected"
            elif minutes_since_last <= 10:
                is_running = False
                reason = "moderate_inactivity_assumed_complete"
            else:
                is_running = False
                reason = "long_inactivity_assumed_complete"

            return {
                "is_running": is_running,
                "reason": reason,
                "last_event_time": last_event_utc.isoformat() + 'Z',
                "last_event_type": last_event.get('event_type'),
                "last_agent_source": last_event.get('agent_source'),
                "minutes_since_last_event": round(minutes_since_last, 1),
                "has_completion_signal": has_completion_signal,
                "current_time": current_utc.isoformat() + 'Z'
            }

        except Exception as e:
            self.logger.error(f"❌ 检查任务状态失败: {e}")
            return {"is_running": False, "reason": f"error: {str(e)}"}

    # ==================== 事件标记 ====================

    async def mark_events_replayed(self, session_id: str, event_ids: List[str] = None) -> bool:
        """
        标记事件为已回放

        Args:
            session_id: 会话ID
            event_ids: 事件ID列表（可选，为空则标记所有）

        Returns:
            bool: 是否成功
        """
        try:
            from utils.redis_client import get_redis_client
            redis_client = await get_redis_client()
            if not redis_client:
                return False

            list_key = f"juben:stream_events:{session_id}"
            event_keys = await redis_client.lrange(list_key, 0, -1)

            count = 0
            for event_key in event_keys:
                try:
                    event_data = await redis_client.get(event_key)
                    if event_data:
                        event_dict = json.loads(event_data)
                        # 如果指定了event_ids，只标记这些事件
                        if event_ids is None or event_dict.get('id') in event_ids:
                            event_dict['is_replayed'] = True
                            await redis_client.set(event_key, json.dumps(event_dict, default=str))
                            count += 1
                except Exception:
                    pass

            self.logger.info(f"✅ 标记了 {count} 个事件为已回放")
            return True

        except Exception as e:
            self.logger.error(f"❌ 标记事件已回放失败: {e}")
            return False

    async def mark_session_complete(self, session_id: str, user_id: str, completion_metadata: Dict = None) -> bool:
        """
        标记会话为已完成

        Args:
            session_id: 会话ID
            user_id: 用户ID
            completion_metadata: 完成元数据

        Returns:
            bool: 是否成功
        """
        return await self.store_event(
            session_id=session_id,
            user_id=user_id,
            event_type="SESSION_COMPLETE",
            content_type="system",
            agent_source="system",
            event_data={"message": "任务已完成", **(completion_metadata or {})},
            event_metadata={"is_system_event": True},
            is_session_complete=True,
            task_phase="completed"
        )

    # ==================== 实时流支持 ====================

    async def get_events_after_timestamp(self, session_id: str, timestamp: float) -> List[Dict[str, Any]]:
        """
        获取指定时间戳之后的事件（用于实时流）

        Args:
            session_id: 会话ID
            timestamp: Unix时间戳

        Returns:
            List[Dict]: 事件列表
        """
        try:
            from utils.redis_client import get_redis_client
            redis_client = await get_redis_client()
            if not redis_client:
                return []

            list_key = f"juben:stream_events:{session_id}"
            event_keys = await redis_client.lrange(list_key, 0, -1)

            events = []
            cutoff_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

            for event_key in event_keys:
                try:
                    event_data = await redis_client.get(event_key)
                    if event_data:
                        event_dict = json.loads(event_data)
                        event_time_str = event_dict.get('created_at', '')
                        if event_time_str:
                            if event_time_str.endswith('Z'):
                                event_time_str = event_time_str.replace('Z', '+00:00')
                            event_time = datetime.fromisoformat(event_time_str)
                            if event_time > cutoff_time:
                                events.append(event_dict)
                except Exception:
                    pass

            return events

        except Exception as e:
            self.logger.error(f"❌ 获取时间戳后事件失败: {e}")
            return []


# ==================== 全局实例 ====================

_stream_replay_manager: Optional[StreamReplayManager] = None


def get_stream_replay_manager() -> StreamReplayManager:
    """获取流式回放管理器单例"""
    global _stream_replay_manager
    if _stream_replay_manager is None:
        _stream_replay_manager = StreamReplayManager()
    return _stream_replay_manager


# ==================== 便捷函数 ====================

async def update_heartbeat(user_id: str, session_id: str) -> bool:
    """更新用户心跳"""
    manager = get_stream_replay_manager()
    return await manager.update_user_heartbeat(user_id, session_id)


async def check_need_replay(session_id: str, user_id: str) -> Dict[str, Any]:
    """检查是否需要回放"""
    manager = get_stream_replay_manager()
    return await manager.check_need_replay(session_id, user_id)


async def check_task_status(session_id: str) -> Dict[str, Any]:
    """检查任务状态"""
    manager = get_stream_replay_manager()
    return await manager.check_task_status(session_id)

"""
Juben停止管理器
 ，提供优雅的停止控制机制
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    from .redis_client import get_redis_client
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from utils.redis_client import get_redis_client


class StopReason(Enum):
    """停止原因枚举"""
    USER_REQUEST = "user_request"
    ERROR = "error"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    SYSTEM_SHUTDOWN = "system_shutdown"


class JubenStoppedException(Exception):
    """Juben停止异常"""
    
    def __init__(self, user_id: str, session_id: str, reason: StopReason, message: str = ""):
        self.user_id = user_id
        self.session_id = session_id
        self.reason = reason
        self.message = message
        super().__init__(f"操作已停止: {message} (用户: {user_id}, 会话: {session_id}, 原因: {reason.value})")


class JubenStopManager:
    """
    Juben停止管理器
    
    功能：
    1. 优雅停止控制
    2. 停止状态管理
    3. 停止原因追踪
    4. 自动清理机制
    """
    
    def __init__(self):
        self.logger = logging.getLogger("JubenStopManager")
        
        # 停止状态存储
        self.stop_states = {}  # {f"{user_id}:{session_id}": StopInfo}
        
        # 配置
        self.cleanup_interval = 3600  # 1小时清理一次过期状态
        self.max_stop_history = 1000   # 最大停止历史记录数
        
        # 停止历史
        self.stop_history = []
        
        self.logger.info("🛑 Juben停止管理器初始化完成")
    
    async def initialize(self):
        """初始化停止管理器"""
        try:
            # 启动清理任务
            asyncio.create_task(self._cleanup_task())
            
            self.logger.info("✅ 停止管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 停止管理器初始化失败: {e}")
            return False
    
    async def _cleanup_task(self):
        """清理任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_states()
            except Exception as e:
                self.logger.error(f"❌ 清理任务失败: {e}")
    
    async def _cleanup_expired_states(self):
        """清理过期的停止状态"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, stop_info in self.stop_states.items():
                # 清理超过24小时的停止状态
                if (current_time - stop_info.timestamp).total_seconds() > 86400:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.stop_states[key]
            
            # 清理停止历史
            if len(self.stop_history) > self.max_stop_history:
                self.stop_history = self.stop_history[-self.max_stop_history:]
            
            if expired_keys:
                self.logger.info(f"🧹 清理了{len(expired_keys)}个过期的停止状态")
                
        except Exception as e:
            self.logger.error(f"❌ 清理过期状态失败: {e}")
    
    async def request_stop(
        self, 
        user_id: str, 
        session_id: str, 
        reason: StopReason, 
        message: str = "",
        agent_name: str = None
    ) -> bool:
        """
        请求停止当前执行
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            reason: 停止原因
            message: 停止消息
            agent_name: 请求停止的Agent名称
            
        Returns:
            bool: 是否成功设置停止状态
        """
        try:
            key = f"{user_id}:{session_id}"
            
            # 创建停止信息
            stop_info = StopInfo(
                user_id=user_id,
                session_id=session_id,
                reason=reason,
                message=message,
                agent_name=agent_name,
                timestamp=datetime.now()
            )
            
            # 存储停止状态
            self.stop_states[key] = stop_info
            
            # 记录停止历史
            self.stop_history.append({
                'user_id': user_id,
                'session_id': session_id,
                'reason': reason.value,
                'message': message,
                'agent_name': agent_name,
                'timestamp': datetime.now().isoformat()
            })
            
            # 尝试存储到Redis（如果可用）
            try:
                redis_client = await get_redis_client()
                if redis_client:
                    redis_key = f"juben:stop:{key}"
                    await redis_client.setex(
                        redis_key, 
                        86400,  # 24小时过期
                        json.dumps(stop_info.to_dict())
                    )
            except Exception as e:
                self.logger.warning(f"⚠️ 存储停止状态到Redis失败: {e}")
            
            self.logger.info(f"🛑 停止请求已设置: {user_id}:{session_id}, 原因: {reason.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 设置停止状态失败: {e}")
            return False
    
    async def is_stopped(self, user_id: str, session_id: str) -> bool:
        """
        检查是否已请求停止
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            bool: 是否已停止
        """
        try:
            key = f"{user_id}:{session_id}"
            
            # 首先检查内存中的状态
            if key in self.stop_states:
                return True
            
            # 检查Redis中的状态
            try:
                redis_client = await get_redis_client()
                if redis_client:
                    redis_key = f"juben:stop:{key}"
                    stop_data = await redis_client.get(redis_key)
                    if stop_data:
                        # 同步到内存
                        stop_info_dict = json.loads(stop_data)
                        stop_info = StopInfo.from_dict(stop_info_dict)
                        self.stop_states[key] = stop_info
                        return True
            except Exception as e:
                self.logger.warning(f"⚠️ 从Redis检查停止状态失败: {e}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 检查停止状态失败: {e}")
            return False
    
    async def check_and_raise_if_stopped(self, user_id: str, session_id: str, current_step: str = ""):
        """
        检查停止状态，如果已停止则抛出异常
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            current_step: 当前执行步骤
            
        Raises:
            JubenStoppedException: 如果已请求停止
        """
        try:
            if await self.is_stopped(user_id, session_id):
                key = f"{user_id}:{session_id}"
                stop_info = self.stop_states.get(key)
                
                if stop_info:
                    raise JubenStoppedException(
                        user_id=user_id,
                        session_id=session_id,
                        reason=stop_info.reason,
                        message=f"{stop_info.message} (步骤: {current_step})"
                    )
                else:
                    raise JubenStoppedException(
                        user_id=user_id,
                        session_id=session_id,
                        reason=StopReason.USER_REQUEST,
                        message=f"操作已停止 (步骤: {current_step})"
                    )
                    
        except JubenStoppedException:
            raise
        except Exception as e:
            self.logger.error(f"❌ 检查停止状态异常: {e}")
    
    async def clear_stop_state(self, user_id: str, session_id: str) -> bool:
        """
        清除停止状态
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            bool: 是否成功清除
        """
        try:
            key = f"{user_id}:{session_id}"
            
            # 清除内存中的状态
            if key in self.stop_states:
                del self.stop_states[key]
            
            # 清除Redis中的状态
            try:
                redis_client = await get_redis_client()
                if redis_client:
                    redis_key = f"juben:stop:{key}"
                    await redis_client.delete(redis_key)
            except Exception as e:
                self.logger.warning(f"⚠️ 从Redis清除停止状态失败: {e}")
            
            self.logger.info(f"✅ 停止状态已清除: {user_id}:{session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 清除停止状态失败: {e}")
            return False
    
    async def get_stop_info(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取停止信息
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            Optional[Dict]: 停止信息
        """
        try:
            key = f"{user_id}:{session_id}"
            stop_info = self.stop_states.get(key)
            
            if stop_info:
                return stop_info.to_dict()
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 获取停止信息失败: {e}")
            return None
    
    async def get_stop_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取停止历史
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List[Dict]: 停止历史列表
        """
        try:
            return self.stop_history[-limit:] if self.stop_history else []
            
        except Exception as e:
            self.logger.error(f"❌ 获取停止历史失败: {e}")
            return []
    
    async def get_stop_stats(self) -> Dict[str, Any]:
        """
        获取停止统计信息
        
        Returns:
            Dict: 停止统计信息
        """
        try:
            # 统计各原因的停止次数
            reason_counts = {}
            for record in self.stop_history:
                reason = record.get('reason', 'unknown')
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            return {
                'total_stops': len(self.stop_history),
                'active_stops': len(self.stop_states),
                'reason_counts': reason_counts,
                'recent_stops': self.stop_history[-10:] if self.stop_history else []
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取停止统计失败: {e}")
            return {'error': str(e)}


class StopInfo:
    """停止信息类"""
    
    def __init__(self, user_id: str, session_id: str, reason: StopReason, 
                 message: str = "", agent_name: str = None, timestamp: datetime = None):
        self.user_id = user_id
        self.session_id = session_id
        self.reason = reason
        self.message = message
        self.agent_name = agent_name
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'reason': self.reason.value,
            'message': self.message,
            'agent_name': self.agent_name,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StopInfo':
        """从字典创建实例"""
        return cls(
            user_id=data['user_id'],
            session_id=data['session_id'],
            reason=StopReason(data['reason']),
            message=data.get('message', ''),
            agent_name=data.get('agent_name'),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


# 全局停止管理器实例
_juben_stop_manager = None


async def get_juben_stop_manager() -> JubenStopManager:
    """获取Juben停止管理器实例"""
    global _juben_stop_manager
    
    if _juben_stop_manager is None:
        _juben_stop_manager = JubenStopManager()
        await _juben_stop_manager.initialize()
    
    return _juben_stop_manager


# 便捷函数
async def request_stop(user_id: str, session_id: str, reason: StopReason, message: str = "", agent_name: str = None) -> bool:
    """请求停止"""
    manager = await get_juben_stop_manager()
    return await manager.request_stop(user_id, session_id, reason, message, agent_name)


async def is_stopped(user_id: str, session_id: str) -> bool:
    """检查是否已停止"""
    manager = await get_juben_stop_manager()
    return await manager.is_stopped(user_id, session_id)


async def clear_stop_state(user_id: str, session_id: str) -> bool:
    """清除停止状态"""
    manager = await get_juben_stop_manager()
    return await manager.clear_stop_state(user_id, session_id)
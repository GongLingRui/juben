"""
分布式锁管理器
基于 Redis 的分布式锁实现，用于解决高并发场景下同一 session_id 的上下文竞争问题

功能：
1. 基于 Redis SET NX EX 实现分布式锁
2. 自动锁释放（包括异常情况）
3. 锁续期机制（长时间任务）
4. 装饰器支持，方便使用

代码作者：宫灵瑞
创建时间：2026年2月7日
"""
import asyncio
import logging
import uuid
from functools import wraps
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta

try:
    from .redis_client import get_redis_client
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.redis_client import get_redis_client


class DistributedLockError(Exception):
    """分布式锁异常"""
    pass


class LockAcquisitionError(DistributedLockError):
    """获取锁失败异常"""

    def __init__(self, lock_key: str, message: str = "锁已被占用，请稍后再试"):
        self.lock_key = lock_key
        super().__init__(f"[{lock_key}] {message}")


class RedisDistributedLock:
    """
    Redis 分布式锁

    使用 SET NX EX 命令实现：
    - NX: 只在键不存在时设置
    - EX: 设置过期时间（秒）

    锁格式：lock:session:{session_id}
    """

    # 默认配置
    DEFAULT_LOCK_TIMEOUT = 300  # 默认锁超时时间（秒）5分钟
    DEFAULT_RETRY_DELAY = 0.1   # 默认重试延迟（秒）
    DEFAULT_MAX_RETRIES = 0     # 默认最大重试次数（0=不重试，直接失败）

    def __init__(
        self,
        redis_client=None,
        lock_timeout: int = None,
        retry_delay: float = None,
        max_retries: int = None
    ):
        """
        初始化分布式锁

        Args:
            redis_client: Redis 客户端（如果为 None，则自动获取）
            lock_timeout: 锁超时时间（秒），默认 300 秒
            retry_delay: 重试延迟（秒），默认 0.1 秒
            max_retries: 最大重试次数，默认 0（不重试）
        """
        self.redis_client = redis_client
        self.lock_timeout = lock_timeout or self.DEFAULT_LOCK_TIMEOUT
        self.retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY
        self.max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self.logger = logging.getLogger("RedisDistributedLock")

        # 锁持有记录 {lock_key: (lock_value, acquired_at)}
        self._held_locks: Dict[str, tuple] = {}

    async def _get_redis(self):
        """获取 Redis 客户端"""
        if self.redis_client is None:
            self.redis_client = await get_redis_client()
        if self.redis_client is None:
            raise DistributedLockError("Redis 客户端不可用")
        return self.redis_client

    def _generate_lock_value(self) -> str:
        """生成锁值（唯一标识）"""
        return f"{uuid.uuid4()}:{datetime.now().timestamp()}"

    async def acquire(
        self,
        lock_key: str,
        timeout: int = None,
        blocking: bool = False,
        blocking_timeout: float = None
    ) -> Optional[str]:
        """
        获取锁

        Args:
            lock_key: 锁的键名
            timeout: 锁的超时时间（秒），None 表示使用默认值
            blocking: 是否阻塞等待
            blocking_timeout: 阻塞等待的最大时间（秒），None 表示无限等待

        Returns:
            str: 锁的值（用于释放锁），如果获取失败则返回 None

        Raises:
            LockAcquisitionError: 如果获取锁失败且不阻塞
        """
        redis = await self._get_redis()
        lock_value = self._generate_lock_value()
        actual_timeout = timeout or self.lock_timeout
        full_lock_key = f"lock:session:{lock_key}"

        start_time = datetime.now()

        while True:
            # 尝试获取锁
            acquired = await redis.set(
                full_lock_key,
                lock_value,
                nx=True,  # 只在键不存在时设置
                ex=actual_timeout  # 设置过期时间
            )

            if acquired:
                # 记录持有的锁
                self._held_locks[full_lock_key] = (lock_value, datetime.now())
                self.logger.info(f"✅ 获取锁成功: {full_lock_key}")
                return lock_value

            # 未获取到锁
            if not blocking:
                # 不阻塞，直接失败
                self.logger.warning(f"⚠️ 获取锁失败: {full_lock_key}（锁已被占用）")
                return None

            # 检查阻塞超时
            if blocking_timeout is not None:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= blocking_timeout:
                    self.logger.warning(f"⚠️ 获取锁超时: {full_lock_key}")
                    return None

            # 等待后重试
            await asyncio.sleep(self.retry_delay)

    async def release(self, lock_key: str, lock_value: str) -> bool:
        """
        释放锁

        使用 Lua 脚本确保只释放自己持有的锁

        Args:
            lock_key: 锁的键名
            lock_value: 锁的值

        Returns:
            bool: 是否成功释放
        """
        redis = await self._get_redis()
        full_lock_key = f"lock:session:{lock_key}"

        # Lua 脚本：确保只删除匹配的锁值
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await redis.eval(lua_script, 1, full_lock_key, lock_value)

            if result:
                # 从持有记录中移除
                self._held_locks.pop(full_lock_key, None)
                self.logger.info(f"✅ 释放锁成功: {full_lock_key}")
                return True
            else:
                self.logger.warning(f"⚠️ 释放锁失败: {full_lock_key}（锁值不匹配或已过期）")
                return False

        except Exception as e:
            self.logger.error(f"❌ 释放锁异常: {full_lock_key}, {e}")
            return False

    async def extend(self, lock_key: str, lock_value: str, additional_time: int = None) -> bool:
        """
        续期锁

        用于长时间运行的任务，延长锁的过期时间

        Args:
            lock_key: 锁的键名
            lock_value: 锁的值
            additional_time: 额外时间（秒），None 表示使用原始超时时间

        Returns:
            bool: 是否成功续期
        """
        redis = await self._get_redis()
        full_lock_key = f"lock:session:{lock_key}"
        extend_time = additional_time or self.lock_timeout

        # Lua 脚本：只续期匹配的锁值
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        try:
            result = await redis.eval(lua_script, 1, full_lock_key, lock_value, extend_time)

            if result:
                self.logger.info(f"✅ 续期锁成功: {full_lock_key}, +{extend_time}秒")
                return True
            else:
                self.logger.warning(f"⚠️ 续期锁失败: {full_lock_key}（锁值不匹配或已过期）")
                return False

        except Exception as e:
            self.logger.error(f"❌ 续期锁异常: {full_lock_key}, {e}")
            return False

    async def is_locked(self, lock_key: str) -> bool:
        """
        检查锁是否被持有

        Args:
            lock_key: 锁的键名

        Returns:
            bool: 锁是否被持有
        """
        redis = await self._get_redis()
        full_lock_key = f"lock:session:{lock_key}"

        try:
            result = await redis.exists(full_lock_key)
            return bool(result)
        except Exception as e:
            self.logger.error(f"❌ 检查锁状态异常: {full_lock_key}, {e}")
            return False

    async def get_lock_ttl(self, lock_key: str) -> Optional[int]:
        """
        获取锁的剩余生存时间

        Args:
            lock_key: 锁的键名

        Returns:
            int: 剩余秒数，如果锁不存在返回 None
        """
        redis = await self._get_redis()
        full_lock_key = f"lock:session:{lock_key}"

        try:
            ttl = await redis.ttl(full_lock_key)
            return ttl if ttl > 0 else None
        except Exception as e:
            self.logger.error(f"❌ 获取锁TTL异常: {full_lock_key}, {e}")
            return None

    async def force_release(self, lock_key: str) -> bool:
        """
        强制释放锁（不检查锁值）

        警告：只应在紧急情况下使用

        Args:
            lock_key: 锁的键名

        Returns:
            bool: 是否成功释放
        """
        redis = await self._get_redis()
        full_lock_key = f"lock:session:{lock_key}"

        try:
            await redis.delete(full_lock_key)
            self._held_locks.pop(full_lock_key, None)
            self.logger.warning(f"⚠️ 强制释放锁: {full_lock_key}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 强制释放锁异常: {full_lock_key}, {e}")
            return False

    def get_held_locks(self) -> Dict[str, Dict[str, Any]]:
        """
        获取当前持有的所有锁

        Returns:
            Dict: 持有的锁信息
        """
        result = {}
        for key, (value, acquired_at) in self._held_locks.items():
            held_duration = (datetime.now() - acquired_at).total_seconds()
            result[key] = {
                "lock_value": value,
                "acquired_at": acquired_at.isoformat(),
                "held_seconds": held_duration
            }
        return result


class SessionLockDecorator:
    """
    Session 锁装饰器

    用于装饰 process_request 等方法，自动处理分布式锁
    """

    def __init__(
        self,
        lock_timeout: int = 300,
        blocking: bool = False,
        blocking_timeout: float = None,
        extend_lock_interval: int = None,
        error_message: str = "AI 正在思考中，请稍后再试"
    ):
        """
        初始化装饰器

        Args:
            lock_timeout: 锁超时时间（秒）
            blocking: 是否阻塞等待
            blocking_timeout: 阻塞等待的最大时间（秒）
            extend_lock_interval: 锁续期间隔（秒），None 表示不续期
            error_message: 获取锁失败时的错误消息
        """
        self.lock_timeout = lock_timeout
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.extend_lock_interval = extend_lock_interval
        self.error_message = error_message
        self.logger = logging.getLogger("SessionLockDecorator")

        # 锁管理器实例（延迟初始化）
        self._lock_manager: Optional[RedisDistributedLock] = None

    async def _get_lock_manager(self) -> RedisDistributedLock:
        """获取锁管理器"""
        if self._lock_manager is None:
            self._lock_manager = RedisDistributedLock(lock_timeout=self.lock_timeout)
        return self._lock_manager

    def __call__(self, func: Callable) -> Callable:
        """装饰器实现"""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 从参数中提取 session_id 和 user_id
            session_id = kwargs.get('session_id')
            user_id = kwargs.get('user_id')

            # 如果参数中没有，尝试从 context 中提取
            if not session_id or not user_id:
                context = kwargs.get('context')
                if isinstance(context, dict):
                    session_id = session_id or context.get('session_id')
                    user_id = user_id or context.get('user_id')

            # 如果仍然没有，从 request_data 中提取
            if not session_id or not user_id:
                request_data = args[1] if len(args) > 1 else kwargs.get('request_data', {})
                if isinstance(request_data, dict):
                    session_id = session_id or request_data.get('session_id')
                    user_id = user_id or request_data.get('user_id')

            # 如果没有 session_id，直接执行（不加锁）
            if not session_id:
                self.logger.warning("⚠️ 未提供 session_id，跳过分布式锁")
                async for result in func(*args, **kwargs):
                    yield result
                return

            lock_manager = await self._get_lock_manager()
            lock_key = f"{user_id or 'unknown'}:{session_id}"

            # 尝试获取锁
            lock_value = await lock_manager.acquire(
                lock_key,
                timeout=self.lock_timeout,
                blocking=self.blocking,
                blocking_timeout=self.blocking_timeout
            )

            if lock_value is None:
                # 获取锁失败
                self.logger.warning(f"⚠️ 获取锁失败: {lock_key}")
                raise LockAcquisitionError(lock_key, self.error_message)

            try:
                # 如果需要续期，启动续期任务
                extend_task = None
                if self.extend_lock_interval:
                    extend_task = asyncio.create_task(
                        self._extend_lock_periodically(lock_manager, lock_key, lock_value)
                    )

                # 执行原函数
                async for result in func(*args, **kwargs):
                    yield result

            finally:
                # 取消续期任务
                if extend_task:
                    extend_task.cancel()
                    try:
                        await extend_task
                    except asyncio.CancelledError:
                        pass

                # 释放锁
                await lock_manager.release(lock_key, lock_value)

        return async_wrapper

    async def _extend_lock_periodically(
        self,
        lock_manager: RedisDistributedLock,
        lock_key: str,
        lock_value: str
    ):
        """定期续期锁"""
        try:
            while True:
                await asyncio.sleep(self.extend_lock_interval)
                success = await lock_manager.extend(lock_key, lock_value)
                if not success:
                    self.logger.warning(f"⚠️ 锁续期失败，停止续期: {lock_key}")
                    break
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass


def with_session_lock(
    lock_timeout: int = 300,
    blocking: bool = False,
    blocking_timeout: float = None,
    extend_lock_interval: int = None,
    error_message: str = "AI 正在思考中，请稍后再试"
):
    """
    Session 锁装饰器（便捷函数）

    用法：
    ```python
    @with_session_lock(lock_timeout=300)
    async def process_request(self, request_data, context):
        async for event in ...:
            yield event
    ```

    Args:
        lock_timeout: 锁超时时间（秒），默认 300
        blocking: 是否阻塞等待
        blocking_timeout: 阻塞等待的最大时间（秒）
        extend_lock_interval: 锁续期间隔（秒），None 表示不续期
        error_message: 获取锁失败时的错误消息

    Returns:
        装饰器函数
    """
    return SessionLockDecorator(
        lock_timeout=lock_timeout,
        blocking=blocking,
        blocking_timeout=blocking_timeout,
        extend_lock_interval=extend_lock_interval,
        error_message=error_message
    )


# 上下文管理器版本的分布式锁
class SessionLockContext:
    """
    Session 锁上下文管理器

    用法：
    ```python
    async with SessionLockContext(session_id, user_id) as lock:
        # 执行需要加锁的代码
        pass
    ```
    """

    def __init__(
        self,
        session_id: str,
        user_id: str = None,
        lock_timeout: int = 300,
        blocking: bool = False,
        blocking_timeout: float = None
    ):
        self.session_id = session_id
        self.user_id = user_id or "unknown"
        self.lock_timeout = lock_timeout
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.lock_manager = RedisDistributedLock(lock_timeout=lock_timeout)
        self.lock_key = f"{self.user_id}:{session_id}"
        self.lock_value = None

    async def __aenter__(self):
        self.lock_value = await self.lock_manager.acquire(
            self.lock_key,
            timeout=self.lock_timeout,
            blocking=self.blocking,
            blocking_timeout=self.blocking_timeout
        )

        if self.lock_value is None:
            raise LockAcquisitionError(
                self.lock_key,
                "AI 正在思考中，请稍后再试"
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.lock_value:
            await self.lock_manager.release(self.lock_key, self.lock_value)


# 全局锁管理器实例
_global_lock_manager: Optional[RedisDistributedLock] = None


async def get_distributed_lock() -> RedisDistributedLock:
    """获取全局分布式锁管理器"""
    global _global_lock_manager
    if _global_lock_manager is None:
        _global_lock_manager = RedisDistributedLock()
    return _global_lock_manager


# 便捷函数
async def acquire_session_lock(
    session_id: str,
    user_id: str = None,
    lock_timeout: int = 300
) -> Optional[str]:
    """获取 session 锁"""
    lock_manager = await get_distributed_lock()
    lock_key = f"{user_id or 'unknown'}:{session_id}"
    return await lock_manager.acquire(lock_key, timeout=lock_timeout)


async def release_session_lock(session_id: str, user_id: str = None, lock_value: str = None):
    """释放 session 锁"""
    lock_manager = await get_distributed_lock()
    lock_key = f"{user_id or 'unknown'}:{session_id}"
    if lock_value:
        await lock_manager.release(lock_key, lock_value)


async def is_session_locked(session_id: str, user_id: str = None) -> bool:
    """检查 session 是否被锁定"""
    lock_manager = await get_distributed_lock()
    lock_key = f"{user_id or 'unknown'}:{session_id}"
    return await lock_manager.is_locked(lock_key)

"""
缓存管理器
提供统一的缓存接口，支持内存、Redis等多种缓存后端
"""

import json
import asyncio
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ==================== 缓存后端接口 ====================

class CacheBackend(ABC):
    """缓存后端抽象接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取键列表"""
        pass


# ==================== 内存缓存实现 ====================

class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            # 检查是否过期
            if entry.get("expires_at") and datetime.now() > entry["expires_at"]:
                del self._cache[key]
                return None

            return entry.get("value")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            # 达到最大容量时，删除最旧的条目
            if len(self._cache) >= self._max_size:
                # 删除最旧的10%
                keys_to_delete = list(self._cache.keys())[:self._max_size // 10]
                for k in keys_to_delete:
                    del self._cache[k]

            entry = {
                "value": value,
                "created_at": datetime.now(),
                "expires_at": None
            }

            if ttl:
                entry["expires_at"] = datetime.now() + timedelta(seconds=ttl)

            self._cache[key] = entry
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return False

            # 检查是否过期
            if entry.get("expires_at") and datetime.now() > entry["expires_at"]:
                del self._cache[key]
                return False

            return True

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True

    async def keys(self, pattern: str = "*") -> List[str]:
        async with self._lock:
            if pattern == "*":
                return list(self._cache.keys())

            # 简单的通配符匹配
            import fnmatch
            return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]


# ==================== 缓存管理器 ====================

class CacheManager:
    """
    缓存管理器
    提供统一的缓存接口，支持命名空间、TTL、标签等功能
    """

    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or MemoryCacheBackend()
        self.logger = logger

    def _generate_key(self, namespace: str, key: str) -> str:
        """生成缓存键"""
        return f"{namespace}:{key}"

    def _hash_key(self, key: Union[str, Dict, List]) -> str:
        """生成键的哈希值"""
        if isinstance(key, str):
            content = key
        else:
            content = json.dumps(key, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            namespace: 命名空间
            key: 缓存键

        Returns:
            缓存值，不存在或过期返回 None
        """
        cache_key = self._generate_key(namespace, key)
        try:
            value = await self.backend.get(cache_key)
            if value is not None:
                self.logger.debug(f"缓存命中: {cache_key}")
            else:
                self.logger.debug(f"缓存未命中: {cache_key}")
            return value
        except Exception as e:
            self.logger.error(f"获取缓存失败: {e}")
            return None

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存

        Args:
            namespace: 命名空间
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        cache_key = self._generate_key(namespace, key)
        try:
            success = await self.backend.set(cache_key, value, ttl)
            if success:
                self.logger.debug(f"缓存已设置: {cache_key}, TTL: {ttl}")
            return success
        except Exception as e:
            self.logger.error(f"设置缓存失败: {e}")
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """删除缓存"""
        cache_key = self._generate_key(namespace, key)
        try:
            return await self.backend.delete(cache_key)
        except Exception as e:
            self.logger.error(f"删除缓存失败: {e}")
            return False

    async def exists(self, namespace: str, key: str) -> bool:
        """检查缓存是否存在"""
        cache_key = self._generate_key(namespace, key)
        try:
            return await self.backend.exists(cache_key)
        except Exception:
            return False

    async def clear_namespace(self, namespace: str) -> bool:
        """清空命名空间下所有缓存"""
        try:
            pattern = f"{namespace}:*"
            keys = await self.backend.keys(pattern)
            for key in keys:
                await self.backend.delete(key)
            self.logger.info(f"已清空命名空间: {namespace}, 删除了 {len(keys)} 个键")
            return True
        except Exception as e:
            self.logger.error(f"清空命名空间失败: {e}")
            return False

    async def get_or_set(
        self,
        namespace: str,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取缓存，如果不存在则通过工厂函数创建

        Args:
            namespace: 命名空间
            key: 缓存键
            factory: 工厂函数
            ttl: 过期时间

        Returns:
            缓存值
        """
        value = await self.get(namespace, key)
        if value is not None:
            return value

        # 调用工厂函数创建值
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        # 存入缓存
        await self.set(namespace, key, value, ttl)
        return value


# ==================== 缓存装饰器 ====================

def cached(
    namespace: str,
    key_func: Optional[Callable] = None,
    ttl: Optional[int] = None
):
    """
    缓存装饰器

    Args:
        namespace: 命名空间
        key_func: 键生成函数，默认使用函数名和参数
        ttl: 过期时间（秒）

    Usage:
        @cached("user", ttl=300)
        async def get_user(user_id: str):
            return await db.fetch_user(user_id)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数的哈希
                key_parts = [func.__name__]
                if args:
                    key_parts.extend(str(a) for a in args)
                if kwargs:
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key = ":".join(key_parts)

            # 尝试获取缓存
            cache = get_cache_manager()
            value = await cache.get(namespace, key)

            if value is not None:
                return value

            # 调用原函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # 存入缓存
            await cache.set(namespace, key, result, ttl)

            return result

        return wrapper
    return decorator


# ==================== 全局实例 ====================

_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# ==================== 预定义命名空间 ====================

class CacheNamespace:
    """预定义的缓存命名空间"""
    AGENT = "agent"
    AGENT_OUTPUT = "agent_output"
    KNOWLEDGE = "knowledge"
    PROJECT = "project"
    USER = "user"
    SESSION = "session"
    API_RESPONSE = "api_response"
    VECTOR_SEARCH = "vector_search"
    EMBEDDING = "embedding"

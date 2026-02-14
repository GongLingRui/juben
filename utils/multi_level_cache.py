"""
多级缓存策略

实现三级缓存架构：
- L1: 内存缓存 (热点数据)
- L2: Redis缓存 (会话数据)
- L3: 数据库 (持久化)
"""
import asyncio
import time
import json
import hashlib
from typing import Any, Optional, Dict, List, Callable, TypeVar
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import wraps
import pickle

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import JubenLogger
from utils.redis_client import get_redis_client
from utils.database_client import fetch_one, execute

logger = JubenLogger("multi_level_cache")


T = TypeVar('T')


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """更新访问时间和次数"""
        self.accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheConfig:
    """缓存配置"""
    # L1 内存缓存配置
    l1_max_size: int = 1000
    l1_ttl: float = 300.0  # 5分钟

    # L2 Redis缓存配置
    l2_ttl: float = 3600.0  # 1小时
    l2_prefix: str = "juben:cache:"

    # L3 数据库配置
    l3_enabled: bool = True
    l3_table: str = "cache_store"

    # 通用配置
    key_prefix: str = ""
    serialize: str = "json"  # json 或 pickle


class L1MemoryCache:
    """
    L1 内存缓存

    特点：
    - 最快的访问速度
    - 容量有限
    - 进程级别隔离
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        """
        初始化内存缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl

        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired():
            del self._cache[key]
            self._stats["expirations"] += 1
            self._stats["misses"] += 1
            return None

        # 更新访问信息
        entry.touch()
        # 移到末尾（LRU）
        self._cache.move_to_end(key)

        self._stats["hits"] += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存值"""
        # 如果已存在，先删除
        if key in self._cache:
            del self._cache[key]

        # 如果超过容量，淘汰最老的条目
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats["evictions"] += 1

        # 添加新条目
        ttl = ttl or self.default_ttl
        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            accessed_at=time.time(),
            ttl=ttl
        )

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 4)
        }


class L2RedisCache:
    """
    L2 Redis缓存

    特点：
    - 跨进程共享
    - 容量大
    - 支持过期时间
    - 持久化可选
    """

    def __init__(
        self,
        ttl: float = 3600.0,
        prefix: str = "juben:cache:"
    ):
        """
        初始化Redis缓存

        Args:
            ttl: 默认过期时间（秒）
            prefix: 键前缀
        """
        self.ttl = ttl
        self.prefix = prefix
        self._redis_client = None

        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }

    async def _get_client(self):
        """获取Redis客户端"""
        if self._redis_client is None:
            self._redis_client = await get_redis_client()
        return self._redis_client

    def _make_key(self, key: str) -> str:
        """生成Redis键"""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)
            value = await client.get(redis_key)

            if value is None:
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return pickle.loads(value)

        except Exception as e:
            logger.error(f"❌ Redis GET 错误: {e}")
            self._stats["errors"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存值"""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)
            serialized = pickle.dumps(value)
            ttl = ttl or self.ttl

            await client.set(redis_key, serialized, ex=int(ttl))

        except Exception as e:
            logger.error(f"❌ Redis SET 错误: {e}")
            self._stats["errors"] += 1

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            client = await self._get_client()
            redis_key = self._make_key(key)
            result = await client.delete(redis_key)
            return result > 0

        except Exception as e:
            logger.error(f"❌ Redis DELETE 错误: {e}")
            return False

    async def clear(self):
        """清空所有缓存（只删除带有前缀的键）"""
        try:
            client = await self._get_client()
            pattern = f"{self.prefix}*"
            keys = []

            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await client.delete(*keys)

        except Exception as e:
            logger.error(f"❌ Redis CLEAR 错误: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 4)
        }


class L3DatabaseCache:
    """
    L3 数据库缓存

    特点：
    - 持久化存储
    - 容量最大
    - 访问最慢
    - 用于冷数据
    """

    def __init__(self, enabled: bool = True, table: str = "cache_store"):
        """
        初始化数据库缓存

        Args:
            enabled: 是否启用
            table: 缓存表名
        """
        self.enabled = enabled
        self.table = table

        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.enabled:
            return None

        try:
            row = await fetch_one(f"SELECT value FROM {self.table} WHERE key = $1", key)

            if row:
                self._stats["hits"] += 1
                return pickle.loads(row["value"])

            self._stats["misses"] += 1
            return None

        except Exception as e:
            logger.error(f"❌ 数据库 GET 错误: {e}")
            self._stats["errors"] += 1
            return None

    async def set(self, key: str, value: Any):
        """设置缓存值"""
        if not self.enabled:
            return

        try:
            serialized = pickle.dumps(value)
            await execute(
                f\"\"\"
                INSERT INTO {self.table} (key, value, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                \"\"\",
                key,
                serialized,
            )

        except Exception as e:
            logger.error(f"❌ 数据库 SET 错误: {e}")
            self._stats["errors"] += 1

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.enabled:
            return False

        try:
            row = await fetch_one(f\"DELETE FROM {self.table} WHERE key = $1 RETURNING key\", key)
            return bool(row)

        except Exception as e:
            logger.error(f"❌ 数据库 DELETE 错误: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()


class MultiLevelCache:
    """
    多级缓存管理器

    缓存策略：
    1. 读取时：L1 -> L2 -> L3 -> 源数据
    2. 写入时：同时写入L1、L2、L3
    3. 淘汰时：使用LRU策略
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初始化多级缓存

        Args:
            config: 缓存配置
        """
        self.config = config or CacheConfig()

        # 初始化各级缓存
        self.l1 = L1MemoryCache(
            max_size=self.config.l1_max_size,
            default_ttl=self.config.l1_ttl
        )
        self.l2 = L2RedisCache(
            ttl=self.config.l2_ttl,
            prefix=self.config.l2_prefix
        )
        self.l3 = L3DatabaseCache(
            enabled=self.config.l3_enabled,
            table=self.config.l3_table
        )

        logger.info("✅ 多级缓存初始化完成")

    def _make_key(self, key: str) -> str:
        """生成缓存键"""
        if self.config.key_prefix:
            return f"{self.config.key_prefix}:{key}"
        return key

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（逐级查找）

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        cache_key = self._make_key(key)

        # L1: 内存缓存
        value = self.l1.get(cache_key)
        if value is not None:
            logger.debug(f"✅ L1 命中: {key}")
            return value

        # L2: Redis缓存
        value = await self.l2.get(cache_key)
        if value is not None:
            logger.debug(f"✅ L2 命中: {key}")
            # 回填L1
            self.l1.set(cache_key, value, self.config.l1_ttl)
            return value

        # L3: 数据库缓存
        value = await self.l3.get(cache_key)
        if value is not None:
            logger.debug(f"✅ L3 命中: {key}")
            # 回填L1和L2
            self.l1.set(cache_key, value, self.config.l1_ttl)
            await self.l2.set(cache_key, value, self.config.l2_ttl)
            return value

        logger.debug(f"❌ 未命中: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        l1_ttl: Optional[float] = None,
        l2_ttl: Optional[float] = None
    ):
        """
        设置缓存值（写入所有级别）

        Args:
            key: 缓存键
            value: 缓存值
            l1_ttl: L1过期时间
            l2_ttl: L2过期时间
        """
        cache_key = self._make_key(key)

        # 写入L1
        self.l1.set(cache_key, value, l1_ttl or self.config.l1_ttl)

        # 写入L2
        await self.l2.set(cache_key, value, l2_ttl or self.config.l2_ttl)

        # 写入L3
        await self.l3.set(cache_key, value)

    async def delete(self, key: str) -> bool:
        """
        删除缓存值（从所有级别删除）

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        cache_key = self._make_key(key)

        # 从L1删除
        self.l1.delete(cache_key)

        # 从L2删除
        await self.l2.delete(cache_key)

        # 从L3删除
        return await self.l3.delete(cache_key)

    async def clear(self):
        """清空所有缓存"""
        self.l1.clear()
        await self.l2.clear()
        # L3不清空，通常不需要

    async def get_stats(self) -> Dict[str, Any]:
        """获取所有级别的统计信息"""
        return {
            "l1": self.l1.get_stats(),
            "l2": await self.l2.get_stats(),
            "l3": await self.l3.get_stats()
        }

    async def cleanup(self):
        """清理过期缓存"""
        l1_cleaned = self.l1.cleanup_expired()
        logger.info(f"🧹 清理了 {l1_cleaned} 个L1过期缓存")


# 全局缓存实例
_global_cache: Optional[MultiLevelCache] = None


def get_cache(config: Optional[CacheConfig] = None) -> MultiLevelCache:
    """
    获取全局缓存实例

    Args:
        config: 缓存配置

    Returns:
        MultiLevelCache: 缓存实例
    """
    global _global_cache

    if _global_cache is None:
        if config is None:
            from utils.cache_policy import get_cache_config
            config = get_cache_config()
        _global_cache = MultiLevelCache(config)

    return _global_cache


# 缓存装饰器
def cached(
    key_func: Optional[Callable[..., str]] = None,
    l1_ttl: float = 300.0,
    l2_ttl: float = 3600.0
):
    """
    缓存装饰器

    用法:
    ```python
    @cached(l1_ttl=60, l2_ttl=300)
    async def expensive_function(param1, param2):
        return await compute_something(param1, param2)
    ```

    Args:
        key_func: 生成缓存键的函数
        l1_ttl: L1缓存时间
        l2_ttl: L2缓存时间
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            cache = get_cache()
            cached_value = await cache.get(cache_key)

            if cached_value is not None:
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 写入缓存
            await cache.set(cache_key, result, l1_ttl=l1_ttl, l2_ttl=l2_ttl)

            return result

        return wrapper
    return decorator


# 缓存键生成器
def generate_cache_key(*parts: str, **kwargs) -> str:
    """
    生成缓存键

    Args:
        *parts: 键的部分
        **kwargs: 额外参数

    Returns:
        str: 缓存键
    """
    key = ":".join(str(p) for p in parts)

    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        query_string = "&".join(f"{k}={v}" for k, v in sorted_kwargs)
        key = f"{key}?{query_string}"

    # 如果太长，使用哈希
    if len(key) > 200:
        key = hashlib.md5(key.encode()).hexdigest()

    return key


if __name__ == "__main__":
    # 测试代码
    async def test_multi_level_cache():
        """测试多级缓存"""
        cache = MultiLevelCache(
            CacheConfig(
                l1_max_size=100,
                l1_ttl=60.0,
                l2_ttl=300.0
            )
        )

        # 测试写入和读取
        await cache.set("test_key", {"data": "测试数据"})
        value = await cache.get("test_key")
        logger.info(f"读取缓存: {value}")

        # 测试统计信息
        stats = await cache.get_stats()
        logger.info("\n=== 缓存统计 ===")
        logger.info(json.dumps(stats, indent=2, ensure_ascii=False))

        # 测试清理
        await cache.cleanup()

    asyncio.run(test_multi_level_cache())

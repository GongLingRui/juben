"""
Token 黑名单管理器 - 带缓存优化
提供高效的 token 撤销检查功能
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Set
from collections import OrderedDict
from functools import lru_cache

from utils.logger import get_logger

logger = get_logger("TokenBlacklistManager")


class TokenBlacklistManager:
    """
    Token 黑名单管理器

    特性：
    - LRU 缓存最近检查的 token
    - 自动清理过期条目
    - 支持 Redis 后端（可选）
    - 内存回退机制
    """

    def __init__(self, cache_size: int = 10000, ttl_seconds: int = 300):
        """
        初始化黑名单管理器

        Args:
            cache_size: LRU 缓存大小
            ttl_seconds: 缓存条目过期时间（秒）
        """
        self._cache_size = cache_size
        self._ttl_seconds = ttl_seconds

        # LRU 缓存存储 (token -> (blacklisted, expiry_time))
        self._cache: OrderedDict[str, tuple] = OrderedDict()

        # 内存黑名单（作为回退）
        self._memory_blacklist: Set[str] = set()

        # Redis 客户端（可选）
        self._redis_client = None

        # 缓存统计
        self._hits = 0
        self._misses = 0

        logger.info(f"Token 黑名单管理器初始化: cache_size={cache_size}, ttl={ttl_seconds}s")

    async def initialize(self):
        """初始化管理器"""
        try:
            # 尝试连接 Redis
            from utils.redis_client import get_redis_client
            self._redis_client = await get_redis_client()
            if self._redis_client:
                logger.info("✅ Token 黑名单管理器使用 Redis 后端")
            else:
                logger.info("⚠️ Token 黑名单管理器使用内存后端")
        except Exception as e:
            logger.warning(f"⚠️ Redis 连接失败，使用内存后端: {e}")
            self._redis_client = None

    async def is_blacklisted(self, token: str) -> bool:
        """
        检查 token 是否在黑名单中（带缓存）

        Args:
            token: 要检查的 token

        Returns:
            bool: 如果在黑名单中返回 True
        """
        now = datetime.utcnow()

        # 首先检查本地缓存
        if token in self._cache:
            entry, expiry = self._cache[token]
            if now < expiry:
                # 缓存命中且未过期
                self._hits += 1
                self._cache.move_to_end(token)  # 更新为最近使用
                return entry
            else:
                # 缓存过期，移除
                del self._cache[token]

        # 缓存未命中，检查实际黑名单
        self._misses += 1

        # 检查 Redis
        if self._redis_client:
            try:
                key = f"blacklist:token:{token}"
                exists = await self._redis_client.exists(key)
                if exists:
                    # 缓存结果
                    self._add_to_cache(token, True, ttl=3600)  # Redis 中的数据长期有效
                    return True
            except Exception as e:
                logger.warning(f"⚠️ Redis 检查失败: {e}")

        # 检查内存黑名单
        if token in self._memory_blacklist:
            self._add_to_cache(token, True, ttl=3600)
            return True

        # 不在黑名单中，缓存结果（短期）
        self._add_to_cache(token, False, ttl=60)  # 未黑名单的 token 短期缓存
        return False

    def _add_to_cache(self, token: str, blacklisted: bool, ttl: int):
        """添加到缓存"""
        now = datetime.utcnow()
        expiry = now + timedelta(seconds=ttl)

        # LRU 淘汰
        if len(self._cache) >= self._cache_size:
            self._cache.popitem(last=False)  # 移除最旧的项

        self._cache[token] = (blacklisted, expiry)

    async def add_to_blacklist(self, token: str, ttl: Optional[int] = None):
        """
        将 token 添加到黑名单

        Args:
            token: 要添加的 token
            ttl: 过期时间（秒），None 表示使用 token 自身的过期时间
        """
        now = datetime.utcnow()

        # 添加到内存黑名单
        self._memory_blacklist.add(token)

        # 添加到 Redis
        if self._redis_client:
            try:
                key = f"blacklist:token:{token}"
                if ttl:
                    await self._redis_client.setex(key, ttl, "1")
                else:
                    # 如果没有指定 TTL，使用默认的 24 小时
                    await self._redis_client.setex(key, 86400, "1")
                logger.debug(f"✅ Token 已添加到 Redis 黑名单: {token[:20]}...")
            except Exception as e:
                logger.warning(f"⚠️ 添加到 Redis 黑名单失败: {e}")

        # 更新缓存
        cache_ttl = ttl if ttl else 3600
        self._add_to_cache(token, True, cache_ttl)

        logger.info(f"✅ Token 已添加到黑名单: {token[:20]}...")

    async def remove_from_blacklist(self, token: str):
        """
        从黑名单中移除 token

        Args:
            token: 要移除的 token
        """
        # 从内存黑名单移除
        self._memory_blacklist.discard(token)

        # 从 Redis 移除
        if self._redis_client:
            try:
                key = f"blacklist:token:{token}"
                await self._redis_client.delete(key)
                logger.debug(f"✅ Token 已从 Redis 黑名单移除: {token[:20]}...")
            except Exception as e:
                logger.warning(f"⚠️ 从 Redis 黑名单移除失败: {e}")

        # 从缓存移除
        if token in self._cache:
            del self._cache[token]

        logger.info(f"✅ Token 已从黑名单移除: {token[:20]}...")

    async def cleanup(self):
        """清理过期的缓存条目"""
        now = datetime.utcnow()
        expired_tokens = []

        for token, (_, expiry) in self._cache.items():
            if now >= expiry:
                expired_tokens.append(token)

        for token in expired_tokens:
            del self._cache[token]

        if expired_tokens:
            logger.debug(f"✅ 清理了 {len(expired_tokens)} 个过期缓存条目")

    async def clear_all(self):
        """清空所有黑名单数据"""
        self._cache.clear()
        self._memory_blacklist.clear()

        if self._redis_client:
            try:
                # 使用 SCAN 查找所有黑名单键
                pattern = "blacklist:token:*"
                keys = []
                async for key in self._redis_client.iscan(match=pattern):
                    keys.append(key)

                if keys:
                    await self._redis_client.delete(*keys)
                    logger.info(f"✅ 清空了 {len(keys)} 个 Redis 黑名单条目")
            except Exception as e:
                logger.warning(f"⚠️ 清空 Redis 黑名单失败: {e}")

        logger.info("✅ Token 黑名单已清空")

    def get_stats(self) -> dict:
        """获取统计信息"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "cache_size": len(self._cache),
            "memory_blacklist_size": len(self._memory_blacklist),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "backend": "redis" if self._redis_client else "memory"
        }

    async def start_cleanup_task(self, interval_seconds: int = 300):
        """启动定期清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self.cleanup()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"❌ 清理任务错误: {e}")

        # 创建后台任务
        task = asyncio.create_task(cleanup_loop())
        logger.info(f"✅ Token 黑名单清理任务已启动 (间隔: {interval_seconds}s)")
        return task


# 全局单例
_blacklist_manager: Optional[TokenBlacklistManager] = None


async def get_token_blacklist_manager() -> TokenBlacklistManager:
    """获取 Token 黑名单管理器单例"""
    global _blacklist_manager
    if _blacklist_manager is None:
        _blacklist_manager = TokenBlacklistManager()
        await _blacklist_manager.initialize()
    return _blacklist_manager

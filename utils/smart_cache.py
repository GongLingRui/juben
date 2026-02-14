"""
智能缓存系统 -  
提供智能缓存、缓存预热、缓存失效和缓存统计
"""
import asyncio
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pickle

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager
from .performance_monitor import get_performance_monitor


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频率
    TTL = "ttl"  # 生存时间
    SIZE = "size"  # 大小限制


class CacheLevel(Enum):
    """缓存级别"""
    MEMORY = "memory"  # 内存缓存
    REDIS = "redis"    # Redis缓存
    DISK = "disk"      # 磁盘缓存


@dataclass
class CacheItem:
    """缓存项"""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl: Optional[int] = None  # 生存时间（秒）
    size: int = 0
    level: CacheLevel = CacheLevel.MEMORY


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size: int = 0
    hit_rate: float = 0.0
    avg_access_time: float = 0.0


class SmartCache:
    """智能缓存系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_cache")
        
        # 缓存配置
        self.max_memory_size = 100 * 1024 * 1024  # 100MB
        self.max_redis_size = 500 * 1024 * 1024   # 500MB
        self.max_disk_size = 1024 * 1024 * 1024   # 1GB
        self.default_ttl = 3600  # 1小时
        self.cleanup_interval = 300  # 5分钟
        
        # 缓存存储
        self.memory_cache: Dict[str, CacheItem] = {}
        self.redis_cache = None
        self.disk_cache_path = "/tmp/juben_cache"
        
        # 缓存策略
        self.strategy = CacheStrategy.LRU
        self.levels = [CacheLevel.MEMORY, CacheLevel.REDIS, CacheLevel.DISK]
        
        # 统计信息
        self.stats = CacheStats()
        self.performance_monitor = get_performance_monitor()
        
        # 缓存预热
        self.warmup_functions: Dict[str, Callable] = {}
        
        # 缓存失效
        self.invalidation_patterns: List[str] = []
        
        self.logger.info("💾 智能缓存系统初始化完成")
    
    async def initialize(self):
        """初始化缓存系统"""
        try:
            # 初始化Redis连接
            connection_pool = get_connection_pool_manager()
            self.redis_cache = await connection_pool.get_redis_connection()
            
            # 创建磁盘缓存目录
            import os
            os.makedirs(self.disk_cache_path, exist_ok=True)
            
            # 启动清理任务
            asyncio.create_task(self._cleanup_task())
            
            self.logger.info("✅ 智能缓存系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化缓存系统失败: {e}")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        try:
            start_time = time.time()
            
            # 按级别查找缓存
            for level in self.levels:
                value = await self._get_from_level(key, level)
                if value is not None:
                    # 更新访问统计
                    await self._update_access_stats(key, level)
                    
                    access_time = time.time() - start_time
                    self.stats.hits += 1
                    self.stats.avg_access_time = (
                        (self.stats.avg_access_time * (self.stats.hits - 1) + access_time) / self.stats.hits
                    )
                    
                    return value
            
            # 缓存未命中
            self.stats.misses += 1
            return default
            
        except Exception as e:
            self.logger.error(f"❌ 获取缓存失败: {e}")
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        level: Optional[CacheLevel] = None
    ) -> bool:
        """设置缓存"""
        try:
            ttl = ttl or self.default_ttl
            level = level or self._select_cache_level(value)
            
            # 创建缓存项
            cache_item = CacheItem(
                key=key,
                value=value,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                ttl=ttl,
                size=self._calculate_size(value),
                level=level
            )
            
            # 存储到指定级别
            success = await self._set_to_level(key, cache_item, level)
            
            if success:
                # 更新统计
                self.stats.total_size += cache_item.size
                
                # 检查是否需要清理
                await self._check_and_cleanup()
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            success = True
            
            # 从所有级别删除
            for level in self.levels:
                if not await self._delete_from_level(key, level):
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 删除缓存失败: {e}")
            return False
    
    async def clear(self, level: Optional[CacheLevel] = None):
        """清空缓存"""
        try:
            if level:
                await self._clear_level(level)
            else:
                for level in self.levels:
                    await self._clear_level(level)
            
            # 重置统计
            self.stats = CacheStats()
            
            self.logger.info("✅ 缓存已清空")
            
        except Exception as e:
            self.logger.error(f"❌ 清空缓存失败: {e}")
    
    async def _get_from_level(self, key: str, level: CacheLevel) -> Any:
        """从指定级别获取缓存"""
        try:
            if level == CacheLevel.MEMORY:
                if key in self.memory_cache:
                    item = self.memory_cache[key]
                    # 检查TTL
                    if self._is_expired(item):
                        del self.memory_cache[key]
                        return None
                    return item.value
            
            elif level == CacheLevel.REDIS:
                if self.redis_cache:
                    value = await self.redis_cache.get(key)
                    if value:
                        return json.loads(value)
            
            elif level == CacheLevel.DISK:
                return await self._get_from_disk(key)
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 从{level.value}获取缓存失败: {e}")
            return None
    
    async def _set_to_level(self, key: str, item: CacheItem, level: CacheLevel) -> bool:
        """设置到指定级别"""
        try:
            if level == CacheLevel.MEMORY:
                self.memory_cache[key] = item
                return True
            
            elif level == CacheLevel.REDIS:
                if self.redis_cache:
                    value = json.dumps(item.value, ensure_ascii=False)
                    if item.ttl:
                        await self.redis_cache.setex(key, item.ttl, value)
                    else:
                        await self.redis_cache.set(key, value)
                    return True
            
            elif level == CacheLevel.DISK:
                return await self._set_to_disk(key, item)
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 设置到{level.value}失败: {e}")
            return False
    
    async def _delete_from_level(self, key: str, level: CacheLevel) -> bool:
        """从指定级别删除"""
        try:
            if level == CacheLevel.MEMORY:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    return True
            
            elif level == CacheLevel.REDIS:
                if self.redis_cache:
                    result = await self.redis_cache.delete(key)
                    return result > 0
            
            elif level == CacheLevel.DISK:
                return await self._delete_from_disk(key)
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 从{level.value}删除失败: {e}")
            return False
    
    async def _get_from_disk(self, key: str) -> Any:
        """从磁盘获取缓存"""
        try:
            import os
            file_path = os.path.join(self.disk_cache_path, f"{key}.cache")
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    item = pickle.load(f)
                
                # 检查TTL
                if self._is_expired(item):
                    os.remove(file_path)
                    return None
                
                return item.value
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 从磁盘获取缓存失败: {e}")
            return None
    
    async def _set_to_disk(self, key: str, item: CacheItem) -> bool:
        """设置到磁盘"""
        try:
            import os
            file_path = os.path.join(self.disk_cache_path, f"{key}.cache")
            
            with open(file_path, 'wb') as f:
                pickle.dump(item, f)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 设置到磁盘失败: {e}")
            return False
    
    async def _delete_from_disk(self, key: str) -> bool:
        """从磁盘删除"""
        try:
            import os
            file_path = os.path.join(self.disk_cache_path, f"{key}.cache")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ 从磁盘删除失败: {e}")
            return False
    
    def _select_cache_level(self, value: Any) -> CacheLevel:
        """选择缓存级别"""
        try:
            size = self._calculate_size(value)
            
            if size < 1024:  # 小于1KB，使用内存
                return CacheLevel.MEMORY
            elif size < 1024 * 1024:  # 小于1MB，使用Redis
                return CacheLevel.REDIS
            else:  # 大于1MB，使用磁盘
                return CacheLevel.DISK
                
        except Exception as e:
            self.logger.error(f"❌ 选择缓存级别失败: {e}")
            return CacheLevel.MEMORY
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float, bool)):
                return 8
            elif isinstance(value, (list, dict)):
                return len(str(value).encode('utf-8'))
            else:
                return len(pickle.dumps(value))
                
        except Exception as e:
            self.logger.error(f"❌ 计算大小失败: {e}")
            return 0
    
    def _is_expired(self, item: CacheItem) -> bool:
        """检查是否过期"""
        try:
            if item.ttl is None:
                return False
            
            return (datetime.now() - item.created_at).total_seconds() > item.ttl
            
        except Exception as e:
            self.logger.error(f"❌ 检查过期失败: {e}")
            return True
    
    async def _update_access_stats(self, key: str, level: CacheLevel):
        """更新访问统计"""
        try:
            if level == CacheLevel.MEMORY and key in self.memory_cache:
                item = self.memory_cache[key]
                item.accessed_at = datetime.now()
                item.access_count += 1
            
        except Exception as e:
            self.logger.error(f"❌ 更新访问统计失败: {e}")
    
    async def _check_and_cleanup(self):
        """检查并清理缓存"""
        try:
            # 检查内存缓存大小
            if self._get_memory_size() > self.max_memory_size:
                await self._cleanup_memory()
            
            # 检查Redis缓存大小
            if self.redis_cache:
                redis_size = await self._get_redis_size()
                if redis_size > self.max_redis_size:
                    await self._cleanup_redis()
            
            # 检查磁盘缓存大小
            disk_size = await self._get_disk_size()
            if disk_size > self.max_disk_size:
                await self._cleanup_disk()
            
        except Exception as e:
            self.logger.error(f"❌ 检查清理失败: {e}")
    
    def _get_memory_size(self) -> int:
        """获取内存缓存大小"""
        try:
            return sum(item.size for item in self.memory_cache.values())
        except Exception as e:
            self.logger.error(f"❌ 获取内存大小失败: {e}")
            return 0
    
    async def _get_redis_size(self) -> int:
        """获取Redis缓存大小"""
        try:
            if not self.redis_cache:
                return 0
            
            info = await self.redis_cache.info('memory')
            return info.get('used_memory', 0)
            
        except Exception as e:
            self.logger.error(f"❌ 获取Redis大小失败: {e}")
            return 0
    
    async def _get_disk_size(self) -> int:
        """获取磁盘缓存大小"""
        try:
            import os
            total_size = 0
            
            for filename in os.listdir(self.disk_cache_path):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.disk_cache_path, filename)
                    total_size += os.path.getsize(file_path)
            
            return total_size
            
        except Exception as e:
            self.logger.error(f"❌ 获取磁盘大小失败: {e}")
            return 0
    
    async def _cleanup_memory(self):
        """清理内存缓存"""
        try:
            if self.strategy == CacheStrategy.LRU:
                # 按访问时间排序，删除最久未访问的
                sorted_items = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1].accessed_at
                )
            elif self.strategy == CacheStrategy.LFU:
                # 按访问次数排序，删除访问次数最少的
                sorted_items = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1].access_count
                )
            else:
                # 默认按创建时间排序
                sorted_items = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1].created_at
                )
            
            # 删除一半的缓存项
            items_to_delete = len(sorted_items) // 2
            for i in range(items_to_delete):
                key, item = sorted_items[i]
                del self.memory_cache[key]
                self.stats.evictions += 1
                self.stats.total_size -= item.size
            
            self.logger.info(f"🧹 内存缓存清理完成，删除了 {items_to_delete} 项")
            
        except Exception as e:
            self.logger.error(f"❌ 清理内存缓存失败: {e}")
    
    async def _cleanup_redis(self):
        """清理Redis缓存"""
        try:
            if not self.redis_cache:
                return
            
            # 获取所有键
            keys = await self.redis_cache.keys('*')
            
            if len(keys) > 1000:  # 如果键太多，随机删除一些
                import random
                keys_to_delete = random.sample(keys, len(keys) // 2)
                await self.redis_cache.delete(*keys_to_delete)
                self.stats.evictions += len(keys_to_delete)
            
            self.logger.info(f"🧹 Redis缓存清理完成")
            
        except Exception as e:
            self.logger.error(f"❌ 清理Redis缓存失败: {e}")
    
    async def _cleanup_disk(self):
        """清理磁盘缓存"""
        try:
            import os
            import time
            
            # 获取所有缓存文件
            cache_files = []
            for filename in os.listdir(self.disk_cache_path):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.disk_cache_path, filename)
                    stat = os.stat(file_path)
                    cache_files.append((file_path, stat.st_mtime))
            
            # 按修改时间排序，删除最旧的
            cache_files.sort(key=lambda x: x[1])
            
            # 删除一半的文件
            files_to_delete = len(cache_files) // 2
            for i in range(files_to_delete):
                file_path, _ = cache_files[i]
                os.remove(file_path)
                self.stats.evictions += 1
            
            self.logger.info(f"🧹 磁盘缓存清理完成，删除了 {files_to_delete} 个文件")
            
        except Exception as e:
            self.logger.error(f"❌ 清理磁盘缓存失败: {e}")
    
    async def _cleanup_task(self):
        """清理任务"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                
                # 清理过期的缓存项
                await self._cleanup_expired()
                
                # 更新统计信息
                self._update_stats()
                
        except Exception as e:
            self.logger.error(f"❌ 清理任务失败: {e}")
    
    async def _cleanup_expired(self):
        """清理过期缓存"""
        try:
            # 清理内存缓存
            expired_keys = []
            for key, item in self.memory_cache.items():
                if self._is_expired(item):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
                self.stats.evictions += 1
            
            # 清理磁盘缓存
            import os
            for filename in os.listdir(self.disk_cache_path):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.disk_cache_path, filename)
                    try:
                        with open(file_path, 'rb') as f:
                            item = pickle.load(f)
                        
                        if self._is_expired(item):
                            os.remove(file_path)
                            self.stats.evictions += 1
                    except:
                        # 如果文件损坏，直接删除
                        os.remove(file_path)
                        self.stats.evictions += 1
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期缓存失败: {e}")
    
    def _update_stats(self):
        """更新统计信息"""
        try:
            total_requests = self.stats.hits + self.stats.misses
            self.stats.hit_rate = (self.stats.hits / total_requests * 100) if total_requests > 0 else 0
            
        except Exception as e:
            self.logger.error(f"❌ 更新统计失败: {e}")
    
    async def warmup(self, warmup_key: str, warmup_func: Callable, *args, **kwargs):
        """缓存预热"""
        try:
            # 检查是否已经预热
            if await self.get(warmup_key) is not None:
                return
            
            # 执行预热函数
            result = await warmup_func(*args, **kwargs)
            
            # 存储结果
            await self.set(warmup_key, result, ttl=3600)  # 1小时
            
            self.logger.info(f"🔥 缓存预热完成: {warmup_key}")
            
        except Exception as e:
            self.logger.error(f"❌ 缓存预热失败: {e}")
    
    async def invalidate_pattern(self, pattern: str):
        """按模式失效缓存"""
        try:
            import fnmatch
            
            # 内存缓存
            keys_to_delete = []
            for key in self.memory_cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.memory_cache[key]
                self.stats.evictions += 1
            
            # Redis缓存
            if self.redis_cache:
                keys = await self.redis_cache.keys(pattern)
                if keys:
                    await self.redis_cache.delete(*keys)
                    self.stats.evictions += len(keys)
            
            # 磁盘缓存
            import os
            for filename in os.listdir(self.disk_cache_path):
                if fnmatch.fnmatch(filename, pattern):
                    file_path = os.path.join(self.disk_cache_path, filename)
                    os.remove(file_path)
                    self.stats.evictions += 1
            
            self.logger.info(f"🗑️ 缓存失效完成: {pattern}")
            
        except Exception as e:
            self.logger.error(f"❌ 缓存失效失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            return {
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'evictions': self.stats.evictions,
                'total_size': self.stats.total_size,
                'hit_rate': self.stats.hit_rate,
                'avg_access_time': self.stats.avg_access_time,
                'memory_size': self._get_memory_size(),
                'memory_items': len(self.memory_cache),
                'strategy': self.strategy.value,
                'levels': [level.value for level in self.levels]
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取缓存统计失败: {e}")
            return {'error': str(e)}


# 全局智能缓存实例
smart_cache = SmartCache()


def get_smart_cache() -> SmartCache:
    """获取智能缓存实例"""
    return smart_cache

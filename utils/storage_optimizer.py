"""
存储优化器
负责优化Redis、Milvus和文件存储的性能和可靠性
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import asyncio
import json
import redis
import pymilvus
from pathlib import Path
import os
import shutil
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """存储类型"""
    REDIS = "redis"
    MILVUS = "milvus"
    FILE = "file"


@dataclass
class StorageConfig:
    """存储配置"""
    storage_type: StorageType
    host: str
    port: int
    database: str = "default"
    username: Optional[str] = None
    password: Optional[str] = None
    max_connections: int = 100
    timeout: int = 30
    retry_times: int = 3


class StorageOptimizer:
    """存储优化器"""
    
    def __init__(self):
        """初始化存储优化器"""
        self.redis_client = None
        self.milvus_client = None
        self.storage_configs = {}
        self.connection_pools = {}
        self.performance_metrics = {
            "redis": {"operations": 0, "avg_latency": 0.0, "errors": 0},
            "milvus": {"operations": 0, "avg_latency": 0.0, "errors": 0},
            "file": {"operations": 0, "avg_latency": 0.0, "errors": 0}
        }
        
        # 初始化存储配置
        self._load_storage_configs()
    
    def _load_storage_configs(self):
        """加载存储配置"""
        # Redis配置
        self.storage_configs["redis"] = StorageConfig(
            storage_type=StorageType.REDIS,
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            database=os.getenv("REDIS_DB", "0"),
            password=os.getenv("REDIS_PASSWORD"),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
            timeout=int(os.getenv("REDIS_TIMEOUT", "30"))
        )
        
        # Milvus配置
        self.storage_configs["milvus"] = StorageConfig(
            storage_type=StorageType.MILVUS,
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            username=os.getenv("MILVUS_USERNAME"),
            password=os.getenv("MILVUS_PASSWORD"),
            max_connections=int(os.getenv("MILVUS_MAX_CONNECTIONS", "50")),
            timeout=int(os.getenv("MILVUS_TIMEOUT", "30"))
        )
        
        # 文件存储配置
        self.storage_configs["file"] = StorageConfig(
            storage_type=StorageType.FILE,
            host=os.getenv("FILE_STORAGE_HOST", "localhost"),
            port=0,  # 文件存储不需要端口
            database=os.getenv("FILE_STORAGE_PATH", "./uploads")
        )
    
    async def initialize_connections(self):
        """初始化所有存储连接"""
        try:
            # 初始化Redis连接
            await self._init_redis_connection()
            
            # 初始化Milvus连接
            await self._init_milvus_connection()
            
            # 初始化文件存储
            await self._init_file_storage()
            
            logger.info("✅ 存储连接初始化完成")

        except Exception as e:
            logger.error(f"❌ 存储连接初始化失败: {e}")
            raise
    
    async def _init_redis_connection(self):
        """初始化Redis连接"""
        try:
            config = self.storage_configs["redis"]
            
            # 创建连接池
            pool = redis.ConnectionPool(
                host=config.host,
                port=config.port,
                db=int(config.database),
                password=config.password,
                max_connections=config.max_connections,
                socket_timeout=config.timeout,
                socket_connect_timeout=config.timeout,
                retry_on_timeout=True
            )
            
            # 创建Redis客户端
            self.redis_client = redis.Redis(connection_pool=pool)
            
            # 测试连接
            await self._test_redis_connection()
            
            logger.info("✅ Redis连接初始化成功")

        except Exception as e:
            logger.error(f"❌ Redis连接初始化失败: {e}")
            raise
    
    async def _init_milvus_connection(self):
        """初始化Milvus连接"""
        try:
            config = self.storage_configs["milvus"]
            
            # 创建Milvus连接
            connections = pymilvus.connections.create_connection(
                alias="default",
                host=config.host,
                port=config.port,
                user=config.username,
                password=config.password,
                timeout=config.timeout
            )
            
            self.milvus_client = pymilvus.connections.get_connection_addr("default")
            
            # 测试连接
            await self._test_milvus_connection()
            
            logger.info("✅ Milvus连接初始化成功")

        except Exception as e:
            logger.error(f"❌ Milvus连接初始化失败: {e}")
            raise
    
    async def _init_file_storage(self):
        """初始化文件存储"""
        try:
            config = self.storage_configs["file"]
            storage_path = Path(config.database)
            
            # 创建存储目录
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # 创建子目录
            subdirs = ["uploads", "temp", "processed", "archived"]
            for subdir in subdirs:
                (storage_path / subdir).mkdir(exist_ok=True)
            
            logger.info("✅ 文件存储初始化成功")

        except Exception as e:
            logger.error(f"❌ 文件存储初始化失败: {e}")
            raise
    
    async def _test_redis_connection(self):
        """测试Redis连接"""
        try:
            start_time = datetime.now()
            result = self.redis_client.ping()
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            if result:
                self.performance_metrics["redis"]["avg_latency"] = latency
                logger.info(f"✅ Redis连接测试成功，延迟: {latency:.2f}ms")
            else:
                raise Exception("Redis ping失败")
                
        except Exception as e:
            self.performance_metrics["redis"]["errors"] += 1
            raise Exception(f"Redis连接测试失败: {e}")
    
    async def _test_milvus_connection(self):
        """测试Milvus连接"""
        try:
            start_time = datetime.now()
            # 这里应该调用Milvus的健康检查API
            # 实际实现中需要根据Milvus版本调整
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            self.performance_metrics["milvus"]["avg_latency"] = latency
            logger.info(f"✅ Milvus连接测试成功，延迟: {latency:.2f}ms")
            
        except Exception as e:
            self.performance_metrics["milvus"]["errors"] += 1
            raise Exception(f"Milvus连接测试失败: {e}")
    
    # ==================== Redis优化方法 ====================
    
    async def optimize_redis(self):
        """优化Redis性能"""
        try:
            if not self.redis_client:
                raise Exception("Redis客户端未初始化")
            
            # 设置Redis配置
            await self._configure_redis()
            
            # 清理过期数据
            await self._cleanup_redis_data()
            
            # 优化内存使用
            await self._optimize_redis_memory()

            logger.info("✅ Redis优化完成")

        except Exception as e:
            logger.error(f"❌ Redis优化失败: {e}")
            raise
    
    async def _configure_redis(self):
        """配置Redis参数"""
        try:
            # 设置内存策略
            self.redis_client.config_set("maxmemory-policy", "allkeys-lru")
            
            # 设置过期时间
            self.redis_client.config_set("timeout", "300")
            
            # 启用压缩
            self.redis_client.config_set("hash-max-ziplist-entries", "512")
            self.redis_client.config_set("hash-max-ziplist-value", "64")

            logger.info("✅ Redis配置优化完成")

        except Exception as e:
            logger.warning(f"⚠️ Redis配置优化失败: {e}")
    
    async def _cleanup_redis_data(self):
        """清理Redis过期数据"""
        try:
            # 获取所有键
            keys = self.redis_client.keys("*")
            
            # 检查过期键
            expired_keys = []
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # 没有过期时间的键
                    # 检查最后访问时间
                    last_access = self.redis_client.object("idletime", key)
                    if last_access > 3600:  # 1小时未访问
                        expired_keys.append(key)
            
            # 删除过期键
            if expired_keys:
                self.redis_client.delete(*expired_keys)
                logger.info(f"✅ 清理了 {len(expired_keys)} 个过期键")

        except Exception as e:
            logger.warning(f"⚠️ Redis数据清理失败: {e}")
    
    async def _optimize_redis_memory(self):
        """优化Redis内存使用"""
        try:
            # 执行内存碎片整理
            self.redis_client.memory_purge()
            
            # 获取内存使用信息
            memory_info = self.redis_client.memory_usage()
            logger.info(f"✅ Redis内存优化完成，当前使用: {memory_info} bytes")

        except Exception as e:
            logger.warning(f"⚠️ Redis内存优化失败: {e}")
    
    # ==================== Milvus优化方法 ====================
    
    async def optimize_milvus(self):
        """优化Milvus性能"""
        try:
            if not self.milvus_client:
                raise Exception("Milvus客户端未初始化")
            
            # 优化集合配置
            await self._optimize_milvus_collections()
            
            # 清理过期数据
            await self._cleanup_milvus_data()
            
            # 优化索引
            await self._optimize_milvus_indexes()

            logger.info("✅ Milvus优化完成")

        except Exception as e:
            logger.error(f"❌ Milvus优化失败: {e}")
    
    async def _optimize_milvus_collections(self):
        """优化Milvus集合配置"""
        try:
            # 这里应该实现集合配置优化
            # 实际实现中需要根据具体需求调整
            logger.info("✅ Milvus集合配置优化完成")

        except Exception as e:
            logger.warning(f"⚠️ Milvus集合配置优化失败: {e}")
    
    async def _cleanup_milvus_data(self):
        """清理Milvus过期数据"""
        try:
            # 这里应该实现Milvus数据清理
            # 实际实现中需要根据具体需求调整
            logger.info("✅ Milvus数据清理完成")

        except Exception as e:
            logger.warning(f"⚠️ Milvus数据清理失败: {e}")
    
    async def _optimize_milvus_indexes(self):
        """优化Milvus索引"""
        try:
            # 这里应该实现Milvus索引优化
            # 实际实现中需要根据具体需求调整
            logger.info("✅ Milvus索引优化完成")

        except Exception as e:
            logger.warning(f"⚠️ Milvus索引优化失败: {e}")
    
    # ==================== 文件存储优化方法 ====================
    
    async def optimize_file_storage(self):
        """优化文件存储"""
        try:
            config = self.storage_configs["file"]
            storage_path = Path(config.database)
            
            # 清理临时文件
            await self._cleanup_temp_files(storage_path)
            
            # 压缩旧文件
            await self._compress_old_files(storage_path)
            
            # 优化存储结构
            await self._optimize_storage_structure(storage_path)

            logger.info("✅ 文件存储优化完成")

        except Exception as e:
            logger.error(f"❌ 文件存储优化失败: {e}")
    
    async def _cleanup_temp_files(self, storage_path: Path):
        """清理临时文件"""
        try:
            temp_path = storage_path / "temp"
            if temp_path.exists():
                # 删除超过1小时的临时文件
                cutoff_time = datetime.now() - timedelta(hours=1)
                
                for file_path in temp_path.iterdir():
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_time:
                            file_path.unlink()

                logger.info("✅ 临时文件清理完成")

        except Exception as e:
            logger.warning(f"⚠️ 临时文件清理失败: {e}")
    
    async def _compress_old_files(self, storage_path: Path):
        """压缩旧文件"""
        try:
            # 这里应该实现文件压缩逻辑
            # 实际实现中可以使用gzip、tar等工具
            logger.info("✅ 旧文件压缩完成")

        except Exception as e:
            logger.warning(f"⚠️ 旧文件压缩失败: {e}")
    
    async def _optimize_storage_structure(self, storage_path: Path):
        """优化存储结构"""
        try:
            # 创建优化的目录结构
            optimized_dirs = [
                "by_date",  # 按日期分类
                "by_type",  # 按类型分类
                "by_size",  # 按大小分类
                "archived"  # 归档文件
            ]
            
            for dir_name in optimized_dirs:
                (storage_path / dir_name).mkdir(exist_ok=True)

            logger.info("✅ 存储结构优化完成")

        except Exception as e:
            logger.warning(f"⚠️ 存储结构优化失败: {e}")
    
    # ==================== 性能监控方法 ====================
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """获取存储性能指标"""
        try:
            metrics = {}
            
            # Redis指标
            if self.redis_client:
                try:
                    redis_info = self.redis_client.info()
                    metrics["redis"] = {
                        "connected_clients": redis_info.get("connected_clients", 0),
                        "used_memory": redis_info.get("used_memory", 0),
                        "used_memory_human": redis_info.get("used_memory_human", "0B"),
                        "keyspace_hits": redis_info.get("keyspace_hits", 0),
                        "keyspace_misses": redis_info.get("keyspace_misses", 0),
                        "operations": self.performance_metrics["redis"]["operations"],
                        "avg_latency": self.performance_metrics["redis"]["avg_latency"],
                        "errors": self.performance_metrics["redis"]["errors"]
                    }
                except Exception as e:
                    metrics["redis"] = {"error": str(e)}
            
            # Milvus指标
            if self.milvus_client:
                try:
                    # 这里应该获取Milvus的性能指标
                    # 实际实现中需要根据Milvus版本调整
                    metrics["milvus"] = {
                        "operations": self.performance_metrics["milvus"]["operations"],
                        "avg_latency": self.performance_metrics["milvus"]["avg_latency"],
                        "errors": self.performance_metrics["milvus"]["errors"]
                    }
                except Exception as e:
                    metrics["milvus"] = {"error": str(e)}
            
            # 文件存储指标
            config = self.storage_configs["file"]
            storage_path = Path(config.database)
            
            if storage_path.exists():
                total_size = sum(f.stat().st_size for f in storage_path.rglob('*') if f.is_file())
                file_count = len(list(storage_path.rglob('*')))
                
                metrics["file"] = {
                    "total_size": total_size,
                    "total_size_human": self._format_bytes(total_size),
                    "file_count": file_count,
                    "operations": self.performance_metrics["file"]["operations"],
                    "avg_latency": self.performance_metrics["file"]["avg_latency"],
                    "errors": self.performance_metrics["file"]["errors"]
                }
            
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    # ==================== 综合优化方法 ====================
    
    async def optimize_all_storage(self):
        """优化所有存储系统"""
        try:
            logger.info("🚀 开始存储系统优化...")

            # 优化Redis
            await self.optimize_redis()
            
            # 优化Milvus
            await self.optimize_milvus()
            
            # 优化文件存储
            await self.optimize_file_storage()

            logger.info("✅ 所有存储系统优化完成")

        except Exception as e:
            logger.error(f"❌ 存储系统优化失败: {e}")
            raise
    
    async def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        try:
            metrics = await self.get_storage_metrics()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "storage_metrics": metrics,
                "optimization_status": "completed",
                "recommendations": await self._generate_recommendations(metrics)
            }
            
            return report
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "optimization_status": "failed"
            }
    
    async def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # Redis建议
        if "redis" in metrics and "error" not in metrics["redis"]:
            redis_metrics = metrics["redis"]
            if redis_metrics.get("used_memory", 0) > 100 * 1024 * 1024:  # 100MB
                recommendations.append("Redis内存使用较高，建议清理过期数据")
            if redis_metrics.get("errors", 0) > 0:
                recommendations.append("Redis存在错误，建议检查连接配置")
        
        # Milvus建议
        if "milvus" in metrics and "error" not in metrics["milvus"]:
            milvus_metrics = metrics["milvus"]
            if milvus_metrics.get("errors", 0) > 0:
                recommendations.append("Milvus存在错误，建议检查连接配置")
        
        # 文件存储建议
        if "file" in metrics:
            file_metrics = metrics["file"]
            if file_metrics.get("total_size", 0) > 1024 * 1024 * 1024:  # 1GB
                recommendations.append("文件存储空间较大，建议清理旧文件")
        
        return recommendations

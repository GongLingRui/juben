"""
Juben项目数据库客户端管理
基于PostgreSQL的三层存储架构：内存 -> Redis -> PostgreSQL
"""
import os
import asyncio
from typing import Optional, Dict, Any
import asyncpg
from utils.logger import JubenLogger

# 全局PostgreSQL连接池
_pg_pool: Optional[asyncpg.Pool] = None

logger = JubenLogger("database_client")


def _get_required_env(var_name: str) -> str:
    """获取必需的环境变量"""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


def _build_dsn(host_override: Optional[str] = None) -> str:
    host = host_override or _get_required_env("POSTGRES_HOST")
    port = _get_required_env("POSTGRES_PORT")
    db = _get_required_env("POSTGRES_DB")
    user = _get_required_env("POSTGRES_USER")
    password = _get_required_env("POSTGRES_PASSWORD")
    sslmode = os.getenv("POSTGRES_SSLMODE", "disable")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}?sslmode={sslmode}"


async def get_postgres_pool() -> asyncpg.Pool:
    """获取PostgreSQL连接池"""
    global _pg_pool
    if _pg_pool is None:
        min_size = int(os.getenv("POSTGRES_POOL_MIN", "1"))
        max_size = int(os.getenv("POSTGRES_POOL_MAX", "10"))
        dsn = _build_dsn()
        try:
            _pg_pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size)
            logger.info("✅ PostgreSQL连接池初始化成功")
        except Exception as e:
            configured_host = os.getenv("POSTGRES_HOST")
            if configured_host == "postgres":
                logger.warning(f"⚠️ PostgreSQL主机 postgres 不可达，尝试回退 localhost: {e}")
                fallback_dsn = _build_dsn(host_override="localhost")
                _pg_pool = await asyncpg.create_pool(dsn=fallback_dsn, min_size=min_size, max_size=max_size)
                logger.info("✅ PostgreSQL已回退连接到 localhost")
            else:
                raise
    return _pg_pool


async def execute(sql: str, *args) -> str:
    """执行SQL（无返回行）"""
    pool = await get_postgres_pool()
    async with pool.acquire() as conn:
        return await conn.execute(sql, *args)


async def fetch_one(sql: str, *args) -> Optional[Dict[str, Any]]:
    """查询单行"""
    pool = await get_postgres_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *args)
        return dict(row) if row else None


async def fetch_all(sql: str, *args) -> list:
    """查询多行"""
    pool = await get_postgres_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)
        return [dict(r) for r in rows]


async def test_connection() -> bool:
    """测试数据库连接"""
    try:
        row = await fetch_one("SELECT 1 AS ok")
        if row and row.get("ok") == 1:
            logger.info("✅ PostgreSQL连接正常")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {e}")
        return False


class DatabaseErrorHandler:
    """数据库错误处理器"""

    def __init__(self, component_name: str):
        self.logger = JubenLogger(f"database_error_handler_{component_name}")
        self.component_name = component_name
        self.max_retries = 3
        self.retry_delay = 1.0

    async def with_retry(self, operation, operation_name: str = "数据库操作", *args, **kwargs):
        """带重试的数据库操作"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.logger.warning(f"⚠️ {operation_name}失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        self.logger.error(f"❌ {operation_name}最终失败: {last_exception}")
        raise last_exception

    def handle_error(self, error: Exception, operation_name: str, context: Dict[str, Any] = None):
        """处理数据库错误"""
        self.logger.error(f"❌ {self.component_name} - {operation_name}失败: {error}")
        if context:
            self.logger.error(f"   上下文: {context}")
        raise error

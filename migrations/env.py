"""
Alembic 环境配置
用于数据库迁移管理
"""
import asyncio
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 添加项目根目录到 sys.path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入配置和模型
from utils.logger import get_logger

logger = get_logger("Alembic")

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = None


def get_database_url():
    """获取数据库 URL

    优先级: DATABASE_URL > POSTGRES_URL > 从环境变量构建 > 默认值
    """
    import os

    # 优先使用 DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # 其次使用 POSTGRES_URL
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url:
        return postgres_url

    # 从环境变量构建
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "juben")
    postgres_user = os.getenv("POSTGRES_USER", "juben")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "juben123")
    postgres_sslmode = os.getenv("POSTGRES_SSLMODE", "disable")

    return (
        f"postgresql://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}?sslmode={postgres_sslmode}"
    )


def run_migrations_offline() -> None:
    """
    运行离线模式的迁移

    在此模式下，无需数据库连接即可生成 SQL 脚本。
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    执行迁移

    Args:
        connection: 数据库连接
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    运行异步模式的迁移

    使用异步数据库连接执行迁移。
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        url=get_database_url(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    运行在线模式的迁移

    在此模式下，需要数据库连接来执行迁移。
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

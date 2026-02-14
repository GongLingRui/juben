"""
图数据库配置文件
Graph Database Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class GraphDBSettings(BaseSettings):
    """图数据库配置"""

    # Neo4j 连接配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    # 连接池配置
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50
    NEO4J_MAX_CONNECTION_LIFETIME: int = 3600  # 秒
    NEO4J_CONNECTION_ACQUISITION_TIMEOUT: int = 60  # 秒
    NEO4J_MAX_TRANSACTION_RETRY_TIME: int = 30  # 秒

    # 查询配置
    NEO4J_QUERY_TIMEOUT: int = 30  # 秒
    NEO4J_MAX_RESULTS: int = 1000

    # 缓存配置
    NEO4J_ENABLE_CACHE: bool = True
    NEO4J_CACHE_TTL: int = 300  # 秒

    # 开发模式
    NEO4J_DEV_MODE: bool = False

    # API 配置（用于图数据库相关功能）
    scope_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量字段


# 全局配置实例
graph_settings = GraphDBSettings()

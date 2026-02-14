"""
核心 API 路由模块

包含主要的 API 路由和数据模式定义
"""
from .api_routes_modular import router as core_router
from .schemas import *

__all__ = [
    'core_router',
    'BaseResponse',
    'ErrorResponse',
    'ChatRequest',
    'ChatResponse',
    'StreamEvent',
    'EventType',
    'AgentInfo',
    'AgentListResponse',
    'HealthResponse',
    'StatsResponse',
]

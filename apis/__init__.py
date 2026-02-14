"""
APIs 模块

包含所有的 API 路由和相关的数据模式定义
"""

# 核心模块
from .core import (
    core_router,
    BaseResponse,
    ErrorResponse,
    ChatRequest,
    ChatResponse,
    StreamEvent,
    EventType,
    AgentInfo,
    AgentListResponse,
    HealthResponse,
    StatsResponse,
)

# 功能模块
from .drama_analysis import drama_analysis_router
from .novel_screening import novel_screening_router
from .agent_outputs import agent_outputs_router
# from .enhanced import enhanced_router  # 暂时注释，因为 enhanced 模块定义的是 app 而不是 router

__all__ = [
    # 核心路由和数据模式
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
    
    # 功能路由
    'drama_analysis_router',
    'novel_screening_router',
    'agent_outputs_router',
    # 'enhanced_router',  # 暂时注释
]

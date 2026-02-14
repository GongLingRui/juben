"""
智能体输出 API 模块

包含智能体输出存储相关的 API 路由
"""

from .api_routes_agent_outputs import router as agent_outputs_router

__all__ = [
    'agent_outputs_router',
]

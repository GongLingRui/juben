"""
戏剧分析 API 模块

包含戏剧分析相关的 API 路由
"""

from .api_routes_drama_analysis import router as drama_analysis_router

__all__ = [
    'drama_analysis_router',
]

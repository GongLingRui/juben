"""
小说初筛 API 模块

包含小说初筛评估相关的 API 路由
"""

from .api_routes_novel_screening import router as novel_screening_router

__all__ = [
    'novel_screening_router',
]

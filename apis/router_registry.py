"""
API 路由注册器

统一管理所有 API 路由的注册和配置
"""

from fastapi import APIRouter
from .core import core_router
from .drama_analysis import drama_analysis_router
from .novel_screening import novel_screening_router
from .agent_outputs import agent_outputs_router
from .enhanced import enhanced_router


def register_all_routes() -> APIRouter:
    """
    注册所有 API 路由
    
    Returns:
        APIRouter: 包含所有路由的主路由器
    """
    # 创建主路由器
    main_router = APIRouter()
    
    # 注册各个功能模块的路由
    main_router.include_router(core_router)
    main_router.include_router(drama_analysis_router, prefix="/drama-analysis", tags=["戏剧分析"])
    main_router.include_router(novel_screening_router, prefix="/novel-screening", tags=["小说初筛"])
    main_router.include_router(agent_outputs_router, prefix="/agent-outputs", tags=["智能体输出"])
    main_router.include_router(enhanced_router, prefix="/enhanced", tags=["增强功能"])
    
    return main_router


# 创建全局路由器实例
api_router = register_all_routes()

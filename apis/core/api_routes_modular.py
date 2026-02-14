"""
核心 API 路由 - 模块化入口
将大型 api_routes.py 拆分为功能子模块

说明：
- 新的模块化路由按功能分组
- legacy_routes 包含原始 api_routes.py 的所有端点以确保向后兼容
- 可以逐步将 legacy_routes 中的端点迁移到各自的功能模块
"""
from fastapi import APIRouter
from .chat_routes import router as chat_router
from .agent_routes import router as agent_router
# note_router removed - conflicts with apis/notes/api_routes_notes.py which handles notes endpoints
from .workflow_routes import router as workflow_router
from .health_routes import router as health_router
from .legacy_routes import router as legacy_router

# 创建主路由器
router = APIRouter(prefix="/juben", tags=["竖屏短剧策划助手"])

# 注册功能子路由（新架构）
router.include_router(chat_router)
router.include_router(agent_router)
# note_router removed - conflicts with apis/notes/api_routes_notes.py which handles notes endpoints
router.include_router(workflow_router)
router.include_router(health_router)

# 注册遗留路由（向后兼容，包含原始 api_routes.py 的所有端点）
router.include_router(legacy_router)

# 导出
__all__ = ["router"]

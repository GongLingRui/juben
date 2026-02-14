"""
增强的API路由
支持流式输出、实时监控、错误处理和性能优化

注意：此模块依赖核心组件，如果导入失败应该快速失败而不是使用模拟类
"""
import os
import traceback
import sys
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
import json
import uuid
from datetime import datetime
import time
import re

# 严格导入核心组件 - 导入失败则启动失败
try:
    from agents.juben_concierge import JubenConcierge
    from agents.juben_orchestrator import JubenOrchestrator
    from utils.monitoring_system import MonitoringSystem
    from utils.error_handler import JubenErrorHandler, ErrorType
    from utils.workflow_manager import WorkflowManager
    from utils.agent_registry import AgentRegistry
except ImportError as e:
    logger.error(f"❌ 导入失败: {e}")
    logger.info("请确保所有依赖模块已正确安装和配置")
    sys.exit(1)


# 创建FastAPI应用
app = FastAPI(
    title="Juben竖屏短剧策划助手API",
    description="专业的竖屏短剧策划和创作助手",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加中间件 - 安全的 CORS 配置
_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
).split(",")

_allowed_methods = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")

_allowed_headers = os.getenv(
    "ALLOWED_HEADERS",
    "Content-Type,Authorization,X-Message-ID,X-Session-ID"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=_allowed_methods,
    allow_headers=_allowed_headers,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 全局组件
monitoring_system = MonitoringSystem()
error_handler = JubenErrorHandler()
workflow_manager = WorkflowManager()
agent_registry = AgentRegistry()

# 启动监控系统
monitoring_system.start_monitoring()


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    """聊天请求模型 - 带验证"""
    query: str
    user_id: str
    session_id: str
    file_ids: Optional[List[str]] = []
    auto_mode: bool = True
    user_selections: Optional[List[str]] = []

    class Config:
        str_strip_whitespace = True

    @classmethod
    def get_validators(cls):
        yield cls.validate_user_id
        yield cls.validate_session_id
        yield cls.validate_query
        yield cls.validate_file_ids

    def validate_user_id(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('user_id must contain only alphanumeric characters, hyphens, and underscores')
        return v

    def validate_session_id(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('session_id must contain only alphanumeric characters, hyphens, and underscores')
        return v

    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('query cannot be empty')
        if len(v) > 10000:
            raise ValueError('query cannot exceed 10000 characters')
        return v.strip()

    def validate_file_ids(cls, v):
        if v is None:
            return []
        if len(v) > 20:
            raise ValueError('cannot process more than 20 files at once')
        return v


class WorkflowRequest(BaseModel):
    """工作流请求模型"""
    instruction: str
    user_id: str
    session_id: str
    workflow_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}


class AgentInfoRequest(BaseModel):
    """Agent信息请求模型"""
    agent_type: Optional[str] = None


# ==================== 依赖注入 ====================

async def get_concierge() -> JubenConcierge:
    """获取接待员实例"""
    return JubenConcierge()


async def get_orchestrator() -> JubenOrchestrator:
    """获取编排器实例"""
    return JubenOrchestrator()


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        system_health = monitoring_system.get_system_health()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system_health": system_health
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    try:
        system_health = monitoring_system.get_system_health()
        metrics_summary = monitoring_system.get_metrics_summary()
        alerts_summary = monitoring_system.get_alerts_summary()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system_health": system_health,
            "metrics": metrics_summary,
            "alerts": alerts_summary,
            "monitoring_config": monitoring_system.get_monitoring_config()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ==================== 聊天接口 ====================

@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    concierge: JubenConcierge = Depends(get_concierge)
):
    """
    聊天接口 - 支持流式输出
    
    Args:
        request: 聊天请求
        background_tasks: 后台任务
        concierge: 接待员实例
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        # 记录请求开始时间
        start_time = time.time()
        
        # 构建请求数据
        request_data = {
            "query": request.query,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "file_ids": request.file_ids or [],
            "auto_mode": request.auto_mode,
            "user_selections": request.user_selections or []
        }
        
        # 创建流式响应生成器（带超时控制）
        async def generate_response() -> AsyncGenerator[str, None]:
            try:
                # 发送开始事件
                yield f"data: {json.dumps({'type': 'start', 'message': '开始处理您的请求...'}, ensure_ascii=False)}\n\n"

                # 设置超时控制
                timeout_seconds = 300  # 5分钟超时
                timeout_task = asyncio.create_task(asyncio.sleep(timeout_seconds))

                # 创建处理任务
                async def process_with_timeout():
                    async for event in concierge.process_request(request_data):
                        # 将事件转换为SSE格式
                        if isinstance(event, dict):
                            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'message', 'content': str(event)}, ensure_ascii=False)}\n\n"

                # 使用异步生成器包装器处理超时
                try:
                    event_count = 0
                    timeout_occurred = False

                    async def event_generator():
                        nonlocal event_count
                        async for event in concierge.process_request(request_data):
                            event_count += 1
                            if isinstance(event, dict):
                                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                            else:
                                yield f"data: {json.dumps({'type': 'message', 'content': str(event)}, ensure_ascii=False)}\n\n"

                    # 使用 wait_for 实现超时
                    iterator = event_generator()
                    while True:
                        try:
                            chunk = await asyncio.wait_for(
                                iterator.__anext__(),
                                timeout=timeout_seconds
                            )
                            yield chunk
                        except StopAsyncIteration:
                            break
                        except asyncio.TimeoutError:
                            timeout_occurred = True
                            yield f"data: {json.dumps({'type': 'error', 'message': f'处理超时（{timeout_seconds}秒），请重试或简化请求'}, ensure_ascii=False)}\n\n"
                            break

                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时发生错误: {str(e)}'}, ensure_ascii=False)}\n\n"
                processing_time = time.time() - start_time
                yield f"data: {json.dumps({'type': 'complete', 'processing_time': processing_time}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                # 发送错误事件
                error_result = await error_handler.handle_error(
                    e, ErrorType.AGENT_ERROR, {"endpoint": "chat", "request": request_data}
                )
                yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'result': error_result}, ensure_ascii=False)}\n\n"
        
        # 返回流式响应
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天接口错误: {str(e)}")


# ==================== 工作流接口 ====================

@app.post("/workflow")
async def workflow_endpoint(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    orchestrator: JubenOrchestrator = Depends(get_orchestrator)
):
    """
    工作流接口 - 支持流式输出
    
    Args:
        request: 工作流请求
        background_tasks: 后台任务
        orchestrator: 编排器实例
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        # 记录请求开始时间
        start_time = time.time()
        
        # 构建请求数据
        request_data = {
            "instruction": request.instruction,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "workflow_type": request.workflow_type,
            "context": request.context or {}
        }
        
        # 创建流式响应生成器
        async def generate_workflow_response() -> AsyncGenerator[str, None]:
            try:
                # 发送开始事件
                yield f"data: {json.dumps({'type': 'workflow_start', 'message': '开始执行工作流...'}, ensure_ascii=False)}\n\n"
                
                # 调用编排器处理请求
                async for event in orchestrator.process_request(request_data):
                    # 将事件转换为SSE格式
                    if isinstance(event, dict):
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'workflow_event', 'content': str(event)}, ensure_ascii=False)}\n\n"
                
                # 发送完成事件
                processing_time = time.time() - start_time
                yield f"data: {json.dumps({'type': 'workflow_complete', 'processing_time': processing_time}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                # 发送错误事件
                error_result = await error_handler.handle_error(
                    e, ErrorType.WORKFLOW_ERROR, {"endpoint": "workflow", "request": request_data}
                )
                yield f"data: {json.dumps({'type': 'workflow_error', 'error': str(e), 'result': error_result}, ensure_ascii=False)}\n\n"
        
        # 返回流式响应
        return StreamingResponse(
            generate_workflow_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工作流接口错误: {str(e)}")


# ==================== 系统信息接口 ====================

@app.get("/system/info")
async def get_system_info():
    """获取系统信息"""
    try:
        return {
            "system_health": monitoring_system.get_system_health(),
            "metrics_summary": monitoring_system.get_metrics_summary(),
            "alerts_summary": monitoring_system.get_alerts_summary(),
            "monitoring_config": monitoring_system.get_monitoring_config(),
            "supported_workflows": workflow_manager.get_supported_workflows(),
            "available_agents": agent_registry.get_available_agents(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@app.get("/system/metrics")
async def get_system_metrics():
    """获取系统指标"""
    try:
        return {
            "metrics": monitoring_system.get_metrics_summary(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统指标失败: {str(e)}")


@app.get("/system/alerts")
async def get_system_alerts():
    """获取系统告警"""
    try:
        return {
            "alerts": monitoring_system.get_alerts_summary(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统告警失败: {str(e)}")


# ==================== Agent管理接口 ====================

@app.get("/agents")
async def get_agents_info(request: AgentInfoRequest = Depends()):
    """获取Agent信息"""
    try:
        if request.agent_type:
            agent_info = agent_registry.get_agent_info(request.agent_type)
            if not agent_info:
                raise HTTPException(status_code=404, detail=f"未找到Agent: {request.agent_type}")
            return {"agent": agent_info}
        else:
            return {
                "agents": agent_registry.get_all_agents_info(),
                "statistics": agent_registry.get_agent_statistics()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent信息失败: {str(e)}")


@app.get("/agents/{agent_type}")
async def get_agent_info(agent_type: str):
    """获取特定Agent信息"""
    try:
        agent_info = agent_registry.get_agent_info(agent_type)
        if not agent_info:
            raise HTTPException(status_code=404, detail=f"未找到Agent: {agent_type}")
        return {"agent": agent_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent信息失败: {str(e)}")


# ==================== 工作流管理接口 ====================

@app.get("/workflows")
async def get_workflows():
    """获取支持的工作流列表"""
    try:
        return {
            "workflows": workflow_manager.get_supported_workflows(),
            "workflow_definitions": {
                workflow_type: workflow_manager.get_workflow_definition(workflow_type)
                for workflow_type in workflow_manager.get_supported_workflows()
            },
            "metrics": workflow_manager.get_workflow_metrics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流信息失败: {str(e)}")


@app.get("/workflows/{workflow_type}")
async def get_workflow_definition(workflow_type: str):
    """获取特定工作流定义"""
    try:
        workflow_def = workflow_manager.get_workflow_definition(workflow_type)
        if not workflow_def:
            raise HTTPException(status_code=404, detail=f"未找到工作流: {workflow_type}")
        return {"workflow": workflow_def}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流定义失败: {str(e)}")


# ==================== 错误处理接口 ====================

@app.get("/errors/summary")
async def get_error_summary():
    """获取错误摘要"""
    try:
        return {
            "error_summary": error_handler.get_error_summary(),
            "error_metrics": error_handler.get_error_metrics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取错误摘要失败: {str(e)}")


# ==================== 数据清理接口 ====================

@app.post("/system/cleanup")
async def cleanup_system_data(hours: int = 24):
    """清理系统数据"""
    try:
        # 清理监控数据
        monitoring_system.clear_old_data(hours)
        
        # 清理Agent缓存
        agent_registry.clear_agent_cache()
        
        return {
            "message": f"已清理 {hours} 小时前的系统数据",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理系统数据失败: {str(e)}")


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 Juben竖屏短剧策划助手API启动中...")
    logger.info("📊 监控系统已启动")
    logger.info("🔧 错误处理器已初始化")
    logger.info("🎬 工作流管理器已初始化")
    logger.info("🤖 Agent注册表已初始化")
    logger.info("✅ API服务启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🛑 Juben竖屏短剧策划助手API关闭中...")
    monitoring_system.stop_monitoring()
    logger.info("📊 监控系统已停止")
    logger.info("✅ API服务关闭完成")


# ==================== 异常处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器 - 不泄露敏感信息"""
    # 记录完整错误信息
    import logging
    logging.error(f"Unhandled exception: {exc}", exc_info=True)

    # 生产环境检查
    app_env = os.getenv("APP_ENV", "development").lower()

    if app_env == "production":
        # 生产环境返回通用错误
        return {
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    else:
        # 开发环境返回详细信息
        return {
            "error": str(exc),
            "error_code": "INTERNAL_ERROR",
            "status_code": 500,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc() if os.getenv("DEBUG", "false").lower() == "true" else None
        }


# ==================== 根路径 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Juben竖屏短剧策划助手API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
遗留 Agent 相关 API 路由
保留原始 api_routes.py 中的所有端点以确保向后兼容
这些端点将被逐步迁移到各自的功能模块中
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from utils.logger import get_logger
from .schemas import BaseResponse

logger = get_logger("LegacyAPI")

# 创建路由器
# 注意：该路由器会被 api_routes_modular 中 prefix="/juben" 的父路由挂载，
# 这里不再重复加 /juben，避免出现 /juben/juben/* 的双前缀问题。
router = APIRouter(tags=["遗留端点"])


# ============== 模型相关端点 ==============

@router.get("/models")
async def list_models():
    """获取可用的模型列表"""
    try:
        from utils.model_registry import get_model_registry
        registry = get_model_registry()
        return {
            "success": True,
            "models": registry.list_models()
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")


@router.get("/models/recommend")
async def recommend_model(task: str = "chat"):
    """推荐适合的模型"""
    try:
        from utils.model_registry import get_model_registry
        registry = get_model_registry()
        model = registry.recommend_model(task)
        return {
            "success": True,
            "model": model
        }
    except Exception as e:
        logger.error(f"推荐模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail="推荐模型失败")


@router.get("/models/types")
async def list_model_types():
    """获取模型类型列表"""
    try:
        return {
            "success": True,
            "types": [
                {"id": "zhipu", "name": "智谱AI", "description": "智谱AI大语言模型"},
                {"id": "openrouter", "name": "OpenRouter", "description": "OpenRouter聚合模型"},
                {"id": "openai", "name": "OpenAI", "description": "OpenAI GPT系列"},
                {"id": "local", "name": "本地模型", "description": "本地部署的开源模型"},
                {"id": "ollama", "name": "Ollama", "description": "Ollama本地模型"}
            ]
        }
    except Exception as e:
        logger.error(f"获取模型类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模型类型失败")


# ============== 配置相关端点 ==============

@router.get("/config")
async def get_config():
    """获取系统配置信息（脱敏）"""
    try:
        import os
        return {
            "success": True,
            "config": {
                "app_env": os.getenv("APP_ENV", "development"),
                "auth_enabled": os.getenv("AUTH_ENABLED", "false"),
                "rate_limit_rpm": os.getenv("RATE_LIMIT_RPM", "120"),
                "enable_web_search": os.getenv("ENABLE_WEB_SEARCH", "true"),
                "enable_knowledge_base": os.getenv("ENABLE_KNOWLEDGE_BASE", "true"),
                # 不返回敏感配置
            }
        }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取配置失败")


# ============== 意图分析端点 ==============

@router.post("/intent/analyze")
async def analyze_intent(request: Dict[str, Any]):
    """分析用户意图"""
    try:
        query = request.get("query", "")
        from utils.intent_analyzer import analyze_user_intent
        intent = await analyze_user_intent(query)
        return {
            "success": True,
            "intent": intent
        }
    except Exception as e:
        logger.error(f"意图分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="意图分析失败")


# ============== 创作相关端点 ==============

@router.post("/creator/chat")
async def creator_chat(request: Dict[str, Any]):
    """创作聊天接口"""
    try:
        from agents.juben_concierge import JubenConciergeAgent
        agent = JubenConciergeAgent()
        result = await agent.process_request(request)
        return result
    except Exception as e:
        logger.error(f"创作聊天失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创作聊天失败")


@router.get("/creator/info")
async def get_creator_info():
    """获取创作Agent信息"""
    return {
        "success": True,
        "agent": {
            "id": "juben_concierge",
            "name": "短剧接待员",
            "description": "短剧创作一站式服务",
            "capabilities": ["策划", "创作", "评估"]
        }
    }


# ============== 评估相关端点 ==============

@router.post("/evaluation/chat")
async def evaluation_chat(request: Dict[str, Any]):
    """评估聊天接口"""
    try:
        from agents.script_evaluator import ScriptEvaluatorAgent
        agent = ScriptEvaluatorAgent()
        result = await agent.process_request(request)
        return result
    except Exception as e:
        logger.error(f"评估聊天失败: {str(e)}")
        raise HTTPException(status_code=500, detail="评估聊天失败")


@router.get("/evaluation/info")
async def get_evaluation_info():
    """获取评估Agent信息"""
    return {
        "success": True,
        "agent": {
            "id": "script_evaluator",
            "name": "剧本评估师",
            "description": "专业的剧本质量评估",
            "capabilities": ["质量评估", "评分", "改进建议"]
        }
    }


@router.post("/evaluation/score")
async def evaluation_score(request: Dict[str, Any]):
    """评估打分接口"""
    try:
        content = request.get("content", "")
        criteria = request.get("criteria", [])
        from agents.script_evaluator import ScriptEvaluatorAgent
        agent = ScriptEvaluatorAgent()
        result = await agent.score(content, criteria)
        return {
            "success": True,
            "score": result
        }
    except Exception as e:
        logger.error(f"评估打分失败: {str(e)}")
        raise HTTPException(status_code=500, detail="评估打分失败")


@router.post("/text/evaluate")
async def text_evaluate(request: Dict[str, Any]):
    """文本评估兼容接口（旧前端端点）"""
    try:
        from agents.short_drama_evaluation_agent import ShortDramaEvaluationAgent
        agent = ShortDramaEvaluationAgent()
        request_data = {
            "input": request.get("input", request.get("query", "")),
            "query": request.get("query", request.get("input", "")),
            "user_id": request.get("user_id", "default_user"),
            "session_id": request.get("session_id", "default_session"),
            "agent_id": "text_processor_evaluation",
        }
        context = {
            "user_id": request_data["user_id"],
            "session_id": request_data["session_id"],
        }
        chunks: List[str] = []
        async for event in agent.process_request(request_data, context):
            event_type = event.get("event") or event.get("event_type") or event.get("type")
            data = event.get("data", {})
            content = data.get("content") if isinstance(data, dict) else data
            if event_type in {"llm_chunk", "message", "content"} and isinstance(content, str) and content:
                chunks.append(content)
        return {
            "success": True,
            "data": {
                "content": "".join(chunks),
                "agent": "short_drama_evaluation",
            },
        }
    except Exception as e:
        logger.error(f"文本评估失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文本评估失败")


# ============== 系统监控端点 ==============

@router.get("/rate-limit/info")
async def get_rate_limit_info():
    """获取限流配置信息"""
    try:
        import os
        return {
            "success": True,
            "config": {
                "requests_per_minute": int(os.getenv("RATE_LIMIT_RPM", "120")),
                "burst_size": int(os.getenv("RATE_LIMIT_BURST", "20"))
            }
        }
    except Exception as e:
        logger.error(f"获取限流信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取限流信息失败")


@router.post("/rate-limit/config")
async def update_rate_limit_config(request: Dict[str, Any]):
    """更新限流配置（仅限管理员）"""
    try:
        # 这里应该添加管理员权限检查
        rpm = request.get("requests_per_minute", 120)
        # 实际更新逻辑
        return {
            "success": True,
            "message": "限流配置已更新"
        }
    except Exception as e:
        logger.error(f"更新限流配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新限流配置失败")


@router.post("/rate-limit/reset")
async def reset_rate_limit(request: Dict[str, Any]):
    """重置限流计数器（仅限管理员）"""
    try:
        user_id = request.get("user_id")
        # 实际重置逻辑
        return {
            "success": True,
            "message": f"用户 {user_id} 的限流计数器已重置"
        }
    except Exception as e:
        logger.error(f"重置限流失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重置限流失败")


# ============== 系统健康与状态端点 ==============

@router.get("/system/connection-pool/health")
async def get_connection_pool_health():
    """获取连接池健康状态"""
    try:
        from utils.connection_pool_manager import get_connection_pool_manager
        pool_manager = await get_connection_pool_manager()
        health = await pool_manager.get_health_status()
        return {
            "success": True,
            "health": health
        }
    except Exception as e:
        logger.error(f"获取连接池健康状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取连接池健康状态失败")


@router.post("/system/connection-pool/warmup")
async def warmup_connection_pools(request: Dict[str, Any]):
    """预热连接池"""
    try:
        pools = request.get("pools", ["high_priority", "normal", "background"])
        from utils.connection_pool_manager import get_connection_pool_manager
        pool_manager = await get_connection_pool_manager()
        await pool_manager.warmup_pools(pools)
        return {
            "success": True,
            "message": f"连接池预热完成: {pools}"
        }
    except Exception as e:
        logger.error(f"预热连接池失败: {str(e)}")
        raise HTTPException(status_code=500, detail="预热连接池失败")


@router.get("/system/access-stats")
async def get_access_stats():
    """获取系统访问统计"""
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()
        stats = await storage.get_access_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取访问统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取访问统计失败")


@router.get("/system/token-dashboard")
async def get_token_dashboard():
    """获取Token使用仪表板"""
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()
        dashboard = await storage.get_token_dashboard()
        return {
            "success": True,
            "dashboard": dashboard
        }
    except Exception as e:
        logger.error(f"获取Token仪表板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Token仪表板失败")


@router.get("/system/port-monitor/status")
async def get_port_monitor_status():
    """获取端口监控状态"""
    try:
        from utils.port_monitor_service import get_port_monitor_service
        monitor = get_port_monitor_service()
        status = await monitor.get_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"获取端口监控状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取端口监控状态失败")


@router.post("/system/port-monitor/start")
async def start_port_monitor(request: Dict[str, Any]):
    """启动端口监控"""
    try:
        interval = request.get("interval", 300)
        from utils.port_monitor_service import get_port_monitor_service
        monitor = get_port_monitor_service()
        await monitor.start_monitoring(interval)
        return {
            "success": True,
            "message": "端口监控已启动"
        }
    except Exception as e:
        logger.error(f"启动端口监控失败: {str(e)}")
        raise HTTPException(status_code=500, detail="启动端口监控失败")


@router.post("/system/port-monitor/stop")
async def stop_port_monitor():
    """停止端口监控"""
    try:
        from utils.port_monitor_service import get_port_monitor_service
        monitor = get_port_monitor_service()
        await monitor.stop_monitoring()
        return {
            "success": True,
            "message": "端口监控已停止"
        }
    except Exception as e:
        logger.error(f"停止端口监控失败: {str(e)}")
        raise HTTPException(status_code=500, detail="停止端口监控失败")


# ============== 流式处理端点 ==============

@router.post("/stream/heartbeat")
async def stream_heartbeat(request: Dict[str, Any]):
    """流式会话心跳"""
    try:
        session_id = request.get("session_id")
        from utils.stream_manager import get_stream_session_manager
        session_manager = get_stream_session_manager()
        session_manager.heartbeat(session_id)
        return {
            "success": True,
            "message": "心跳已更新"
        }
    except Exception as e:
        logger.error(f"心跳更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="心跳更新失败")


@router.get("/stream/check-replay/{session_id}")
async def check_stream_replay(session_id: str):
    """检查流式会话回放状态"""
    try:
        from utils.stream_manager import get_stream_session_manager
        session_manager = get_stream_session_manager()
        status = session_manager.get_replay_status(session_id)
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"检查回放状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查回放状态失败")


# ============== 请求停止端点 ==============

@router.post("/stop/request")
async def stop_request(request: Dict[str, Any]):
    """停止正在处理的请求"""
    try:
        user_id = request.get("user_id")
        session_id = request.get("session_id")
        from utils.request_stop_manager import get_request_stop_manager
        stop_manager = get_request_stop_manager()
        stop_manager.stop_request(user_id, session_id)
        return {
            "success": True,
            "message": "停止请求已发送"
        }
    except Exception as e:
        logger.error(f"停止请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="停止请求失败")


# 导出
__all__ = ["router"]

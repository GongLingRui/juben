"""
聊天相关 API 路由
处理用户聊天请求、流式响应等
"""
import asyncio
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.stream_manager import get_stream_response_generator
from utils.logger import get_logger
from utils.error_handler import handle_error
from utils.agent_dispatch import build_agent_generator
from .schemas import ChatRequest, StreamEvent

logger = get_logger("ChatAPI")

# 创建路由器
router = APIRouter(prefix="/chat", tags=["聊天"])


def _snake_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)


def _resolve_agent_import(agent_id: Optional[str]) -> tuple[str, str]:
    """将前端 agent_id 映射到可加载的 Agent 类"""
    normalized = (agent_id or "short_drama_planner").strip().lower()
    mapping = {
        "short_drama_planner": ("agents.short_drama_planner_agent", "ShortDramaPlannerAgent"),
        "short_drama_planner_agent": ("agents.short_drama_planner_agent", "ShortDramaPlannerAgent"),
        "short_drama_creator": ("agents.short_drama_creator_agent", "ShortDramaCreatorAgent"),
        "short_drama_creator_agent": ("agents.short_drama_creator_agent", "ShortDramaCreatorAgent"),
        "short_drama_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "short_drama_evaluation_agent": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        # 兼容前端旧Agent ID，统一映射到评估Agent，避免404后退化为planner
        "text_processor_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "script_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "ip_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "story_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "story_outline_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "novel_screening_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "result_analyzer_evaluation": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        "score_analyzer": ("agents.short_drama_evaluation_agent", "ShortDramaEvaluationAgent"),
        # 命名不规则的Agent
        "websearch": ("agents.websearch_agent", "WebSearchAgent"),
        "ip_evaluation": ("agents.ip_evaluation_agent", "IPEvaluationAgent"),
    }
    if normalized in mapping:
        return mapping[normalized]

    # 通用命名约定：agents/<agent_id>_agent.py + <PascalCase>Agent
    return (f"agents.{normalized}_agent", f"{_snake_to_pascal(normalized)}Agent")


@router.post("")
async def chat_handler(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """
    处理聊天请求 - 支持流式输出

    Args:
        request: 聊天请求
        background_tasks: 后台任务
        http_request: HTTP 请求对象

    Returns:
        StreamingResponse: 流式响应
    """
    try:
        # 记录请求
        logger.info(f"收到聊天请求: user_id={request.user_id}, session_id={request.session_id}")
        logger.debug(f"请求内容: {request.input[:100] if len(request.input) > 100 else request.input}...")

        # 解析引用
        resolved_input = request.input
        reference_trace = []

        if request.file_ids and request.file_refs == "auto":
            from utils.reference_resolver import get_juben_reference_resolver
            resolver = get_juben_reference_resolver()
            resolved_input, reference_trace = await resolver.resolve_references(
                request.input,
                request.file_ids,
                request.user_id
            )
            logger.debug(f"解析引用完成: 引用数量 {len(reference_trace)}")

        # 构建请求数据
        request_data = {
            "input": resolved_input,
            "query": resolved_input,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "file_ids": request.file_ids or [],
            "auto_mode": request.auto_mode,
            "user_selections": request.user_selections or [],
            "reference_trace": reference_trace,
            "original_input": request.input,
            "stream_mode": True
        }

        # 解析并加载 Agent 实例
        agent_id = request.agent_id or "short_drama_planner"
        module_path, class_name = _resolve_agent_import(agent_id)
        try:
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            agent = agent_class()
        except Exception as agent_error:
            logger.error(f"Agent加载失败: agent_id={agent_id}, error={agent_error}")
            raise HTTPException(status_code=404, detail=f"未找到可用Agent: {agent_id}")

        # 构建上下文并获取 Agent 生成器
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "project_id": request.project_id,
            "request_path": str(http_request.url.path),
        }
        agent_generator = build_agent_generator(agent, request_data, context)

        # 创建流式响应（统一转换为标准 SSE 事件）
        session_id = request.session_id or f"session_{hash(request.input)}"
        user_id = request.user_id or "default_user"
        stream_generator = get_stream_response_generator()
        return StreamingResponse(
            stream_generator.generate(
                agent_generator=agent_generator,
                session_id=session_id,
                user_id=user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        error_result = await handle_error(e, "chat_processing", {
            "user_id": getattr(request, 'user_id', 'unknown'),
            "session_id": getattr(request, 'session_id', 'unknown')
        })
        raise HTTPException(status_code=500, detail=error_result.get("message", "处理失败"))


@router.post("/resume")
async def resume_chat(request: Request):
    """
    恢复中断的聊天会话

    Args:
        request: HTTP 请求对象

    Returns:
        StreamingResponse: 从断点继续的流式响应
    """
    try:
        # 从请求体获取恢复参数
        request_data = await request.json()
        session_id = request_data.get("session_id")
        message_id = request_data.get("message_id")
        from_sequence = request_data.get("from_sequence", 0)

        if not session_id or not message_id:
            raise HTTPException(status_code=400, detail="缺少必要参数")

        logger.info(f"恢复会话: session_id={session_id}, message_id={message_id}, from_sequence={from_sequence}")

        # 获取流式会话管理器
        from utils.stream_manager import get_stream_session_manager
        session_manager = get_stream_session_manager()

        # 恢复会话
        stream_generator = session_manager.resume_session(session_id, message_id, from_sequence)

        if not stream_generator:
            raise HTTPException(status_code=404, detail="会话不存在或已过期")

        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="恢复会话失败")


@router.post("/stop")
async def stop_chat(request: Request):
    """
    停止正在进行的聊天会话

    Args:
        request: HTTP 请求对象

    Returns:
        停止结果
    """
    try:
        request_data = await request.json()
        session_id = request_data.get("session_id")
        message_id = request_data.get("message_id")

        if not session_id:
            raise HTTPException(status_code=400, detail="缺少 session_id")

        logger.info(f"停止会话: session_id={session_id}, message_id={message_id}")

        # 获取流式会话管理器
        from utils.stream_manager import get_stream_session_manager
        session_manager = get_stream_session_manager()

        # 停止会话
        stopped = session_manager.stop_session(session_id, message_id)

        return {
            "success": stopped,
            "message": "会话已停止" if stopped else "会话不存在或已结束"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="停止会话失败")


@router.get("/sessions")
async def list_sessions(user_id: str):
    """
    获取用户的聊天会话列表

    Args:
        user_id: 用户 ID

    Returns:
        会话列表
    """
    try:
        # 从存储获取会话列表
        from utils.storage_manager import get_storage
        storage = get_storage()

        sessions = await storage.list_user_sessions(user_id)

        return {
            "success": True,
            "sessions": sessions
        }

    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.get("/sessions/{session_id}")
async def get_session_history(session_id: str):
    """
    获取会话的历史消息

    Args:
        session_id: 会话 ID

    Returns:
        消息历史
    """
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()

        history = await storage.get_session_history(session_id)

        return {
            "success": True,
            "history": history
        }

    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话历史失败")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话

    Args:
        session_id: 会话 ID

    Returns:
        删除结果
    """
    try:
        from utils.storage_manager import get_storage
        storage = get_storage()

        await storage.delete_session(session_id)

        return {
            "success": True,
            "message": "会话已删除"
        }

    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除会话失败")


# 导出
__all__ = ["router"]

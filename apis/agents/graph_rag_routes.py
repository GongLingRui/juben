"""
GraphRAG API 路由
GraphRAG API Routes

提供GraphRAG集成的RESTful API接口：
1. 智能问答
2. 实体分析
3. 路径查找
4. 一致性检查
5. 世界观验证

作者：Claude
创建时间：2025-02-08
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from agents.graph_rag_agent import GraphRAGAgent, QuestionType
from utils.agent_dispatch import build_agent_generator

router = APIRouter(prefix="/graph-rag", tags=["GraphRAG智能问答"])


# ============ 请求/响应模型 ============

class AskQuestionRequest(BaseModel):
    """问答请求"""
    story_id: str = Field(..., description="故事ID")
    question: str = Field(..., description="问题")
    question_type: Optional[str] = Field(None, description="问题类型（可选）")


class AskQuestionResponse(BaseModel):
    """问答响应"""
    question: str
    answer: str
    confidence: float
    context_summary: str
    sources: List[str]


class AnalyzeEntityRequest(BaseModel):
    """实体分析请求"""
    story_id: str = Field(..., description="故事ID")
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(..., description="实体类型")
    depth: int = Field(2, ge=1, le=5, description="分析深度")


class FindPathsRequest(BaseModel):
    """路径查找请求"""
    story_id: str = Field(..., description="故事ID")
    start_entity: str = Field(..., description="起始实体ID")
    end_entity: str = Field(..., description="目标实体ID")
    max_depth: int = Field(5, ge=1, le=10, description="最大深度")


class VerifyWorldRulesRequest(BaseModel):
    """世界观验证请求"""
    story_id: str = Field(..., description="故事ID")
    plot_data: Dict[str, Any] = Field(..., description="待验证的情节数据")


# ============ 依赖注入 ============

async def get_rag_agent() -> GraphRAGAgent:
    """获取GraphRAG Agent实例"""
    try:
        agent = GraphRAGAgent()
        return agent
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"GraphRAG Agent 初始化失败: {str(e)}"
        )


# ============ API 端点 ============

@router.post("/ask", response_model=AskQuestionResponse)
async def ask_question(
    request: AskQuestionRequest,
    background_tasks: BackgroundTasks,
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    智能问答

    基于知识图谱的智能问答系统，支持：
    - 事实性问题：谁、什么、哪里
    - 关系性问题：A与B的关系
    - 时序性问题：何时、顺序
    - 因果性问题：为什么、导致
    - 分析性问题：分析、对比
    - 创作性问题：基于世界观生成

    Args:
        request: 问答请求

    Returns:
        问答响应，包括答案、置信度、上下文摘要等
    """
    try:
        result = None
        error = None

        async for event in build_agent_generator(agent, {
            "operation": "ask_question",
            **request.dict()
        }, None):
            if event.get("event_type") == "tool_complete":
                result = event["data"]["result"]
            elif event.get("event_type") == "error":
                error = event["data"]["error"]

        if error:
            raise HTTPException(
                status_code=500,
                detail=error
            )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="问答失败，未返回结果"
            )

        return AskQuestionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"问答失败: {str(e)}"
        )


@router.post("/analyze-entity")
async def analyze_entity(
    request: AnalyzeEntityRequest,
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    分析实体

    分析实体的属性、关系网络和作用

    Args:
        request: 实体分析请求

    Returns:
        实体分析结果
    """
    try:
        result = None
        error = None

        async for event in build_agent_generator(agent, {
            "operation": "analyze_entity",
            **request.dict()
        }, None):
            if event.get("event_type") == "tool_complete":
                result = event["data"]["result"]
            elif event.get("event_type") == "error":
                error = event["data"]["error"]

        if error:
            raise HTTPException(
                status_code=500,
                detail=error
            )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="实体分析失败，未返回结果"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"实体分析失败: {str(e)}"
        )


@router.post("/find-paths")
async def find_paths(
    request: FindPathsRequest,
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    寻找实体间路径

    查找两个实体之间的最短路径或所有路径

    Args:
        request: 路径查找请求

    Returns:
        路径查找结果
    """
    try:
        result = None
        error = None

        async for event in build_agent_generator(agent, {
            "operation": "find_paths",
            **request.dict()
        }, None):
            if event.get("event_type") == "tool_complete":
                result = event["data"]["result"]
            elif event.get("event_type") == "error":
                error = event["data"]["error"]

        if error:
            raise HTTPException(
                status_code=500,
                detail=error
            )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="路径查找失败，未返回结果"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"路径查找失败: {str(e)}"
        )


@router.post("/check-consistency")
async def check_consistency(
    story_id: str = Query(..., description="故事ID"),
    check_type: Optional[str] = Query(None, description="检查类型"),
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    检查剧情一致性

    调用逻辑一致性检测Agent进行检查

    Args:
        story_id: 故事ID
        check_type: 检查类型（可选）

    Returns:
        一致性检查结果
    """
    try:
        result = None
        error = None

        async for event in build_agent_generator(agent, {
            "operation": "check_consistency",
            "story_id": story_id,
            "check_type": check_type
        }, None):
            if event.get("event_type") == "tool_complete":
                result = event["data"]["result"]
            elif event.get("event_type") == "error":
                error = event["data"]["error"]

        if error:
            raise HTTPException(
                status_code=500,
                detail=error
            )

        return result or {"message": "一致性检查完成"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"一致性检查失败: {str(e)}"
        )


@router.post("/verify-world-rules")
async def verify_world_rules(
    request: VerifyWorldRulesRequest,
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    验证世界观规则

    验证情节是否遵守世界观规则

    Args:
        request: 世界观验证请求

    Returns:
        验证结果
    """
    try:
        result = None
        error = None

        async for event in build_agent_generator(agent, {
            "operation": "verify_world_rules",
            **request.dict()
        }, None):
            if event.get("event_type") == "tool_complete":
                result = event["data"]["result"]
            elif event.get("event_type") == "error":
                error = event["data"]["error"]

        if error:
            raise HTTPException(
                status_code=500,
                detail=error
            )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="世界观验证失败，未返回结果"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"世界观验证失败: {str(e)}"
        )


@router.get("/context/{entity_id}")
async def get_entity_context(
    entity_id: str,
    entity_type: str = Query(..., description="实体类型"),
    depth: int = Query(2, ge=1, le=5, description="遍历深度"),
    limit: int = Query(20, ge=1, le=100, description="结果限制"),
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    获取实体上下文

    用于RAG检索增强生成的上下文获取

    Args:
        entity_id: 实体ID
        entity_type: 实体类型
        depth: 遍历深度
        limit: 结果数量限制

    Returns:
        实体上下文数据
    """
    try:
        from utils.graph_enhanced import get_enhanced_graph_manager, GraphRAGQuery

        graph_manager = await get_enhanced_graph_manager()

        # 获取上下文
        query = GraphRAGQuery.get_context_for_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            depth=depth,
            limit=limit
        )

        records, execution_time = await graph_manager.execute_query(
            query,
            parameters={"entity_id": entity_id}
        )

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "context": records,
            "context_count": len(records) if isinstance(records, list) else 0,
            "execution_time": execution_time,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取实体上下文失败: {str(e)}"
        )


@router.post("/search")
async def search_by_keywords(
    story_id: str = Query(..., description="故事ID"),
    keywords: List[str] = Query(..., description="关键词列表"),
    limit: int = Query(10, ge=1, le=50, description="结果限制"),
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    根据关键词搜索

    用于RAG检索增强生成的关键词匹配

    Args:
        story_id: 故事ID
        keywords: 关键词列表
        limit: 结果限制

    Returns:
        搜索结果
    """
    try:
        from utils.graph_enhanced import get_enhanced_graph_manager, GraphRAGQuery

        graph_manager = await get_enhanced_graph_manager()

        # 搜索上下文
        query = GraphRAGQuery.get_relevant_context(
            story_id=story_id,
            keywords=keywords,
            limit=limit
        )

        records, execution_time = await graph_manager.execute_query(
            query,
            parameters={"story_id": story_id}
        )

        return {
            "story_id": story_id,
            "keywords": keywords,
            "results": records,
            "result_count": len(records) if isinstance(records, list) else 0,
            "execution_time": execution_time,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"关键词搜索失败: {str(e)}"
        )


# ============ 批量操作 ============

@router.post("/batch/ask")
async def batch_ask_questions(
    questions: List[AskQuestionRequest],
    agent: GraphRAGAgent = Depends(get_rag_agent)
):
    """
    批量问答

    Args:
        questions: 问题列表

    Returns:
        批量问答结果
    """
    try:
        results = []
        errors = []

        for i, question_req in enumerate(questions):
            try:
                result = None
                error = None

                async for event in build_agent_generator(agent, {
                    "operation": "ask_question",
                    **question_req.dict()
                }, None):
                    if event.get("event_type") == "tool_complete":
                        result = event["data"]["result"]
                    elif event.get("event_type") == "error":
                        error = event["data"]["error"]

                if error:
                    errors.append({"index": i, "error": error})
                elif result:
                    results.append(result)

            except Exception as e:
                errors.append({"index": i, "error": str(e)})

        return {
            "total": len(questions),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量问答失败: {str(e)}"
        )

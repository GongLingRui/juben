"""
用户反馈 API 路由
提供反馈收集、黄金样本管理的接口

端点：
- POST   /juben/feedback                # 提交反馈（点赞/点踩/评分）
- POST   /juben/feedback/refinement     # 提交编辑修改反馈
- GET    /juben/feedback                # 获取反馈列表
- GET    /juben/feedback/statistics     # 获取反馈统计
- GET    /juben/feedback/gold           # 获取黄金样本
- GET    /juben/feedback/gold/examples  # 获取成功案例用于Prompt增强

代码作者：Claude
创建时间：2026年2月7日
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from utils.feedback_manager import (
    get_feedback_manager,
    get_gold_sample_manager,
    AgentFeedback,
    FeedbackType,
    FeedbackSource,
    record_feedback,
    record_refinement,
    generate_trace_id,
    get_success_examples
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["用户反馈"])


# ==================== 请求/响应模型 ====================

class FeedbackRequest(BaseModel):
    """反馈请求"""
    trace_id: Optional[str] = Field(None, description="追踪ID（可选，自动生成）")
    agent_name: str = Field(..., description="Agent名称")
    user_input: str = Field(..., description="用户输入")
    ai_output: str = Field(..., description="AI输出")
    feedback_type: str = Field(..., description="反馈类型: like/dislike/rating")
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分(1-5)")
    user_id: str = Field(default="unknown", description="用户ID")
    session_id: str = Field(default="unknown", description="会话ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加信息")


class FeedbackRefinementRequest(BaseModel):
    """编辑修改反馈请求"""
    trace_id: str = Field(..., description="追踪ID")
    agent_name: str = Field(..., description="Agent名称")
    original_text: str = Field(..., description="原始文本(AI生成)")
    modified_text: str = Field(..., description="修改后的文本(用户编辑)")
    user_id: str = Field(default="unknown", description="用户ID")
    session_id: str = Field(default="unknown", description="会话ID")
    context: str = Field(default="", description="上下文信息")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    trace_id: Optional[str] = None
    is_gold_sample: Optional[bool] = None
    gold_reason: Optional[str] = None
    error: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """反馈列表响应"""
    success: bool
    total: int
    data: List[Dict[str, Any]]
    error: Optional[str] = None


class StatisticsResponse(BaseModel):
    """统计响应"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class GoldSamplesResponse(BaseModel):
    """黄金样本响应"""
    success: bool
    data: List[Dict[str, Any]]
    error: Optional[str] = None


class ExamplesResponse(BaseModel):
    """成功案例响应"""
    success: bool
    examples: List[Dict[str, str]]
    count: int
    error: Optional[str] = None


# ==================== 反馈提交 API ====================

@router.post("")
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    提交反馈

    支持的反馈类型：
    - like: 点赞
    - dislike: 点踩
    - rating: 评分(需要提供user_rating)

    Example:
    ```json
    {
      "agent_name": "short_drama_creator",
      "user_input": "写一个都市甜宠剧",
      "ai_output": "剧名：《霸道总裁爱上我》...",
      "feedback_type": "like",
      "user_rating": 5
    }
    ```
    """
    try:
        # 生成或使用提供的trace_id
        trace_id = request.trace_id or generate_trace_id()

        # 转换反馈类型
        feedback_type_map = {
            "like": FeedbackType.LIKE,
            "dislike": FeedbackType.DISLIKE,
            "rating": FeedbackType.RATING,
            "skip": FeedbackType.SKIP
        }
        feedback_type = feedback_type_map.get(request.feedback_type, FeedbackType.LIKE)

        # 创建反馈对象
        feedback = AgentFeedback(
            trace_id=trace_id,
            agent_name=request.agent_name,
            user_input=request.user_input,
            ai_output=request.ai_output,
            feedback_type=feedback_type,
            feedback_source=FeedbackSource.CHAT,
            user_rating=request.user_rating,
            user_id=request.user_id,
            session_id=request.session_id,
            metadata=request.metadata
        )

        # 保存反馈
        manager = get_feedback_manager()
        saved = await manager.save_feedback(feedback)

        if not saved:
            raise HTTPException(status_code=500, detail="保存反馈失败")

        # 如果是黄金样本，也保存到黄金样本库
        sample_id = None
        if feedback.is_gold_sample:
            gold_manager = get_gold_sample_manager()
            sample_id = await gold_manager.save_sample(feedback)

        return FeedbackResponse(
            success=True,
            trace_id=trace_id,
            is_gold_sample=feedback.is_gold_sample,
            gold_reason=feedback.gold_sample_reason
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refinement")
async def submit_refinement_feedback(request: FeedbackRefinementRequest) -> FeedbackResponse:
    """
    提交编辑修改反馈

    当用户在编辑器中修改AI生成的内容并保存时调用此接口。
    系统会自动计算编辑距离和相似度，判断是否为黄金样本。

    Example:
    ```json
    {
      "trace_id": "trace_1234567890_abc123",
      "agent_name": "short_drama_creator",
      "original_text": "他生气了",
      "modified_text": "他额角的青筋暴起，双眼通红"
    }
    ```
    """
    try:
        # 使用便捷函数记录反馈
        saved = await record_refinement(
            trace_id=request.trace_id,
            agent_name=request.agent_name,
            original_text=request.original_text,
            modified_text=request.modified_text,
            user_id=request.user_id,
            session_id=request.session_id
        )

        if not saved:
            raise HTTPException(status_code=500, detail="保存修改反馈失败")

        # 获取保存的反馈以查看是否为黄金样本
        manager = get_feedback_manager()
        feedbacks = await manager.get_feedback(trace_id=request.trace_id, limit=1)

        is_gold = False
        gold_reason = None
        if feedbacks:
            is_gold = feedbacks[0].is_gold_sample
            gold_reason = feedbacks[0].gold_sample_reason

            # 如果是黄金样本，保存到样本库
            if is_gold:
                gold_manager = get_gold_sample_manager()
                await gold_manager.save_sample(feedbacks[0])

        return FeedbackResponse(
            success=True,
            trace_id=request.trace_id,
            is_gold_sample=is_gold,
            gold_reason=gold_reason
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交修改反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 反馈查询 API ====================

@router.get("")
async def get_feedback_list(
    user_id: Optional[str] = Query(None, description="用户ID"),
    agent_name: Optional[str] = Query(None, description="Agent名称"),
    trace_id: Optional[str] = Query(None, description="追踪ID"),
    is_gold_sample: Optional[bool] = Query(None, description="是否为黄金样本"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量")
) -> FeedbackListResponse:
    """
    获取反馈列表

    支持按以下条件过滤：
    - user_id: 用户ID
    - agent_name: Agent名称
    - trace_id: 追踪ID
    - is_gold_sample: 是否为黄金样本
    """
    try:
        manager = get_feedback_manager()
        feedbacks = await manager.get_feedback(
            trace_id=trace_id,
            user_id=user_id,
            agent_name=agent_name,
            is_gold_sample=is_gold_sample,
            limit=limit
        )

        return FeedbackListResponse(
            success=True,
            total=len(feedbacks),
            data=[fb.to_dict() for fb in feedbacks]
        )

    except Exception as e:
        logger.error(f"获取反馈列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_feedback_statistics(
    agent_name: Optional[str] = Query(None, description="Agent名称"),
    days: int = Query(30, ge=1, le=365, description="统计天数")
) -> StatisticsResponse:
    """
    获取反馈统计

    返回统计信息：
    - period_days: 统计周期
    - total_feedbacks: 总反馈数
    - gold_samples: 黄金样本数
    - gold_ratio: 黄金样本比例
    - by_type: 按类型统计
    - by_agent: 按Agent统计
    """
    try:
        manager = get_feedback_manager()
        stats = await manager.get_statistics(agent_name=agent_name, days=days)

        return StatisticsResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 黄金样本 API ====================

@router.get("/gold")
async def get_gold_samples(
    agent_name: Optional[str] = Query(None, description="Agent名称"),
    query: Optional[str] = Query(None, description="查询文本"),
    top_k: int = Query(10, ge=1, le=100, description="返回数量")
) -> GoldSamplesResponse:
    """
    获取黄金样本

    从向量库中检索高质量的成功案例。
    可以按Agent名称和查询文本进行过滤。
    """
    try:
        manager = get_gold_sample_manager()

        if query:
            # 搜索相似样本
            samples = await manager.search_similar(
                query_input=query,
                agent_name=agent_name,
                top_k=top_k
            )
        else:
            # 获取最近添加的样本（简化处理）
            samples = []

        return GoldSamplesResponse(
            success=True,
            data=[
                {
                    "sample_id": s.sample_id,
                    "trace_id": s.trace_id,
                    "agent_name": s.agent_name,
                    "user_input": s.user_input,
                    "ai_output": s.ai_output[:500] + "..." if len(s.ai_output) > 500 else s.ai_output,
                    "score": s.score,
                    "gold_reason": s.feedback.gold_sample_reason
                }
                for s in samples
            ]
        )

    except Exception as e:
        logger.error(f"获取黄金样本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gold/examples")
async def get_success_examples_for_prompt(
    agent_name: str = Query(..., description="Agent名称"),
    query_input: str = Query(..., description="当前输入"),
    count: int = Query(3, ge=1, le=10, description="返回数量")
) -> ExamplesResponse:
    """
    获取成功案例用于Prompt增强

    返回与当前输入最相似的成功案例，格式化为可直接插入Prompt的形式。
    """
    try:
        examples = await get_success_examples(
            agent_name=agent_name,
            query_input=query_input,
            count=count
        )

        return ExamplesResponse(
            success=True,
            examples=examples,
            count=len(examples)
        )

    except Exception as e:
        logger.error(f"获取成功案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量操作 API ====================

@router.post("/batch")
async def batch_submit_feedback(
    requests: List[FeedbackRequest],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    批量提交反馈

    支持一次性提交多个反馈，适合批量处理场景。
    """
    try:
        results = []
        manager = get_feedback_manager()

        for req in requests:
            try:
                trace_id = req.trace_id or generate_trace_id()

                feedback_type_map = {
                    "like": FeedbackType.LIKE,
                    "dislike": FeedbackType.DISLIKE,
                    "rating": FeedbackType.RATING,
                    "skip": FeedbackType.SKIP
                }
                feedback_type = feedback_type_map.get(req.feedback_type, FeedbackType.LIKE)

                feedback = AgentFeedback(
                    trace_id=trace_id,
                    agent_name=req.agent_name,
                    user_input=req.user_input,
                    ai_output=req.ai_output,
                    feedback_type=feedback_type,
                    feedback_source=FeedbackSource.CHAT,
                    user_rating=req.user_rating,
                    user_id=req.user_id,
                    session_id=req.session_id,
                    metadata=req.metadata
                )

                saved = await manager.save_feedback(feedback)

                results.append({
                    "trace_id": trace_id,
                    "success": saved,
                    "is_gold_sample": feedback.is_gold_sample
                })

                # 异步保存黄金样本
                if saved and feedback.is_gold_sample:
                    background_tasks.add_task(
                        save_gold_sample_background,
                        feedback
                    )

            except Exception as e:
                logger.error(f"处理反馈失败: {e}")
                results.append({
                    "trace_id": req.trace_id,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "total": len(requests),
            "results": results
        }

    except Exception as e:
        logger.error(f"批量提交失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def save_gold_sample_background(feedback: AgentFeedback):
    """后台任务：保存黄金样本"""
    try:
        gold_manager = get_gold_sample_manager()
        await gold_manager.save_sample(feedback)
    except Exception as e:
        logger.error(f"后台保存黄金样本失败: {e}")


# ==================== 追踪ID生成 API ====================

@router.get("/trace/generate")
async def generate_trace() -> Dict[str, str]:
    """
    生成追踪ID

    在Agent生成内容前调用此接口获取trace_id，
    用于后续关联反馈。
    """
    trace_id = generate_trace_id()
    return {
        "trace_id": trace_id
    }


# ==================== Agent集成辅助 API ====================

@router.post("/agent/success")
async def record_agent_success(
    trace_id: str,
    agent_name: str,
    user_input: str,
    ai_output: str,
    user_id: str = "unknown",
    session_id: str = "unknown"
) -> FeedbackResponse:
    """
    记录Agent成功案例（供Agent内部调用）

    当Agent认为某次生成特别成功时，可以主动调用此接口记录。
    """
    try:
        feedback = AgentFeedback(
            trace_id=trace_id,
            agent_name=agent_name,
            user_input=user_input,
            ai_output=ai_output,
            feedback_type=FeedbackType.LIKE,
            feedback_source=FeedbackSource.API,
            user_rating=5,  # 默认最高评分
            user_id=user_id,
            session_id=session_id
        )

        manager = get_feedback_manager()
        saved = await manager.save_feedback(feedback)

        if saved and feedback.is_gold_sample:
            gold_manager = get_gold_sample_manager()
            await gold_manager.save_sample(feedback)

        return FeedbackResponse(
            success=True,
            trace_id=trace_id,
            is_gold_sample=feedback.is_gold_sample,
            gold_reason=feedback.gold_sample_reason
        )

    except Exception as e:
        logger.error(f"记录成功案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
进化 API 路由
提供 Prompt 进化、版本管理和 A/B 测试的接口

端点：
- GET  /juben/evolution/status          # 获取进化状态
- POST /juben/evolution/trigger          # 手动触发进化
- GET  /juben/evolution/versions         # 获取版本列表
- GET  /juben/evolution/ab/test          # 获取 A/B 测试状态
- POST /juben/evolution/ab/promote       # 晋升新版本
- GET  /juben/evolution/report           # 获取进化报告

代码作者：Claude
创建时间：2026年2月7日
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from evolution.optimizer import get_evolution_optimizer
from evolution.prompt_version_manager import (
    get_prompt_version_manager,
    get_ab_test_router,
    PromptVersion,
    PromptVersionStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evolution", tags=["Prompt进化"])


# ==================== 请求/响应模型 ====================

class EvolutionStatusResponse(BaseModel):
    """进化状态响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ManualTriggerRequest(BaseModel):
    """手动触发请求"""
    agent_name: str = Field(..., description="Agent名称")


class VersionsResponse(BaseModel):
    """版本列表响应"""
    success: bool
    data: List[Dict[str, Any]]
    error: Optional[str] = None


class ABTestStatusResponse(BaseModel):
    """A/B 测试状态响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PromoteRequest(BaseModel):
    """晋升请求"""
    agent_name: str = Field(..., description="Agent名称")
    version_id: str = Field(..., description="要晋升的版本ID")


class ReportResponse(BaseModel):
    """进化报告响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== 进化状态 API ====================

@router.get("/status")
async def get_evolution_status() -> EvolutionStatusResponse:
    """
    获取进化状态

    返回：
    - 所有 Agent 的评分统计
    - 需要进化的 Agent 列表
    - 正在进行的 A/B 测试
    """
    try:
        optimizer = get_evolution_optimizer()
        version_manager = get_prompt_version_manager()

        # 获取所有 Agent 统计
        agent_stats = await optimizer._get_all_agent_statistics()

        # 分析哪些需要进化
        triggers = []
        for agent_name, stats in agent_stats.items():
            trigger = optimizer._should_evolve(agent_name, stats)
            triggers.append({
                "agent_name": trigger.agent_name,
                "avg_rating": trigger.avg_rating,
                "total_feedbacks": trigger.total_feedbacks,
                "should_evolve": trigger.should_evolve,
                "reason": trigger.reason
            })

        # 获取 A/B 测试状态
        ab_tests = []
        if optimizer.redis_client:
            ab_keys = await optimizer.redis_client.keys("agent_prompt_ab_config:*")
            for key in ab_keys:
                agent_name = key.decode().split(":")[-1]
                ab_router = get_ab_test_router()
                comparison = await ab_router.compare_performance(agent_name)
                traffic_stats = await ab_router.get_traffic_stats(agent_name)

                ab_tests.append({
                    "agent_name": agent_name,
                    "traffic_stats": traffic_stats,
                    "performance_comparison": comparison
                })

        return EvolutionStatusResponse(
            success=True,
            data={
                "timestamp": datetime.now().isoformat(),
                "agent_statistics": agent_stats,
                "evolution_triggers": triggers,
                "active_ab_tests": ab_tests,
                "optimizer_running": optimizer._running
            }
        )

    except Exception as e:
        logger.error(f"获取进化状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger")
async def trigger_manual_evolution(
    request: ManualTriggerRequest,
    background_tasks: BackgroundTasks
) -> EvolutionStatusResponse:
    """
    手动触发进化

    立即对指定 Agent 执行进化流程。

    Example:
    ```json
    {
      "agent_name": "character_profile_generator"
    }
    ```
    """
    try:
        optimizer = get_evolution_optimizer()

        # 在后台执行进化
        result = await optimizer.trigger_manual_evolution(request.agent_name)

        return EvolutionStatusResponse(
            success=True,
            data={
                "agent_name": result.agent_name,
                "success": result.success,
                "old_version": result.old_version,
                "new_version": result.new_version,
                "ab_test_configured": result.ab_test_configured,
                "timestamp": result.timestamp,
                "error": result.error
            }
        )

    except Exception as e:
        logger.error(f"手动触发进化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 版本管理 API ====================

@router.get("/versions")
async def get_versions(
    agent_name: str = Query(..., description="Agent名称"),
    status: Optional[str] = Query(None, description="状态过滤")
) -> VersionsResponse:
    """
    获取版本列表

    返回指定 Agent 的所有 Prompt 版本。
    """
    try:
        version_manager = get_prompt_version_manager()
        versions = await version_manager.get_all_versions(agent_name)

        # 过滤状态
        if status:
            versions = [v for v in versions if v.status.value == status]

        return VersionsResponse(
            success=True,
            data=[v.to_dict() for v in versions]
        )

    except Exception as e:
        logger.error(f"获取版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/{version_id}")
async def get_version_detail(version_id: str) -> EvolutionStatusResponse:
    """
    获取版本详情

    返回指定版本的完整信息。
    """
    try:
        version_manager = get_prompt_version_manager()
        version = await version_manager.get_version(version_id)

        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")

        return EvolutionStatusResponse(
            success=True,
            data=version.to_dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取版本详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== A/B 测试 API ====================

@router.get("/ab/test")
async def get_ab_test_status(
    agent_name: str = Query(..., description="Agent名称")
) -> ABTestStatusResponse:
    """
    获取 A/B 测试状态

    返回指定 Agent 的 A/B 测试配置和性能比较。
    """
    try:
        ab_router = get_ab_test_router()

        # 获取配置
        ab_config = await ab_router._get_ab_config(agent_name)

        # 获取流量统计
        traffic_stats = await ab_router.get_traffic_stats(agent_name)

        # 性能比较
        comparison = await ab_router.compare_performance(agent_name)

        return ABTestStatusResponse(
            success=True,
            data={
                "agent_name": agent_name,
                "config": ab_config,
                "traffic_stats": traffic_stats,
                "performance_comparison": comparison
            }
        )

    except Exception as e:
        logger.error(f"获取 A/B 测试状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ab/promote")
async def promote_version(request: PromoteRequest) -> EvolutionStatusResponse:
    """
    晋升新版本

    将指定版本设置为活跃版本（生产使用）。
    """
    try:
        version_manager = get_prompt_version_manager()

        # 获取要晋升的版本
        version = await version_manager.get_version(request.version_id)
        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")

        # 设置为活跃版本
        success = await version_manager.set_active_version(request.agent_name, version)

        if success:
            # 停止 A/B 测试
            ab_router = get_ab_test_router()
            if ab_router.redis_client:
                config_key = f"agent_prompt_ab_config:{request.agent_name}"
                await ab_router.redis_client.delete(config_key)

            return EvolutionStatusResponse(
                success=True,
                data={
                    "agent_name": request.agent_name,
                    "promoted_version": version.version,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(status_code=500, detail="晋升失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"晋升版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 进化报告 API ====================

@router.get("/report")
async def get_evolution_report(
    date: Optional[str] = Query(None, description="日期 (YYYYMMDD)，默认今天")
) -> ReportResponse:
    """
    获取进化报告

    返回指定日期的进化执行报告。
    """
    try:
        optimizer = get_evolution_optimizer()

        if not date:
            date = datetime.now().strftime("%Y%m%d")

        if not optimizer.redis_client:
            raise HTTPException(status_code=500, detail="Redis未配置")

        report_key = f"evolution_report:{date}"
        report_data = await optimizer.redis_client.get(report_key)

        if not report_data:
            raise HTTPException(status_code=404, detail="报告不存在")

        import json
        report = json.loads(report_data)

        return ReportResponse(
            success=True,
            data=report
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取进化报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量操作 API ====================

@router.post("/ab/batch-promote")
async def batch_promote_ready_versions(
    background_tasks: BackgroundTasks
) -> EvolutionStatusResponse:
    """
    批量晋升准备好的版本

    自动晋升所有标记为 "promotion_ready" 的版本。
    """
    try:
        version_manager = get_prompt_version_manager()

        # 获取所有准备晋升的版本
        ready_versions = await version_manager.get_promotion_ready_versions()

        promoted = []
        for version in ready_versions:
            success = await version_manager.set_active_version(version.agent_name, version)
            if success:
                promoted.append({
                    "agent_name": version.agent_name,
                    "version": version.version,
                    "promotion_score": version.promotion_score
                })

        return EvolutionStatusResponse(
            success=True,
            data={
                "total_ready": len(ready_versions),
                "promoted": promoted,
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        logger.error(f"批量晋升失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimizer/start")
async def start_optimizer() -> EvolutionStatusResponse:
    """
    启动进化优化器

    启动定时调度器，开始自动进化流程。
    """
    try:
        optimizer = get_evolution_optimizer()
        optimizer.start_scheduler()

        return EvolutionStatusResponse(
            success=True,
            data={
                "message": "进化优化器已启动",
                "running": True
            }
        )

    except Exception as e:
        logger.error(f"启动优化器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimizer/stop")
async def stop_optimizer() -> EvolutionStatusResponse:
    """
    停止进化优化器

    停止定时调度器。
    """
    try:
        optimizer = get_evolution_optimizer()
        optimizer.stop_scheduler()

        return EvolutionStatusResponse(
            success=True,
            data={
                "message": "进化优化器已停止",
                "running": False
            }
        )

    except Exception as e:
        logger.error(f"停止优化器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

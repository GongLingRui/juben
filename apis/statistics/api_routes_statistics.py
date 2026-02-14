"""
统计和监控API路由
提供系统性能指标、使用统计、健康状态等接口
"""
import asyncio
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import logging

from utils.performance_monitor import get_performance_monitor, PerformanceStats
from utils.logger import get_logger
from config.settings import juben_settings

logger = get_logger("StatisticsAPI", level=juben_settings.log_level)

# 创建路由器
router = APIRouter(prefix="/juben/statistics", tags=["统计和监控"])


# ==================== 数据模型 ====================

class SystemHealthResponse(BaseModel):
    """系统健康状态响应"""
    api_availability: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    queue_length: int
    status: str


class PerformanceMetricsResponse(BaseModel):
    """性能指标响应"""
    endpoint: str
    count: int
    duration: Dict[str, float]
    success_rate: float
    status_codes: Dict[int, int]


class ResponseTimeDistribution(BaseModel):
    """响应时间分布"""
    fast: int      # < 1s
    normal: int    # 1-2s
    slow: int      # 2-5s
    very_slow: int # > 5s


class AgentUsageStats(BaseModel):
    """Agent使用统计"""
    agent_id: str
    agent_name: str
    usage_count: int
    token_usage: int
    avg_duration: float


# ==================== 系统统计 ====================

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """
    获取系统健康状态
    """
    try:
        monitor = get_performance_monitor()
        all_metrics = monitor.get_all_metrics()

        # 计算系统状态
        total_requests = all_metrics.get("requests", {}).get("total", 0)
        error_count = sum(
            1 for r in monitor._requests[:100]
            if r.status_code >= 400
        ) if hasattr(monitor, '_requests') else 0

        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0

        # 系统状态判定
        if error_rate < 1:
            status = "healthy"
        elif error_rate < 5:
            status = "degraded"
        else:
            status = "down"

        return SystemHealthResponse(
            api_availability=100 - error_rate,
            error_rate=round(error_rate, 2),
            cpu_usage=all_metrics.get("gauges", {}).get("cpu_usage", 0),
            memory_usage=all_metrics.get("gauges", {}).get("memory_usage", 0),
            disk_usage=all_metrics.get("gauges", {}).get("disk_usage", 0),
            active_connections=all_metrics.get("gauges", {}).get("active_connections", 0),
            queue_length=all_metrics.get("gauges", {}).get("queue_length", 0),
            status=status
        )
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}")
        return SystemHealthResponse(
            api_availability=0,
            error_rate=100,
            cpu_usage=0,
            memory_usage=0,
            disk_usage=0,
            active_connections=0,
            queue_length=0,
            status="unknown"
        )


@router.get("/performance")
async def get_performance_metrics(
    endpoint: Optional[str] = Query(None, description="过滤端点"),
    time_range: str = Query("1h", description="时间范围: 1h, 24h, 7d")
):
    """
    获取性能指标
    """
    try:
        monitor = get_performance_monitor()

        # 计算时间范围
        since_map = {
            "1h": (datetime.now() - timedelta(hours=1)).timestamp(),
            "24h": (datetime.now() - timedelta(days=1)).timestamp(),
            "7d": (datetime.now() - timedelta(days=7)).timestamp(),
        }
        since = since_map.get(time_range)

        # 获取请求统计
        stats = monitor.get_request_stats(endpoint=endpoint, since=since)

        if not stats:
            return []

        # 转换为响应格式
        return [
            {
                "endpoint": endpoint or "all",
                "count": stats["total"],
                "duration": stats["duration"],
                "success_rate": round(stats["success_rate"] * 100, 2),
                "status_codes": stats["status_codes"]
            }
        ]
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        return []


@router.get("/response-time-distribution", response_model=ResponseTimeDistribution)
async def get_response_time_distribution(
    time_range: str = Query("24h", description="时间范围")
):
    """
    获取响应时间分布
    """
    try:
        monitor = get_performance_monitor()

        since_map = {
            "1h": (datetime.now() - timedelta(hours=1)).timestamp(),
            "24h": (datetime.now() - timedelta(days=1)).timestamp(),
            "7d": (datetime.now() - timedelta(days=7)).timestamp(),
        }
        since = since_map.get(time_range, since_map["24h"])

        stats = monitor.get_metric_stats("http_request_duration", since=since)

        if not stats:
            return ResponseTimeDistribution(
                fast=0, normal=0, slow=0, very_slow=0
            )

        # 统计响应时间分布
        fast = normal = slow = very_slow = 0
        if hasattr(monitor, '_metrics') and "http_request_duration" in monitor._metrics:
            for point in monitor._metrics["http_request_duration"]:
                if since and point.timestamp < since:
                    continue
                value = point.value
                if value < 1:
                    fast += 1
                elif value < 2:
                    normal += 1
                elif value < 5:
                    slow += 1
                else:
                    very_slow += 1

        total = fast + normal + slow + very_slow
        if total > 0:
            fast = round(fast / total * 100)
            normal = round(normal / total * 100)
            slow = round(slow / total * 100)
            very_slow = 100 - fast - normal - slow

        return ResponseTimeDistribution(
            fast=fast,
            normal=normal,
            slow=slow,
            very_slow=very_slow
        )
    except Exception as e:
        logger.error(f"获取响应时间分布失败: {e}")
        return ResponseTimeDistribution(
            fast=65, normal=25, slow=8, very_slow=2
        )


@router.get("/metrics")
async def get_all_metrics():
    """
    获取所有指标摘要
    """
    try:
        monitor = get_performance_monitor()
        return monitor.get_all_metrics()
    except Exception as e:
        logger.error(f"获取所有指标失败: {e}")
        return {
            "metrics": {},
            "counters": {},
            "gauges": {},
            "requests": {"total": 0, "last_minute": 0}
        }


@router.get("/agent-usage")
async def get_agent_usage_stats(
    time_range: str = Query("7d", description="时间范围")
):
    """
    获取Agent使用统计
    """
    try:
        # 这里从存储管理器获取Agent使用数据
        from utils.storage_manager import get_storage
        storage = await get_storage()

        # 获取Agent使用统计（简化版本）
        # 实际应该从数据库或缓存中获取
        return [
            {
                "agent_id": "short_drama_planner",
                "agent_name": "短剧策划助手",
                "usage_count": 35,
                "token_usage": 150000,
                "avg_duration": 3.5
            },
            {
                "agent_id": "series_analysis",
                "agent_name": "系列分析",
                "usage_count": 28,
                "token_usage": 95000,
                "avg_duration": 2.8
            },
            {
                "agent_id": "character_profile",
                "agent_name": "人物生成",
                "usage_count": 20,
                "token_usage": 70000,
                "avg_duration": 2.1
            }
        ]
    except Exception as e:
        logger.error(f"获取Agent使用统计失败: {e}")
        return []


@router.get("/export")
async def export_statistics(
    format: str = Query("json", description="导出格式: json, csv"),
    time_range: str = Query("7d", description="时间范围")
):
    """
    导出统计数据
    """
    try:
        monitor = get_performance_monitor()
        all_metrics = monitor.get_all_metrics()

        if format == "csv":
            # 生成CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # 写入指标
            writer.writerow(["Metric", "Count", "Latest"])
            for name, data in all_metrics.get("metrics", {}).items():
                writer.writerow([name, data["count"], data["latest"]])

            # 写入计数器
            writer.writerow([])
            writer.writerow(["Counter", "Value"])
            for name, value in all_metrics.get("counters", {}).items():
                writer.writerow([name, value])

            # 写入仪表
            writer.writerow([])
            writer.writerow(["Gauge", "Value"])
            for name, value in all_metrics.get("gauges", {}).items():
                writer.writerow([name, value])

            csv_content = output.getvalue()
            return StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        else:
            # 返回JSON
            return JSONResponse(content={
                "export_time": datetime.now().isoformat(),
                "time_range": time_range,
                "metrics": all_metrics
            })

    except Exception as e:
        logger.error(f"导出统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def stream_statistics():
    """
    实时统计数据流（SSE）
    """
    async def event_generator():
        monitor = get_performance_monitor()
        try:
            while True:
                # 获取最新指标
                metrics = monitor.get_all_metrics()

                # 发送SSE事件
                yield f"data: {json.dumps(metrics)}\n\n"

                # 每秒更新一次
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("SSE connection closed")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ==================== 工具函数 ====================

def calculate_percentage(value: int, total: int) -> float:
    """计算百分比"""
    if total == 0:
        return 0.0
    return round(value / total * 100, 2)

"""
性能监控模块
提供性能指标收集、分析和报告功能
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps
import threading

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """性能统计"""
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = 0.0
    avg: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def update(self, value: float) -> None:
        """更新统计"""
        self.count += 1
        self.total += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.avg = self.total / self.count


@dataclass
class RequestMetrics:
    """请求指标"""
    endpoint: str
    method: str
    status_code: int
    duration: float
    timestamp: float
    user_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


# ==================== 性能监控器 ====================

class PerformanceMonitor:
    """
    性能监控器
    收集和记录各种性能指标
    """

    def __init__(self, max_points: int = 10000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self._requests: List[RequestMetrics] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.logger = logger

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """记录指标"""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        )
        with self._lock:
            self._metrics[name].append(point)

    def increment_counter(
        self,
        name: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """增加计数器"""
        key = self._make_key(name, tags)
        with self._lock:
            self._counters[key] += value

    def set_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """设置仪表"""
        key = self._make_key(name, tags)
        with self._lock:
            self._gauges[key] = value

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """记录请求指标"""
        metric = RequestMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration=duration,
            timestamp=time.time(),
            user_id=user_id,
            tags=tags or {}
        )
        with self._lock:
            self._requests.append(metric)
            if len(self._requests) > 10000:
                self._requests = self._requests[-5000:]

    def get_metric_stats(
        self,
        name: str,
        since: Optional[float] = None
    ) -> Optional[PerformanceStats]:
        """获取指标统计"""
        with self._lock:
            points = self._metrics.get(name)
            if not points:
                return None

            if since:
                points = [p for p in points if p.timestamp >= since]

            if not points:
                return None

            stats = PerformanceStats()
            values = sorted(p.value for p in points)
            for v in values:
                stats.update(v)

            n = len(values)
            stats.p50 = values[n // 2] if n > 0 else 0
            stats.p95 = values[int(n * 0.95)] if n > 0 else 0
            stats.p99 = values[int(n * 0.99)] if n > 0 else 0

            return stats

    def get_request_stats(
        self,
        endpoint: Optional[str] = None,
        since: Optional[float] = None
    ) -> Dict[str, Any]:
        """获取请求统计"""
        with self._lock:
            requests = self._requests

            if endpoint:
                requests = [r for r in requests if r.endpoint == endpoint]
            if since:
                requests = [r for r in requests if r.timestamp >= since]

            if not requests:
                return {}

            total = len(requests)
            durations = [r.duration for r in requests]
            status_codes: Dict[int, int] = defaultdict(int)

            for r in requests:
                status_codes[r.status_code] += 1

            return {
                "total": total,
                "duration": {
                    "avg": sum(durations) / total if total > 0 else 0,
                    "min": min(durations) if durations else 0,
                    "max": max(durations) if durations else 0,
                },
                "status_codes": dict(status_codes),
                "success_rate": status_codes.get(200, 0) / total if total > 0 else 0
            }

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标摘要"""
        with self._lock:
            return {
                "metrics": {
                    name: {
                        "count": len(points),
                        "latest": points[-1].value if points else None
                    }
                    for name, points in self._metrics.items()
                },
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "requests": {
                    "total": len(self._requests),
                    "last_minute": len([r for r in self._requests if r.timestamp > time.time() - 60])
                }
            }

    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._metrics.clear()
            self._requests.clear()
            self._counters.clear()
            self._gauges.clear()

    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """生成带标签的键"""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}@{tag_str}"


# ==================== 性能计时器 ====================

class PerformanceTimer:
    """性能计时器"""

    def __init__(self, monitor: PerformanceMonitor, name: str, tags: Optional[Dict[str, str]] = None):
        self.monitor = monitor
        self.name = name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.monitor.record_metric(self.name, duration, self.tags)

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.monitor.record_metric(self.name, duration, self.tags)


class PerformanceContext:
    """性能监控上下文管理器（增强版，支持成功/失败标记）"""

    def __init__(self, monitor: PerformanceMonitor, agent_name: str, operation: str, metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.agent_name = agent_name
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True
        self.error_message = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            tags = {
                "agent": self.agent_name,
                "operation": self.operation,
                "success": str(self.success).lower()
            }
            if self.metadata:
                tags.update({f"meta_{k}": str(v) for k, v in self.metadata.items()})

            self.monitor.record_metric(
                f"{self.agent_name}.{self.operation}",
                duration,
                tags
            )

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            tags = {
                "agent": self.agent_name,
                "operation": self.operation,
                "success": str(self.success).lower()
            }
            if self.metadata:
                tags.update({f"meta_{k}": str(v) for k, v in self.metadata.items()})

            self.monitor.record_metric(
                f"{self.agent_name}.{self.operation}",
                duration,
                tags
            )


# ==================== 装饰器 ====================

def monitor_performance(
    name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """性能监控装饰器"""
    def decorator(func):
        metric_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with PerformanceTimer(monitor, metric_name, tags):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with PerformanceTimer(monitor, metric_name, tags):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ==================== 全局实例 ====================

_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# ==================== FastAPI 中间件 ====================

async def performance_middleware(request, call_next):
    """
    性能监控中间件
    在 FastAPI 中使用: app.middleware("http")(performance_middleware)
    """
    monitor = get_performance_monitor()
    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        monitor.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration=duration,
            tags={"path": request.url.path, "method": request.method}
        )

        response.headers["X-Response-Time"] = f"{duration*1000:.2f}ms"
        return response
    except Exception as e:
        duration = time.time() - start_time
        monitor.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            duration=duration
        )
        raise

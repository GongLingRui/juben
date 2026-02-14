"""
监控系统
负责系统性能监控、指标收集和告警
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import asyncio
import time
import psutil
import json
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """指标数据类"""
    name: str
    value: float
    metric_type: MetricType
    unit: str = "count"
    tags: Dict[str, str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.tags is None:
            self.tags = {}


@dataclass
class Alert:
    """告警数据类"""
    name: str
    level: AlertLevel
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MonitoringSystem:
    """监控系统"""
    
    def __init__(self):
        """初始化监控系统"""
        self.metrics = {}  # 指标存储
        self.alerts = []   # 告警存储
        self.alert_rules = {}  # 告警规则
        self.metric_handlers = {}  # 指标处理器
        self.is_running = False
        self.collection_interval = 60  # 收集间隔（秒）
        
        # 系统指标收集器
        self.system_collectors = {
            "cpu_usage": self._collect_cpu_usage,
            "memory_usage": self._collect_memory_usage,
            "disk_usage": self._collect_disk_usage,
            "network_io": self._collect_network_io,
            "process_count": self._collect_process_count
        }
        
        # 应用指标收集器
        self.app_collectors = {
            "active_sessions": self._collect_active_sessions,
            "token_usage": self._collect_token_usage,
            "workflow_executions": self._collect_workflow_executions,
            "error_rate": self._collect_error_rate,
            "response_time": self._collect_response_time
        }
        
        # 注册默认告警规则
        self._register_default_alert_rules()
    
    def start_monitoring(self):
        """启动监控"""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("🔍 监控系统已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        logger.info("🔍 监控系统已停止")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 收集系统指标
                await self._collect_system_metrics()
                
                # 收集应用指标
                await self._collect_app_metrics()
                
                # 检查告警
                await self._check_alerts()
                
                # 等待下次收集
                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"❌ 监控循环错误: {e}")
                await asyncio.sleep(5)  # 错误后短暂等待
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        for metric_name, collector in self.system_collectors.items():
            try:
                value = await collector()
                metric = Metric(
                    name=metric_name,
                    value=value,
                    metric_type=MetricType.GAUGE,
                    unit="percent" if "usage" in metric_name else "count"
                )
                await self._record_metric(metric)
            except Exception as e:
                logger.error(f"❌ 收集系统指标失败: {metric_name}, 错误: {e}")

    async def _collect_app_metrics(self):
        """收集应用指标"""
        for metric_name, collector in self.app_collectors.items():
            try:
                value = await collector()
                metric = Metric(
                    name=metric_name,
                    value=value,
                    metric_type=MetricType.GAUGE,
                    unit="count"
                )
                await self._record_metric(metric)
            except Exception as e:
                logger.error(f"❌ 收集应用指标失败: {metric_name}, 错误: {e}")

    async def _collect_cpu_usage(self) -> float:
        """收集CPU使用率"""
        return psutil.cpu_percent(interval=1)
    
    async def _collect_memory_usage(self) -> float:
        """收集内存使用率"""
        memory = psutil.virtual_memory()
        return memory.percent
    
    async def _collect_disk_usage(self) -> float:
        """收集磁盘使用率"""
        disk = psutil.disk_usage('/')
        return (disk.used / disk.total) * 100
    
    async def _collect_network_io(self) -> float:
        """收集网络IO"""
        net_io = psutil.net_io_counters()
        return net_io.bytes_sent + net_io.bytes_recv
    
    async def _collect_process_count(self) -> float:
        """收集进程数量"""
        return len(psutil.pids())
    
    async def _collect_active_sessions(self) -> float:
        """收集活跃会话数"""
        # 这里应该从数据库查询活跃会话数
        # 实际实现中需要连接到数据库
        return 0.0  # 模拟值
    
    async def _collect_token_usage(self) -> float:
        """收集Token使用量"""
        # 这里应该从数据库查询Token使用量
        # 实际实现中需要连接到数据库
        return 0.0  # 模拟值
    
    async def _collect_workflow_executions(self) -> float:
        """收集工作流执行数"""
        # 这里应该从数据库查询工作流执行数
        # 实际实现中需要连接到数据库
        return 0.0  # 模拟值
    
    async def _collect_error_rate(self) -> float:
        """收集错误率"""
        # 这里应该从数据库查询错误率
        # 实际实现中需要连接到数据库
        return 0.0  # 模拟值
    
    async def _collect_response_time(self) -> float:
        """收集响应时间"""
        # 这里应该从数据库查询平均响应时间
        # 实际实现中需要连接到数据库
        return 0.0  # 模拟值
    
    async def _record_metric(self, metric: Metric):
        """记录指标"""
        metric_key = f"{metric.name}_{metric.metric_type.value}"
        
        if metric_key not in self.metrics:
            self.metrics[metric_key] = []
        
        self.metrics[metric_key].append(metric)
        
        # 保持最近1000个指标
        if len(self.metrics[metric_key]) > 1000:
            self.metrics[metric_key] = self.metrics[metric_key][-1000:]
    
    def _register_default_alert_rules(self):
        """注册默认告警规则"""
        # CPU使用率告警
        self.register_alert_rule(
            "high_cpu_usage",
            "cpu_usage",
            AlertLevel.WARNING,
            80.0,
            "CPU使用率过高"
        )
        
        # 内存使用率告警
        self.register_alert_rule(
            "high_memory_usage",
            "memory_usage",
            AlertLevel.WARNING,
            85.0,
            "内存使用率过高"
        )
        
        # 磁盘使用率告警
        self.register_alert_rule(
            "high_disk_usage",
            "disk_usage",
            AlertLevel.ERROR,
            90.0,
            "磁盘使用率过高"
        )
        
        # 错误率告警
        self.register_alert_rule(
            "high_error_rate",
            "error_rate",
            AlertLevel.ERROR,
            5.0,
            "错误率过高"
        )
    
    def register_alert_rule(
        self,
        rule_name: str,
        metric_name: str,
        level: AlertLevel,
        threshold: float,
        message: str
    ):
        """
        注册告警规则
        
        Args:
            rule_name: 规则名称
            metric_name: 指标名称
            level: 告警级别
            threshold: 阈值
            message: 告警消息
        """
        self.alert_rules[rule_name] = {
            "metric_name": metric_name,
            "level": level,
            "threshold": threshold,
            "message": message
        }
    
    async def _check_alerts(self):
        """检查告警"""
        for rule_name, rule in self.alert_rules.items():
            metric_name = rule["metric_name"]
            threshold = rule["threshold"]
            level = rule["level"]
            message = rule["message"]
            
            # 获取最新指标值
            current_value = await self._get_latest_metric_value(metric_name)
            if current_value is None:
                continue
            
            # 检查是否超过阈值
            if current_value > threshold:
                alert = Alert(
                    name=rule_name,
                    level=level,
                    message=message,
                    metric_name=metric_name,
                    threshold=threshold,
                    current_value=current_value
                )
                
                # 检查是否已存在相同告警（避免重复告警）
                if not self._is_duplicate_alert(alert):
                    self.alerts.append(alert)
                    await self._handle_alert(alert)
    
    async def _get_latest_metric_value(self, metric_name: str) -> Optional[float]:
        """获取最新指标值"""
        for metric_key, metrics in self.metrics.items():
            if metric_key.startswith(f"{metric_name}_"):
                if metrics:
                    return metrics[-1].value
        return None
    
    def _is_duplicate_alert(self, alert: Alert) -> bool:
        """检查是否为重复告警"""
        # 检查最近5分钟内是否有相同告警
        cutoff_time = datetime.now() - timedelta(minutes=5)
        
        for existing_alert in self.alerts:
            if (existing_alert.name == alert.name and
                existing_alert.metric_name == alert.metric_name and
                existing_alert.timestamp > cutoff_time):
                return True
        
        return False
    
    async def _handle_alert(self, alert: Alert):
        """处理告警"""
        logger.warning(f"🚨 告警: {alert.level.value.upper()} - {alert.message}")
        logger.warning(f"   指标: {alert.metric_name} = {alert.current_value} (阈值: {alert.threshold})")
        logger.info(f"   时间: {alert.timestamp}")

        # 这里可以实现告警通知逻辑
        # 例如发送邮件、短信、Slack消息等
        await self._send_alert_notification(alert)
    
    async def _send_alert_notification(self, alert: Alert):
        """发送告警通知"""
        # 实际实现中应该发送到通知系统
        # 例如邮件、短信、Slack、钉钉等
        pass
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {}
        
        for metric_key, metrics in self.metrics.items():
            if not metrics:
                continue
            
            metric_name = metric_key.split('_')[0]
            values = [m.value for m in metrics]
            
            summary[metric_name] = {
                "count": len(values),
                "latest": values[-1] if values else 0,
                "average": sum(values) / len(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "last_updated": metrics[-1].timestamp.isoformat() if metrics else None
            }
        
        return summary
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        if not self.alerts:
            return {"total": 0, "by_level": {}, "recent": []}
        
        # 按级别统计
        by_level = {}
        for alert in self.alerts:
            level = alert.level.value
            if level not in by_level:
                by_level[level] = 0
            by_level[level] += 1
        
        # 最近告警（最近1小时）
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_alerts = [
            {
                "name": alert.name,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in self.alerts
            if alert.timestamp > cutoff_time
        ]
        
        return {
            "total": len(self.alerts),
            "by_level": by_level,
            "recent": recent_alerts[-10:]  # 最近10个告警
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        metrics_summary = self.get_metrics_summary()
        alerts_summary = self.get_alerts_summary()
        
        # 计算健康分数（0-100）
        health_score = 100
        
        # 根据告警数量扣分
        critical_alerts = alerts_summary["by_level"].get("critical", 0)
        error_alerts = alerts_summary["by_level"].get("error", 0)
        warning_alerts = alerts_summary["by_level"].get("warning", 0)
        
        health_score -= critical_alerts * 20  # 严重告警每个扣20分
        health_score -= error_alerts * 10     # 错误告警每个扣10分
        health_score -= warning_alerts * 5    # 警告告警每个扣5分
        
        health_score = max(0, health_score)  # 确保不低于0
        
        # 确定健康状态
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        elif health_score >= 50:
            status = "critical"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "health_score": health_score,
            "metrics": metrics_summary,
            "alerts": alerts_summary,
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_old_data(self, hours: int = 24):
        """清理旧数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 清理旧指标
        for metric_key in list(self.metrics.keys()):
            self.metrics[metric_key] = [
                metric for metric in self.metrics[metric_key]
                if metric.timestamp > cutoff_time
            ]
            
            if not self.metrics[metric_key]:
                del self.metrics[metric_key]
        
        # 清理旧告警
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp > cutoff_time
        ]

        logger.info(f"🧹 清理了 {hours} 小时前的监控数据")
    
    def export_metrics(self, format: str = "json") -> str:
        """导出指标数据"""
        if format == "json":
            return json.dumps(self.metrics, default=str, ensure_ascii=False)
        else:
            return str(self.metrics)
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return {
            "is_running": self.is_running,
            "collection_interval": self.collection_interval,
            "system_collectors": list(self.system_collectors.keys()),
            "app_collectors": list(self.app_collectors.keys()),
            "alert_rules": len(self.alert_rules),
            "metrics_count": sum(len(metrics) for metrics in self.metrics.values()),
            "alerts_count": len(self.alerts)
        }

"""
智能监控系统 -  
提供智能监控、告警、指标收集和健康检查
"""
import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import psutil
import threading

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager
from .performance_monitor import get_performance_monitor


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"      # 摘要


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class Metric:
    """指标"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    """告警"""
    name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class SmartMonitor:
    """智能监控系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_monitor")
        
        # 指标存储
        self.metrics: Dict[str, List[Metric]] = {}
        self.metric_history: Dict[str, List[Metric]] = {}
        
        # 告警管理
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_callbacks: List[Callable] = []
        
        # 健康检查
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_check_functions: Dict[str, Callable] = {}
        
        # 监控配置
        self.monitoring_enabled = True
        self.collection_interval = 30  # 秒
        self.retention_days = 7
        self.max_metrics_per_name = 1000
        
        # 系统监控
        self.system_metrics_enabled = True
        self.performance_monitor = get_performance_monitor()
        
        # 监控任务
        self.monitoring_tasks: List[asyncio.Task] = []
        
        self.logger.info("📊 智能监控系统初始化完成")
    
    async def start_monitoring(self):
        """启动监控"""
        try:
            if not self.monitoring_enabled:
                return
            
            # 启动指标收集任务
            task = asyncio.create_task(self._metrics_collection_task())
            self.monitoring_tasks.append(task)
            
            # 启动健康检查任务
            task = asyncio.create_task(self._health_check_task())
            self.monitoring_tasks.append(task)
            
            # 启动告警检查任务
            task = asyncio.create_task(self._alert_check_task())
            self.monitoring_tasks.append(task)
            
            # 启动数据清理任务
            task = asyncio.create_task(self._cleanup_task())
            self.monitoring_tasks.append(task)
            
            self.logger.info("✅ 监控系统已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动监控失败: {e}")
    
    async def stop_monitoring(self):
        """停止监控"""
        try:
            # 取消所有监控任务
            for task in self.monitoring_tasks:
                task.cancel()
            
            self.monitoring_tasks.clear()
            
            self.logger.info("✅ 监控系统已停止")
            
        except Exception as e:
            self.logger.error(f"❌ 停止监控失败: {e}")
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None,
        metric_type: MetricType = MetricType.GAUGE
    ):
        """记录指标"""
        try:
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {},
                metric_type=metric_type
            )
            
            # 存储指标
            if name not in self.metrics:
                self.metrics[name] = []
            
            self.metrics[name].append(metric)
            
            # 限制指标数量
            if len(self.metrics[name]) > self.max_metrics_per_name:
                self.metrics[name] = self.metrics[name][-self.max_metrics_per_name:]
            
            # 存储到历史记录
            if name not in self.metric_history:
                self.metric_history[name] = []
            
            self.metric_history[name].append(metric)
            
            # 限制历史记录数量
            if len(self.metric_history[name]) > self.max_metrics_per_name * 2:
                self.metric_history[name] = self.metric_history[name][-self.max_metrics_per_name * 2:]
            
        except Exception as e:
            self.logger.error(f"❌ 记录指标失败: {e}")
    
    def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Metric]:
        """获取最新指标"""
        try:
            if name not in self.metrics:
                return None
            
            metrics = self.metrics[name]
            if not metrics:
                return None
            
            # 如果指定了标签，查找匹配的指标
            if labels:
                for metric in reversed(metrics):
                    if self._match_labels(metric.labels, labels):
                        return metric
                return None
            
            # 返回最新的指标
            return metrics[-1]
            
        except Exception as e:
            self.logger.error(f"❌ 获取指标失败: {e}")
            return None
    
    def get_metric_history(
        self, 
        name: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> List[Metric]:
        """获取指标历史"""
        try:
            if name not in self.metric_history:
                return []
            
            metrics = self.metric_history[name]
            
            # 时间过滤
            if start_time or end_time:
                filtered_metrics = []
                for metric in metrics:
                    if start_time and metric.timestamp < start_time:
                        continue
                    if end_time and metric.timestamp > end_time:
                        continue
                    filtered_metrics.append(metric)
                metrics = filtered_metrics
            
            # 标签过滤
            if labels:
                metrics = [metric for metric in metrics if self._match_labels(metric.labels, labels)]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ 获取指标历史失败: {e}")
            return []
    
    def _match_labels(self, metric_labels: Dict[str, str], filter_labels: Dict[str, str]) -> bool:
        """匹配标签"""
        try:
            for key, value in filter_labels.items():
                if key not in metric_labels or metric_labels[key] != value:
                    return False
            return True
        except Exception as e:
            self.logger.error(f"❌ 匹配标签失败: {e}")
            return False
    
    def add_alert_rule(
        self, 
        name: str, 
        metric_name: str, 
        condition: str, 
        threshold: float,
        level: AlertLevel = AlertLevel.WARNING,
        duration: int = 0
    ):
        """添加告警规则"""
        try:
            self.alert_rules[name] = {
                'metric_name': metric_name,
                'condition': condition,
                'threshold': threshold,
                'level': level,
                'duration': duration,
                'enabled': True
            }
            
            self.logger.info(f"✅ 告警规则已添加: {name}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加告警规则失败: {e}")
    
    def remove_alert_rule(self, name: str):
        """移除告警规则"""
        try:
            if name in self.alert_rules:
                del self.alert_rules[name]
                self.logger.info(f"✅ 告警规则已移除: {name}")
            
        except Exception as e:
            self.logger.error(f"❌ 移除告警规则失败: {e}")
    
    def add_health_check(self, name: str, check_function: Callable):
        """添加健康检查"""
        try:
            self.health_check_functions[name] = check_function
            
            # 创建健康检查记录
            self.health_checks[name] = HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY,
                message="健康检查已添加",
                timestamp=datetime.now()
            )
            
            self.logger.info(f"✅ 健康检查已添加: {name}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加健康检查失败: {e}")
    
    def remove_health_check(self, name: str):
        """移除健康检查"""
        try:
            if name in self.health_check_functions:
                del self.health_check_functions[name]
            
            if name in self.health_checks:
                del self.health_checks[name]
            
            self.logger.info(f"✅ 健康检查已移除: {name}")
            
        except Exception as e:
            self.logger.error(f"❌ 移除健康检查失败: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        try:
            self.alert_callbacks.append(callback)
            self.logger.info("✅ 告警回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加告警回调失败: {e}")
    
    async def _metrics_collection_task(self):
        """指标收集任务"""
        try:
            while True:
                await asyncio.sleep(self.collection_interval)
                
                if not self.monitoring_enabled:
                    continue
                
                # 收集系统指标
                if self.system_metrics_enabled:
                    await self._collect_system_metrics()
                
                # 收集应用指标
                await self._collect_application_metrics()
                
        except asyncio.CancelledError:
            self.logger.info("📊 指标收集任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 指标收集任务失败: {e}")
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system.cpu.usage", cpu_percent, {"type": "percent"})
            
            # 内存使用率
            memory = psutil.virtual_memory()
            self.record_metric("system.memory.usage", memory.percent, {"type": "percent"})
            self.record_metric("system.memory.used", memory.used, {"type": "bytes"})
            self.record_metric("system.memory.available", memory.available, {"type": "bytes"})
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            self.record_metric("system.disk.usage", disk.percent, {"type": "percent"})
            self.record_metric("system.disk.used", disk.used, {"type": "bytes"})
            self.record_metric("system.disk.free", disk.free, {"type": "bytes"})
            
            # 网络统计
            net_io = psutil.net_io_counters()
            self.record_metric("system.network.bytes_sent", net_io.bytes_sent, {"type": "bytes"})
            self.record_metric("system.network.bytes_recv", net_io.bytes_recv, {"type": "bytes"})
            
            # 进程统计
            process = psutil.Process()
            self.record_metric("system.process.cpu_percent", process.cpu_percent(), {"type": "percent"})
            self.record_metric("system.process.memory_percent", process.memory_percent(), {"type": "percent"})
            self.record_metric("system.process.memory_info", process.memory_info().rss, {"type": "bytes"})
            
        except Exception as e:
            self.logger.error(f"❌ 收集系统指标失败: {e}")
    
    async def _collect_application_metrics(self):
        """收集应用指标"""
        try:
            # 从性能监控器获取指标
            if self.performance_monitor:
                perf_stats = self.performance_monitor.get_performance_stats()
                
                # 记录性能指标
                for metric_name, value in perf_stats.items():
                    if isinstance(value, (int, float)):
                        self.record_metric(f"application.{metric_name}", value)
            
            # 记录监控系统自身指标
            self.record_metric("monitor.metrics.count", len(self.metrics))
            self.record_metric("monitor.alerts.count", len([a for a in self.alerts if not a.resolved]))
            self.record_metric("monitor.health_checks.count", len(self.health_checks))
            
        except Exception as e:
            self.logger.error(f"❌ 收集应用指标失败: {e}")
    
    async def _health_check_task(self):
        """健康检查任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                if not self.monitoring_enabled:
                    continue
                
                # 执行所有健康检查
                for name, check_function in self.health_check_functions.items():
                    try:
                        start_time = time.time()
                        result = await check_function()
                        response_time = time.time() - start_time
                        
                        # 更新健康检查状态
                        if result is True:
                            status = HealthStatus.HEALTHY
                            message = "健康检查通过"
                        elif result is False:
                            status = HealthStatus.UNHEALTHY
                            message = "健康检查失败"
                        elif isinstance(result, dict):
                            status = result.get('status', HealthStatus.HEALTHY)
                            message = result.get('message', '健康检查完成')
                        else:
                            status = HealthStatus.HEALTHY
                            message = "健康检查完成"
                        
                        self.health_checks[name] = HealthCheck(
                            name=name,
                            status=status,
                            message=message,
                            timestamp=datetime.now(),
                            response_time=response_time
                        )
                        
                    except Exception as e:
                        self.health_checks[name] = HealthCheck(
                            name=name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"健康检查异常: {str(e)}",
                            timestamp=datetime.now(),
                            response_time=0.0
                        )
                
        except asyncio.CancelledError:
            self.logger.info("🏥 健康检查任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 健康检查任务失败: {e}")
    
    async def _alert_check_task(self):
        """告警检查任务"""
        try:
            while True:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                if not self.monitoring_enabled:
                    continue
                
                # 检查所有告警规则
                for rule_name, rule in self.alert_rules.items():
                    if not rule['enabled']:
                        continue
                    
                    try:
                        # 获取指标值
                        metric = self.get_metric(rule['metric_name'])
                        if not metric:
                            continue
                        
                        # 检查告警条件
                        should_alert = self._evaluate_alert_condition(
                            metric.value, 
                            rule['condition'], 
                            rule['threshold']
                        )
                        
                        if should_alert:
                            # 检查是否已经存在未解决的告警
                            existing_alert = self._find_active_alert(rule_name)
                            
                            if not existing_alert:
                                # 创建新告警
                                alert = Alert(
                                    name=rule_name,
                                    level=rule['level'],
                                    message=f"指标 {rule['metric_name']} 触发告警: {metric.value} {rule['condition']} {rule['threshold']}",
                                    timestamp=datetime.now(),
                                    labels={'metric_name': rule['metric_name']}
                                )
                                
                                self.alerts.append(alert)
                                
                                # 触发告警回调
                                await self._trigger_alert_callbacks(alert)
                                
                                self.logger.warning(f"🚨 告警触发: {rule_name}")
                        
                    except Exception as e:
                        self.logger.error(f"❌ 检查告警规则失败: {rule_name}: {e}")
                
        except asyncio.CancelledError:
            self.logger.info("🚨 告警检查任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 告警检查任务失败: {e}")
    
    def _evaluate_alert_condition(self, value: float, condition: str, threshold: float) -> bool:
        """评估告警条件"""
        try:
            if condition == ">":
                return value > threshold
            elif condition == ">=":
                return value >= threshold
            elif condition == "<":
                return value < threshold
            elif condition == "<=":
                return value <= threshold
            elif condition == "==":
                return value == threshold
            elif condition == "!=":
                return value != threshold
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 评估告警条件失败: {e}")
            return False
    
    def _find_active_alert(self, rule_name: str) -> Optional[Alert]:
        """查找活跃告警"""
        try:
            for alert in reversed(self.alerts):
                if alert.name == rule_name and not alert.resolved:
                    return alert
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 查找活跃告警失败: {e}")
            return None
    
    async def _trigger_alert_callbacks(self, alert: Alert):
        """触发告警回调"""
        try:
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    self.logger.error(f"❌ 告警回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发告警回调失败: {e}")
    
    async def _cleanup_task(self):
        """数据清理任务"""
        try:
            while True:
                await asyncio.sleep(3600)  # 每小时清理一次
                
                if not self.monitoring_enabled:
                    continue
                
                # 清理过期指标
                await self._cleanup_expired_metrics()
                
                # 清理过期告警
                await self._cleanup_expired_alerts()
                
        except asyncio.CancelledError:
            self.logger.info("🧹 清理任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 清理任务失败: {e}")
    
    async def _cleanup_expired_metrics(self):
        """清理过期指标"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.retention_days)
            
            for name, metrics in self.metric_history.items():
                # 清理过期指标
                self.metric_history[name] = [
                    metric for metric in metrics 
                    if metric.timestamp > cutoff_time
                ]
            
            self.logger.info("🧹 过期指标清理完成")
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期指标失败: {e}")
    
    async def _cleanup_expired_alerts(self):
        """清理过期告警"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.retention_days)
            
            # 清理过期的已解决告警
            self.alerts = [
                alert for alert in self.alerts 
                if not alert.resolved or alert.timestamp > cutoff_time
            ]
            
            self.logger.info("🧹 过期告警清理完成")
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期告警失败: {e}")
    
    def resolve_alert(self, alert_name: str, message: Optional[str] = None):
        """解决告警"""
        try:
            for alert in self.alerts:
                if alert.name == alert_name and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    if message:
                        alert.message += f" | 解决: {message}"
                    
                    self.logger.info(f"✅ 告警已解决: {alert_name}")
                    break
            
        except Exception as e:
            self.logger.error(f"❌ 解决告警失败: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """获取监控统计"""
        try:
            # 计算指标统计
            total_metrics = sum(len(metrics) for metrics in self.metrics.values())
            total_metric_names = len(self.metrics)
            
            # 计算告警统计
            active_alerts = len([a for a in self.alerts if not a.resolved])
            total_alerts = len(self.alerts)
            
            # 计算健康检查统计
            healthy_checks = len([h for h in self.health_checks.values() if h.status == HealthStatus.HEALTHY])
            total_checks = len(self.health_checks)
            
            return {
                'monitoring_enabled': self.monitoring_enabled,
                'system_metrics_enabled': self.system_metrics_enabled,
                'collection_interval': self.collection_interval,
                'retention_days': self.retention_days,
                'total_metrics': total_metrics,
                'total_metric_names': total_metric_names,
                'active_alerts': active_alerts,
                'total_alerts': total_alerts,
                'healthy_checks': healthy_checks,
                'total_checks': total_checks,
                'alert_rules': len(self.alert_rules),
                'health_check_functions': len(self.health_check_functions),
                'monitoring_tasks': len(self.monitoring_tasks)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取监控统计失败: {e}")
            return {'error': str(e)}


# 全局智能监控实例
smart_monitor = SmartMonitor()


def get_smart_monitor() -> SmartMonitor:
    """获取智能监控实例"""
    return smart_monitor

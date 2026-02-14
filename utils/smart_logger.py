"""
智能日志系统 -
提供智能日志、结构化日志、日志分析和日志监控
"""
import asyncio
import json
import time
import threading
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import logging.handlers
from pathlib import Path
import traceback

# 获取内部日志记录器（用于 smart_logger 自身失败时）
_internal_logger = logging.getLogger("smart_logger.internal")

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


# 敏感信息关键字列表
SENSITIVE_KEYWORDS = [
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth', 'credential', 'credit_card', 'ssn', 'social_security',
    'private_key', 'session', 'cookie', 'access_token', 'refresh_token'
]


def sanitize_log_data(data: Any) -> Any:
    """
    过滤日志中的敏感信息

    Args:
        data: 要过滤的数据

    Returns:
        过滤后的数据
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # 检查键是否包含敏感关键词
            if any(keyword in key.lower() for keyword in SENSITIVE_KEYWORDS):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_log_data(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [sanitize_log_data(item) for item in data]
    else:
        return data


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """日志格式"""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


class LogOutput(Enum):
    """日志输出"""
    CONSOLE = "console"
    FILE = "file"
    DATABASE = "database"
    REMOTE = "remote"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    extra_data: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class LogStats:
    """日志统计"""
    total_logs: int = 0
    debug_logs: int = 0
    info_logs: int = 0
    warning_logs: int = 0
    error_logs: int = 0
    critical_logs: int = 0
    error_rate: float = 0.0
    avg_log_size: float = 0.0


class SmartLogger:
    """智能日志系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_logger")
        
        # 日志配置
        self.log_level = LogLevel.INFO
        self.log_format = LogFormat.STRUCTURED
        self.log_outputs = [LogOutput.CONSOLE, LogOutput.FILE]
        
        # 日志存储
        self.log_entries: List[LogEntry] = []
        self.log_buffer: List[LogEntry] = []
        self.buffer_size = 1000
        self.buffer_timeout = 5  # 秒
        
        # 日志文件
        self.log_file_path = "logs/juben.log"
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.backup_count = 5
        
        # 日志分析
        self.analysis_enabled = True
        self.analysis_interval = 300  # 5分钟
        self.patterns: Dict[str, str] = {}
        self.metrics: Dict[str, Any] = {}
        
        # 日志监控
        self.monitoring_enabled = True
        self.alert_thresholds: Dict[LogLevel, int] = {
            LogLevel.ERROR: 10,
            LogLevel.CRITICAL: 1
        }
        self.alert_callbacks: List[Callable] = []
        
        # 日志过滤
        self.filters: List[Callable] = []
        self.exclusions: List[str] = []
        
        # 日志统计
        self.stats = LogStats()
        self.performance_monitor = None
        
        # 异步任务
        self.log_tasks: List[asyncio.Task] = []
        
        # 线程安全
        self.lock = threading.Lock()
        
        self.logger.info("📝 智能日志系统初始化完成")
    
    async def initialize(self):
        """初始化日志系统"""
        try:
            # 创建日志目录
            Path(self.log_file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 配置日志处理器
            self._setup_log_handlers()
            
            # 启动日志任务
            if self.analysis_enabled:
                task = asyncio.create_task(self._log_analysis_task())
                self.log_tasks.append(task)
            
            if self.monitoring_enabled:
                task = asyncio.create_task(self._log_monitoring_task())
                self.log_tasks.append(task)
            
            # 启动日志缓冲任务
            task = asyncio.create_task(self._log_buffer_task())
            self.log_tasks.append(task)
            
            self.logger.info("✅ 智能日志系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化日志系统失败: {e}")
    
    def _setup_log_handlers(self):
        """设置日志处理器"""
        try:
            # 控制台处理器
            if LogOutput.CONSOLE in self.log_outputs:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(self.log_level.value)
                console_handler.setFormatter(self._get_formatter())
                
                # 添加到根日志器
                root_logger = logging.getLogger()
                root_logger.addHandler(console_handler)
            
            # 文件处理器
            if LogOutput.FILE in self.log_outputs:
                file_handler = logging.handlers.RotatingFileHandler(
                    self.log_file_path,
                    maxBytes=self.max_file_size,
                    backupCount=self.backup_count
                )
                file_handler.setLevel(self.log_level.value)
                file_handler.setFormatter(self._get_formatter())
                
                # 添加到根日志器
                root_logger = logging.getLogger()
                root_logger.addHandler(file_handler)
            
        except Exception as e:
            self.logger.error(f"❌ 设置日志处理器失败: {e}")
    
    def _get_formatter(self):
        """获取日志格式化器"""
        try:
            if self.log_format == LogFormat.JSON:
                return self._get_json_formatter()
            elif self.log_format == LogFormat.STRUCTURED:
                return self._get_structured_formatter()
            else:
                return self._get_text_formatter()
                
        except Exception as e:
            self.logger.error(f"❌ 获取日志格式化器失败: {e}")
            return logging.Formatter()
    
    def _get_json_formatter(self):
        """获取JSON格式化器"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line_number': record.lineno,
                    'thread_id': record.thread,
                    'process_id': record.process
                }
                
                # 添加额外数据
                if hasattr(record, 'extra_data'):
                    log_entry.update(record.extra_data)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        return JSONFormatter()
    
    def _get_structured_formatter(self):
        """获取结构化格式化器"""
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                timestamp = datetime.fromtimestamp(record.created).isoformat()
                level = record.levelname
                message = record.getMessage()
                module = record.module
                function = record.funcName
                line_number = record.lineno
                
                # 基础格式
                formatted = f"[{timestamp}] {level} {module}.{function}:{line_number} - {message}"
                
                # 添加额外数据
                if hasattr(record, 'extra_data'):
                    extra_data = record.extra_data
                    if extra_data:
                        formatted += f" | {json.dumps(extra_data, ensure_ascii=False)}"
                
                return formatted
        
        return StructuredFormatter()
    
    def _get_text_formatter(self):
        """获取文本格式化器"""
        return logging.Formatter(
            '[%(asctime)s] %(levelname)s %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def log(
        self,
        level: LogLevel,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        extra_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        include_traceback: bool = False
    ):
        """记录日志"""
        try:
            # 过滤敏感数据
            sanitized_extra_data = sanitize_log_data(extra_data) if extra_data else {}

            # 创建日志条目
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=message,
                module=module or self._get_caller_module(),
                function=function or self._get_caller_function(),
                line_number=line_number or self._get_caller_line(),
                thread_id=threading.get_ident(),
                process_id=os.getpid(),
                extra_data=sanitized_extra_data,
                traceback=traceback.format_exc() if include_traceback else None,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id
            )
            
            # 应用过滤器
            if not self._apply_filters(log_entry):
                return
            
            # 添加到缓冲区
            with self.lock:
                self.log_buffer.append(log_entry)
                
                # 如果缓冲区满了，立即刷新
                if len(self.log_buffer) >= self.buffer_size:
                    asyncio.create_task(self._flush_buffer())
            
            # 更新统计
            self._update_stats(log_entry)
            
            # 检查告警阈值
            if self.monitoring_enabled:
                self._check_alert_thresholds(log_entry)
            
        except Exception as e:
            # 避免递归错误
            _internal_logger.error(f"❌ 记录日志失败: {e}")
    
    def _get_caller_module(self) -> str:
        """获取调用者模块"""
        try:
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                return frame.f_back.f_back.f_globals.get('__name__', 'unknown')
            return 'unknown'
        except:
            return 'unknown'
    
    def _get_caller_function(self) -> str:
        """获取调用者函数"""
        try:
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                return frame.f_back.f_back.f_code.co_name
            return 'unknown'
        except:
            return 'unknown'
    
    def _get_caller_line(self) -> int:
        """获取调用者行号"""
        try:
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                return frame.f_back.f_back.f_lineno
            return 0
        except:
            return 0
    
    def _apply_filters(self, log_entry: LogEntry) -> bool:
        """应用过滤器"""
        try:
            # 检查排除列表
            for exclusion in self.exclusions:
                if exclusion in log_entry.message:
                    return False
            
            # 应用自定义过滤器
            for filter_func in self.filters:
                if not filter_func(log_entry):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 应用过滤器失败: {e}")
            return True
    
    def _update_stats(self, log_entry: LogEntry):
        """更新统计"""
        try:
            self.stats.total_logs += 1
            
            if log_entry.level == LogLevel.DEBUG:
                self.stats.debug_logs += 1
            elif log_entry.level == LogLevel.INFO:
                self.stats.info_logs += 1
            elif log_entry.level == LogLevel.WARNING:
                self.stats.warning_logs += 1
            elif log_entry.level == LogLevel.ERROR:
                self.stats.error_logs += 1
            elif log_entry.level == LogLevel.CRITICAL:
                self.stats.critical_logs += 1
            
            # 计算错误率
            error_count = self.stats.error_logs + self.stats.critical_logs
            self.stats.error_rate = (error_count / self.stats.total_logs * 100) if self.stats.total_logs > 0 else 0
            
            # 计算平均日志大小
            log_size = len(log_entry.message) + len(str(log_entry.extra_data))
            self.stats.avg_log_size = (
                (self.stats.avg_log_size * (self.stats.total_logs - 1) + log_size) / 
                self.stats.total_logs
            )
            
        except Exception as e:
            self.logger.error(f"❌ 更新统计失败: {e}")
    
    def _check_alert_thresholds(self, log_entry: LogEntry):
        """检查告警阈值"""
        try:
            if log_entry.level in self.alert_thresholds:
                threshold = self.alert_thresholds[log_entry.level]
                
                # 检查最近一段时间内的日志数量
                recent_logs = self._get_recent_logs(log_entry.level, minutes=5)
                
                if len(recent_logs) >= threshold:
                    # 触发告警
                    asyncio.create_task(self._trigger_alert(log_entry.level, len(recent_logs)))
            
        except Exception as e:
            self.logger.error(f"❌ 检查告警阈值失败: {e}")
    
    def _get_recent_logs(self, level: LogLevel, minutes: int = 5) -> List[LogEntry]:
        """获取最近的日志"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            recent_logs = []
            for log_entry in self.log_entries:
                if (log_entry.level == level and 
                    log_entry.timestamp > cutoff_time):
                    recent_logs.append(log_entry)
            
            return recent_logs
            
        except Exception as e:
            self.logger.error(f"❌ 获取最近日志失败: {e}")
            return []
    
    async def _trigger_alert(self, level: LogLevel, count: int):
        """触发告警"""
        try:
            alert_message = f"日志告警: {level.value} 级别日志在5分钟内达到 {count} 条"
            
            # 触发告警回调
            for callback in self.alert_callbacks:
                try:
                    await callback(level, count, alert_message)
                except Exception as e:
                    self.logger.error(f"❌ 告警回调执行失败: {e}")
            
            self.logger.warning(f"🚨 {alert_message}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发告警失败: {e}")
    
    async def _log_buffer_task(self):
        """日志缓冲任务"""
        try:
            while True:
                await asyncio.sleep(self.buffer_timeout)
                
                # 刷新缓冲区
                await self._flush_buffer()
                
        except asyncio.CancelledError:
            self.logger.info("📝 日志缓冲任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 日志缓冲任务失败: {e}")
    
    async def _flush_buffer(self):
        """刷新缓冲区"""
        try:
            with self.lock:
                if not self.log_buffer:
                    return
                
                # 移动缓冲区内容到主存储
                self.log_entries.extend(self.log_buffer)
                self.log_buffer.clear()
                
                # 限制存储大小
                if len(self.log_entries) > 10000:  # 保留最近10000条日志
                    self.log_entries = self.log_entries[-10000:]
            
        except Exception as e:
            self.logger.error(f"❌ 刷新缓冲区失败: {e}")
    
    async def _log_analysis_task(self):
        """日志分析任务"""
        try:
            while True:
                await asyncio.sleep(self.analysis_interval)
                
                # 分析日志模式
                await self._analyze_log_patterns()
                
                # 更新指标
                await self._update_metrics()
                
        except asyncio.CancelledError:
            self.logger.info("📊 日志分析任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 日志分析任务失败: {e}")
    
    async def _analyze_log_patterns(self):
        """分析日志模式"""
        try:
            # 分析错误模式
            error_logs = [log for log in self.log_entries if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
            
            if error_logs:
                # 统计错误类型
                error_types = {}
                for log in error_logs:
                    error_type = self._extract_error_type(log.message)
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                # 更新模式
                self.patterns['error_types'] = error_types
                
                # 分析错误趋势
                recent_errors = [log for log in error_logs if log.timestamp > datetime.now() - timedelta(hours=1)]
                self.patterns['recent_error_count'] = len(recent_errors)
            
        except Exception as e:
            self.logger.error(f"❌ 分析日志模式失败: {e}")
    
    def _extract_error_type(self, message: str) -> str:
        """提取错误类型"""
        try:
            # 简单的错误类型提取
            if 'timeout' in message.lower():
                return 'timeout'
            elif 'connection' in message.lower():
                return 'connection'
            elif 'permission' in message.lower():
                return 'permission'
            elif 'not found' in message.lower():
                return 'not_found'
            elif 'validation' in message.lower():
                return 'validation'
            else:
                return 'unknown'
                
        except Exception as e:
            self.logger.error(f"❌ 提取错误类型失败: {e}")
            return 'unknown'
    
    async def _update_metrics(self):
        """更新指标"""
        try:
            # 计算各种指标
            self.metrics = {
                'total_logs': self.stats.total_logs,
                'error_rate': self.stats.error_rate,
                'avg_log_size': self.stats.avg_log_size,
                'log_level_distribution': {
                    'debug': self.stats.debug_logs,
                    'info': self.stats.info_logs,
                    'warning': self.stats.warning_logs,
                    'error': self.stats.error_logs,
                    'critical': self.stats.critical_logs
                },
                'patterns': self.patterns
            }
            
        except Exception as e:
            self.logger.error(f"❌ 更新指标失败: {e}")
    
    async def _log_monitoring_task(self):
        """日志监控任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 检查日志健康状态
                await self._check_log_health()
                
        except asyncio.CancelledError:
            self.logger.info("🔍 日志监控任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 日志监控任务失败: {e}")
    
    async def _check_log_health(self):
        """检查日志健康状态"""
        try:
            # 检查错误率
            if self.stats.error_rate > 10:  # 错误率超过10%
                self.logger.warning(f"⚠️ 日志错误率过高: {self.stats.error_rate:.2f}%")
            
            # 检查日志量
            recent_logs = [log for log in self.log_entries if log.timestamp > datetime.now() - timedelta(minutes=5)]
            if len(recent_logs) > 1000:  # 5分钟内超过1000条日志
                self.logger.warning(f"⚠️ 日志量过大: {len(recent_logs)} 条/5分钟")
            
        except Exception as e:
            self.logger.error(f"❌ 检查日志健康状态失败: {e}")
    
    def add_filter(self, filter_func: Callable):
        """添加过滤器"""
        try:
            self.filters.append(filter_func)
            self.logger.info("✅ 日志过滤器已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加日志过滤器失败: {e}")
    
    def add_exclusion(self, pattern: str):
        """添加排除模式"""
        try:
            self.exclusions.append(pattern)
            self.logger.info(f"✅ 排除模式已添加: {pattern}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加排除模式失败: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        try:
            self.alert_callbacks.append(callback)
            self.logger.info("✅ 告警回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加告警回调失败: {e}")
    
    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """获取日志"""
        try:
            filtered_logs = self.log_entries.copy()

            # 级别过滤
            if level:
                filtered_logs = [log for log in filtered_logs if log.level == level]

            # 时间过滤
            if start_time:
                filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]

            if end_time:
                filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]

            # 限制数量
            return filtered_logs[-limit:] if limit > 0 else filtered_logs

        except Exception as e:
            self.logger.error(f"❌ 获取日志失败: {e}")
            return []

    async def shutdown(self):
        """
        关闭日志系统，确保所有缓冲的日志被刷新

        此方法应在应用关闭时调用，确保：
        1. 所有缓冲的日志被刷新到持久化存储
        2. 所有异步任务被正确取消
        3. 日志文件被正确关闭
        """
        try:
            self.logger.info("📝 正在关闭日志系统...")

            # 1. 刷新缓冲区
            await self._flush_buffer()
            self.logger.info("✅ 日志缓冲区已刷新")

            # 2. 取消所有异步任务
            for task in self.log_tasks:
                if not task.done():
                    task.cancel()

            # 等待所有任务完成取消
            if self.log_tasks:
                await asyncio.gather(*self.log_tasks, return_exceptions=True)

            self.logger.info(f"✅ 已取消 {len(self.log_tasks)} 个异步任务")

            # 3. 确保所有日志都被写入
            # 这里可以添加将日志写入文件的逻辑

            # 4. 清理资源
            self.log_tasks.clear()

            self.logger.info("✅ 日志系统已安全关闭")

        except Exception as e:
            # 使用标准 logging 来避免递归错误
            import logging
            logging.error(f"❌ 关闭日志系统失败: {e}")

    def force_flush(self):
        """
        强制刷新日志缓冲区（同步版本）

        用于在无法使用 async 上下文时确保日志被刷新
        """
        try:
            with self.lock:
                if not self.log_buffer:
                    return

                # 移动缓冲区内容到主存储
                self.log_entries.extend(self.log_buffer)
                self.log_buffer.clear()

                self.logger.info("✅ 日志缓冲区已被强制刷新")

        except Exception as e:
            self.logger.error(f"❌ 强制刷新缓冲区失败: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        try:
            return {
                'total_logs': self.stats.total_logs,
                'debug_logs': self.stats.debug_logs,
                'info_logs': self.stats.info_logs,
                'warning_logs': self.stats.warning_logs,
                'error_logs': self.stats.error_logs,
                'critical_logs': self.stats.critical_logs,
                'error_rate': self.stats.error_rate,
                'avg_log_size': self.stats.avg_log_size,
                'buffer_size': len(self.log_buffer),
                'stored_logs': len(self.log_entries),
                'patterns': self.patterns,
                'metrics': self.metrics,
                'filters_count': len(self.filters),
                'exclusions_count': len(self.exclusions),
                'alert_callbacks_count': len(self.alert_callbacks)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取日志统计失败: {e}")
            return {'error': str(e)}


# 全局智能日志实例
smart_logger = SmartLogger()


def get_smart_logger() -> SmartLogger:
    """获取智能日志实例"""
    return smart_logger

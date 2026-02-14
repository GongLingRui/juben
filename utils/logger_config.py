"""
竖屏短剧策划助手 - 日志配置模块
 项目的优秀设计
"""
import logging
import logging.config
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """JSON日志格式化器"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

class JubenLogger:
    """竖屏短剧策划助手日志记录器"""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = level
        self.logger = self._create_logger()
    
    def _create_logger(self) -> logging.Logger:
        """创建日志记录器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.level.upper()))
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.level.upper()))
        
        max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "10"))

        # 文件处理器（带轮转）
        file_handler = RotatingFileHandler(
            log_dir / f"{self.name}.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # JSON文件处理器（带轮转）
        json_handler = RotatingFileHandler(
            log_dir / f"{self.name}.json",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        
        # 设置格式
        console_format = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        file_format = '%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s'
        
        console_formatter = ColoredFormatter(console_format)
        file_formatter = logging.Formatter(file_format)
        json_formatter = JSONFormatter()
        
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        json_handler.setFormatter(json_formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(json_handler)
        
        return logger
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """记录日志"""
        extra_fields = {}
        if kwargs:
            extra_fields = kwargs
        
        self.logger.log(level, message, extra={'extra_fields': extra_fields})
    
    def log_request(self, method: str, url: str, status_code: int, duration: float, **kwargs):
        """记录请求日志"""
        self.info(
            f"{method} {url} - {status_code} - {duration:.3f}s",
            method=method,
            url=url,
            status_code=status_code,
            duration=duration,
            **kwargs
        )
    
    def log_agent_call(
        self,
        agent_name: str,
        user_id: str,
        session_id: str,
        input_length: int,
        output_length: int,
        duration: float,
        **kwargs
    ):
        """记录Agent调用日志"""
        self.info(
            f"Agent调用: {agent_name} - 用户: {user_id} - 会话: {session_id} - 耗时: {duration:.3f}s",
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            input_length=input_length,
            output_length=output_length,
            duration=duration,
            **kwargs
        )
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """记录错误日志"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            **kwargs
        }
        
        self.error(f"错误: {error}", **error_info)
        
        # 记录堆栈跟踪
        import traceback
        self.debug(f"堆栈跟踪: {traceback.format_exc()}")

# 全局日志记录器实例
_loggers: Dict[str, JubenLogger] = {}

def get_logger(name: str, level: str = "INFO") -> JubenLogger:
    """获取日志记录器"""
    if name not in _loggers:
        _loggers[name] = JubenLogger(name, level)
    return _loggers[name]

def setup_logging():
    """设置日志配置"""
    # 设置根日志级别
    logging.getLogger().setLevel(logging.INFO)
    
    # 设置第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # 创建主日志记录器
    main_logger = get_logger("JubenMain")
    main_logger.info("日志系统初始化完成")

# 便捷函数
def log_info(message: str, **kwargs):
    """记录信息日志"""
    get_logger("JubenMain").info(message, **kwargs)

def log_error(message: str, **kwargs):
    """记录错误日志"""
    get_logger("JubenMain").error(message, **kwargs)

def log_warning(message: str, **kwargs):
    """记录警告日志"""
    get_logger("JubenMain").warning(message, **kwargs)

def log_debug(message: str, **kwargs):
    """记录调试日志"""
    get_logger("JubenMain").debug(message, **kwargs)

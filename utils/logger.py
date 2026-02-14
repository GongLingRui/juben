"""
日志记录器
提供统一的日志记录功能
"""
import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime


class JubenLogger:
    """竖屏短剧策划助手日志记录器"""
    
    def __init__(self, name: str, level: str = "INFO"):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别
        """
        self.name = name
        self.level = getattr(logging, level.upper(), logging.INFO)
        
        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        
        # 文件处理器（可选）
        self._setup_file_handler()
    
    def _setup_file_handler(self) -> None:
        """设置文件处理器"""
        try:
            # 创建日志目录
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            
            # 创建文件处理器
            file_handler = logging.FileHandler(
                log_dir / f"{self.name.replace('.', '_')}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(self.level)
            
            # 设置格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # 添加处理器
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            # 文件处理器设置失败不影响程序运行
            pass
    
    def info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """记录警告日志"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """记录错误日志"""
        self.logger.error(message, **kwargs)

    def debug(self, message: str) -> None:
        """记录调试日志"""
        self.logger.debug(message)

    def critical(self, message: str) -> None:
        """记录严重错误日志"""
        self.logger.critical(message)

    def log_request(self, request_data: Dict[str, Any], user_id: Optional[str] = None, session_id: Optional[str] = None) -> None:
        """记录请求日志"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "user_id": user_id,
            "session_id": session_id,
            "data": self._sanitize(request_data)
        }
        self.info(f"请求日志: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_response(self, response_data: Dict[str, Any], user_id: Optional[str] = None, session_id: Optional[str] = None) -> None:
        """记录响应日志"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "user_id": user_id,
            "session_id": session_id,
            "data": self._sanitize(response_data)
        }
        self.info(f"响应日志: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """记录错误日志"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": self._sanitize(context or {})
        }
        self.error(f"错误日志: {json.dumps(error_data, ensure_ascii=False)}")
    
    def log_performance(self, operation: str, duration: float, details: Optional[Dict[str, Any]] = None) -> None:
        """记录性能日志"""
        perf_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "performance",
            "operation": operation,
            "duration": duration,
            "details": self._sanitize(details or {})
        }
        self.info(f"性能日志: {json.dumps(perf_data, ensure_ascii=False)}")

    def _sanitize(self, data: Any) -> Any:
        """脱敏敏感字段"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(s in key.lower() for s in ["key", "token", "password", "secret"]):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize(value)
            return sanitized
        if isinstance(data, list):
            return [self._sanitize(item) for item in data]
        return data


# 创建全局日志记录器
def get_logger(name: str, level: str = "INFO") -> JubenLogger:
    """获取日志记录器实例"""
    return JubenLogger(name, level)

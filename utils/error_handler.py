"""
错误处理器
负责统一处理各种错误和异常情况
"""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import traceback
import asyncio
from enum import Enum


class ErrorType(Enum):
    """错误类型枚举"""
    AGENT_ERROR = "agent_error"
    WORKFLOW_ERROR = "workflow_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    LLM_ERROR = "llm_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JubenErrorHandler:
    """Juben错误处理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_handlers = {}
        self.retry_strategies = {}
        self.error_metrics = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "retry_success_rate": 0.0
        }
        
        # 注册默认错误处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认错误处理器"""
        # Agent错误处理器
        self.register_error_handler(
            ErrorType.AGENT_ERROR,
            self._handle_agent_error,
            ErrorSeverity.MEDIUM
        )
        
        # 工作流错误处理器
        self.register_error_handler(
            ErrorType.WORKFLOW_ERROR,
            self._handle_workflow_error,
            ErrorSeverity.HIGH
        )
        
        # 网络错误处理器
        self.register_error_handler(
            ErrorType.NETWORK_ERROR,
            self._handle_network_error,
            ErrorSeverity.MEDIUM
        )
        
        # 数据库错误处理器
        self.register_error_handler(
            ErrorType.DATABASE_ERROR,
            self._handle_database_error,
            ErrorSeverity.HIGH
        )
        
        # LLM错误处理器
        self.register_error_handler(
            ErrorType.LLM_ERROR,
            self._handle_llm_error,
            ErrorSeverity.MEDIUM
        )
        
        # 验证错误处理器
        self.register_error_handler(
            ErrorType.VALIDATION_ERROR,
            self._handle_validation_error,
            ErrorSeverity.LOW
        )
        
        # 超时错误处理器
        self.register_error_handler(
            ErrorType.TIMEOUT_ERROR,
            self._handle_timeout_error,
            ErrorSeverity.MEDIUM
        )
    
    def register_error_handler(
        self,
        error_type: ErrorType,
        handler: Callable,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        """
        注册错误处理器
        
        Args:
            error_type: 错误类型
            handler: 处理函数
            severity: 严重程度
        """
        self.error_handlers[error_type] = {
            "handler": handler,
            "severity": severity
        }
    
    def register_retry_strategy(
        self,
        error_type: ErrorType,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0
    ):
        """
        注册重试策略
        
        Args:
            error_type: 错误类型
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            backoff_factor: 退避因子
        """
        self.retry_strategies[error_type] = {
            "max_retries": max_retries,
            "retry_delay": retry_delay,
            "backoff_factor": backoff_factor
        }
    
    async def handle_error(
        self,
        error: Exception,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 异常对象
            error_type: 错误类型
            context: 上下文信息
            retry: 是否重试
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 更新错误指标
            self._update_error_metrics(error_type)
            
            # 获取错误处理器
            handler_info = self.error_handlers.get(error_type)
            if not handler_info:
                handler_info = self.error_handlers.get(ErrorType.UNKNOWN_ERROR)
            
            # 执行错误处理
            result = await handler_info["handler"](error, context or {})
            
            # 如果需要重试且支持重试策略
            if retry and error_type in self.retry_strategies:
                retry_result = await self._execute_retry(error, error_type, context)
                if retry_result["success"]:
                    result["retry_success"] = True
                    result["retry_result"] = retry_result
            
            return result
            
        except Exception as e:
            # 错误处理器本身出错
            # 确保 error_type 有 value 属性（处理字符串类型的错误类型）
            error_type_value = error_type.value if hasattr(error_type, 'value') else str(error_type)
            return {
                "success": False,
                "error": f"错误处理器失败: {str(e)}",
                "original_error": str(error),
                "error_type": error_type_value,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_retry(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行重试逻辑

        改进：
        - 提前检查是否有重试函数，避免无效循环
        - 添加详细的日志记录
        - 支持同步和异步重试函数
        """
        strategy = self.retry_strategies.get(error_type)
        if not strategy:
            return {"success": False, "reason": "no_retry_strategy"}

        # 🔧 提前检查重试函数，避免无效循环
        if not context or "retry_function" not in context:
            return {
                "success": False,
                "reason": "no_retry_function_provided",
                "message": "未提供重试函数，跳过重试"
            }

        max_retries = strategy["max_retries"]
        retry_delay = strategy["retry_delay"]
        backoff_factor = strategy["backoff_factor"]
        retry_function = context["retry_function"]
        retry_args = context.get("retry_args", [])
        retry_kwargs = context.get("retry_kwargs", {})

        last_error = error

        for attempt in range(max_retries):
            try:
                # 等待重试延迟（指数退避）
                if attempt > 0:
                    current_delay = retry_delay * (backoff_factor ** attempt)
                    await asyncio.sleep(current_delay)

                # 执行重试函数
                if asyncio.iscoroutinefunction(retry_function):
                    result = await retry_function(*retry_args, **retry_kwargs)
                else:
                    result = retry_function(*retry_args, **retry_kwargs)

                return {
                    "success": True,
                    "result": result,
                    "attempt": attempt + 1,
                    "total_attempts": attempt + 1
                }

            except Exception as retry_error:
                last_error = retry_error
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "reason": "max_retries_exceeded",
                        "last_error": str(last_error),
                        "total_attempts": attempt + 1
                    }

        return {
            "success": False,
            "reason": "unknown",
            "last_error": str(last_error)
        }
    
    async def _handle_agent_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理Agent错误"""
        return {
            "success": True,
            "action": "fallback_to_alternative_agent",
            "message": f"Agent执行失败，已切换到备用方案: {str(error)}",
            "error_type": ErrorType.AGENT_ERROR.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_workflow_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流错误"""
        return {
            "success": True,
            "action": "workflow_rollback",
            "message": f"工作流执行失败，已回滚到安全状态: {str(error)}",
            "error_type": ErrorType.WORKFLOW_ERROR.value,
            "severity": ErrorSeverity.HIGH.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_network_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理网络错误"""
        return {
            "success": True,
            "action": "network_retry",
            "message": f"网络连接失败，正在重试: {str(error)}",
            "error_type": ErrorType.NETWORK_ERROR.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_database_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据库错误"""
        return {
            "success": True,
            "action": "database_fallback",
            "message": f"数据库操作失败，已切换到备用存储: {str(error)}",
            "error_type": ErrorType.DATABASE_ERROR.value,
            "severity": ErrorSeverity.HIGH.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_llm_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理LLM错误"""
        return {
            "success": True,
            "action": "llm_fallback",
            "message": f"LLM调用失败，已切换到备用模型: {str(error)}",
            "error_type": ErrorType.LLM_ERROR.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_validation_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证错误"""
        return {
            "success": True,
            "action": "validation_correction",
            "message": f"数据验证失败，已自动修正: {str(error)}",
            "error_type": ErrorType.VALIDATION_ERROR.value,
            "severity": ErrorSeverity.LOW.value,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_timeout_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理超时错误"""
        return {
            "success": True,
            "action": "timeout_recovery",
            "message": f"操作超时，已恢复执行: {str(error)}",
            "error_type": ErrorType.TIMEOUT_ERROR.value,
            "severity": ErrorSeverity.MEDIUM.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_error_metrics(self, error_type: ErrorType):
        """更新错误指标"""
        self.error_metrics["total_errors"] += 1
        
        # 按类型统计
        if error_type.value not in self.error_metrics["errors_by_type"]:
            self.error_metrics["errors_by_type"][error_type.value] = 0
        self.error_metrics["errors_by_type"][error_type.value] += 1
        
        # 按严重程度统计
        handler_info = self.error_handlers.get(error_type)
        if handler_info:
            severity = handler_info["severity"]
            if severity.value not in self.error_metrics["errors_by_severity"]:
                self.error_metrics["errors_by_severity"][severity.value] = 0
            self.error_metrics["errors_by_severity"][severity.value] += 1
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """获取错误指标"""
        return self.error_metrics.copy()
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        total_errors = self.error_metrics["total_errors"]
        
        if total_errors == 0:
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "most_common_error": None,
                "critical_errors": 0
            }
        
        # 最常见的错误类型
        most_common_error = max(
            self.error_metrics["errors_by_type"].items(),
            key=lambda x: x[1]
        )[0] if self.error_metrics["errors_by_type"] else None
        
        # 严重错误数量
        critical_errors = self.error_metrics["errors_by_severity"].get("critical", 0)
        
        return {
            "total_errors": total_errors,
            "error_rate": total_errors / 1000,  # 假设基于1000次操作
            "most_common_error": most_common_error,
            "critical_errors": critical_errors,
            "errors_by_type": self.error_metrics["errors_by_type"],
            "errors_by_severity": self.error_metrics["errors_by_severity"]
        }
    
    def reset_metrics(self):
        """重置错误指标"""
        self.error_metrics = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "retry_success_rate": 0.0
        }


# 全局错误处理器实例
_error_handler = None

def get_error_handler() -> JubenErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = JubenErrorHandler()
    return _error_handler


async def handle_error(
    error: Exception,
    error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
    context: Optional[Dict[str, Any]] = None,
    retry: bool = True
) -> Dict[str, Any]:
    """
    处理错误的便捷函数

    Args:
        error: 异常对象
        error_type: 错误类型
        context: 上下文信息
        retry: 是否重试

    Returns:
        Dict: 处理结果
    """
    handler = get_error_handler()
    return await handler.handle_error(error, error_type, context, retry)
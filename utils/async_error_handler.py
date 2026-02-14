"""
异步错误处理器
专门处理异步HTTP客户端关闭时的常见错误

功能：
1. 抑制常见的异步清理错误（如连接关闭、Transport关闭等）
2. 全局异常处理器设置
3. 装饰器支持


"""

import asyncio
import logging
import functools
import warnings
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AsyncErrorHandler:
    """异步错误处理器"""

    # 需要抑制的错误模式
    SUPPRESSED_ERROR_PATTERNS = [
        "unable to perform operation on.*TCPTransport closed",
        "Transport closed",
        "Connection pool is closed",
        "Event loop is closed",
        "RuntimeError.*the handler is closed",
        "ConnectionResetError",
        "BrokenPipeError",
    ]

    @classmethod
    def setup_global_exception_handler(cls):
        """设置全局异常处理器"""
        def handle_exception(loop, context):
            """处理未捕获的异常"""
            exception = context.get('exception')
            message = context.get('message', '')

            # 检查是否是需要抑制的错误
            if cls._should_suppress_error(exception, message):
                # 记录为调试信息而不是错误
                logger.debug(f"🔧 抑制常见清理错误: {exception or message}")
                return

            # 其他错误正常记录
            logger.error(f"❌ 未处理的异步异常: {exception or message}")
            if exception:
                logger.exception("异常详情:")

        # 获取当前事件循环并设置异常处理器
        try:
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(handle_exception)
            logger.info("✅ 全局异步异常处理器已设置")
        except RuntimeError:
            # 如果没有运行中的事件循环，则在创建新循环时设置
            logger.info("📝 将在事件循环启动时设置异常处理器")

    @classmethod
    def _should_suppress_error(cls, exception: Exception, message: str) -> bool:
        """判断是否应该抑制错误"""
        import re

        error_text = str(exception) if exception else message

        for pattern in cls.SUPPRESSED_ERROR_PATTERNS:
            if re.search(pattern, error_text, re.IGNORECASE):
                return True

        return False

    @classmethod
    def async_safe(cls, func: Callable) -> Callable:
        """装饰器：为异步函数添加安全错误处理"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if cls._should_suppress_error(e, str(e)):
                    logger.debug(f"🔧 抑制函数 {func.__name__} 中的清理错误: {e}")
                    return None
                else:
                    # 重新抛出不应抑制的错误
                    raise
        return wrapper


# ==================== 全局实例 ====================

_async_error_handler = None


def get_async_error_handler() -> AsyncErrorHandler:
    """获取异步错误处理器单例"""
    global _async_error_handler
    if _async_error_handler is None:
        _async_error_handler = AsyncErrorHandler()
    return _async_error_handler


# ==================== 便捷函数 ====================

def setup_async_error_handling():
    """设置异步错误处理"""
    AsyncErrorHandler.setup_global_exception_handler()


def async_safe(func):
    """为异步函数添加安全错误处理的装饰器"""
    return AsyncErrorHandler.async_safe(func)

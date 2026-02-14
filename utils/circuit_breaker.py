"""
熔断器 (Circuit Breaker) 实现

实现状态机模式的熔断器，防止级联故障
"""
import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Any, TypeVar, Coro
from collections import deque
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import JubenLogger

logger = JubenLogger("circuit_breaker")


T = TypeVar('T')


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"           # 正常状态，允许请求通过
    OPEN = "open"               # 熔断状态，拒绝所有请求
    HALF_OPEN = "half_open"     # 半开状态，允许部分请求测试


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    # 失败阈值：达到此失败次数后触发熔断
    failure_threshold: int = 5

    # 成功阈值：半开状态下需要连续成功的次数才能恢复
    success_threshold: int = 2

    # 超时时间：熔断后等待多久进入半开状态（秒）
    timeout: float = 60.0

    # 滑动窗口大小：记录最近的请求数量
    sliding_window_size: int = 100

    # 调用超时时间（秒）
    call_timeout: float = 30.0


class CircuitBreakerError(Exception):
    """熔断器异常"""
    pass


class CircuitBreaker:
    """
    熔断器实现

    状态转换：
    CLOSED -> OPEN: 失败次数达到阈值
    OPEN -> HALF_OPEN: 超时时间到期
    HALF_OPEN -> CLOSED: 成功次数达到阈值
    HALF_OPEN -> OPEN: 再次失败
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        初始化熔断器

        Args:
            name: 熔断器名称
            config: 熔断器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # 当前状态
        self._state = CircuitState.CLOSED

        # 统计信息
        self._failure_count = 0
        self._success_count = 0
        self._total_calls = 0

        # 滑动窗口：记录最近的请求结果
        self._sliding_window = deque(maxlen=self.config.sliding_window_size)

        # 状态变更时间
        self._state_changed_at = time.time()

        # 半开状态下的成功计数
        self._half_open_successes = 0

        logger.info(f"✅ 熔断器 '{name}' 初始化完成")

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    @property
    def failure_count(self) -> int:
        """获取失败次数"""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """获取成功次数"""
        return self._success_count

    @property
    def total_calls(self) -> int:
        """获取总调用次数"""
        return self._total_calls

    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置（从OPEN到HALF_OPEN）"""
        return (
            self._state == CircuitState.OPEN and
            time.time() - self._state_changed_at >= self.config.timeout
        )

    def _record_success(self):
        """记录成功调用"""
        self._success_count += 1
        self._sliding_window.append(True)

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
                logger.info(f"🔄 熔断器 '{self.name}' 已恢复到CLOSED状态")

    def _record_failure(self):
        """记录失败调用"""
        self._failure_count += 1
        self._sliding_window.append(False)

        if self._state == CircuitState.HALF_OPEN:
            # 半开状态下失败，重新进入熔断状态
            self._transition_to(CircuitState.OPEN)
            logger.warning(f"⚠️ 熔断器 '{self.name}' 半开状态下失败，重新进入OPEN状态")
        elif self._failure_count >= self.config.failure_threshold:
            # 达到失败阈值，进入熔断状态
            self._transition_to(CircuitState.OPEN)
            logger.warning(
                f"🔴 熔断器 '{self.name}' 触发熔断 (失败次数: {self._failure_count})"
            )

    def _transition_to(self, new_state: CircuitState):
        """转换到新状态"""
        old_state = self._state
        self._state = new_state
        self._state_changed_at = time.time()

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_successes = 0
        elif new_state == CircuitState.OPEN:
            self._half_open_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0

        logger.info(
            f"🔀 熔断器 '{self.name}' 状态变更: {old_state.value} -> {new_state.value}"
        )

    async def call(
        self,
        func: Callable[..., Coro[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        通过熔断器调用函数

        Args:
            func: 要调用的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerError: 熔断器处于OPEN状态时
            Exception: 函数执行异常
        """
        self._total_calls += 1

        # 检查是否应该尝试重置
        if self._should_attempt_reset():
            self._transition_to(CircuitState.HALF_OPEN)
            logger.info(f"🔓 熔断器 '{self.name}' 进入半开状态，尝试恢复")

        # 检查熔断器状态
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"熔断器 '{self.name}' 处于OPEN状态，拒绝调用"
            )

        # 执行函数调用
        try:
            # 使用超时控制
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )

            # 记录成功
            self._record_success()

            return result

        except asyncio.TimeoutError as e:
            logger.warning(f"⏱️ 熔断器 '{self.name}' 调用超时")
            self._record_failure()
            raise CircuitBreakerError(f"调用超时: {e}") from e

        except Exception as e:
            logger.error(f"❌ 熔断器 '{self.name}' 调用失败: {e}")
            self._record_failure()
            raise

    def get_stats(self) -> dict:
        """获取熔断器统计信息"""
        # 计算滑动窗口内的失败率
        recent_failures = sum(1 for r in self._sliding_window if not r)
        recent_successes = sum(1 for r in self._sliding_window if r)
        total_recent = len(self._sliding_window)

        failure_rate = (
            recent_failures / total_recent if total_recent > 0 else 0
        )

        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "failure_rate": round(failure_rate, 4),
            "recent_failures": recent_failures,
            "recent_successes": recent_successes,
            "state_changed_at": self._state_changed_at,
            "time_in_state": time.time() - self._state_changed_at
        }

    def reset(self):
        """重置熔断器到初始状态"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_successes = 0
        self._sliding_window.clear()
        self._state_changed_at = time.time()

        logger.info(f"🔄 熔断器 '{self.name}' 已重置")


class CircuitBreakerRegistry:
    """熔断器注册表"""

    _breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def register(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        注册或获取熔断器

        Args:
            name: 熔断器名称
            config: 熔断器配置

        Returns:
            CircuitBreaker: 熔断器实例
        """
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]

    @classmethod
    def get(cls, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return cls._breakers.get(name)

    @classmethod
    def get_all_stats(cls) -> dict:
        """获取所有熔断器的统计信息"""
        return {
            name: breaker.get_stats()
            for name, breaker in cls._breakers.items()
        }

    @classmethod
    def reset_all(cls):
        """重置所有熔断器"""
        for breaker in cls._breakers.values():
            breaker.reset()


# 装饰器实现
def with_circuit_breaker(
    breaker_name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """
    熔断器装饰器

    用法:
    ```python
    @with_circuit_breaker("llm_api")
    async def call_llm_api(prompt: str):
        return await llm_client.chat(prompt)
    ```
    """
    def decorator(func: Callable[..., Coro[T]]) -> Callable[..., Coro[T]]:
        async def wrapper(*args, **kwargs) -> T:
            breaker = CircuitBreakerRegistry.register(breaker_name, config)
            return await breaker.call(func, *args, **kwargs)

        return wrapper
    return decorator


# 预定义的熔断器配置
DEFAULT_BREAKERS = {
    "llm_zhipu": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=30.0,
        sliding_window_size=50,
        call_timeout=60.0
    ),
    "llm_openrouter": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0,
        sliding_window_size=30,
        call_timeout=90.0
    ),
    "postgres": CircuitBreakerConfig(
        failure_threshold=10,
        success_threshold=5,
        timeout=10.0,
        sliding_window_size=100,
        call_timeout=5.0
    ),
    "redis": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=5.0,
        sliding_window_size=50,
        call_timeout=2.0
    ),
    "milvus": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=15.0,
        sliding_window_size=50,
        call_timeout=10.0
    ),
}


def get_breaker(name: str) -> CircuitBreaker:
    """
    获取预定义的熔断器

    Args:
        name: 熔断器名称 (llm_zhipu, postgres, redis, milvus)

    Returns:
        CircuitBreaker: 熔断器实例
    """
    config = DEFAULT_BREAKERS.get(name)
    return CircuitBreakerRegistry.register(name, config)


# 健康检查
async def check_circuit_breakers() -> dict:
    """
    检查所有熔断器状态

    Returns:
        dict: 熔断器状态报告
    """
    stats = CircuitBreakerRegistry.get_all_stats()

    # 计算整体健康状态
    open_count = sum(1 for s in stats.values() if s["state"] == "open")
    half_open_count = sum(1 for s in stats.values() if s["state"] == "half_open")

    overall_status = "healthy"
    if open_count > 0:
        overall_status = "degraded"
    if open_count >= len(stats) / 2:
        overall_status = "unhealthy"

    return {
        "overall_status": overall_status,
        "breakers": stats,
        "summary": {
            "total": len(stats),
            "closed": sum(1 for s in stats.values() if s["state"] == "closed"),
            "open": open_count,
            "half_open": half_open_count
        }
    }


if __name__ == "__main__":
    # 测试代码
    import random

    async def test_failing_service():
        """模拟失败的服务"""
        await asyncio.sleep(0.1)
        if random.random() < 0.3:
            raise Exception("服务调用失败")
        return "成功"

    async def main():
        # 创建熔断器
        breaker = CircuitBreaker(
            "test_service",
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=5.0,
                call_timeout=1.0
            )
        )

        # 测试调用
        logger.info("开始测试熔断器...")

        for i in range(20):
            try:
                result = await breaker.call(test_failing_service)
                logger.info(f"[{i+1}] 成功: {result}")
            except CircuitBreakerError as e:
                logger.error(f"[{i+1}] 熔断器错误: {e}")
            except Exception as e:
                logger.error(f"[{i+1}] 服务错误: {e}")

            # 查看状态
            stats = breaker.get_stats()
            logger.info(f"    状态: {stats['state']}, 失败: {stats['failure_count']}")

            await asyncio.sleep(0.5)

    asyncio.run(main())

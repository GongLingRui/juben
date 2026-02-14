"""
智能限流系统 -  
提供智能限流、动态调整、多维度限流和限流统计
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager
from .performance_monitor import get_performance_monitor


class RateLimitStrategy(Enum):
    """限流策略"""
    FIXED_WINDOW = "fixed_window"      # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    TOKEN_BUCKET = "token_bucket"      # 令牌桶
    LEAKY_BUCKET = "leaky_bucket"      # 漏桶


class RateLimitScope(Enum):
    """限流范围"""
    GLOBAL = "global"          # 全局限流
    USER = "user"             # 用户限流
    IP = "ip"                 # IP限流
    ENDPOINT = "endpoint"      # 端点限流
    AGENT = "agent"           # Agent限流


@dataclass
class RateLimitRule:
    """限流规则"""
    name: str
    scope: RateLimitScope
    strategy: RateLimitStrategy
    limit: int                    # 限制数量
    window: int                   # 时间窗口（秒）
    burst: int = 0                # 突发限制
    recovery_rate: float = 1.0   # 恢复速率
    enabled: bool = True
    priority: int = 0             # 优先级（数字越小优先级越高）


@dataclass
class RateLimitResult:
    """限流结果"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    reason: Optional[str] = None


@dataclass
class RateLimitStats:
    """限流统计"""
    total_requests: int = 0
    allowed_requests: int = 0
    blocked_requests: int = 0
    block_rate: float = 0.0
    avg_response_time: float = 0.0


class SmartRateLimiter:
    """智能限流系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_rate_limiter")
        
        # 限流规则
        self.rules: Dict[str, RateLimitRule] = {}
        self.rule_cache: Dict[str, List[RateLimitRule]] = {}
        
        # 限流状态
        self.counters: Dict[str, Dict[str, Any]] = {}
        self.windows: Dict[str, Dict[str, Any]] = {}
        self.buckets: Dict[str, Dict[str, Any]] = {}
        
        # 统计信息
        self.stats = RateLimitStats()
        self.performance_monitor = get_performance_monitor()
        
        # 动态调整
        self.auto_adjust = True
        self.adjust_interval = 60  # 秒
        self.performance_threshold = 0.8  # 性能阈值
        
        # 限流回调
        self.callbacks: Dict[str, List[Callable]] = {
            'before_check': [],
            'after_check': [],
            'on_blocked': [],
            'on_allowed': []
        }
        
        self.logger.info("🚦 智能限流系统初始化完成")
    
    def add_rule(self, rule: RateLimitRule):
        """添加限流规则"""
        try:
            self.rules[rule.name] = rule
            
            # 更新规则缓存
            self._update_rule_cache()
            
            # 初始化计数器
            self._init_counters(rule)
            
            self.logger.info(f"✅ 限流规则已添加: {rule.name}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加限流规则失败: {e}")
    
    def remove_rule(self, rule_name: str):
        """移除限流规则"""
        try:
            if rule_name in self.rules:
                del self.rules[rule_name]
                self._update_rule_cache()
                
                # 清理相关数据
                self._cleanup_rule_data(rule_name)
                
                self.logger.info(f"✅ 限流规则已移除: {rule_name}")
            
        except Exception as e:
            self.logger.error(f"❌ 移除限流规则失败: {e}")
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        scope: RateLimitScope,
        endpoint: Optional[str] = None,
        agent: Optional[str] = None
    ) -> RateLimitResult:
        """检查限流"""
        try:
            start_time = time.time()
            
            # 获取适用的规则
            applicable_rules = self._get_applicable_rules(scope, endpoint, agent)
            
            if not applicable_rules:
                return RateLimitResult(
                    allowed=True,
                    remaining=999999,
                    reset_time=int(time.time() + 3600)
                )
            
            # 按优先级排序
            applicable_rules.sort(key=lambda x: x.priority)
            
            # 检查每个规则
            for rule in applicable_rules:
                if not rule.enabled:
                    continue
                
                result = await self._check_rule(rule, identifier)
                
                if not result.allowed:
                    # 触发限流回调
                    await self._trigger_callbacks('on_blocked', rule, identifier, result)
                    
                    # 更新统计
                    self.stats.blocked_requests += 1
                    self.stats.total_requests += 1
                    
                    return result
            
            # 所有规则都通过
            response_time = time.time() - start_time
            
            # 更新统计
            self.stats.allowed_requests += 1
            self.stats.total_requests += 1
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.allowed_requests - 1) + response_time) / 
                self.stats.allowed_requests
            )
            
            # 触发允许回调
            await self._trigger_callbacks('on_allowed', None, identifier, None)
            
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=int(time.time() + 3600)
            )
            
        except Exception as e:
            self.logger.error(f"❌ 检查限流失败: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=int(time.time() + 60),
                reason=f"限流检查失败: {str(e)}"
            )
    
    def _get_applicable_rules(
        self, 
        scope: RateLimitScope, 
        endpoint: Optional[str] = None,
        agent: Optional[str] = None
    ) -> List[RateLimitRule]:
        """获取适用的规则"""
        try:
            applicable_rules = []
            
            for rule in self.rules.values():
                if not rule.enabled:
                    continue
                
                # 检查范围匹配
                if rule.scope != scope:
                    continue
                
                # 检查端点匹配
                if endpoint and rule.scope == RateLimitScope.ENDPOINT:
                    if not self._match_endpoint(rule.name, endpoint):
                        continue
                
                # 检查Agent匹配
                if agent and rule.scope == RateLimitScope.AGENT:
                    if not self._match_agent(rule.name, agent):
                        continue
                
                applicable_rules.append(rule)
            
            return applicable_rules
            
        except Exception as e:
            self.logger.error(f"❌ 获取适用规则失败: {e}")
            return []
    
    def _match_endpoint(self, rule_name: str, endpoint: str) -> bool:
        """匹配端点"""
        try:
            # 简单的通配符匹配
            if '*' in rule_name:
                import fnmatch
                return fnmatch.fnmatch(endpoint, rule_name)
            else:
                return rule_name == endpoint
                
        except Exception as e:
            self.logger.error(f"❌ 匹配端点失败: {e}")
            return False
    
    def _match_agent(self, rule_name: str, agent: str) -> bool:
        """匹配Agent"""
        try:
            # 简单的通配符匹配
            if '*' in rule_name:
                import fnmatch
                return fnmatch.fnmatch(agent, rule_name)
            else:
                return rule_name == agent
                
        except Exception as e:
            self.logger.error(f"❌ 匹配Agent失败: {e}")
            return False
    
    async def _check_rule(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """检查单个规则"""
        try:
            if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                return await self._check_fixed_window(rule, identifier)
            
            elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return await self._check_sliding_window(rule, identifier)
            
            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return await self._check_token_bucket(rule, identifier)
            
            elif rule.strategy == RateLimitStrategy.LEAKY_BUCKET:
                return await self._check_leaky_bucket(rule, identifier)
            
            else:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=int(time.time() + 60),
                    reason="未知的限流策略"
                )
                
        except Exception as e:
            self.logger.error(f"❌ 检查规则失败: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=int(time.time() + 60),
                reason=f"规则检查失败: {str(e)}"
            )
    
    async def _check_fixed_window(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """固定窗口限流"""
        try:
            current_time = int(time.time())
            window_start = current_time - (current_time % rule.window)
            key = f"{rule.name}:{identifier}:{window_start}"
            
            # 获取当前计数
            current_count = self.counters.get(key, {}).get('count', 0)
            
            if current_count >= rule.limit:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=window_start + rule.window,
                    retry_after=window_start + rule.window - current_time,
                    reason=f"固定窗口限流: {current_count}/{rule.limit}"
                )
            
            # 增加计数
            if key not in self.counters:
                self.counters[key] = {'count': 0, 'created_at': current_time}
            
            self.counters[key]['count'] += 1
            
            return RateLimitResult(
                allowed=True,
                remaining=rule.limit - current_count - 1,
                reset_time=window_start + rule.window
            )
            
        except Exception as e:
            self.logger.error(f"❌ 固定窗口限流失败: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=int(time.time() + 60),
                reason=f"固定窗口限流失败: {str(e)}"
            )
    
    async def _check_sliding_window(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """滑动窗口限流"""
        try:
            current_time = int(time.time())
            key = f"{rule.name}:{identifier}"
            
            # 获取窗口数据
            if key not in self.windows:
                self.windows[key] = {'requests': [], 'last_cleanup': current_time}
            
            window_data = self.windows[key]
            requests = window_data['requests']
            
            # 清理过期请求
            cutoff_time = current_time - rule.window
            requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
            
            if len(requests) >= rule.limit:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=requests[0] + rule.window,
                    retry_after=requests[0] + rule.window - current_time,
                    reason=f"滑动窗口限流: {len(requests)}/{rule.limit}"
                )
            
            # 添加当前请求
            requests.append(current_time)
            window_data['last_cleanup'] = current_time
            
            return RateLimitResult(
                allowed=True,
                remaining=rule.limit - len(requests),
                reset_time=requests[0] + rule.window if requests else current_time + rule.window
            )
            
        except Exception as e:
            self.logger.error(f"❌ 滑动窗口限流失败: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=int(time.time() + 60),
                reason=f"滑动窗口限流失败: {str(e)}"
            )
    
    async def _check_token_bucket(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """令牌桶限流"""
        try:
            current_time = time.time()
            key = f"{rule.name}:{identifier}"
            
            # 获取桶数据
            if key not in self.buckets:
                self.buckets[key] = {
                    'tokens': rule.limit,
                    'last_refill': current_time,
                    'capacity': rule.limit
                }
            
            bucket = self.buckets[key]
            
            # 计算需要补充的令牌
            time_passed = current_time - bucket['last_refill']
            tokens_to_add = time_passed * rule.recovery_rate
            bucket['tokens'] = min(bucket['capacity'], bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = current_time
            
            if bucket['tokens'] < 1:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=int(current_time + (1 - bucket['tokens']) / rule.recovery_rate),
                    retry_after=int((1 - bucket['tokens']) / rule.recovery_rate),
                    reason=f"令牌桶限流: {bucket['tokens']:.2f}/{bucket['capacity']}"
                )
            
            # 消耗令牌
            bucket['tokens'] -= 1
            
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket['tokens']),
                reset_time=int(current_time + bucket['tokens'] / rule.recovery_rate)
            )
            
        except Exception as e:
            self.logger.error(f"❌ 令牌桶限流失败: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=int(time.time() + 60),
                reason=f"令牌桶限流失败: {str(e)}"
            )
    
    async def _check_leaky_bucket(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """漏桶限流"""
        try:
            current_time = time.time()
            key = f"{rule.name}:{identifier}"
            
            # 获取桶数据
            if key not in self.buckets:
                self.buckets[key] = {
                    'level': 0,
                    'last_leak': current_time,
                    'capacity': rule.limit
                }
            
            bucket = self.buckets[key]
            
            # 计算泄漏量
            time_passed = current_time - bucket['last_leak']
            leaked = time_passed * rule.recovery_rate
            bucket['level'] = max(0, bucket['level'] - leaked)
            bucket['last_leak'] = current_time
            
            if bucket['level'] >= bucket['capacity']:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=int(current_time + (bucket['level'] - bucket['capacity']) / rule.recovery_rate),
                    retry_after=int((bucket['level'] - bucket['capacity']) / rule.recovery_rate),
                    reason=f"漏桶限流: {bucket['level']:.2f}/{bucket['capacity']}"
                )
            
            # 增加水位
            bucket['level'] += 1
            
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket['capacity'] - bucket['level']),
                reset_time=int(current_time + bucket['level'] / rule.recovery_rate)
            )
            
        except Exception as e:
            self.logger.error(f"❌ 漏桶限流失败: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=int(time.time() + 60),
                reason=f"漏桶限流失败: {str(e)}"
            )
    
    def _init_counters(self, rule: RateLimitRule):
        """初始化计数器"""
        try:
            # 这里可以初始化一些预分配的数据结构
            pass
            
        except Exception as e:
            self.logger.error(f"❌ 初始化计数器失败: {e}")
    
    def _update_rule_cache(self):
        """更新规则缓存"""
        try:
            self.rule_cache.clear()
            
            for rule in self.rules.values():
                scope_key = rule.scope.value
                if scope_key not in self.rule_cache:
                    self.rule_cache[scope_key] = []
                self.rule_cache[scope_key].append(rule)
            
        except Exception as e:
            self.logger.error(f"❌ 更新规则缓存失败: {e}")
    
    def _cleanup_rule_data(self, rule_name: str):
        """清理规则数据"""
        try:
            # 清理计数器
            keys_to_remove = [key for key in self.counters.keys() if key.startswith(f"{rule_name}:")]
            for key in keys_to_remove:
                del self.counters[key]
            
            # 清理窗口数据
            keys_to_remove = [key for key in self.windows.keys() if key.startswith(f"{rule_name}:")]
            for key in keys_to_remove:
                del self.windows[key]
            
            # 清理桶数据
            keys_to_remove = [key for key in self.buckets.keys() if key.startswith(f"{rule_name}:")]
            for key in keys_to_remove:
                del self.buckets[key]
            
        except Exception as e:
            self.logger.error(f"❌ 清理规则数据失败: {e}")
    
    async def _trigger_callbacks(
        self, 
        event: str, 
        rule: Optional[RateLimitRule], 
        identifier: str, 
        result: Optional[RateLimitResult]
    ):
        """触发回调"""
        try:
            if event in self.callbacks:
                for callback in self.callbacks[event]:
                    try:
                        await callback(rule, identifier, result)
                    except Exception as e:
                        self.logger.error(f"❌ 回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发回调失败: {e}")
    
    def add_callback(self, event: str, callback: Callable):
        """添加回调"""
        try:
            if event in self.callbacks:
                self.callbacks[event].append(callback)
                self.logger.info(f"✅ 回调已添加: {event}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加回调失败: {e}")
    
    def remove_callback(self, event: str, callback: Callable):
        """移除回调"""
        try:
            if event in self.callbacks and callback in self.callbacks[event]:
                self.callbacks[event].remove(callback)
                self.logger.info(f"✅ 回调已移除: {event}")
            
        except Exception as e:
            self.logger.error(f"❌ 移除回调失败: {e}")
    
    async def cleanup_expired_data(self):
        """清理过期数据"""
        try:
            current_time = int(time.time())
            
            # 清理过期的计数器
            expired_counters = []
            for key, data in self.counters.items():
                if current_time - data.get('created_at', 0) > 3600:  # 1小时
                    expired_counters.append(key)
            
            for key in expired_counters:
                del self.counters[key]
            
            # 清理过期的窗口数据
            expired_windows = []
            for key, data in self.windows.items():
                if current_time - data.get('last_cleanup', 0) > 3600:  # 1小时
                    expired_windows.append(key)
            
            for key in expired_windows:
                del self.windows[key]
            
            # 清理过期的桶数据
            expired_buckets = []
            for key, data in self.buckets.items():
                if current_time - data.get('last_refill', 0) > 3600:  # 1小时
                    expired_buckets.append(key)
            
            for key in expired_buckets:
                del self.buckets[key]
            
            if expired_counters or expired_windows or expired_buckets:
                self.logger.info(f"🧹 清理过期数据完成: 计数器{len(expired_counters)}, 窗口{len(expired_windows)}, 桶{len(expired_buckets)}")
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期数据失败: {e}")
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """获取限流统计"""
        try:
            # 计算阻塞率
            total_requests = self.stats.total_requests
            self.stats.block_rate = (self.stats.blocked_requests / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_requests': self.stats.total_requests,
                'allowed_requests': self.stats.allowed_requests,
                'blocked_requests': self.stats.blocked_requests,
                'block_rate': self.stats.block_rate,
                'avg_response_time': self.stats.avg_response_time,
                'active_rules': len(self.rules),
                'enabled_rules': len([r for r in self.rules.values() if r.enabled]),
                'counters_count': len(self.counters),
                'windows_count': len(self.windows),
                'buckets_count': len(self.buckets)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取限流统计失败: {e}")
            return {'error': str(e)}


# 全局智能限流器实例
smart_rate_limiter = SmartRateLimiter()


def get_smart_rate_limiter() -> SmartRateLimiter:
    """获取智能限流器实例"""
    return smart_rate_limiter

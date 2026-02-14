"""
Token累加器
统计单次会话中所有LLM调用的token消耗

扩展功能：
- 配额检查器：检查用户每日Token使用配额
- 使用报告：计算每日预计消耗金额
- 排行榜功能：用户Token消耗排行榜
- 仪表盘数据：Token统计仪表盘


"""
import os
import json
import logging
import asyncio
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from pathlib import Path


class QuotaExceededError(Exception):
    """
    配额超限异常

    当用户的每日Token使用量超过预设阈值时抛出
    """
    def __init__(
        self,
        user_id: str,
        used_tokens: int,
        quota_limit: int,
        user_tier: str,
        estimated_cost: float = 0.0
    ):
        self.user_id = user_id
        self.used_tokens = used_tokens
        self.quota_limit = quota_limit
        self.user_tier = user_tier
        self.estimated_cost = estimated_cost
        self.percentage_used = (used_tokens / quota_limit * 100) if quota_limit > 0 else 0

        message = (
            f"🚫 配额超限 | 用户: {user_id} | "
            f"已用: {used_tokens:,} / {quota_limit:,} tokens ({self.percentage_used:.1f}%) | "
            f"等级: {user_tier} | 预计费用: ¥{estimated_cost:.4f}"
        )
        super().__init__(message)


@dataclass
class TokenUsage:
    """Token使用情况"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        """计算总token数"""
        self.total_tokens = self.prompt_tokens + self.completion_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenUsage':
        """从字典创建"""
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0)
        )


@dataclass
class DailyUsageReport:
    """每日使用报告"""
    user_id: str
    date: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    quota_limit: int
    quota_remaining: int
    quota_percentage: float
    user_tier: str
    llm_calls: int
    model_breakdown: Dict[str, int]  # 按模型分组的token使用量

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class QuotaChecker:
    """
    Token配额检查器

    功能：
    1. 检查用户每日Token使用配额
    2. 记录Token使用到Redis
    3. 生成每日使用报告
    4. 根据智谱AI价格计算费用
    """

    def __init__(self, redis_client=None, quota_settings=None):
        """
        初始化配额检查器

        Args:
            redis_client: Redis客户端实例
            quota_settings: 配额设置配置
        """
        self.logger = logging.getLogger(__name__)
        self._redis = redis_client
        self._quota_settings = quota_settings
        self._memory_usage: Dict[str, Dict[str, Any]] = {}

        # 延迟加载配置和Redis客户端
        self._settings_loaded = False

    def _ensure_settings(self):
        """确保配置已加载"""
        if not self._settings_loaded:
            if self._quota_settings is None:
                from config.settings import juben_settings
                self._quota_settings = juben_settings.quota

            if self._redis is None:
                try:
                    from utils.redis_client import get_redis_client
                    self._redis = get_redis_client()
                    if asyncio.iscoroutine(self._redis):
                        # 同步上下文无法await，回退到内存模式
                        self.logger.warning("⚠️ Redis客户端为异步对象，配额检查将使用内存存储")
                        self._redis = {}
                except ImportError:
                    self.logger.warning("⚠️ 无法导入Redis客户端，配额检查将使用内存存储")
                    self._redis = {}  # 使用内存存储作为后备

            self._settings_loaded = True

    def _get_daily_key(self, user_id: str, date_str: Optional[str] = None) -> str:
        """
        生成每日配额Redis键

        Args:
            user_id: 用户ID
            date_str: 日期字符串 (YYYY-MM-DD)，默认为今天

        Returns:
            str: Redis键，格式为 quota:daily:{user_id}:YYYY-MM-DD
        """
        if date_str is None:
            date_str = date.today().isoformat()

        prefix = self._quota_settings.redis_key_prefix if self._quota_settings else "quota"
        return f"{prefix}:daily:{user_id}:{date_str}"

    def _get_user_tier_quota(self, user_tier: str) -> int:
        """
        获取用户等级对应的配额

        Args:
            user_tier: 用户等级 (free, basic, pro, enterprise)

        Returns:
            int: 每日配额（tokens）
        """
        if not self._quota_settings:
            return 100000  # 默认配额

        mapping = self._quota_settings.user_level_mapping or {}
        quota_field = mapping.get(user_tier, "free_daily_quota")
        return getattr(self._quota_settings, quota_field, 100000)

    def get_daily_usage(
        self,
        user_id: str,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户每日Token使用量

        Args:
            user_id: 用户ID
            date_str: 日期字符串 (YYYY-MM-DD)，默认为今天

        Returns:
            Dict: {
                "total_tokens": int,
                "prompt_tokens": int,
                "completion_tokens": int,
                "llm_calls": int,
                "model_breakdown": {...}
            }
        """
        self._ensure_settings()

        key = self._get_daily_key(user_id, date_str)

        if isinstance(self._redis, dict):
            # 内存存储模式
            data = self._redis.get(key, {})
        else:
            # 异步客户端则使用内存镜像避免阻塞
            if hasattr(self._redis, "hgetall") and asyncio.iscoroutinefunction(self._redis.hgetall):
                data = self._memory_usage.get(key, {})
            else:
                # Redis模式（同步）
                try:
                    data = self._redis.hgetall(key)
                    if data:
                        # Redis返回bytes，需要解码
                        data = {k.decode(): json.loads(v.decode()) if v.startswith('{') else v
                               for k, v in data.items()}
                except Exception as e:
                    self.logger.error(f"❌ 从Redis获取每日使用量失败: {e}")
                    data = {}

        # 兼容不同存储形态下的 model_breakdown 类型：
        # - Redis 模式：字符串形式的 JSON
        # - 内存/字典模式：可能直接是 dict
        raw_breakdown = data.get("model_breakdown", "{}")
        if isinstance(raw_breakdown, dict):
            model_breakdown = raw_breakdown
        else:
            try:
                # 既兼容 bytes 也兼容 str
                if isinstance(raw_breakdown, bytes):
                    raw_breakdown = raw_breakdown.decode("utf-8", errors="ignore")
                model_breakdown = json.loads(raw_breakdown or "{}")
            except Exception:
                model_breakdown = {}

        return {
            "total_tokens": int(data.get("total_tokens", 0)),
            "prompt_tokens": int(data.get("prompt_tokens", 0)),
            "completion_tokens": int(data.get("completion_tokens", 0)),
            "llm_calls": int(data.get("llm_calls", 0)),
            "model_breakdown": model_breakdown,
        }

    def check_quota(
        self,
        user_id: str,
        user_tier: str = "free",
        raise_on_exceed: bool = True
    ) -> Dict[str, Any]:
        """
        检查用户配额

        Args:
            user_id: 用户ID
            user_tier: 用户等级 (free, basic, pro, enterprise)
            raise_on_exceed: 超限时是否抛出异常

        Returns:
            Dict: {
                "allowed": bool,
                "used_tokens": int,
                "quota_limit": int,
                "remaining": int,
                "percentage": float,
                "user_tier": str
            }

        Raises:
            QuotaExceededError: 当配额超限且raise_on_exceed=True时
        """
        self._ensure_settings()

        # 检查是否启用配额限制
        if self._quota_settings and not self._quota_settings.enabled:
            return {
                "allowed": True,
                "used_tokens": 0,
                "quota_limit": float('inf'),
                "remaining": float('inf'),
                "percentage": 0.0,
                "user_tier": user_tier,
                "message": "配额检查已禁用"
            }

        daily_usage = self.get_daily_usage(user_id)
        quota_limit = self._get_user_tier_quota(user_tier)
        used_tokens = daily_usage["total_tokens"]

        remaining = quota_limit - used_tokens
        percentage = (used_tokens / quota_limit * 100) if quota_limit > 0 else 0

        # 检查配额检查模式
        check_mode = self._quota_settings.quota_check_mode if self._quota_settings else "soft"

        # soft模式：只警告不阻止
        # hard模式：超限时阻止请求
        should_block = check_mode == "hard" and used_tokens >= quota_limit

        result = {
            "allowed": not should_block,
            "used_tokens": used_tokens,
            "quota_limit": quota_limit,
            "remaining": max(0, remaining),
            "percentage": percentage,
            "user_tier": user_tier,
            "check_mode": check_mode
        }

        # 如果超限且需要抛出异常
        if should_block and raise_on_exceed:
            # 计算预计费用
            estimated_cost = self._estimate_cost(used_tokens, daily_usage.get("model_breakdown", {}))
            raise QuotaExceededError(
                user_id=user_id,
                used_tokens=used_tokens,
                quota_limit=quota_limit,
                user_tier=user_tier,
                estimated_cost=estimated_cost
            )

        # soft模式或未超限时的日志
        if percentage > 80:
            self.logger.warning(
                f"⚠️ 配额即将用尽 | 用户: {user_id} | "
                f"已用: {used_tokens:,} / {quota_limit:,} ({percentage:.1f}%)"
            )

        return result

    def record_usage(
        self,
        user_id: str,
        tokens: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "unknown"
    ) -> bool:
        """
        记录Token使用量

        Args:
            user_id: 用户ID
            tokens: 总token数
            prompt_tokens: 输入token数
            completion_tokens: 输出token数
            model_name: 模型名称

        Returns:
            bool: 是否成功
        """
        self._ensure_settings()

        key = self._get_daily_key(user_id)

        try:
            # 始终更新内存镜像，确保并发一致性
            mem = self._memory_usage.get(key, {})
            mem["total_tokens"] = mem.get("total_tokens", 0) + tokens
            mem["prompt_tokens"] = mem.get("prompt_tokens", 0) + prompt_tokens
            mem["completion_tokens"] = mem.get("completion_tokens", 0) + completion_tokens
            mem["llm_calls"] = mem.get("llm_calls", 0) + 1
            mem_breakdown = json.loads(mem.get("model_breakdown", "{}"))
            mem_breakdown[model_name] = mem_breakdown.get(model_name, 0) + tokens
            mem["model_breakdown"] = json.dumps(mem_breakdown)
            self._memory_usage[key] = mem

            if isinstance(self._redis, dict):
                # 内存存储模式
                data = self._redis.get(key, {})
                data["total_tokens"] = data.get("total_tokens", 0) + tokens
                data["prompt_tokens"] = data.get("prompt_tokens", 0) + prompt_tokens
                data["completion_tokens"] = data.get("completion_tokens", 0) + completion_tokens
                data["llm_calls"] = data.get("llm_calls", 0) + 1

                model_breakdown = data.get("model_breakdown", {})
                model_breakdown[model_name] = model_breakdown.get(model_name, 0) + tokens
                data["model_breakdown"] = model_breakdown

                self._redis[key] = data
            else:
                # Redis模式
                if hasattr(self._redis, "pipeline") and not asyncio.iscoroutinefunction(self._redis.pipeline):
                    pipe = self._redis.pipeline()
                    pipe.hincrby(key, "total_tokens", tokens)
                    pipe.hincrby(key, "prompt_tokens", prompt_tokens)
                    pipe.hincrby(key, "completion_tokens", completion_tokens)
                    pipe.hincrby(key, "llm_calls", 1)

                    current_data = self._redis.hget(key, "model_breakdown")
                    if current_data:
                        model_breakdown = json.loads(current_data.decode())
                    else:
                        model_breakdown = {}

                    model_breakdown[model_name] = model_breakdown.get(model_name, 0) + tokens
                    pipe.hset(key, "model_breakdown", json.dumps(model_breakdown))

                    ttl = self._quota_settings.daily_ttl if self._quota_settings else 172800
                    pipe.expire(key, ttl)
                    pipe.execute()
                else:
                    async def _async_write():
                        try:
                            pipe = self._redis.pipeline()
                            await pipe.hincrby(key, "total_tokens", tokens)
                            await pipe.hincrby(key, "prompt_tokens", prompt_tokens)
                            await pipe.hincrby(key, "completion_tokens", completion_tokens)
                            await pipe.hincrby(key, "llm_calls", 1)
                            current_data = await self._redis.hget(key, "model_breakdown")
                            model_breakdown = json.loads(current_data) if current_data else {}
                            model_breakdown[model_name] = model_breakdown.get(model_name, 0) + tokens
                            await pipe.hset(key, "model_breakdown", json.dumps(model_breakdown))
                            ttl = self._quota_settings.daily_ttl if self._quota_settings else 172800
                            await pipe.expire(key, ttl)
                            await pipe.execute()
                        except Exception as e:
                            self.logger.error(f"❌ 异步记录Token使用量失败: {e}")

                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(_async_write())
                    except RuntimeError:
                        asyncio.run(_async_write())

            self.logger.debug(f"✅ 记录Token使用: {user_id} +{tokens} tokens")
            return True

        except Exception as e:
            self.logger.error(f"❌ 记录Token使用失败: {e}")
            return False

    def _estimate_cost(
        self,
        total_tokens: int,
        model_breakdown: Dict[str, int],
        default_model: str = "glm-4-flash"
    ) -> float:
        """
        估算Token使用成本

        Args:
            total_tokens: 总token数
            model_breakdown: 按模型分组的token使用量
            default_model: 默认模型名称

        Returns:
            float: 预计费用（元）
        """
        if not self._quota_settings or not self._quota_settings.zhipu_prices:
            return 0.0

        prices = self._quota_settings.zhipu_prices
        completion_multiplier = prices.pop("completion_multiplier", 2.0)

        total_cost = 0.0

        if model_breakdown:
            # 按模型分别计算
            for model, tokens in model_breakdown.items():
                price_per_1k = prices.get(model, prices.get(default_model, 0.0001))
                total_cost += (tokens / 1000) * price_per_1k
        else:
            # 使用默认价格
            price_per_1k = prices.get(default_model, 0.0001)
            total_cost = (total_tokens / 1000) * price_per_1k

        return total_cost


class TokenAccumulator:
    """
    Token累加器

    功能：
    1. 统计单次会话中所有LLM调用的token消耗
    2. 使用内存存储token统计数据
    3. 计算积分扣减（1000 tokens = 10 积分）
    4. 生成积分扣减报告
    5. 检查每日配额限制
    """

    def __init__(self, quota_checker: Optional[QuotaChecker] = None):
        self.logger = logging.getLogger(__name__)
        self.token_to_points_ratio = 1000  # 1000 tokens = 10 积分
        self.points_per_ratio = 10
        self._accumulators = {}  # 内存存储
        self._quota_checker = quota_checker  # 配额检查器
    
    def _get_accumulator_key(self, user_id: str, session_id: str) -> str:
        """生成累加器的键"""
        return f"{user_id}:{session_id}"
    
    def initialize_accumulator(
        self,
        user_id: str,
        session_id: str,
        request_timestamp: Optional[str] = None,
        user_tier: str = "free",
        check_quota: bool = True
    ) -> str:
        """
        初始化Token累加器（会话级别）

        在初始化之前会检查用户的每日配额。

        Args:
            user_id: 用户ID
            session_id: 会话ID
            request_timestamp: 请求时间戳（已弃用，保留是为了兼容性）
            user_tier: 用户等级 (free, basic, pro, enterprise)
            check_quota: 是否检查配额

        Returns:
            str: 累加器的唯一标识符

        Raises:
            QuotaExceededError: 当用户配额超限时
        """
        # 检查配额（在初始化累加器之前）
        if check_quota and self._quota_checker:
            quota_status = self._quota_checker.check_quota(
                user_id=user_id,
                user_tier=user_tier,
                raise_on_exceed=True  # 超限则抛出异常
            )

            self.logger.info(
                f"📊 配额检查通过 | 用户: {user_id} | "
                f"已用: {quota_status['used_tokens']:,} / {quota_status['quota_limit']:,} "
                f"({quota_status['percentage']:.1f}%)"
            )

        accumulator_key = self._get_accumulator_key(user_id, session_id)

        # 初始化累加器数据
        accumulator_data = {
            "user_id": user_id,
            "session_id": session_id,
            "user_tier": user_tier,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "usage": TokenUsage().to_dict(),
            "llm_calls": []  # 记录每次LLM调用的详细信息
        }

        self._accumulators[accumulator_key] = accumulator_data

        self.logger.info(f"✅ Token累加器初始化成功: {accumulator_key}")
        return accumulator_key
    
    def add_token_usage(
        self,
        accumulator_key: str,
        usage: TokenUsage,
        agent_name: str = "unknown",
        model_name: str = "unknown",
        provider: str = "unknown"
    ) -> bool:
        """
        添加token使用情况

        同时记录到会话累加器和每日配额统计。

        Args:
            accumulator_key: 累加器键
            usage: token使用情况
            agent_name: Agent名称
            model_name: 模型名称
            provider: 提供商

        Returns:
            bool: 是否成功
        """
        try:
            if accumulator_key not in self._accumulators:
                self.logger.warning(f"⚠️ 累加器不存在: {accumulator_key}")
                return False

            accumulator_data = self._accumulators[accumulator_key]
            user_id = accumulator_data.get("user_id", "")

            # 累加token使用情况
            current_usage = TokenUsage.from_dict(accumulator_data["usage"])
            current_usage.prompt_tokens += usage.prompt_tokens
            current_usage.completion_tokens += usage.completion_tokens
            current_usage.total_tokens += usage.total_tokens

            accumulator_data["usage"] = current_usage.to_dict()
            accumulator_data["updated_at"] = datetime.now().isoformat()

            # 记录LLM调用详情
            call_record = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "model_name": model_name,
                "provider": provider,
                "usage": usage.to_dict()
            }
            accumulator_data["llm_calls"].append(call_record)

            # 同时记录到配额检查器
            if self._quota_checker and user_id:
                self._quota_checker.record_usage(
                    user_id=user_id,
                    tokens=usage.total_tokens,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    model_name=model_name
                )

            self.logger.info(f"✅ Token使用量已累加: {usage.total_tokens} tokens (总计: {current_usage.total_tokens} tokens)")
            return True

        except Exception as e:
            self.logger.error(f"❌ 添加token使用量失败: {e}")
            return False
    
    def get_billing_summary(self, accumulator_key: str) -> Optional[Dict[str, Any]]:
        """
        获取计费摘要
        
        Args:
            accumulator_key: 累加器键
            
        Returns:
            Dict: 计费摘要
        """
        try:
            if accumulator_key not in self._accumulators:
                return None
            
            accumulator_data = self._accumulators[accumulator_key]
            usage = TokenUsage.from_dict(accumulator_data["usage"])
            
            # 计算积分扣减
            deducted_points = (usage.total_tokens // self.token_to_points_ratio) * self.points_per_ratio
            
            summary = {
                "total_tokens": usage.total_tokens,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_llm_calls": len(accumulator_data["llm_calls"]),
                "deducted_points": deducted_points,
                "token_to_points_ratio": self.token_to_points_ratio,
                "points_per_ratio": self.points_per_ratio,
                "session_duration": self._calculate_session_duration(accumulator_data),
                "llm_calls": accumulator_data["llm_calls"]
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ 获取计费摘要失败: {e}")
            return None
    
    def _calculate_session_duration(self, accumulator_data: Dict[str, Any]) -> float:
        """计算会话持续时间（秒）"""
        try:
            created_at = datetime.fromisoformat(accumulator_data["created_at"])
            updated_at = datetime.fromisoformat(accumulator_data["updated_at"])
            duration = (updated_at - created_at).total_seconds()
            return duration
        except:
            return 0.0
    
    def cleanup_accumulator(self, accumulator_key: str) -> bool:
        """
        清理累加器
        
        Args:
            accumulator_key: 累加器键
            
        Returns:
            bool: 是否成功
        """
        try:
            if accumulator_key in self._accumulators:
                del self._accumulators[accumulator_key]
                self.logger.info(f"✅ Token累加器已清理: {accumulator_key}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ 清理累加器失败: {e}")
            return False


# 全局实例
quota_checker = QuotaChecker()
token_accumulator = TokenAccumulator(quota_checker=quota_checker)


# 便捷函数
def create_token_accumulator(
    user_id: str,
    session_id: str,
    request_timestamp: Optional[str] = None,
    user_tier: str = "free",
    check_quota: bool = True
) -> str:
    """创建token累加器"""
    return token_accumulator.initialize_accumulator(user_id, session_id, request_timestamp, user_tier, check_quota)


async def add_token_usage(
    accumulator_key: str,
    usage: TokenUsage,
    agent_name: str = "unknown",
    model_name: str = "unknown",
    provider: str = "unknown"
) -> bool:
    """添加token使用情况"""
    return token_accumulator.add_token_usage(accumulator_key, usage, agent_name, model_name, provider)


def get_billing_summary(accumulator_key: str) -> Optional[Dict[str, Any]]:
    """获取计费摘要"""
    return token_accumulator.get_billing_summary(accumulator_key)


def cleanup_token_accumulator(accumulator_key: str) -> bool:
    """清理token累加器"""
    return token_accumulator.cleanup_accumulator(accumulator_key)


async def get_usage_report(
    user_id: str,
    user_tier: str = "free",
    date_str: Optional[str] = None
) -> DailyUsageReport:
    """
    获取用户每日使用报告

    计算当日Token使用量、预计费用、配额剩余等信息。

    Args:
        user_id: 用户ID
        user_tier: 用户等级 (free, basic, pro, enterprise)
        date_str: 日期字符串 (YYYY-MM-DD)，默认为今天

    Returns:
        DailyUsageReport: 每日使用报告

    Raises:
        QuotaExceededError: 当配额超限时（仅hard模式）
    """
    # 获取每日使用量
    daily_usage = quota_checker.get_daily_usage(user_id, date_str)

    # 获取配额限制
    quota_limit = quota_checker._get_user_tier_quota(user_tier)

    # 计算预计费用
    estimated_cost = quota_checker._estimate_cost(
        daily_usage["total_tokens"],
        daily_usage.get("model_breakdown", {})
    )

    # 计算剩余配额和百分比
    quota_remaining = max(0, quota_limit - daily_usage["total_tokens"])
    quota_percentage = (daily_usage["total_tokens"] / quota_limit * 100) if quota_limit > 0 else 0

    # 获取日期
    if date_str is None:
        date_str = date.today().isoformat()

    # 创建报告
    report = DailyUsageReport(
        user_id=user_id,
        date=date_str,
        total_tokens=daily_usage["total_tokens"],
        prompt_tokens=daily_usage["prompt_tokens"],
        completion_tokens=daily_usage["completion_tokens"],
        estimated_cost=estimated_cost,
        quota_limit=quota_limit,
        quota_remaining=quota_remaining,
        quota_percentage=quota_percentage,
        user_tier=user_tier,
        llm_calls=daily_usage["llm_calls"],
        model_breakdown=daily_usage.get("model_breakdown", {})
    )

    return report


def check_user_quota(
    user_id: str,
    user_tier: str = "free",
    raise_on_exceed: bool = False
) -> Dict[str, Any]:
    """
    检查用户配额

    便捷函数，用于快速检查用户配额状态。

    Args:
        user_id: 用户ID
        user_tier: 用户等级
        raise_on_exceed: 超限时是否抛出异常

    Returns:
        Dict: 配额状态
    """
    return quota_checker.check_quota(user_id, user_tier, raise_on_exceed)


def record_token_usage(
    user_id: str,
    tokens: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model_name: str = "unknown"
) -> bool:
    """
    记录Token使用量

    便捷函数，用于直接记录Token使用到每日配额统计。

    Args:
        user_id: 用户ID
        tokens: 总token数
        prompt_tokens: 输入token数
        completion_tokens: 输出token数
        model_name: 模型名称

    Returns:
        bool: 是否成功
    """
    return quota_checker.record_usage(user_id, tokens, prompt_tokens, completion_tokens, model_name)


# ==================== 🆕 排行榜和仪表盘功能 ====================

class TokenRankingManager:
    """
    Token排行榜管理器

    功能：
    1. 每日用户Token消耗排行榜
    2. 每日/月度Token统计
    3. Token仪表盘数据
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection_pool_manager = None

    async def _get_redis_client(self):
        """获取Redis客户端（使用连接池管理器）"""
        if self.connection_pool_manager is None:
            from utils.connection_pool_manager import get_connection_pool_manager
            self.connection_pool_manager = await get_connection_pool_manager()

        return await self.connection_pool_manager.get_redis_client('normal')

    async def get_daily_token_stats(self, days: int = 7) -> Dict[str, int]:
        """
        获取最近几天的Token消耗统计

        Args:
            days: 获取最近多少天的数据，默认7天

        Returns:
            Dict[str, int]: 日期 -> Token消耗量
        """
        try:
            redis_client = await self._get_redis_client()

            daily_stats = {}

            for i in range(days):
                date_str = (date.today() - timedelta(days=i)).isoformat()
                key = f"token_stats:daily:{date_str}"

                try:
                    value = await redis_client.get(key)
                    tokens = int(value) if value else 0
                    daily_stats[date_str] = tokens
                except Exception as e:
                    self.logger.warning(f"⚠️ 获取日统计失败: {key}, {e}")
                    daily_stats[date_str] = 0

            # 按日期排序
            return dict(sorted(daily_stats.items()))

        except Exception as e:
            self.logger.error(f"获取日Token统计失败: {e}")
            return {}

    async def get_monthly_token_stats(self, months: int = 3) -> Dict[str, int]:
        """
        获取最近几个月的Token消耗统计

        Args:
            months: 获取最近多少个月的数据，默认3个月

        Returns:
            Dict[str, int]: 月份 -> Token消耗量
        """
        try:
            redis_client = await self._get_redis_client()

            monthly_stats = {}

            for i in range(months):
                month = (datetime.now() - timedelta(days=i * 30)).strftime("%Y-%m")
                key = f"token_stats:monthly:{month}"

                try:
                    value = await redis_client.get(key)
                    tokens = int(value) if value else 0
                    monthly_stats[month] = tokens
                except Exception as e:
                    self.logger.warning(f"⚠️ 获取月统计失败: {key}, {e}")
                    monthly_stats[month] = 0

            # 按月份排序
            return dict(sorted(monthly_stats.items()))

        except Exception as e:
            self.logger.error(f"获取月Token统计失败: {e}")
            return {}

    async def get_daily_user_token_ranking(
        self,
        target_date: Optional[str] = None,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取指定日期用户Token消耗排行榜

        Args:
            target_date: 目标日期，格式：YYYY-MM-DD，默认今天
            top_n: 返回前N名用户，默认10名

        Returns:
            List[Dict[str, Any]]: 用户Token消耗排行榜
        """
        try:
            if not target_date:
                target_date = date.today().isoformat()

            redis_client = await self._get_redis_client()

            # 从每日配额统计key获取用户数据
            pattern = f"quota:daily:*:{target_date}"
            keys = await redis_client.keys(pattern)

            user_token_stats = {}

            for key in keys:
                try:
                    # 确保key为字符串类型（Redis返回bytes）
                    key_str = key.decode() if isinstance(key, bytes) else key

                    # 从key中提取user_id: quota:daily:{user_id}:{date}
                    parts = key_str.split(":")
                    if len(parts) >= 4:
                        user_id = parts[2]

                        # 获取total_tokens字段
                        total_tokens = await redis_client.hget(key, "total_tokens")
                        tokens = int(total_tokens) if total_tokens else 0

                        if tokens > 0:
                            # 获取会话数和调用次数
                            llm_calls = await redis_client.hget(key, "llm_calls")
                            llm_calls = int(llm_calls) if llm_calls else 1

                            user_token_stats[user_id] = {
                                "user_id": user_id,
                                "total_tokens": tokens,
                                "llm_calls": llm_calls,
                                "avg_tokens_per_call": tokens // llm_calls
                            }

                except Exception as e:
                    self.logger.warning(f"处理用户Token排行数据失败: {key}, {e}")
                    continue

            # 按Token消耗量排序并取前N名
            ranking = sorted(
                user_token_stats.values(),
                key=lambda x: x["total_tokens"],
                reverse=True
            )[:top_n]

            # 添加排名信息
            for i, user_stats in enumerate(ranking, 1):
                user_stats["rank"] = i

            self.logger.info(f"获取{target_date}用户Token排行榜完成，共{len(ranking)}名用户")
            return ranking

        except Exception as e:
            self.logger.error(f"获取用户Token排行榜失败: {e}")
            return []

    async def get_token_dashboard_data(self) -> Dict[str, Any]:
        """
        获取Token统计仪表盘数据

        Returns:
            Dict[str, Any]: Token统计仪表盘数据
        """
        try:
            # 获取基础统计数据
            daily_stats = await self.get_daily_token_stats(7)
            monthly_stats = await self.get_monthly_token_stats(3)
            today_ranking = await self.get_daily_user_token_ranking(top_n=10)

            # 计算总体统计
            today_total = 0
            weekly_total = sum(daily_stats.values())
            monthly_total = sum(monthly_stats.values())

            today_date = date.today().isoformat()
            today_total = daily_stats.get(today_date, 0)

            # 格式化图表数据
            daily_chart_data = {
                "labels": list(daily_stats.keys()),
                "token_counts": list(daily_stats.values())
            }

            monthly_chart_data = {
                "labels": list(monthly_stats.keys()),
                "token_counts": list(monthly_stats.values())
            }

            return {
                "summary": {
                    "today_tokens": today_total,
                    "weekly_tokens": weekly_total,
                    "monthly_tokens": monthly_total,
                    "today_top_users": len(today_ranking)
                },
                "daily_chart": daily_chart_data,
                "monthly_chart": monthly_chart_data,
                "today_ranking": today_ranking,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"获取Token仪表盘数据失败: {e}")
            return {
                "summary": {
                    "today_tokens": 0,
                    "weekly_tokens": 0,
                    "monthly_tokens": 0,
                    "today_top_users": 0
                },
                "daily_chart": {"labels": [], "token_counts": []},
                "monthly_chart": {"labels": [], "token_counts": []},
                "today_ranking": [],
                "error": str(e)
            }


# 全局排行榜管理器实例
_token_ranking_manager: Optional[TokenRankingManager] = None


def get_token_ranking_manager() -> TokenRankingManager:
    """获取Token排行榜管理器单例"""
    global _token_ranking_manager
    if _token_ranking_manager is None:
        _token_ranking_manager = TokenRankingManager()
    return _token_ranking_manager


# ==================== 便捷函数 ====================

async def get_daily_token_ranking(top_n: int = 10) -> List[Dict[str, Any]]:
    """获取每日Token排行榜"""
    manager = get_token_ranking_manager()
    return await manager.get_daily_user_token_ranking(top_n=top_n)


async def get_token_stats(days: int = 7) -> Dict[str, int]:
    """获取Token统计数据"""
    manager = get_token_ranking_manager()
    return await manager.get_daily_token_stats(days)


async def get_token_dashboard() -> Dict[str, Any]:
    """获取Token仪表盘数据"""
    manager = get_token_ranking_manager()
    return await manager.get_token_dashboard_data()

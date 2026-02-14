"""
后台进化优化器
定时分析反馈数据，触发 Prompt 进化流程

功能：
1. 定时任务调度（APScheduler）
2. 反馈数据分析
3. 进化触发判断
4. 自动调用 MetaOptimizerAgent
5. 版本管理和 A/B 测试配置

代码作者：Claude
创建时间：2026年2月7日
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvolutionTrigger:
    """进化触发条件"""
    agent_name: str
    avg_rating: float
    total_feedbacks: int
    should_evolve: bool
    reason: str


@dataclass
class EvolutionResult:
    """进化结果"""
    agent_name: str
    success: bool
    old_version: str
    new_version: str
    ab_test_configured: bool
    timestamp: str
    error: Optional[str] = None


class EvolutionOptimizer:
    """
    后台进化优化器

    负责：
    1. 定时分析各 Agent 的反馈数据
    2. 判断是否需要进化
    3. 调用 MetaOptimizerAgent 生成新 Prompt
    4. 配置 A/B 测试
    5. 通知管理员
    """

    def __init__(
        self,
        redis_client=None,
        feedback_manager=None,
        version_manager=None
    ):
        """
        初始化进化优化器

        Args:
            redis_client: Redis 客户端
            feedback_manager: 反馈管理器
            version_manager: 版本管理器
        """
        self.redis_client = redis_client
        self.feedback_manager = feedback_manager
        self.version_manager = version_manager
        self.logger = logger

        # 进化配置
        self.evolution_threshold_rating = 3.5  # 评分阈值
        self.evolution_min_feedbacks = 10     # 最小反馈数
        self.ab_test_percentage = 10          # A/B 测试流量百分比
        self.ab_test_duration_days = 7        # A/B 测试持续时间

        # 调度器
        self.scheduler = None
        self._running = False

    def start_scheduler(self):
        """启动定时调度器"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger

            self.scheduler = AsyncIOScheduler()

            # 每天凌晨 2 点执行进化分析
            self.scheduler.add_job(
                self._daily_evolution_check,
                trigger=CronTrigger(hour=2, minute=0),
                id='daily_evolution_check',
                name='每日进化检查'
            )

            self.scheduler.start()
            self._running = True
            self.logger.info("✅ 进化优化器已启动，将在每天凌晨 2 点执行检查")

        except ImportError:
            self.logger.warning("APScheduler 未安装，进化优化器将无法自动运行")
        except Exception as e:
            self.logger.error(f"启动调度器失败: {e}")

    def stop_scheduler(self):
        """停止定时调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            self._running = False
            self.logger.info("进化优化器已停止")

    async def _daily_evolution_check(self):
        """每日进化检查（定时任务）"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🔬 开始每日进化检查")
            self.logger.info("=" * 60)

            # 1. 获取所有 Agent 的反馈统计
            agent_stats = await self._get_all_agent_statistics()

            # 2. 分析哪些 Agent 需要进化
            triggers = []
            for agent_name, stats in agent_stats.items():
                trigger = self._should_evolve(agent_name, stats)
                triggers.append(trigger)

            # 3. 对需要进化的 Agent 执行优化
            evolution_results = []
            for trigger in triggers:
                if trigger.should_evolve:
                    self.logger.info(f"🎯 触发进化: {trigger.agent_name} - {trigger.reason}")
                    result = await self._execute_evolution(trigger)
                    evolution_results.append(result)

            # 4. 检查 A/B 测试结果
            await self._check_ab_test_results()

            # 5. 生成进化报告
            await self._generate_evolution_report(triggers, evolution_results)

            self.logger.info("=" * 60)
            self.logger.info("✅ 每日进化检查完成")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"每日进化检查失败: {e}")

    async def _get_all_agent_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的统计信息"""
        try:
            if not self.feedback_manager:
                return {}

            # 获取过去 24 小时的统计
            stats = await self.feedback_manager.get_statistics(days=1)

            # 按分组组
            agent_stats = {}
            for agent_stat in stats.get('by_agent', []):
                agent_name = agent_stat['agent_name']
                agent_stats[agent_name] = agent_stat

            return agent_stats

        except Exception as e:
            self.logger.error(f"获取 Agent 统计失败: {e}")
            return {}

    def _should_evolve(self, agent_name: str, stats: Dict[str, Any]) -> EvolutionTrigger:
        """
        判断是否需要进化

        条件：
        1. 平均评分 < 3.5
        2. 反馈数量 >= 10

        Args:
            agent_name: Agent 名称
            stats: 统计信息

        Returns:
            EvolutionTrigger: 进化触发条件
        """
        avg_rating = stats.get('avg_rating', 0)
        total_feedbacks = stats.get('total_feedbacks', 0)

        should_evolve = (
            avg_rating < self.evolution_threshold_rating and
            total_feedbacks >= self.evolution_min_feedbacks
        )

        if should_evolve:
            reason = f"平均评分 {avg_rating:.2f} 低于阈值 {self.evolution_threshold_rating}"
        else:
            reason = f"评分正常 ({avg_rating:.2f}) 或反馈不足"

        return EvolutionTrigger(
            agent_name=agent_name,
            avg_rating=avg_rating,
            total_feedbacks=total_feedbacks,
            should_evolve=should_evolve,
            reason=reason
        )

    async def _execute_evolution(self, trigger: EvolutionTrigger) -> EvolutionResult:
        """
        执行进化

        Args:
            trigger: 进化触发条件

        Returns:
            EvolutionResult: 进化结果
        """
        try:
            agent_name = trigger.agent_name

            # 1. 获取当前活跃版本
            active_version = await self.version_manager.get_active_version(agent_name)
            if not active_version:
                return EvolutionResult(
                    agent_name=agent_name,
                    success=False,
                    old_version="",
                    new_version="",
                    ab_test_configured=False,
                    timestamp=datetime.now().isoformat(),
                    error="未找到活跃版本"
                )

            # 2. 获取差评案例
            negative_cases = await self._get_negative_cases(agent_name, limit=5)
            if not negative_cases:
                return EvolutionResult(
                    agent_name=agent_name,
                    success=False,
                    old_version=active_version.version,
                    new_version="",
                    ab_test_configured=False,
                    timestamp=datetime.now().isoformat(),
                    error="未找到足够的差评案例"
                )

            # 3. 获取好评案例/正确范文
            positive_cases = await self._get_positive_cases(agent_name, limit=5)

            # 4. 调用 MetaOptimizerAgent 进行优化
            from agents.meta_optimizer_agent import get_meta_optimizer_agent
            optimizer = get_meta_optimizer_agent()

            optimization_result = await optimizer.optimize_prompt(
                agent_name=agent_name,
                current_prompt=active_version.prompt_content,
                negative_cases=negative_cases,
                positive_cases=positive_cases
            )

            # 5. 创建新版本
            new_version_id = self.version_manager.generate_version_id(
                agent_name, optimization_result.version
            )

            from evolution.prompt_version_manager import PromptVersion, PromptVersionStatus
            new_version = PromptVersion(
                version_id=new_version_id,
                agent_name=agent_name,
                version=optimization_result.version,
                prompt_content=optimization_result.optimized_prompt,
                status=PromptVersionStatus.TESTING,
                parent_version_id=active_version.version_id,
                created_by="meta_optimizer",
                changelog="\n".join(optimization_result.improvement_suggestions),
                optimization_reason=optimization_result.optimization_reasoning,
                ab_test_percentage=self.ab_test_percentage
            )

            # 6. 保存新版本并配置 A/B 测试
            await self.version_manager.save_version(new_version)
            await self.version_manager.set_candidate_version(agent_name, new_version)

            from evolution.ab_test_router import ABTestRouter
            ab_router = ABTestRouter(self.redis_client, self.version_manager)
            await ab_router.set_ab_config(
                agent_name=agent_name,
                control_version_id=active_version.version_id,
                treatment_version_id=new_version.version_id,
                traffic_percentage=self.ab_test_percentage
            )

            self.logger.info(f"✅ 进化完成 (agent: {agent_name}, new version: {optimization_result.version})")

            return EvolutionResult(
                agent_name=agent_name,
                success=True,
                old_version=active_version.version,
                new_version=optimization_result.version,
                ab_test_configured=True,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            self.logger.error(f"执行进化失败: {e}")
            return EvolutionResult(
                agent_name=trigger.agent_name,
                success=False,
                old_version="",
                new_version="",
                ab_test_configured=False,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )

    async def _get_negative_cases(self, agent_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取差评案例"""
        try:
            if not self.feedback_manager:
                return []

            # 获取低评分反馈
            feedbacks = await self.feedback_manager.get_feedback(
                agent_name=agent_name,
                limit=100
            )

            # 筛选差评（评分 < 3）
            negative_cases = []
            for fb in feedbacks:
                if fb.user_rating and fb.user_rating < 3:
                    negative_cases.append({
                        "user_input": fb.user_input,
                        "ai_output": fb.ai_output,
                        "feedback": f"评分: {fb.user_rating}/5"
                    })
                    if len(negative_cases) >= limit:
                        break

            return negative_cases

        except Exception as e:
            self.logger.error(f"获取差评案例失败: {e}")
            return []

    async def _get_positive_cases(self, agent_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取好评案例/正确范文"""
        try:
            if not self.feedback_manager:
                return []

            # 获取黄金样本
            from utils.feedback_manager import get_gold_sample_manager
            gold_manager = get_gold_sample_manager()

            gold_samples = await gold_manager.search_similar(
                query_text="",  # 搜索所有
                agent_name=agent_name,
                top_k=limit
            )

            positive_cases = []
            for sample in gold_samples:
                positive_cases.append({
                    "user_input": sample.user_input,
                    "ai_output": sample.ai_output,
                    "success_reason": sample.feedback.gold_sample_reason or "黄金样本"
                })

            return positive_cases

        except Exception as e:
            self.logger.error(f"获取好评案例失败: {e}")
            return []

    async def _check_ab_test_results(self):
        """检查 A/B 测试结果"""
        try:
            from evolution.ab_test_router import ABTestRouter
            ab_router = ABTestRouter(self.redis_client, self.version_manager)

            # 获取所有有 A/B 测试的 Agent
            if not self.redis_client:
                return

            ab_keys = await self.redis_client.keys("agent_prompt_ab_config:*")

            for key in ab_keys:
                agent_name = key.decode().split(":")[-1]

                # 比较性能
                comparison = await ab_router.compare_performance(agent_name)

                if comparison.get('comparison', {}).get('significant_improvement'):
                    await self._notify_promotion_ready(agent_name, comparison)

        except Exception as e:
            self.logger.error(f"检查 A/B 测试结果失败: {e}")

    async def _notify_promotion_ready(self, agent_name: str, comparison: Dict[str, Any]):
        """通知管理员准备晋升"""
        try:
            # 将版本标记为待晋升
            from evolution.prompt_version_manager import PromptVersionStatus

            versions = await self.version_manager.get_all_versions(agent_name)
            for version in versions:
                if version.status == PromptVersionStatus.TESTING:
                    version.status = PromptVersionStatus.STAGED
                    version.promotion_ready = True
                    await self.version_manager.save_version(version)

            self.logger.info(f"📢 晋升通知: {agent_name} 的新版本表现显著提升，建议晋升")

            # 这里可以发送邮件、Slack、钉钉等通知
            # await self._send_admin_notification(agent_name, comparison)

        except Exception as e:
            self.logger.error(f"通知晋升失败: {e}")

    async def _generate_evolution_report(
        self,
        triggers: List[EvolutionTrigger],
        results: List[EvolutionResult]
    ):
        """生成进化报告"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_agents_checked": len(triggers),
                    "agents_need_evolution": sum(1 for t in triggers if t.should_evolve),
                    "evolution_executed": sum(1 for r in results if r.success),
                    "ab_tests_active": len([r for r in results if r.ab_test_configured])
                },
                "triggers": [
                    {
                        "agent_name": t.agent_name,
                        "avg_rating": t.avg_rating,
                        "total_feedbacks": t.total_feedbacks,
                        "should_evolve": t.should_evolve,
                        "reason": t.reason
                    }
                    for t in triggers
                ],
                "results": [
                    {
                        "agent_name": r.agent_name,
                        "success": r.success,
                        "old_version": r.old_version,
                        "new_version": r.new_version,
                        "ab_test_configured": r.ab_test_configured,
                        "error": r.error
                    }
                    for r in results
                ]
            }

            # 保存报告到 Redis
            if self.redis_client:
                report_key = f"evolution_report:{datetime.now().strftime('%Y%m%d')}"
                await self.redis_client.set(
                    report_key,
                    __import__('json').dumps(report, ensure_ascii=False),
                    ex=60 * 60 * 24 * 7  # 保留 7 天
                )

            self.logger.info(f"📊 进化报告已生成: {report['summary']}")

        except Exception as e:
            self.logger.error(f"生成进化报告失败: {e}")

    async def trigger_manual_evolution(self, agent_name: str) -> EvolutionResult:
        """
        手动触发进化

        Args:
            agent_name: Agent 名称

        Returns:
            EvolutionResult: 进化结果
        """
        try:
            self.logger.info(f"🔧 手动触发进化: {agent_name}")

            # 获取统计
            stats = await self.feedback_manager.get_statistics(agent_name=agent_name, days=7)

            trigger = EvolutionTrigger(
                agent_name=agent_name,
                avg_rating=stats.get('avg_rating', 0),
                total_feedbacks=stats.get('total_feedbacks', 0),
                should_evolve=True,
                reason="手动触发"
            )

            return await self._execute_evolution(trigger)

        except Exception as e:
            self.logger.error(f"手动触发进化失败: {e}")
            return EvolutionResult(
                agent_name=agent_name,
                success=False,
                old_version="",
                new_version="",
                ab_test_configured=False,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )


# ==================== 全局实例 ====================

_evolution_optimizer: Optional[EvolutionOptimizer] = None


def get_evolution_optimizer(
    redis_client=None,
    feedback_manager=None,
    version_manager=None
) -> EvolutionOptimizer:
    """获取进化优化器单例"""
    global _evolution_optimizer
    if _evolution_optimizer is None:
        _evolution_optimizer = EvolutionOptimizer(
            redis_client=redis_client,
            feedback_manager=feedback_manager,
            version_manager=version_manager
        )
    return _evolution_optimizer

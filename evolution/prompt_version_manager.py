"""
Prompt 版本管理器
实现 Prompt 的版本控制、A/B 测试和灰度发布

功能：
1. PromptVersion: 版本数据模型
2. PromptVersionManager: 版本管理（Redis）
3. ABTestRouter: A/B 测试流量路由

代码作者：Claude
创建时间：2026年2月7日
"""

import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ==================== 版本数据模型 ====================

class PromptVersionStatus(Enum):
    """Prompt 版本状态"""
    DRAFT = "draft"           # 草稿
    CANDIDATE = "candidate"   # 候选（待测试）
    TESTING = "testing"       # 测试中
    ACTIVE = "active"         # 活跃（生产使用）
    STAGED = "staged"         # 待晋升
    DEPRECATED = "deprecated" # 已弃用
    ARCHIVED = "archived"     # 已归档


@dataclass
class PromptVersion:
    """
    Prompt 版本

    字段：
    - version_id: 版本ID
    - agent_name: Agent名称
    - version: 版本号（如 v1.0.0）
    - prompt_content: Prompt内容
    - status: 版本状态
    - parent_version_id: 父版本ID
    - performance_metrics: 性能指标
    """
    version_id: str
    agent_name: str
    version: str
    prompt_content: str

    # 状态
    status: PromptVersionStatus
    parent_version_id: Optional[str] = None

    # 性能指标
    avg_rating: float = 0.0
    total_feedbacks: int = 0
    gold_sample_count: int = 0
    edit_ratio_avg: float = 0.0

    # A/B 测试
    ab_test_percentage: int = 0    # A/B 测试流量百分比（0-100）
    ab_test_started_at: Optional[str] = None
    ab_test_requests: int = 0

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "system"     # system / admin / meta_optimizer
    changelog: str = ""            # 变更日志
    optimization_reason: str = ""  # 优化原因

    # 晋升建议
    promotion_score: float = 0.0   # 晋升评分（0-1）
    promotion_ready: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptVersion':
        """从字典创建"""
        if isinstance(data.get('status'), str):
            data['status'] = PromptVersionStatus(data['status'])
        return cls(**data)

    def calculate_promotion_score(self) -> float:
        """
        计算晋升评分

        综合考虑：
        1. 平均评分（权重40%）
        2. 黄金样本比例（权重30%）
        3. 低编辑比例（权重20%）
        4. 反馈数量（权重10%）

        Returns:
            float: 晋升评分 (0-1)
        """
        # 评分归一化
        rating_score = self.avg_rating / 5.0

        # 黄金样本比例
        gold_ratio = self.gold_sample_count / max(self.total_feedbacks, 1)

        # 低编辑比例（编辑越少越好）
        edit_score = 1.0 - min(self.edit_ratio_avg, 1.0)

        # 反馈数量（至少30个反馈）
        feedback_score = min(self.total_feedbacks / 30, 1.0)

        # 加权计算
        self.promotion_score = (
            rating_score * 0.4 +
            gold_ratio * 0.3 +
            edit_score * 0.2 +
            feedback_score * 0.1
        )

        # 晋升条件：评分 > 0.7 且 反馈数量 >= 20
        self.promotion_ready = (
            self.promotion_score > 0.7 and
            self.total_feedbacks >= 20
        )

        return self.promotion_score


@dataclass
class ABTestConfig:
    """A/B 测试配置"""
    agent_name: str
    control_version_id: str      # 对照组（当前生产版本）
    treatment_version_id: str    # 实验组（新版本）
    traffic_percentage: int      # 实验组流量百分比（0-100）
    started_at: str
    min_samples: int = 50        # 最小样本数
    test_duration_days: int = 7  # 测试持续时间（天）
    status: str = "running"      # running, paused, completed


# ==================== 版本管理器 ====================

class PromptVersionManager:
    """
    Prompt 版本管理器

    负责：
    1. 版本的创建、存储、检索
    2. 版本状态管理
    3. 性能指标更新
    4. 晋升决策
    """

    def __init__(self, redis_client=None):
        """
        初始化版本管理器

        Args:
            redis_client: Redis 客户端
        """
        self.redis_client = redis_client
        self.logger = logger

        # Key 前缀
        self.version_key_prefix = "agent_prompt_version"
        self.versions_list_key = "agent_prompt_versions"
        self.active_prompt_key = "agent_prompt_active"
        self.candidate_prompt_key = "agent_prompt_candidate"

    def _get_version_key(self, version_id: str) -> str:
        """获取版本 Redis key"""
        return f"{self.version_key_prefix}:{version_id}"

    def _get_agent_versions_key(self, agent_name: str) -> str:
        """获取 Agent 版本列表 Redis key"""
        return f"{self.versions_list_key}:{agent_name}"

    def _get_active_prompt_key(self, agent_name: str) -> str:
        """获取活跃 Prompt Redis key"""
        return f"{self.active_prompt_key}:{agent_name}"

    def _get_candidate_prompt_key(self, agent_name: str) -> str:
        """获取候选 Prompt Redis key"""
        return f"{self.candidate_prompt_key}:{agent_name}"

    async def save_version(self, version: PromptVersion) -> bool:
        """
        保存版本

        Args:
            version: 版本对象

        Returns:
            bool: 是否保存成功
        """
        try:
            if not self.redis_client:
                self.logger.warning("Redis客户端未配置，跳过保存")
                return False

            # 保存版本
            version_key = self._get_version_key(version.version_id)
            data = json.dumps(version.to_dict(), ensure_ascii=False)
            await self.redis_client.set(version_key, data)

            # 添加到 Agent 版本列表
            list_key = self._get_agent_versions_key(version.agent_name)
            await self.redis_client.sadd(list_key, version.version_id)

            self.logger.info(f"✅ 保存 Prompt 版本 (agent: {version.agent_name}, version: {version.version})")
            return True

        except Exception as e:
            self.logger.error(f"保存版本失败: {e}")
            return False

    async def get_version(self, version_id: str) -> Optional[PromptVersion]:
        """
        获取版本

        Args:
            version_id: 版本ID

        Returns:
            Optional[PromptVersion]: 版本对象
        """
        try:
            if not self.redis_client:
                return None

            version_key = self._get_version_key(version_id)
            data = await self.redis_client.get(version_key)

            if data:
                return PromptVersion.from_dict(json.loads(data))
            return None

        except Exception as e:
            self.logger.error(f"获取版本失败: {e}")
            return None

    async def get_active_version(self, agent_name: str) -> Optional[PromptVersion]:
        """
        获取活跃版本（生产使用的版本）

        Args:
            agent_name: Agent名称

        Returns:
            Optional[PromptVersion]: 活跃版本
        """
        try:
            if not self.redis_client:
                return None

            active_key = self._get_active_prompt_key(agent_name)
            version_id = await self.redis_client.get(active_key)

            if version_id:
                return await self.get_version(version_id.decode())
            return None

        except Exception as e:
            self.logger.error(f"获取活跃版本失败: {e}")
            return None

    async def get_candidate_version(self, agent_name: str) -> Optional[PromptVersion]:
        """
        获取候选版本（待测试的版本）

        Args:
            agent_name: Agent名称

        Returns:
            Optional[PromptVersion]: 候选版本
        """
        try:
            if not self.redis_client:
                return None

            candidate_key = self._get_candidate_prompt_key(agent_name)
            version_id = await self.redis_client.get(candidate_key)

            if version_id:
                return await self.get_version(version_id.decode())
            return None

        except Exception as e:
            self.logger.error(f"获取候选版本失败: {e}")
            return None

    async def set_active_version(self, agent_name: str, version: PromptVersion) -> bool:
        """
        设置活跃版本

        Args:
            agent_name: Agent名称
            version: 版本对象

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.redis_client:
                return False

            # 更新版本状态
            version.status = PromptVersionStatus.ACTIVE
            await self.save_version(version)

            # 设置为活跃
            active_key = self._get_active_prompt_key(agent_name)
            await self.redis_client.set(active_key, version.version_id)

            self.logger.info(f"✅ 设置活跃版本 (agent: {agent_name}, version: {version.version})")
            return True

        except Exception as e:
            self.logger.error(f"设置活跃版本失败: {e}")
            return False

    async def set_candidate_version(self, agent_name: str, version: PromptVersion) -> bool:
        """
        设置候选版本（用于 A/B 测试）

        Args:
            agent_name: Agent名称
            version: 版本对象

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.redis_client:
                return False

            # 更新版本状态
            version.status = PromptVersionStatus.TESTING
            await self.save_version(version)

            # 设置为候选
            candidate_key = self._get_candidate_prompt_key(agent_name)
            await self.redis_client.set(candidate_key, version.version_id)

            self.logger.info(f"✅ 设置候选版本 (agent: {agent_name}, version: {version.version})")
            return True

        except Exception as e:
            self.logger.error(f"设置候选版本失败: {e}")
            return False

    async def get_all_versions(self, agent_name: str) -> List[PromptVersion]:
        """
        获取 Agent 的所有版本

        Args:
            agent_name: Agent名称

        Returns:
            List[PromptVersion]: 版本列表
        """
        try:
            if not self.redis_client:
                return []

            list_key = self._get_agent_versions_key(agent_name)
            version_ids = await self.redis_client.smembers(list_key)

            versions = []
            for vid in version_ids:
                version = await self.get_version(vid.decode())
                if version:
                    versions.append(version)

            # 按创建时间排序
            versions.sort(key=lambda v: v.created_at, reverse=True)
            return versions

        except Exception as e:
            self.logger.error(f"获取所有版本失败: {e}")
            return []

    async def update_version_metrics(
        self,
        version_id: str,
        avg_rating: float,
        total_feedbacks: int,
        gold_sample_count: int,
        edit_ratio_avg: float
    ) -> bool:
        """
        更新版本性能指标

        Args:
            version_id: 版本ID
            avg_rating: 平均评分
            total_feedbacks: 总反馈数
            gold_sample_count: 黄金样本数
            edit_ratio_avg: 平均编辑比例

        Returns:
            bool: 是否更新成功
        """
        try:
            version = await self.get_version(version_id)
            if not version:
                return False

            version.avg_rating = avg_rating
            version.total_feedbacks = total_feedbacks
            version.gold_sample_count = gold_sample_count
            version.edit_ratio_avg = edit_ratio_avg

            # 重新计算晋升评分
            version.calculate_promotion_score()

            await self.save_version(version)
            return True

        except Exception as e:
            self.logger.error(f"更新版本指标失败: {e}")
            return False

    async def get_promotion_ready_versions(self) -> List[PromptVersion]:
        """
        获取所有准备晋升的版本

        Returns:
            List[PromptVersion]: 准备晋升的版本列表
        """
        try:
            if not self.redis_client:
                return []

            # 获取所有 Agent
            agent_keys = await self.redis_client.keys(f"{self.versions_list_key}:*")
            ready_versions = []

            for agent_key in agent_keys:
                agent_name = agent_key.decode().split(":")[-1]
                versions = await self.get_all_versions(agent_name)

                for version in versions:
                    # 重新计算评分
                    version.calculate_promotion_score()

                    if version.promotion_ready:
                        ready_versions.append(version)
                        await self.save_version(version)

            # 按晋升评分排序
            ready_versions.sort(key=lambda v: v.promotion_score, reverse=True)
            return ready_versions

        except Exception as e:
            self.logger.error(f"获取准备晋升的版本失败: {e}")
            return []

    def generate_version_id(self, agent_name: str, version: str) -> str:
        """
        生成版本ID

        Args:
            agent_name: Agent名称
            version: 版本号

        Returns:
            str: 版本ID
        """
        content = f"{agent_name}:{version}:{datetime.now().isoformat()}"
        hash_hex = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"pv_{hash_hex}"

    def generate_next_version(self, current_version: str) -> str:
        """
        生成下一个版本号

        Args:
            current_version: 当前版本号（如 v1.0.0）

        Returns:
            str: 下一个版本号（如 v1.0.1）
        """
        try:
            # 解析版本号
            if current_version.startswith('v'):
                current_version = current_version[1:]

            parts = current_version.split('.')
            if len(parts) >= 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                patch += 1
                return f"v{major}.{minor}.{patch}"
            else:
                return "v1.0.1"
        except:
            return "v1.0.1"


# ==================== A/B 测试路由器 ====================

class ABTestRouter:
    """
    A/B 测试路由器

    负责：
    1. 流量分配（根据百分比）
    2. 版本选择
    3. 测试数据收集
    """

    def __init__(self, redis_client=None, version_manager: PromptVersionManager = None):
        """
        初始化 A/B 测试路由器

        Args:
            redis_client: Redis 客户端
            version_manager: 版本管理器
        """
        self.redis_client = redis_client
        self.version_manager = version_manager or PromptVersionManager(redis_client)
        self.logger = logger

        # A/B 测试配置 key
        self.ab_config_key = "agent_prompt_ab_config"
        self.ab_traffic_key = "agent_prompt_ab_traffic"

    async def get_prompt_for_request(
        self,
        agent_name: str,
        user_id: str,
        session_id: str
    ) -> Tuple[str, Optional[str]]:
        """
        获取请求应使用的 Prompt

        根据用户/会话分配到不同版本，实现 A/B 测试。

        Args:
            agent_name: Agent名称
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Tuple[str, Optional[str]]: (prompt_content, version_id)
        """
        try:
            # 获取 A/B 测试配置
            ab_config = await self._get_ab_config(agent_name)

            if not ab_config:
                # 没有 A/B 测试配置，使用活跃版本
                active_version = await self.version_manager.get_active_version(agent_name)
                if active_version:
                    return active_version.prompt_content, active_version.version_id
                return "", None

            # 计算流量分配
            treatment_percentage = ab_config.get('traffic_percentage', 0)

            # 基于用户 ID 的一致性哈希
            user_hash = int(hashlib.md5(f"{user_id}:{agent_name}".encode()).hexdigest(), 16)
            hash_mod = user_hash % 100

            # 记录流量
            await self._record_traffic(agent_name, hash_mod < treatment_percentage)

            # 分配版本
            if hash_mod < treatment_percentage:
                # 实验组（新版本）
                candidate_version = await self.version_manager.get_candidate_version(agent_name)
                if candidate_version:
                    self.logger.debug(f"🔬 A/B 测试: 使用实验组版本 (agent: {agent_name}, user: {user_id})")
                    return candidate_version.prompt_content, candidate_version.version_id

            # 对照组（当前版本）
            active_version = await self.version_manager.get_active_version(agent_name)
            if active_version:
                return active_version.prompt_content, active_version.version_id

            return "", None

        except Exception as e:
            self.logger.error(f"获取 Prompt 失败: {e}")
            return "", None

    async def _get_ab_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取 A/B 测试配置"""
        try:
            if not self.redis_client:
                return None

            config_key = f"{self.ab_config_key}:{agent_name}"
            config = await self.redis_client.get(config_key)

            if config:
                return json.loads(config)
            return None

        except Exception as e:
            self.logger.error(f"获取 A/B 配置失败: {e}")
            return None

    async def set_ab_config(
        self,
        agent_name: str,
        control_version_id: str,
        treatment_version_id: str,
        traffic_percentage: int
    ) -> bool:
        """
        设置 A/B 测试配置

        Args:
            agent_name: Agent名称
            control_version_id: 对照组版本ID
            treatment_version_id: 实验组版本ID
            traffic_percentage: 实验组流量百分比

        Returns:
            bool: 是否设置成功
        """
        try:
            if not self.redis_client:
                return False

            config = {
                "agent_name": agent_name,
                "control_version_id": control_version_id,
                "treatment_version_id": treatment_version_id,
                "traffic_percentage": traffic_percentage,
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }

            config_key = f"{self.ab_config_key}:{agent_name}"
            await self.redis_client.set(config_key, json.dumps(config))

            self.logger.info(f"✅ 设置 A/B 测试配置 (agent: {agent_name}, traffic: {traffic_percentage}%)")
            return True

        except Exception as e:
            self.logger.error(f"设置 A/B 配置失败: {e}")
            return False

    async def _record_traffic(self, agent_name: str, is_treatment: bool) -> None:
        """记录流量分配"""
        try:
            if not self.redis_client:
                return

            traffic_key = f"{self.ab_traffic_key}:{agent_name}"
            field = "treatment" if is_treatment else "control"
            await self.redis_client.hincrby(traffic_key, field, 1)

        except Exception as e:
            self.logger.error(f"记录流量失败: {e}")

    async def get_traffic_stats(self, agent_name: str) -> Dict[str, Any]:
        """
        获取流量统计

        Args:
            agent_name: Agent名称

        Returns:
            Dict: 流量统计
        """
        try:
            if not self.redis_client:
                return {}

            traffic_key = f"{self.ab_traffic_key}:{agent_name}"
            stats = await self.redis_client.hgetall(traffic_key)

            control = int(stats.get(b'control', 0))
            treatment = int(stats.get(b'treatment', 0))
            total = control + treatment

            return {
                "agent_name": agent_name,
                "control_requests": control,
                "treatment_requests": treatment,
                "total_requests": total,
                "treatment_ratio": treatment / total if total > 0 else 0
            }

        except Exception as e:
            self.logger.error(f"获取流量统计失败: {e}")
            return {}

    async def compare_performance(self, agent_name: str) -> Dict[str, Any]:
        """
        比较对照组和实验组的性能

        Args:
            agent_name: Agent名称

        Returns:
            Dict: 性能比较结果
        """
        try:
            ab_config = await self._get_ab_config(agent_name)
            if not ab_config:
                return {}

            control_version = await self.version_manager.get_version(ab_config['control_version_id'])
            treatment_version = await self.version_manager.get_version(ab_config['treatment_version_id'])

            if not control_version or not treatment_version:
                return {}

            # 计算性能差异
            rating_diff = treatment_version.avg_rating - control_version.avg_rating
            edit_ratio_diff = treatment_version.edit_ratio_avg - control_version.edit_ratio_avg

            # 判断是否显著提升
            significant_improvement = (
                rating_diff > 0.3 and  # 评分提升超过 0.3
                treatment_version.total_feedbacks >= 20  # 至少20个反馈
            )

            return {
                "agent_name": agent_name,
                "control": {
                    "version": control_version.version,
                    "avg_rating": control_version.avg_rating,
                    "total_feedbacks": control_version.total_feedbacks,
                    "edit_ratio_avg": control_version.edit_ratio_avg
                },
                "treatment": {
                    "version": treatment_version.version,
                    "avg_rating": treatment_version.avg_rating,
                    "total_feedbacks": treatment_version.total_feedbacks,
                    "edit_ratio_avg": treatment_version.edit_ratio_avg
                },
                "comparison": {
                    "rating_diff": rating_diff,
                    "edit_ratio_diff": edit_ratio_diff,
                    "significant_improvement": significant_improvement
                }
            }

        except Exception as e:
            self.logger.error(f"比较性能失败: {e}")
            return {}


# ==================== 全局实例 ====================

_prompt_version_manager: Optional[PromptVersionManager] = None
_ab_test_router: Optional[ABTestRouter] = None


def get_prompt_version_manager(redis_client=None) -> PromptVersionManager:
    """获取版本管理器单例"""
    global _prompt_version_manager
    if _prompt_version_manager is None:
        _prompt_version_manager = PromptVersionManager(redis_client)
    return _prompt_version_manager


def get_ab_test_router(redis_client=None) -> ABTestRouter:
    """获取 A/B 测试路由器单例"""
    global _ab_test_router
    if _ab_test_router is None:
        version_manager = get_prompt_version_manager(redis_client)
        _ab_test_router = ABTestRouter(redis_client, version_manager)
    return _ab_test_router

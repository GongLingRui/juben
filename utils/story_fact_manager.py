"""
故事事实管理器

从剧本片段中提取并管理关键事实（人物、道具、场景等）。
使用 Redis 存储事实，按 session_id 组织。
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from enum import Enum


logger = logging.getLogger(__name__)


class FactType(Enum):
    """事实类型"""
    CHARACTER = "character"        # 新登场人物
    RELATIONSHIP = "relationship"   # 人际关系变化
    LOCATION = "location"          # 场景地点
    PROP = "prop"                  # 重要道具
    EVENT = "event"                # 重要事件
    DEATH = "death"                # 角色死亡
    BIRTH = "birth"                # 角色出生
    ABILITY = "ability"            # 特殊能力
    BACKGROUND = "background"      # 背景设定
    CONSTRAINT = "constraint"      # 其他约束


@dataclass
class StoryFact:
    """故事事实"""
    fact_type: FactType
    content: str
    source_scene: str = ""
    confidence: float = 1.0
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["fact_type"] = self.fact_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryFact":
        """从字典创建"""
        data = data.copy()
        if isinstance(data.get("fact_type"), str):
            data["fact_type"] = FactType(data["fact_type"])
        return cls(**data)


@dataclass
class FactExtractionResult:
    """事实提取结果"""
    facts: List[StoryFact] = field(default_factory=list)
    summary: str = ""
    model_used: str = ""
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "facts": [f.to_dict() for f in self.facts],
            "summary": self.summary,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "extracted_at": datetime.now().isoformat()
        }


class StoryFactManager:
    """
    故事事实管理器

    功能：
    1. 从剧本片段中提取关键事实
    2. 将事实存储到 Redis
    3. 生成用于 System Prompt 的事实约束文本
    """

    def __init__(self, redis_client=None):
        """
        初始化事实管理器

        Args:
            redis_client: Redis 客户端实例
        """
        self.logger = logging.getLogger(__name__)
        self._redis = redis_client
        self._redis_loaded = False

    def _ensure_redis(self):
        """确保 Redis 客户端已加载"""
        if not self._redis_loaded:
            if self._redis is None:
                try:
                    from utils.storage_manager import get_redis_client
                    self._redis = get_redis_client()
                except ImportError:
                    self.logger.warning("无法导入 Redis 客户端，使用内存存储")
                    self._redis = {}
            self._redis_loaded = True

    def _get_redis_key(self, session_id: str) -> str:
        """生成 Redis 键"""
        return f"facts:{session_id}"

    async def extract_and_save_facts(
        self,
        session_id: str,
        text: str,
        scene_title: str = "",
        model_name: str = "glm-4-flash"
    ) -> FactExtractionResult:
        """
        从剧本片段中提取并保存事实

        Args:
            session_id: 会话 ID
            text: 剧本文本
            scene_title: 场景标题（可选）
            model_name: 使用的模型名称

        Returns:
            FactExtractionResult: 提取结果
        """
        self._ensure_redis()

        # 调用轻量级模型提取事实
        facts = await self._extract_facts_with_llm(text, scene_title, model_name)

        # 保存到 Redis
        await self.save_facts(session_id, facts)

        # 生成摘要
        summary = self._generate_summary(facts)

        self.logger.info(f"从剧本中提取 {len(facts)} 个事实: {session_id}")

        return FactExtractionResult(
            facts=facts,
            summary=summary,
            model_used=model_name
        )

    async def _extract_facts_with_llm(
        self,
        text: str,
        scene_title: str,
        model_name: str
    ) -> List[StoryFact]:
        """
        使用 LLM 提取事实

        Args:
            text: 剧本文本
            scene_title: 场景标题
            model_name: 模型名称

        Returns:
            List[StoryFact]: 提取的事实列表
        """
        from utils.llm_client import llm_client

        # 构建提取提示词
        prompt = self._build_extraction_prompt(text, scene_title)

        try:
            # 调用 LLM
            response = await llm_client.call_llm(
                messages=[{"role": "user", "content": prompt}],
                model_name=model_name,
                temperature=0.3,
                max_tokens=2000
            )

            # 解析响应
            facts = self._parse_facts_from_response(response, scene_title)
            return facts

        except Exception as e:
            self.logger.error(f"LLM 事实提取失败: {e}")
            # 降级到正则表达式提取
            return self._extract_facts_with_regex(text, scene_title)

    def _build_extraction_prompt(self, text: str, scene_title: str) -> str:
        """构建事实提取提示词"""
        return f"""请从以下剧本片段中提取关键事实（人物、道具、场景、事件等）。

【场景】{scene_title or "未知场景"}

【剧本内容】
{text[:3000]}

【提取要求】
请识别以下类型的事实，以 JSON 格式输出：
1. character: 新登场人物
2. relationship: 人际关系变化
3. location: 场景地点
4. prop: 重要道具
5. event: 重要事件
6. death: 角色死亡
7. birth: 角色出生
8. ability: 特殊能力
9. background: 背景设定
10. constraint: 其他约束

【输出格式】
{{
  "facts": [
    {{"type": "character", "content": "张三，35岁，公司高管，性格冷酷"}},
    {{"type": "prop", "content": "一把古老的钥匙，能打开密室"}},
    {{"type": "event", "content": "主角发现了公司账目异常"}}
  ]
}}

请只输出 JSON，不要包含其他说明。"""

    def _parse_facts_from_response(self, response: str, scene_title: str) -> List[StoryFact]:
        """解析 LLM 响应中的事实"""
        facts = []

        try:
            # 尝试提取 JSON
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            data = json.loads(response)

            for item in data.get("facts", []):
                try:
                    fact_type = FactType(item.get("type", "constraint"))
                    facts.append(StoryFact(
                        fact_type=fact_type,
                        content=item.get("content", ""),
                        source_scene=scene_title,
                        confidence=0.9
                    ))
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"跳过无效事实: {item}, 错误: {e}")
                    continue

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON 解析失败: {e}")

        return facts

    def _extract_facts_with_regex(self, text: str, scene_title: str) -> List[StoryFact]:
        """使用正则表达式提取事实（降级方案）"""
        import re

        facts = []
        patterns = {
            FactType.CHARACTER: [
                r'(?:新登场|出现|登场|引入)(?:人物|角色)[：:]\s*([^。\n]+)',
                r'([A-Z][a-z]+)\s+(?:登场|出现|走进)',
            ],
            FactType.PROP: [
                r'(?:发现|拿起|拿着|佩戴)(?:道具|物品|武器|首饰)[：:]\s*([^。\n]+)',
            ],
            FactType.LOCATION: [
                r'(?:来到|前往|进入|抵达)(?:地点|场景|地方)[：:]\s*([^。\n]+)',
            ],
        }

        for fact_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text)
                for match in matches:
                    content = match.group(1).strip()
                    if len(content) > 2:  # 过滤太短的匹配
                        facts.append(StoryFact(
                            fact_type=fact_type,
                            content=content,
                            source_scene=scene_title,
                            confidence=0.7
                        ))

        return facts

    async def save_facts(
        self,
        session_id: str,
        facts: List[StoryFact],
        merge: bool = True
    ) -> bool:
        """
        保存事实到 Redis

        Args:
            session_id: 会话 ID
            facts: 事实列表
            merge: 是否合并现有事实

        Returns:
            bool: 是否成功
        """
        self._ensure_redis()

        key = self._get_redis_key(session_id)

        try:
            if merge:
                # 获取现有事实
                existing_facts = await self.get_facts(session_id)
                existing_content_set = {f.content for f in existing_facts}

                # 只添加新事实（基于内容去重）
                for fact in facts:
                    if fact.content not in existing_content_set:
                        existing_facts.append(fact)

                facts_to_save = existing_facts
            else:
                facts_to_save = facts

            # 保存到 Redis
            data = [f.to_dict() for f in facts_to_save]

            if isinstance(self._redis, dict):
                self._redis[key] = json.dumps(data)
            else:
                self._redis.set(key, json.dumps(data), ex=86400 * 7)  # 7天过期

            self.logger.debug(f"保存 {len(facts_to_save)} 个事实到 {key}")
            return True

        except Exception as e:
            self.logger.error(f"保存事实失败: {e}")
            return False

    async def get_facts(self, session_id: str) -> List[StoryFact]:
        """
        从 Redis 获取事实

        Args:
            session_id: 会话 ID

        Returns:
            List[StoryFact]: 事实列表
        """
        self._ensure_redis()

        key = self._get_redis_key(session_id)

        try:
            if isinstance(self._redis, dict):
                data_str = self._redis.get(key)
            else:
                data_str = self._redis.get(key)

            if not data_str:
                return []

            if isinstance(data_str, bytes):
                data_str = data_str.decode()

            data = json.loads(data_str)
            return [StoryFact.from_dict(item) for item in data]

        except Exception as e:
            self.logger.error(f"获取事实失败: {e}")
            return []

    async def generate_constraints_prompt(
        self,
        session_id: str,
        max_facts: int = 20,
        priority_types: List[FactType] = None
    ) -> str:
        """
        生成用于 System Prompt 的事实约束文本

        Args:
            session_id: 会话 ID
            max_facts: 最大事实数量
            priority_types: 优先显示的事实类型

        Returns:
            str: 事实约束文本
        """
        facts = await self.get_facts(session_id)

        if not facts:
            return ""

        # 按类型和置信度排序
        if priority_types:
            priority_set = set(priority_types)
            facts = sorted(
                facts,
                key=lambda f: (f.fact_type not in priority_set, -f.confidence),
            )
        else:
            facts = sorted(facts, key=lambda f: -f.confidence)

        # 限制数量
        facts = facts[:max_facts]

        # 按类型分组
        grouped: Dict[FactType, List[StoryFact]] = {}
        for fact in facts:
            grouped.setdefault(fact.fact_type, []).append(fact)

        # 生成文本
        lines = ["【核心设定约束】"]
        lines.append("以下是故事中已确立的关键设定，请严格遵守避免冲突：\n")

        type_names = {
            FactType.CHARACTER: "👤 人物",
            FactType.RELATIONSHIP: "🔗 关系",
            FactType.LOCATION: "📍 场景",
            FactType.PROP: "🎭 道具",
            FactType.EVENT: "⚡ 事件",
            FactType.DEATH: "💀 死亡",
            FactType.BIRTH: "👶 出生",
            FactType.ABILITY: "✨ 能力",
            FactType.BACKGROUND: "📜 背景",
            FactType.CONSTRAINT: "⚠️ 约束",
        }

        for fact_type, type_facts in grouped.items():
            type_name = type_names.get(fact_type, fact_type.value)
            lines.append(f"{type_name}:")
            for fact in type_facts:
                lines.append(f"  • {fact.content}")
            lines.append("")

        return "\n".join(lines)

    def _generate_summary(self, facts: List[StoryFact]) -> str:
        """生成事实摘要"""
        if not facts:
            return "未提取到事实"

        type_counts: Dict[FactType, int] = {}
        for fact in facts:
            type_counts[fact.fact_type] = type_counts.get(fact.fact_type, 0) + 1

        summary_parts = []
        for fact_type, count in type_counts.items():
            summary_parts.append(f"{fact_type.value}:{count}")

        return f"提取到 {len(facts)} 个事实 ({', '.join(summary_parts)})"

    async def clear_facts(self, session_id: str) -> bool:
        """
        清除会话的所有事实

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否成功
        """
        self._ensure_redis()

        key = self._get_redis_key(session_id)

        try:
            if isinstance(self._redis, dict):
                if key in self._redis:
                    del self._redis[key]
            else:
                self._redis.delete(key)

            self.logger.debug(f"清除事实: {key}")
            return True

        except Exception as e:
            self.logger.error(f"清除事实失败: {e}")
            return False


# 全局实例
_story_fact_manager: Optional[StoryFactManager] = None


def get_story_fact_manager() -> StoryFactManager:
    """获取故事事实管理器单例"""
    global _story_fact_manager
    if _story_fact_manager is None:
        _story_fact_manager = StoryFactManager()
    return _story_fact_manager


# 便捷函数
async def extract_and_save_facts(
    session_id: str,
    text: str,
    scene_title: str = "",
    model_name: str = "glm-4-flash"
) -> FactExtractionResult:
    """
    从剧本片段中提取并保存事实

    Args:
        session_id: 会话 ID
        text: 剧本文本
        scene_title: 场景标题
        model_name: 模型名称

    Returns:
        FactExtractionResult: 提取结果
    """
    manager = get_story_fact_manager()
    return await manager.extract_and_save_facts(session_id, text, scene_title, model_name)


async def get_facts(session_id: str) -> List[StoryFact]:
    """获取会话的事实列表"""
    manager = get_story_fact_manager()
    return await manager.get_facts(session_id)


async def generate_constraints_prompt(session_id: str, max_facts: int = 20) -> str:
    """生成事实约束文本"""
    manager = get_story_fact_manager()
    return await manager.generate_constraints_prompt(session_id, max_facts)

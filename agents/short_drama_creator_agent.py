"""
短剧创作Agent
专门用于竖屏短剧的创作和生成

业务处理逻辑：
1. 需求分析：接收创作需求，分析主题、风格、时长等参数
2. 剧本结构设计：设计完整的短剧剧本结构（开场、发展、高潮、结尾）
3. 角色创作：创建主要角色，包括性格特征、背景故事、对话风格
4. 情节设计：设计引人入胜的情节发展，包含冲突、转折、高潮
5. 场景描述：提供详细的场景描述，包括环境、氛围、道具等
6. 对话生成：创作生动的角色对话，符合角色性格和剧情需要
7. 内容优化：优化剧本节奏、语言表达、视觉效果描述
8. 文件保存：自动保存创作内容到文件系统，支持多种格式
9. 质量控制：确保剧本符合竖屏短剧特点（3分钟时长、紧凑节奏）

🆕 设定自动提取功能：
1. 在生成剧本片段后自动提取关键设定
2. 将设定存储到 Redis Hash（project:{project_id}:facts）
3. 下次创作时从 Redis 读取设定约束
4. 确保创作不吃设定，保持一致性

代码作者：宫灵瑞
创建时间：2024年10月19日
优化时间：2026年2月7日
"""
import asyncio
import json
import re
from typing import AsyncGenerator, Dict, Any, List, Optional, Union, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .base_juben_agent import BaseJubenAgent


class FactType(Enum):
    """设定类型枚举"""
    CHARACTER = "character"       # 人物设定
    RELATIONSHIP = "relationship"  # 人际关系
    LOCATION = "location"         # 场景地点
    PROP = "prop"                # 重要道具
    EVENT = "event"              # 重要事件
    DEATH = "death"              # 角色死亡
    BIRTH = "birth"              # 角色出生
    ABILITY = "ability"          # 特殊能力
    BACKGROUND = "background"    # 背景设定
    CONSTRAINT = "constraint"    # 约束条件


@dataclass
class StoryFact:
    """故事设定数据类"""
    fact_type: FactType
    content: str
    source_scene: str = ""
    confidence: float = 1.0
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "fact_type": self.fact_type.value,
            "content": self.content,
            "source_scene": self.source_scene,
            "confidence": self.confidence,
            "extracted_at": self.extracted_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryFact":
        """从字典创建"""
        return cls(
            fact_type=FactType(data.get("fact_type", "constraint")),
            content=data.get("content", ""),
            source_scene=data.get("source_scene", ""),
            confidence=data.get("confidence", 1.0),
            extracted_at=data.get("extracted_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )


class StoryFactExtractor:
    """
    故事设定提取器

    从剧本片段中自动提取关键设定信息
    """

    # 提取模式
    PATTERNS = {
        FactType.CHARACTER: [
            r'(?:新登场|出现|登场|引入)(?:人物|角色)[：:]\s*([^。\n]+)',
            r'([^。\n]+?)（(?:\d+岁|年龄|人物|角色)）',
            r'人物[：:]\s*([^。\n]+)',
        ],
        FactType.RELATIONSHIP: [
            r'([^。\n]+?)是([^。\n]+?)的(?:父|母|子|女|兄|妹|丈夫|妻子|恋人|朋友|敌人|上司|下属)',
            r'([^。\n]+?)与([^。\n]+?)(?:是|为)(?:恋人|情侣|夫妻|朋友|仇人|对手)',
        ],
        FactType.LOCATION: [
            r'(?:场景|地点|场所)[：:]\s*([^。\n]+)',
            r'在([^。\n]+?)(?:场景|地方|场所)',
        ],
        FactType.PROP: [
            r'(?:道具|物品|法器|神器)[：:]\s*([^。\n]+)',
            r'([^。\n]+?)(?:为|是)(?:重要|关键)(?:道具|物品)',
        ],
        FactType.DEATH: [
            r'([^。\n]+?)(?:死亡|牺牲|被杀|离世)',
            r'([^。\n]+?)(?:的|之)(?:死|死亡|牺牲)',
        ],
        FactType.BIRTH: [
            r'([^。\n]+?)(?:出生|诞生|出世)',
        ],
        FactType.ABILITY: [
            r'([^。\n]+?)(?:能力|技能|功夫|法术|神力)[：:]\s*([^。\n]+)',
            r'([^。\n]+?)能(?:够|可以)([^。\n]+)',
        ],
    }

    def __init__(self):
        from utils.logger import JubenLogger
        self.logger = JubenLogger("StoryFactExtractor")

    async def extract_facts_from_script(
        self,
        script_content: str,
        scene_title: str = "",
        existing_facts: List[StoryFact] = None
    ) -> List[StoryFact]:
        """
        从剧本内容提取设定

        Args:
            script_content: 剧本内容
            scene_title: 场景标题
            existing_facts: 已存在的设定（用于去重）

        Returns:
            List[StoryFact]: 提取的设定列表
        """
        try:
            existing_facts = existing_facts or []
            extracted_facts = []
            existing_contents = {fact.content for fact in existing_facts}

            # 使用 LLM 进行智能提取
            llm_facts = await self._extract_with_llm(script_content, scene_title)

            # 使用正则表达式进行规则提取
            regex_facts = self._extract_with_regex(script_content, scene_title)

            # 合并去重
            all_facts = llm_facts + regex_facts
            for fact in all_facts:
                # 检查是否已存在
                is_duplicate = any(
                    fact.fact_type == existing_fact.fact_type and
                    fact.content == existing_fact.content
                    for existing_fact in existing_facts + extracted_facts
                )
                if not is_duplicate and fact.content not in existing_contents:
                    extracted_facts.append(fact)

            if extracted_facts:
                self.logger.info(f"📝 从 {scene_title} 提取到 {len(extracted_facts)} 个设定")

            return extracted_facts

        except Exception as e:
            self.logger.error(f"提取设定失败: {e}")
            return []

    async def _extract_with_llm(
        self,
        script_content: str,
        scene_title: str
    ) -> List[StoryFact]:
        """使用 LLM 提取设定"""
        try:
            # 截取内容（避免过长）
            content = script_content[:3000] if len(script_content) > 3000 else script_content

            prompt = f"""请从以下剧本片段中提取关键设定信息。

场景标题: {scene_title}

剧本内容:
{content}

请提取以下类型的设定（以JSON数组格式返回）：
1. character - 新登场人物（姓名、年龄、职业、性格等）
2. relationship - 人际关系（人物之间的关系描述）
3. location - 场景地点（重要场景名称、描述）
4. prop - 重要道具（关键物品、法器等）
5. event - 重要事件（对剧情有重大影响的事件）
6. death - 角色死亡（死亡的角色）
7. ability - 特殊能力（角色的特殊技能或能力）
8. background - 背景设定（世界观设定、历史背景等）

返回格式示例：
[
  {{"fact_type": "character", "content": "张三，25岁，剑客，性格冷傲"}},
  {{"fact_type": "relationship", "content": "张三是李四的师兄"}},
  {{"fact_type": "location", "content": "青云门，位于青云山的修仙门派"}}
]

只返回JSON数组，不要其他说明文字。"""

            # 这里需要调用 LLM，暂时返回空列表
            # 实际使用时需要集成 LLM 客户端
            # result = await llm_client.chat([{"role": "user", "content": prompt}])
            # facts_data = json.loads(result)
            # return [StoryFact(**fact) for fact in facts_data]

            return []

        except Exception as e:
            self.logger.error(f"LLM 提取设定失败: {e}")
            return []

    def _extract_with_regex(
        self,
        script_content: str,
        scene_title: str
    ) -> List[StoryFact]:
        """使用正则表达式提取设定"""
        facts = []

        for fact_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, script_content)
                for match in matches:
                    content = match.group(0).strip()
                    if len(content) > 200:  # 过滤过长的匹配
                        continue

                    fact = StoryFact(
                        fact_type=fact_type,
                        content=content,
                        source_scene=scene_title,
                        confidence=0.7  # 正则匹配的置信度较低
                    )
                    facts.append(fact)

        return facts


class StoryFactManager:
    """
    故事设定管理器

    负责：
    1. 将设定存储到 Redis Hash
    2. 从 Redis 读取设定
    3. 生成设定约束文本
    """

    def __init__(self):
        from utils.logger import JubenLogger
        self.logger = JubenLogger("StoryFactManager")
        self._redis_client = None

    async def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis_client is None:
            try:
                from utils.redis_client import get_redis_client
                self._redis_client = await get_redis_client()
            except Exception as e:
                self.logger.warning(f"Redis 客户端初始化失败: {e}")
        return self._redis_client

    def _get_facts_key(self, project_id: str) -> str:
        """获取 Redis 键"""
        return f"project:{project_id}:facts"

    async def save_facts(
        self,
        project_id: str,
        facts: List[StoryFact],
        merge: bool = True
    ) -> bool:
        """
        保存设定到 Redis

        Args:
            project_id: 项目 ID
            facts: 设定列表
            merge: 是否与现有设定合并

        Returns:
            bool: 是否成功
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                self.logger.warning("Redis 不可用，设定将不会被持久化")
                return False

            key = self._get_facts_key(project_id)

            if merge:
                # 获取现有设定
                existing_facts_dict = await redis_client.hgetall(key)
                existing_facts = [
                    StoryFact.from_dict({"fact_type": k, **v})
                    if isinstance(v, dict) else StoryFact.from_dict(v)
                    for k, v in existing_facts_dict.items()
                ]
                existing_contents = {fact.content for fact in existing_facts}
            else:
                existing_contents = set()

            # 保存新设定
            saved_count = 0
            for fact in facts:
                if fact.content not in existing_contents:
                    field_name = f"{fact.fact_type.value}_{len(existing_contents) + saved_count}"
                    success = await redis_client.hset(
                        key,
                        field_name,
                        fact.to_dict()
                    )
                    if success:
                        saved_count += 1

            # 设置过期时间（7天）
            await redis_client.expire(key, 7 * 24 * 3600)

            self.logger.info(f"💾 保存 {saved_count} 个设定到 Redis: {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"保存设定失败: {e}")
            return False

    async def get_facts(
        self,
        project_id: str,
        fact_types: List[FactType] = None
    ) -> List[StoryFact]:
        """
        从 Redis 获取设定

        Args:
            project_id: 项目 ID
            fact_types: 筛选的设定类型（None 表示获取全部）

        Returns:
            List[StoryFact]: 设定列表
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return []

            key = self._get_facts_key(project_id)
            facts_dict = await redis_client.hgetall(key)

            facts = []
            for field_name, fact_data in facts_dict.items():
                try:
                    if isinstance(fact_data, dict):
                        fact = StoryFact.from_dict(fact_data)
                    else:
                        fact = StoryFact.from_dict({"fact_type": "constraint", "content": str(fact_data)})

                    # 筛选类型
                    if fact_types is None or fact.fact_type in fact_types:
                        facts.append(fact)
                except Exception as e:
                    self.logger.warning(f"解析设定失败: {field_name}, {e}")

            return facts

        except Exception as e:
            self.logger.error(f"获取设定失败: {e}")
            return []

    async def generate_constraints_prompt(
        self,
        project_id: str,
        max_facts: int = 20
    ) -> str:
        """
        生成设定约束文本

        Args:
            project_id: 项目 ID
            max_facts: 最大设定数量

        Returns:
            str: 约束文本
        """
        try:
            facts = await self.get_facts(project_id)

            if not facts:
                return ""

            # 按类型分组
            grouped_facts = {}
            for fact in facts[:max_facts]:
                if fact.fact_type not in grouped_facts:
                    grouped_facts[fact.fact_type] = []
                grouped_facts[fact.fact_type].append(fact)

            # 生成约束文本
            constraints = ["## 核心设定约束（必须遵守）\n"]

            type_labels = {
                FactType.CHARACTER: "👤 人物设定",
                FactType.RELATIONSHIP: "🔗 人际关系",
                FactType.LOCATION: "📍 场景地点",
                FactType.PROP: "🎭 重要道具",
                FactType.EVENT: "⚡ 重要事件",
                FactType.DEATH: "💀 角色死亡",
                FactType.BIRTH: "👶 角色出生",
                FactType.ABILITY: "✨ 特殊能力",
                FactType.BACKGROUND: "📜 背景设定",
                FactType.CONSTRAINT: "⚠️ 其他约束",
            }

            for fact_type, fact_list in grouped_facts.items():
                label = type_labels.get(fact_type, fact_type.value)
                constraints.append(f"\n### {label}\n")
                for fact in fact_list:
                    constraints.append(f"- {fact.content}")

            return "\n".join(constraints)

        except Exception as e:
            self.logger.error(f"生成约束文本失败: {e}")
            return ""

    async def clear_facts(self, project_id: str) -> bool:
        """清除项目的所有设定"""
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            key = self._get_facts_key(project_id)
            await redis_client.delete(key)
            self.logger.info(f"🗑️ 清除项目设定: {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"清除设定失败: {e}")
            return False


class ShortDramaCreatorAgent(BaseJubenAgent):
    """
    短剧创作Agent

    核心职责：
    1. 🎬 短剧剧本创作：生成完整的竖屏短剧剧本
    2. 🎭 角色对话生成：创作生动的角色对话
    3. 📝 情节设计：设计引人入胜的情节结构
    4. 🎨 场景描述：提供详细的场景描述
    5. 💾 内容保存：自动保存创作内容到文件系统
    6. 🆕 📝 设定自动提取：自动提取和存储关键设定
    7. 🆕 ⚙️ 设定约束管理：在创作中应用已提取的设定
    """

    def __init__(self, model_provider: str = "zhipu"):
        """初始化短剧创作Agent"""
        super().__init__("short_drama_creator_agent", model_provider)

        # 🔧 修正系统提示词来源：使用 prompts/short_drama_creater_system.txt
        # 这样 ShortDramaCreatorAgent 会复用已经在 prompts 里的专业创作提示词
        try:
            from pathlib import Path

            prompts_dir = Path(__file__).parent.parent / "prompts"
            legacy_prompt_path = prompts_dir / "short_drama_creater_system.txt"
            if legacy_prompt_path.exists():
                with open(legacy_prompt_path, "r", encoding="utf-8") as f:
                    self.system_prompt = f.read().strip()
                self.logger.info(
                    f"从 legacy 提示词文件加载短剧创作系统提示词成功: {legacy_prompt_path}"
                )
        except Exception as e:
            # 加载失败不影响主流程，仍使用基类已加载的默认系统提示词
            self.logger.warning(
                f"加载 short_drama_creater_system 提示词失败，使用默认系统提示词: {e}"
            )

        # 创作配置
        self.creation_config = {
            "max_scenes": 10,  # 最大场景数
            "max_dialogue_length": 200,  # 最大对话长度
            "target_duration": 3,  # 目标时长（分钟）
            "style": "modern",  # 创作风格
            "tone": "engaging"  # 语调
        }

        # 创作模板
        self.creation_templates = {
            "romance": {
                "theme": "现代都市爱情",
                "key_elements": ["相遇", "误会", "和解", "表白"],
                "tone": "温馨浪漫"
            },
            "comedy": {
                "theme": "轻松幽默喜剧",
                "key_elements": ["误会", "巧合", "反转", "笑点"],
                "tone": "轻松幽默"
            },
            "drama": {
                "theme": "情感剧情",
                "key_elements": ["冲突", "成长", "选择", "结局"],
                "tone": "深刻感人"
            },
            "thriller": {
                "theme": "悬疑惊悚",
                "key_elements": ["悬念", "线索", "反转", "真相"],
                "tone": "紧张刺激"
            }
        }

        # 🆕 初始化设定提取器和管理器
        self.fact_extractor = StoryFactExtractor()
        self.fact_manager = StoryFactManager()

        # 🆕 当前项目 ID（用于设定管理）
        self._current_project_id: Optional[str] = None

        self.logger.info("🎬 短剧创作Agent初始化完成")
        self.logger.info(f"🎭 支持创作类型: {list(self.creation_templates.keys())}")
        self.logger.info(f"📝 创作配置: {self.creation_config}")
        self.logger.info(f"🆕 设定自动提取: 已启用")

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理短剧创作请求

        Args:
            request_data: 请求数据
                - instruction: 创作指令
                - user_id: 用户 ID
                - session_id: 会话 ID
                - project_id: 项目 ID
                - character_voices: (可选) 角色语气字典
                    格式: {
                        "character_id": {
                            "name": "角色名",
                            "style": "casual",
                            "samples": ["对白样本1", "对白样本2"],
                            "traits": ["性格1", "性格2"],
                            "catchphrases": ["口头禅"]
                        }
                    }
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        user_id = request_data.get("user_id", "unknown")
        session_id = request_data.get("session_id", "unknown")

        # 兼容 /chat 入口：优先使用显式 instruction，没有则回退到 input/query
        instruction = request_data.get("instruction") or request_data.get("input") or request_data.get("query") or ""

        # 🆕 设置当前项目 ID
        self._current_project_id = request_data.get("project_id", f"{user_id}_{session_id}")

        # 🆕 提取角色语气配置
        character_voices = request_data.get("character_voices", {})
        if character_voices:
            self.logger.info(f"🎭 收到角色语气配置: {len(character_voices)} 个角色")

        # 初始化Token累加器
        await self.initialize_token_accumulator(user_id, session_id)

        try:
            self.logger.info(f"🎬 开始短剧创作: {instruction[:100]}...")

            # 发送创作开始事件
            yield await self._emit_event(
                "creation_start",
                f"开始创作短剧: {instruction}",
                {"agent": "short_drama_creator", "status": "starting"}
            )

            # 分析创作需求
            creation_plan = await self._analyze_creation_requirements(instruction, context)

            yield await self._emit_event(
                "creation_plan",
                f"创作计划制定完成: {creation_plan['drama_type']}",
                {"plan": creation_plan, "status": "planning"}
            )

            # 执行创作流程（传递角色语气配置）
            creation_result = await self._execute_creation_workflow(
                creation_plan, user_id, session_id, character_voices
            )

            # 保存创作结果到文件系统
            save_result = await self._save_creation_output(creation_result, user_id, session_id)

            # 在流中输出完整剧本内容，避免前端只看到进度而看不到剧本
            script_text = self._format_creation_result_as_text(creation_result)
            for chunk in self._chunk_text(script_text, max_len=1200):
                if chunk.strip():
                    # 使用统一的内容事件（llm_chunk -> 在前端视为 message）
                    yield await self._emit_event("llm_chunk", chunk)

            # 发送创作完成事件（带上保存结果等元数据）
            yield await self._emit_event(
                "creation_complete",
                f"短剧创作完成: {creation_result['title']}",
                {
                    "result": creation_result,
                    "save_result": save_result,
                    "status": "completed"
                }
            )

            self.logger.info(f"✅ 短剧创作完成: {creation_result['title']}")

        except Exception as e:
            self.logger.error(f"❌ 短剧创作失败: {e}")
            yield await self._emit_event(
                "creation_error",
                f"短剧创作失败: {str(e)}",
                {"error_type": "creation_failed", "error": str(e)}
            )
            raise

    async def _analyze_creation_requirements(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析创作需求"""
        try:
            # 构建分析提示词
            analysis_prompt = f"""
            请分析以下短剧创作需求，制定详细的创作计划：

            用户需求: {instruction}

            可选创作类型：
            1. romance - 现代都市爱情
            2. comedy - 轻松幽默喜剧
            3. drama - 情感剧情
            4. thriller - 悬疑惊悚

            请分析并返回JSON格式的创作计划，包含：
            1. drama_type: 短剧类型
            2. title: 建议标题
            3. theme: 主题描述
            4. target_audience: 目标受众
            5. key_elements: 关键元素列表
            6. scene_count: 建议场景数
            7. main_characters: 主要角色设定
            8. plot_outline: 情节大纲
            """

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]

            # 调用LLM分析
            response = await self._call_llm(messages, user_id="system", session_id="creation_analysis")

            # 解析响应
            try:
                creation_plan = json.loads(response)
            except json.JSONDecodeError:
                # 如果解析失败，使用默认计划
                creation_plan = self._create_default_plan(instruction)

            # 验证和补充计划
            creation_plan = self._validate_creation_plan(creation_plan)

            self.logger.info(f"🎯 创作计划制定完成: {creation_plan['drama_type']}")
            return creation_plan

        except Exception as e:
            self.logger.error(f"❌ 创作需求分析失败: {e}")
            return self._create_default_plan(instruction)

    def _create_default_plan(self, instruction: str) -> Dict[str, Any]:
        """创建默认创作计划"""
        return {
            "drama_type": "romance",
            "title": "现代爱情故事",
            "theme": "现代都市爱情",
            "target_audience": "年轻观众",
            "key_elements": ["相遇", "误会", "和解", "表白"],
            "scene_count": 5,
            "main_characters": [
                {"name": "男主角", "age": 25, "personality": "阳光开朗"},
                {"name": "女主角", "age": 23, "personality": "温柔善良"}
            ],
            "plot_outline": "两个年轻人在都市中相遇，经历误会和考验，最终走到一起的爱情故事"
        }

    def _validate_creation_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """验证和补充创作计划"""
        # 确保必要字段存在
        required_fields = ["drama_type", "title", "theme", "target_audience", "key_elements", "scene_count"]
        for field in required_fields:
            if field not in plan:
                if field == "drama_type":
                    plan[field] = "romance"
                elif field == "title":
                    plan[field] = "现代爱情故事"
                elif field == "theme":
                    plan[field] = "现代都市爱情"
                elif field == "target_audience":
                    plan[field] = "年轻观众"
                elif field == "key_elements":
                    plan[field] = ["相遇", "误会", "和解", "表白"]
                elif field == "scene_count":
                    plan[field] = 5

        # 补充缺失字段
        if "main_characters" not in plan:
            plan["main_characters"] = [
                {"name": "男主角", "age": 25, "personality": "阳光开朗"},
                {"name": "女主角", "age": 23, "personality": "温柔善良"}
            ]

        if "plot_outline" not in plan:
            plan["plot_outline"] = "两个年轻人在都市中相遇，经历误会和考验，最终走到一起的爱情故事"

        return plan

    async def _execute_creation_workflow(
        self,
        creation_plan: Dict[str, Any],
        user_id: str,
        session_id: str,
        character_voices: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行创作工作流

        Args:
            creation_plan: 创作计划
            user_id: 用户 ID
            session_id: 会话 ID
            character_voices: 角色语气配置（可选）
        """
        try:
            drama_type = creation_plan["drama_type"]
            scene_count = creation_plan["scene_count"]

            # 获取创作模板
            template = self.creation_templates.get(drama_type, self.creation_templates["romance"])

            # 生成角色设定
            characters = await self._generate_characters(creation_plan["main_characters"])

            # 生成场景列表
            scenes = await self._generate_scenes(creation_plan, scene_count)

            # 🆕 生成详细剧本（带设定提取和角色语气）
            script = await self._generate_script_with_facts(
                creation_plan, characters, scenes, character_voices
            )

            # 生成创作总结
            summary = await self._generate_creation_summary(creation_plan, characters, scenes, script)

            # 构建创作结果
            creation_result = {
                "title": creation_plan["title"],
                "drama_type": drama_type,
                "theme": creation_plan["theme"],
                "target_audience": creation_plan["target_audience"],
                "characters": characters,
                "scenes": scenes,
                "script": script,
                "summary": summary,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "agent_name": self.agent_name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "project_id": self._current_project_id,
                    "creation_config": self.creation_config
                }
            }

            return creation_result

        except Exception as e:
            self.logger.error(f"❌ 创作工作流执行失败: {e}")
            raise

    async def _generate_characters(self, character_templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成角色设定"""
        try:
            characters = []

            for template in character_templates:
                # 构建角色生成提示词
                character_prompt = f"""
                请基于以下模板生成详细的角色设定：

                角色模板: {json.dumps(template, ensure_ascii=False)}

                请生成包含以下信息的详细角色设定：
                1. 基本信息：姓名、年龄、职业、外貌
                2. 性格特点：主要性格特征、兴趣爱好
                3. 背景故事：成长经历、重要事件
                4. 人际关系：与其他人物的关系
                5. 台词风格：说话方式和语言特点

                请以JSON格式输出。
                """

                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": character_prompt}
                ]

                # 调用LLM生成角色
                response = await self._call_llm(messages, user_id="system", session_id="character_generation")

                try:
                    character = json.loads(response)
                    characters.append(character)
                except json.JSONDecodeError:
                    # 如果解析失败，使用模板信息
                    characters.append(template)

            return characters

        except Exception as e:
            self.logger.error(f"❌ 角色生成失败: {e}")
            return character_templates

    async def _generate_scenes(self, creation_plan: Dict[str, Any], scene_count: int) -> List[Dict[str, Any]]:
        """生成场景列表"""
        try:
            # 构建场景生成提示词
            scene_prompt = f"""
            请为以下短剧创作生成{scene_count}个场景：

            短剧信息:
            - 类型: {creation_plan['drama_type']}
            - 主题: {creation_plan['theme']}
            - 关键元素: {', '.join(creation_plan['key_elements'])}
            - 情节大纲: {creation_plan['plot_outline']}

            请为每个场景生成：
            1. 场景标题
            2. 场景描述
            3. 主要角色
            4. 场景目的
            5. 关键对话要点

            请以JSON格式输出场景列表。
            """

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": scene_prompt}
            ]

            # 调用LLM生成场景
            response = await self._call_llm(messages, user_id="system", session_id="scene_generation")

            try:
                scenes = json.loads(response)
                if not isinstance(scenes, list):
                    scenes = [scenes]
            except json.JSONDecodeError:
                # 如果解析失败，创建默认场景
                scenes = self._create_default_scenes(scene_count, creation_plan)

            return scenes

        except Exception as e:
            self.logger.error(f"❌ 场景生成失败: {e}")
            return self._create_default_scenes(scene_count, creation_plan)

    def _create_default_scenes(self, scene_count: int, creation_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建默认场景"""
        scenes = []
        for i in range(scene_count):
            scene = {
                "scene_number": i + 1,
                "title": f"场景{i + 1}",
                "description": f"第{i + 1}个场景的描述",
                "main_characters": ["男主角", "女主角"],
                "purpose": f"推进情节发展",
                "key_dialogue": f"场景{i + 1}的关键对话"
            }
            scenes.append(scene)
        return scenes

    async def _generate_script_with_facts(
        self,
        creation_plan: Dict[str, Any],
        characters: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        character_voices: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成详细剧本（带设定提取和角色语气）

        🆕 新增功能：
        1. 生成剧本时应用已有的设定约束
        2. 应用角色语气样本，保持对话风格一致性
        3. 生成后自动提取新设定并存储到 Redis
        """
        try:
            # 🆕 获取现有设定约束
            facts_constraints = await self.fact_manager.generate_constraints_prompt(
                self._current_project_id,
                max_facts=20
            )

            # 🆕 处理角色语气配置
            voice_prompt_section = ""
            if character_voices:
                try:
                    from utils.persona_helper import get_persona_helper
                    persona_helper = get_persona_helper()

                    # 批量设置角色语气到 Redis
                    await persona_helper.set_character_voices_from_input(
                        self._current_project_id,
                        character_voices
                    )

                    # 获取角色 ID 列表
                    character_ids = list(character_voices.keys())

                    # 格式化角色语气为 Prompt
                    voice_prompt_section = await persona_helper.format_voice_prompt(
                        character_ids,
                        max_samples_per_character=2
                    )

                    if voice_prompt_section:
                        self.logger.info(f"🎭 已应用 {len(character_ids)} 个角色的语气样本")

                except Exception as e:
                    self.logger.warning(f"角色语气处理失败: {e}")

            # 构建剧本生成提示词（加入设定约束和角色语气）
            constraints_section = f"\n\n{facts_constraints}" if facts_constraints else ""
            voice_section = f"\n\n{voice_prompt_section}" if voice_prompt_section else ""

            script_prompt = f"""
            请基于以下信息生成完整的短剧剧本：
            {constraints_section}
            {voice_section}

            短剧信息:
            - 标题: {creation_plan['title']}
            - 类型: {creation_plan['drama_type']}
            - 主题: {creation_plan['theme']}

            角色设定:
            {json.dumps(characters, ensure_ascii=False, indent=2)}

            场景列表:
            {json.dumps(scenes, ensure_ascii=False, indent=2)}

            请生成包含以下内容的完整剧本：
            1. 剧本标题和基本信息
            2. 角色列表和设定
            3. 每个场景的详细内容：
               - 场景描述
               - 角色动作
               - 完整对话（严格参考角色语气样本）
               - 情感表达
            4. 剧本总结和创作说明

            请以结构化的JSON格式输出。
            """

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": script_prompt}
            ]

            # 调用LLM生成剧本
            response = await self._call_llm(messages, user_id="system", session_id="script_generation")

            try:
                script = json.loads(response)
            except json.JSONDecodeError:
                # 如果解析失败，创建默认剧本
                script = self._create_default_script(creation_plan, characters, scenes)

            # 🆕 异步提取设定
            asyncio.create_task(self._extract_and_save_facts(script, scenes))

            return script

        except Exception as e:
            self.logger.error(f"❌ 剧本生成失败: {e}")
            return self._create_default_script(creation_plan, characters, scenes)

    async def _extract_and_save_facts(
        self,
        script: Dict[str, Any],
        scenes: List[Dict[str, Any]]
    ):
        """
        🆕 提取并保存设定

        在剧本生成后异步执行，提取关键设定并存储到 Redis
        """
        try:
            if not self._current_project_id:
                return

            all_facts = []

            # 从每个场景提取设定
            for scene in scenes:
                scene_title = scene.get("title", f"场景{scene.get('scene_number', '')}")

                # 从剧本中查找对应场景的内容
                scene_content = self._extract_scene_content(script, scene)

                if scene_content:
                    # 提取设定
                    facts = await self.fact_extractor.extract_facts_from_script(
                        scene_content,
                        scene_title
                    )
                    all_facts.extend(facts)

            # 保存到 Redis
            if all_facts:
                await self.fact_manager.save_facts(
                    self._current_project_id,
                    all_facts,
                    merge=True
                )
                self.logger.info(f"✅ 自动保存 {len(all_facts)} 个设定到 Redis")

        except Exception as e:
            self.logger.error(f"提取和保存设定失败: {e}")

    def _extract_scene_content(self, script: Dict[str, Any], scene: Dict[str, Any]) -> str:
        """从剧本中提取场景内容"""
        try:
            scene_number = scene.get("scene_number", 0)
            scene_title = scene.get("title", "")

            # 尝试从剧本的 scenes 字段获取
            if "scenes" in script:
                for script_scene in script["scenes"]:
                    if (script_scene.get("scene_number") == scene_number or
                        script_scene.get("title") == scene_title):
                        return json.dumps(script_scene, ensure_ascii=False)

            # 尝试从 script_content 获取
            if "script_content" in script:
                content = script["script_content"]
                if isinstance(content, str):
                    # 尝试提取相关部分
                    if scene_title in content:
                        start = content.find(scene_title)
                        end = start + 2000  # 取2000字符
                        return content[start:end]
                    return content[:2000]
                elif isinstance(content, dict):
                    return json.dumps(content, ensure_ascii=False)

            return ""

        except Exception as e:
            self.logger.error(f"提取场景内容失败: {e}")
            return ""

    async def _generate_script(
        self,
        creation_plan: Dict[str, Any],
        characters: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成详细剧本（兼容旧接口，调用新方法）"""
        return await self._generate_script_with_facts(creation_plan, characters, scenes)

    def _create_default_script(
        self,
        creation_plan: Dict[str, Any],
        characters: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建默认剧本"""
        return {
            "title": creation_plan["title"],
            "drama_type": creation_plan["drama_type"],
            "characters": characters,
            "scenes": scenes,
            "script_content": f"这是{creation_plan['title']}的剧本内容",
            "summary": f"剧本创作完成，共{len(scenes)}个场景"
        }

    async def _generate_creation_summary(
        self,
        creation_plan: Dict[str, Any],
        characters: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
        script: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成创作总结"""
        try:
            # 构建总结生成提示词
            summary_prompt = f"""
            请为以下短剧创作生成总结报告：

            创作计划: {json.dumps(creation_plan, ensure_ascii=False, indent=2)}
            角色数量: {len(characters)}
            场景数量: {len(scenes)}

            请生成包含以下内容的总结：
            1. 创作概述
            2. 角色分析
            3. 情节结构分析
            4. 创作亮点
            5. 改进建议
            6. 市场定位分析

            请以JSON格式输出。
            """

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": summary_prompt}
            ]

            # 调用LLM生成总结
            response = await self._call_llm(messages, user_id="system", session_id="summary_generation")

            try:
                summary = json.loads(response)
            except json.JSONDecodeError:
                # 如果解析失败，创建默认总结
                summary = self._create_default_summary(creation_plan, characters, scenes)

            return summary

        except Exception as e:
            self.logger.error(f"❌ 创作总结生成失败: {e}")
            return self._create_default_summary(creation_plan, characters, scenes)

    def _create_default_summary(
        self,
        creation_plan: Dict[str, Any],
        characters: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建默认总结"""
        return {
            "overview": f"成功创作了{creation_plan['title']}短剧",
            "character_analysis": f"共创建{len(characters)}个角色",
            "plot_analysis": f"共设计{len(scenes)}个场景",
            "highlights": ["角色设定丰富", "情节结构完整", "对话生动自然"],
            "improvements": ["可以增加更多细节描述", "优化角色对话"],
            "market_analysis": f"适合{creation_plan['target_audience']}观看"
        }

    async def _save_creation_output(
        self,
        creation_result: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """保存创作输出到文件系统"""
        try:
            # 自动保存创作结果
            save_result = await self.auto_save_output(
                output_content=creation_result,
                user_id=user_id,
                session_id=session_id,
                file_type="json",
                metadata={
                    "creation_type": "short_drama",
                    "drama_type": creation_result.get("drama_type", "unknown"),
                    "scene_count": len(creation_result.get("scenes", [])),
                    "character_count": len(creation_result.get("characters", [])),
                    "project_id": self._current_project_id,
                    "creation_timestamp": datetime.now().isoformat()
                }
            )

            if save_result.get("success"):
                self.logger.info(f"💾 创作输出保存成功: {save_result.get('file_info', {}).get('file_id')}")
            else:
                self.logger.error(f"❌ 创作输出保存失败: {save_result.get('error')}")

            return save_result

        except Exception as e:
            self.logger.error(f"❌ 保存创作输出失败: {e}")
            return {"success": False, "error": str(e)}

    # ==================== 输出格式化与分片工具 ====================

    def _format_creation_result_as_text(self, creation_result: Dict[str, Any]) -> str:
        """
        将创作结果格式化为可直接展示的文本剧本。

        说明：
        - 保留标题、设定、场景和对话等核心信息；
        - 对于结构化的 script（JSON），尽量展开为易读的文本；
        - 如果结构不符合预期，则退化为 JSON 字符串，保证至少能看到全部内容。
        """
        try:
            lines: List[str] = []

            title = creation_result.get("title") or "短剧剧本"
            theme = creation_result.get("theme") or ""
            drama_type = creation_result.get("drama_type") or ""
            target_audience = creation_result.get("target_audience") or ""

            lines.append(f"《{title}》")
            basic_info_parts = []
            if drama_type:
                basic_info_parts.append(f"类型：{drama_type}")
            if theme:
                basic_info_parts.append(f"主题：{theme}")
            if target_audience:
                basic_info_parts.append(f"目标受众：{target_audience}")
            if basic_info_parts:
                lines.append("，".join(basic_info_parts))
            lines.append("")

            # 角色列表
            characters = creation_result.get("characters") or []
            if isinstance(characters, list) and characters:
                lines.append("【角色设定】")
                for idx, ch in enumerate(characters, 1):
                    if isinstance(ch, dict):
                        name = ch.get("name") or ch.get("character_name") or f"角色{idx}"
                        age = ch.get("age")
                        personality = ch.get("personality") or ch.get("traits")
                        desc_parts = [str(name)]
                        if age:
                            desc_parts.append(f"{age}岁")
                        if personality:
                            desc_parts.append(f"性格：{personality}")
                        lines.append("· " + "，".join(map(str, desc_parts)))
                    else:
                        lines.append(f"· {ch}")
                lines.append("")

            # 场景 + 剧本内容
            script = creation_result.get("script") or {}

            # 如果 script 已经是纯文本，直接输出
            if isinstance(script, str):
                lines.append("【剧本正文】")
                lines.append(script.strip())
            else:
                scenes = creation_result.get("scenes") or script.get("scenes") or []
                scenes_text = script.get("scenes_text") if isinstance(script, dict) else None

                if scenes_text and isinstance(scenes_text, str):
                    # 有预先串好的文本
                    lines.append("【剧本正文】")
                    lines.append(scenes_text.strip())
                elif isinstance(scenes, list) and scenes:
                    lines.append("【剧本场景】")
                    for scene in scenes:
                        if not isinstance(scene, dict):
                            continue
                        num = scene.get("scene_number")
                        s_title = scene.get("title") or f"场景{num or ''}"
                        desc = scene.get("description") or ""
                        key_dialogue = scene.get("key_dialogue") or ""

                        header = f"场景{num}：{s_title}" if num is not None else str(s_title)
                        lines.append("")
                        lines.append(header)
                        if desc:
                            lines.append(desc)
                        if key_dialogue:
                            lines.append(f"【关键对话】{key_dialogue}")

                    # 如果 script 里还有额外的正文字段，附在最后
                    extra_text = script.get("full_text") or script.get("script_text")
                    if isinstance(extra_text, str) and extra_text.strip():
                        lines.append("")
                        lines.append("【剧本补充正文】")
                        lines.append(extra_text.strip())
                else:
                    # 结构未知，退化为 JSON 展示
                    lines.append("【剧本（结构化数据）】")
                    lines.append(json.dumps(script, ensure_ascii=False, indent=2))

            # 创作总结（如果有）
            summary = creation_result.get("summary") or {}
            if summary:
                lines.append("")
                lines.append("【创作总结】")
                if isinstance(summary, dict):
                    overview = summary.get("overview")
                    if overview:
                        lines.append(f"- 总览：{overview}")
                    for key, value in summary.items():
                        if key == "overview":
                            continue
                        if isinstance(value, list):
                            lines.append(f"- {key}：")
                            for item in value:
                                lines.append(f"  · {item}")
                        else:
                            lines.append(f"- {key}：{value}")
                else:
                    lines.append(str(summary))

            return "\n".join(lines)

        except Exception as e:
            # 任何异常都退化为完整 JSON，确保不会什么都看不到
            self.logger.error(f"格式化创作结果为文本失败: {e}")
            try:
                return json.dumps(creation_result, ensure_ascii=False, indent=2)
            except Exception:
                return str(creation_result)

    def _chunk_text(self, text: str, max_len: int = 1200) -> List[str]:
        """
        将长文本按指定长度分片，避免单个 SSE 事件过大。
        """
        if not text:
            return []
        chunks: List[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + max_len, length)
            chunks.append(text[start:end])
            start = end
        return chunks

    # 🆕 重写 _prepare_messages 方法，加入设定约束
    async def _prepare_messages(
        self,
        session_id: str,
        user_id: str,
        user_input: str,
        enable_rag: bool = False,
        include_scratchpad: bool = False,
        scratchpad_task: str = None
    ) -> List[Dict[str, str]]:
        """
        准备消息列表（🆕 加入设定约束）

        增强版消息准备，从 Redis 读取已保存的设定并作为约束加入系统提示词
        """
        # 构建基础消息
        base_system_prompt = self.system_prompt

        # 🆕 获取设定约束
        if self._current_project_id:
            facts_constraints = await self.fact_manager.generate_constraints_prompt(
                self._current_project_id,
                max_facts=20
            )

            # 将设定约束加入系统提示词
            if facts_constraints:
                enhanced_system_prompt = f"{base_system_prompt}\n\n{facts_constraints}"
            else:
                enhanced_system_prompt = base_system_prompt
        else:
            enhanced_system_prompt = base_system_prompt

        # 使用增强的系统提示词构建消息
        messages = []

        # 添加系统提示词
        messages.append({"role": "system", "content": enhanced_system_prompt})

        # 如果启用RAG，使用rebuild_context_with_rag
        if enable_rag:
            messages = await self.rebuild_context_with_rag(
                session_id, user_id,
                enhanced_system_prompt,
                user_input,
                enable_auto_rag=True,
                max_rag_items=3
            )
        else:
            # 否则使用普通的rebuild_optimized_context
            messages = await self.rebuild_optimized_context(
                session_id, user_id, user_input
            )
            # 确保第一个消息是系统提示词
            if messages and messages[0].get("role") != "system":
                messages.insert(0, {"role": "system", "content": enhanced_system_prompt})

        # 添加用户输入
        messages.append({
            "role": "user",
            "content": user_input
        })

        return messages

    # 🆕 新增方法：获取当前项目的所有设定
    async def get_project_facts(
        self,
        project_id: str = None,
        fact_types: List[FactType] = None
    ) -> List[StoryFact]:
        """
        获取项目的所有设定

        Args:
            project_id: 项目 ID（默认使用当前项目）
            fact_types: 筛选的设定类型

        Returns:
            List[StoryFact]: 设定列表
        """
        project_id = project_id or self._current_project_id
        if not project_id:
            return []

        return await self.fact_manager.get_facts(project_id, fact_types)

    # 🆕 新增方法：清除项目设定
    async def clear_project_facts(self, project_id: str = None) -> bool:
        """
        清除项目的所有设定

        Args:
            project_id: 项目 ID（默认使用当前项目）

        Returns:
            bool: 是否成功
        """
        project_id = project_id or self._current_project_id
        if not project_id:
            return False

        return await self.fact_manager.clear_facts(project_id)

    # ==================== 角色语气管理便捷方法 ====================

    async def set_character_voice(
        self,
        character_id: str,
        character_name: str,
        style: str = "casual",
        samples: List[str] = None,
        traits: List[str] = None,
        catchphrases: List[str] = None
    ) -> bool:
        """
        设置角色语气

        Args:
            character_id: 角色 ID
            character_name: 角色名称
            style: 语气风格 (casual, formal, aggressive, gentle, etc.)
            samples: 对白样本列表
            traits: 性格特征
            catchphrases: 口头禅列表

        Returns:
            bool: 是否成功
        """
        try:
            from utils.persona_helper import get_persona_helper, VoiceStyle

            persona_helper = get_persona_helper()

            # 创建或更新档案
            profile = await persona_helper.create_profile(
                character_id=character_id,
                character_name=character_name,
                dominant_style=VoiceStyle(style),
                personality_traits=traits or [],
                catchphrases=catchphrases or []
            )

            # 添加样本
            if samples:
                for sample in samples:
                    await persona_helper.add_sample(
                        character_id=character_id,
                        dialogue_sample=sample,
                        context="用户提供的样本",
                        voice_style=VoiceStyle(style)
                    )

            # 添加到当前项目
            if self._current_project_id:
                await persona_helper.add_character_to_project(self._current_project_id, character_id)

            self.logger.info(f"✅ 设置角色语气成功: {character_name} ({len(samples or [])} 个样本)")
            return True

        except Exception as e:
            self.logger.error(f"❌ 设置角色语气失败: {e}")
            return False

    async def get_character_voice(self, character_id: str) -> Optional[Dict[str, Any]]:
        """
        获取角色语气配置

        Args:
            character_id: 角色 ID

        Returns:
            Optional[Dict]: 角色语气信息
        """
        try:
            from utils.persona_helper import get_persona_helper
            persona_helper = get_persona_helper()
            profile = await persona_helper.get_profile(character_id)

            if profile:
                return profile.to_dict()
            return None

        except Exception as e:
            self.logger.error(f"获取角色语气失败: {e}")
            return None

    async def add_character_voice_sample(
        self,
        character_id: str,
        dialogue: str,
        context: str = "默认场景",
        style: str = "casual"
    ) -> bool:
        """
        添加角色语气样本

        Args:
            character_id: 角色 ID
            dialogue: 对白内容
            context: 使用场景
            style: 语气风格

        Returns:
            bool: 是否成功
        """
        try:
            from utils.persona_helper import get_persona_helper, VoiceStyle
            persona_helper = get_persona_helper()

            return await persona_helper.add_sample(
                character_id=character_id,
                dialogue_sample=dialogue,
                context=context,
                voice_style=VoiceStyle(style)
            )

        except Exception as e:
            self.logger.error(f"添加语气样本失败: {e}")
            return False

    async def get_project_characters(self, project_id: str = None) -> List[Dict[str, Any]]:
        """
        获取项目的所有角色语气配置

        Args:
            project_id: 项目 ID（默认使用当前项目）

        Returns:
            List[Dict]: 角色列表
        """
        try:
            from utils.persona_helper import get_persona_helper
            persona_helper = get_persona_helper()

            project_id = project_id or self._current_project_id
            if not project_id:
                return []

            character_ids = await persona_helper.get_project_characters(project_id)
            profiles = []

            for char_id in character_ids:
                profile = await persona_helper.get_profile(char_id)
                if profile:
                    profiles.append(profile.to_dict())

            return profiles

        except Exception as e:
            self.logger.error(f"获取项目角色失败: {e}")
            return []

    async def format_scene_voices_prompt(
        self,
        character_ids: List[str],
        compact: bool = False
    ) -> str:
        """
        格式化场景角色的语气为 Prompt

        Args:
            character_ids: 角色 ID 列表
            compact: 是否使用紧凑格式

        Returns:
            str: Prompt 格式的语气说明
        """
        try:
            from utils.persona_helper import get_persona_helper
            persona_helper = get_persona_helper()

            if compact:
                return await persona_helper.format_compact_voice_prompt(character_ids)
            else:
                return await persona_helper.format_voice_prompt(character_ids)

        except Exception as e:
            self.logger.error(f"格式化语气 Prompt 失败: {e}")
            return ""

    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "short_drama_creator",
            "creation_config": self.creation_config,
            "supported_drama_types": list(self.creation_templates.keys()),
            "output_tag": "drama_creation",
            "features": {
                "fact_extraction": True,
                "fact_management": True,
                "constraint_enforcement": True,
                "character_voice_control": True  # 🆕 角色语气控制
            }
        })
        return base_info

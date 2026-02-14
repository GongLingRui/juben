"""
角色语气样本管理器

用于维护角色的标志性对白样本，实现角色语气的一致性控制。

核心功能：
1. 增删改查：对角色语气样本进行 CRUD 操作
2. 场景匹配：根据当前场景涉及的角色检索相关样本
3. Prompt 集成：将样本格式化为 Prompt 可用的格式
4. Redis 持久化：样本数据持久化存储

代码作者：宫灵瑞
创建时间：2026年2月7日
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from enum import Enum


logger = logging.getLogger(__name__)


class VoiceStyle(Enum):
    """语气风格"""
    CASUAL = "casual"           # 随意
    FORMAL = "formal"           # 正式
    AGGRESSIVE = "aggressive"   # 强势
    GENTLE = "gentle"           # 温柔
    HUMOROUS = "humorous"       # 幽默
    COLD = "cold"               # 冷漠
    ENTHUSIASTIC = "enthusiastic"  # 热情
    SARCASTIC = "sarcastic"     # 讽刺
    SHY = "shy"                 # 害羞
    CONFIDENT = "confident"     # 自信
    MYSTERIOUS = "mysterious"   # 神秘
    CHILDLIKE = "childlike"     # 天真


@dataclass
class CharacterVoiceSample:
    """角色语气样本"""
    character_id: str              # 角色 ID
    character_name: str            # 角色名称
    dialogue_sample: str           # 对白样本
    context: str                   # 使用场景/上下文
    voice_style: VoiceStyle        # 语气风格
    emotion: str = "neutral"       # 情绪状态
    tone_tags: List[str] = field(default_factory=list)  # 语气标签
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["voice_style"] = self.voice_style.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterVoiceSample":
        """从字典创建"""
        data = data.copy()
        if isinstance(data.get("voice_style"), str):
            data["voice_style"] = VoiceStyle(data["voice_style"])
        return cls(**data)


@dataclass
class CharacterVoiceProfile:
    """角色语气档案"""
    character_id: str
    character_name: str
    voice_samples: List[CharacterVoiceSample] = field(default_factory=list)
    dominant_style: VoiceStyle = VoiceStyle.CASUAL
    personality_traits: List[str] = field(default_factory=list)
    speech_patterns: Dict[str, str] = field(default_factory=dict)  # 说话模式
    catchphrases: List[str] = field(default_factory=list)  # 口头禅
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "voice_samples": [s.to_dict() for s in self.voice_samples],
            "dominant_style": self.dominant_style.value,
            "personality_traits": self.personality_traits,
            "speech_patterns": self.speech_patterns,
            "catchphrases": self.catchphrases,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterVoiceProfile":
        """从字典创建"""
        voice_samples = [
            CharacterVoiceSample.from_dict(s)
            for s in data.get("voice_samples", [])
        ]
        return cls(
            character_id=data["character_id"],
            character_name=data["character_name"],
            voice_samples=voice_samples,
            dominant_style=VoiceStyle(data.get("dominant_style", VoiceStyle.CASUAL.value)),
            personality_traits=data.get("personality_traits", []),
            speech_patterns=data.get("speech_patterns", {}),
            catchphrases=data.get("catchphrases", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


class PersonaHelper:
    """
    角色语气样本管理器

    功能：
    1. 样本管理：增删改查角色语气样本
    2. 档案管理：维护角色语气档案
    3. 场景匹配：根据场景角色检索相关样本
    4. Prompt 生成：格式化为 Prompt 可用格式
    """

    def __init__(self, redis_client=None):
        """
        初始化管理器

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

    def _get_profile_key(self, character_id: str) -> str:
        """生成角色档案 Redis 键"""
        return f"persona:profile:{character_id}"

    def _get_project_key(self, project_id: str) -> str:
        """生成项目角色映射 Redis 键"""
        return f"persona:project:{project_id}"

    # ==================== 档案管理 ====================

    async def create_profile(
        self,
        character_id: str,
        character_name: str,
        dominant_style: VoiceStyle = VoiceStyle.CASUAL,
        personality_traits: List[str] = None,
        speech_patterns: Dict[str, str] = None,
        catchphrases: List[str] = None
    ) -> CharacterVoiceProfile:
        """
        创建角色语气档案

        Args:
            character_id: 角色 ID
            character_name: 角色名称
            dominant_style: 主导语气风格
            personality_traits: 性格特征
            speech_patterns: 说话模式
            catchphrases: 口头禅

        Returns:
            CharacterVoiceProfile: 角色语气档案
        """
        profile = CharacterVoiceProfile(
            character_id=character_id,
            character_name=character_name,
            dominant_style=dominant_style,
            personality_traits=personality_traits or [],
            speech_patterns=speech_patterns or {},
            catchphrases=catchphrases or []
        )

        await self.save_profile(profile)
        self.logger.info(f"创建角色语气档案: {character_name} ({character_id})")
        return profile

    async def get_profile(self, character_id: str) -> Optional[CharacterVoiceProfile]:
        """
        获取角色语气档案

        Args:
            character_id: 角色 ID

        Returns:
            Optional[CharacterVoiceProfile]: 角色语气档案
        """
        self._ensure_redis()

        key = self._get_profile_key(character_id)

        try:
            if isinstance(self._redis, dict):
                data_str = self._redis.get(key)
            else:
                data_str = self._redis.get(key)

            if not data_str:
                return None

            if isinstance(data_str, bytes):
                data_str = data_str.decode()

            data = json.loads(data_str)
            return CharacterVoiceProfile.from_dict(data)

        except Exception as e:
            self.logger.error(f"获取角色档案失败: {e}")
            return None

    async def save_profile(self, profile: CharacterVoiceProfile) -> bool:
        """
        保存角色语气档案

        Args:
            profile: 角色语气档案

        Returns:
            bool: 是否成功
        """
        self._ensure_redis()

        key = self._get_profile_key(profile.character_id)
        profile.updated_at = datetime.now().isoformat()

        try:
            data = json.dumps(profile.to_dict(), ensure_ascii=False)

            if isinstance(self._redis, dict):
                self._redis[key] = data
            else:
                self._redis.set(key, data, ex=86400 * 30)  # 30天过期

            self.logger.debug(f"保存角色档案: {profile.character_name}")
            return True

        except Exception as e:
            self.logger.error(f"保存角色档案失败: {e}")
            return False

    async def delete_profile(self, character_id: str) -> bool:
        """
        删除角色语气档案

        Args:
            character_id: 角色 ID

        Returns:
            bool: 是否成功
        """
        self._ensure_redis()

        key = self._get_profile_key(character_id)

        try:
            if isinstance(self._redis, dict):
                if key in self._redis:
                    del self._redis[key]
            else:
                self._redis.delete(key)

            self.logger.info(f"删除角色档案: {character_id}")
            return True

        except Exception as e:
            self.logger.error(f"删除角色档案失败: {e}")
            return False

    async def list_profiles(self, project_id: str = None) -> List[CharacterVoiceProfile]:
        """
        列出角色语气档案

        Args:
            project_id: 项目 ID（可选，用于筛选）

        Returns:
            List[CharacterVoiceProfile]: 档案列表
        """
        if project_id:
            # 从项目角色映射获取
            return await self._list_profiles_by_project(project_id)

        # 返回所有档案（需要扫描）
        self._ensure_redis()
        profiles = []

        try:
            if isinstance(self._redis, dict):
                for key, value in self._redis.items():
                    if key.startswith("persona:profile:"):
                        data = json.loads(value)
                        profiles.append(CharacterVoiceProfile.from_dict(data))
            else:
                # Redis 模式需要 scan
                pattern = "persona:profile:*"
                async for key in self._redis.scan_iter(match=pattern, count=100):
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    data_str = self._redis.get(key_str)
                    if data_str:
                        if isinstance(data_str, bytes):
                            data_str = data_str.decode()
                        data = json.loads(data_str)
                        profiles.append(CharacterVoiceProfile.from_dict(data))

        except Exception as e:
            self.logger.error(f"列出档案失败: {e}")

        return profiles

    async def _list_profiles_by_project(self, project_id: str) -> List[CharacterVoiceProfile]:
        """列出项目的角色档案"""
        self._ensure_redis()

        key = self._get_project_key(project_id)

        try:
            if isinstance(self._redis, dict):
                character_ids = self._redis.get(key, [])
            else:
                data = self._redis.get(key)
                character_ids = json.loads(data) if data else []

            profiles = []
            for character_id in character_ids:
                profile = await self.get_profile(character_id)
                if profile:
                    profiles.append(profile)

            return profiles

        except Exception as e:
            self.logger.error(f"列出项目档案失败: {e}")
            return []

    # ==================== 样本管理 ====================

    async def add_sample(
        self,
        character_id: str,
        dialogue_sample: str,
        context: str,
        voice_style: VoiceStyle,
        emotion: str = "neutral",
        tone_tags: List[str] = None
    ) -> bool:
        """
        添加语气样本

        Args:
            character_id: 角色 ID
            dialogue_sample: 对白样本
            context: 使用场景
            voice_style: 语气风格
            emotion: 情绪状态
            tone_tags: 语气标签

        Returns:
            bool: 是否成功
        """
        profile = await self.get_profile(character_id)
        if not profile:
            self.logger.warning(f"角色档案不存在: {character_id}")
            return False

        sample = CharacterVoiceSample(
            character_id=character_id,
            character_name=profile.character_name,
            dialogue_sample=dialogue_sample,
            context=context,
            voice_style=voice_style,
            emotion=emotion,
            tone_tags=tone_tags or []
        )

        profile.voice_samples.append(sample)
        return await self.save_profile(profile)

    async def remove_sample(self, character_id: str, sample_index: int) -> bool:
        """
        移除语气样本

        Args:
            character_id: 角色 ID
            sample_index: 样本索引

        Returns:
            bool: 是否成功
        """
        profile = await self.get_profile(character_id)
        if not profile:
            return False

        if 0 <= sample_index < len(profile.voice_samples):
            profile.voice_samples.pop(sample_index)
            return await self.save_profile(profile)

        return False

    async def update_sample(
        self,
        character_id: str,
        sample_index: int,
        dialogue_sample: str = None,
        context: str = None,
        voice_style: VoiceStyle = None,
        emotion: str = None,
        tone_tags: List[str] = None
    ) -> bool:
        """
        更新语气样本

        Args:
            character_id: 角色 ID
            sample_index: 样本索引
            dialogue_sample: 对白样本
            context: 使用场景
            voice_style: 语气风格
            emotion: 情绪状态
            tone_tags: 语气标签

        Returns:
            bool: 是否成功
        """
        profile = await self.get_profile(character_id)
        if not profile:
            return False

        if 0 <= sample_index < len(profile.voice_samples):
            sample = profile.voice_samples[sample_index]

            if dialogue_sample is not None:
                sample.dialogue_sample = dialogue_sample
            if context is not None:
                sample.context = context
            if voice_style is not None:
                sample.voice_style = voice_style
            if emotion is not None:
                sample.emotion = emotion
            if tone_tags is not None:
                sample.tone_tags = tone_tags

            return await self.save_profile(profile)

        return False

    # ==================== 场景匹配 ====================

    async def get_samples_for_scene(
        self,
        character_ids: List[str],
        max_samples_per_character: int = 3,
        style_filter: VoiceStyle = None
    ) -> Dict[str, List[CharacterVoiceSample]]:
        """
        获取场景相关角色的语气样本

        Args:
            character_ids: 场景涉及的角色 ID 列表
            max_samples_per_character: 每个角色最大样本数
            style_filter: 风格筛选（可选）

        Returns:
            Dict[str, List[CharacterVoiceSample]]: 角色 -> 样本列表
        """
        result = {}

        for character_id in character_ids:
            profile = await self.get_profile(character_id)
            if not profile:
                continue

            samples = profile.voice_samples

            # 风格筛选
            if style_filter:
                samples = [s for s in samples if s.voice_style == style_filter]

            # 限制数量（优先取最新的）
            samples = samples[-max_samples_per_character:]

            if samples:
                result[character_id] = samples

        return result

    # ==================== Prompt 生成 ====================

    async def format_voice_prompt(
        self,
        character_ids: List[str],
        max_samples_per_character: int = 2
    ) -> str:
        """
        格式化角色语气样本为 Prompt 格式

        Args:
            character_ids: 角色 ID 列表
            max_samples_per_character: 每个角色最大样本数

        Returns:
            str: Prompt 格式的语气说明
        """
        samples_dict = await self.get_samples_for_scene(
            character_ids,
            max_samples_per_character
        )

        if not samples_dict:
            return ""

        lines = ["【角色语气参考】"]
        lines.append("以下是各角色的标志性对白风格，请在创作对话时参考：\n")

        for character_id, samples in samples_dict.items():
            if not samples:
                continue

            profile = await self.get_profile(character_id)
            if not profile:
                continue

            lines.append(f"## {profile.character_name}")

            # 添加性格特征
            if profile.personality_traits:
                lines.append(f"- 性格特征: {', '.join(profile.personality_traits)}")

            # 添加口头禅
            if profile.catchphrases:
                lines.append(f"- 口头禅: {', '.join(profile.catchphrases)}")

            # 添加语气风格
            lines.append(f"- 主导风格: {profile.dominant_style.value}")

            lines.append("\n对白样本示例:")

            # 添加样本
            for sample in samples:
                lines.append(f"  Example ({sample.context}):")
                lines.append(f"    \"{sample.dialogue_sample}\"")
                if sample.tone_tags:
                    lines.append(f"    语气标签: {', '.join(sample.tone_tags)}")
                lines.append("")

        return "\n".join(lines)

    async def format_compact_voice_prompt(
        self,
        character_ids: List[str]
    ) -> str:
        """
        格式化紧凑版角色语气说明

        Args:
            character_ids: 角色 ID 列表

        Returns:
            str: 紧凑格式的语气说明
        """
        samples_dict = await self.get_samples_for_scene(character_ids, max_samples_per_character=1)

        if not samples_dict:
            return ""

        lines = ["角色语气:"]
        for character_id, samples in samples_dict.items():
            profile = await self.get_profile(character_id)
            if profile and samples:
                sample = samples[0]
                lines.append(
                    f"- {profile.character_name}: \"{sample.dialogue_sample}\" "
                    f"({profile.dominant_style.value})"
                )

        return "\n".join(lines)

    # ==================== 项目管理 ====================

    async def add_character_to_project(
        self,
        project_id: str,
        character_id: str
    ) -> bool:
        """
        添加角色到项目

        Args:
            project_id: 项目 ID
            character_id: 角色 ID

        Returns:
            bool: 是否成功
        """
        self._ensure_redis()

        key = self._get_project_key(project_id)

        try:
            if isinstance(self._redis, dict):
                character_ids = self._redis.get(key, [])
            else:
                data = self._redis.get(key)
                character_ids = json.loads(data) if data else []

            if character_id not in character_ids:
                character_ids.append(character_id)

                if isinstance(self._redis, dict):
                    self._redis[key] = character_ids
                else:
                    self._redis.set(key, json.dumps(character_ids), ex=86400 * 30)

            return True

        except Exception as e:
            self.logger.error(f"添加角色到项目失败: {e}")
            return False

    async def get_project_characters(self, project_id: str) -> List[str]:
        """
        获取项目的角色列表

        Args:
            project_id: 项目 ID

        Returns:
            List[str]: 角色 ID 列表
        """
        self._ensure_redis()

        key = self._get_project_key(project_id)

        try:
            if isinstance(self._redis, dict):
                return self._redis.get(key, [])
            else:
                data = self._redis.get(key)
                return json.loads(data) if data else []

        except Exception as e:
            self.logger.error(f"获取项目角色失败: {e}")
            return []

    async def set_character_voices_from_input(
        self,
        project_id: str,
        character_voices: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        从 input_data 的 character_voices 批量设置角色语气

        Args:
            project_id: 项目 ID
            character_voices: character_voices 字典
                格式: {
                    "character_id": {
                        "name": "角色名",
                        "style": "casual",
                        "samples": ["对白样本1", "对白样本2"],
                        "traits": ["性格1", "性格2"],
                        "catchphrases": ["口头禅"]
                    }
                }

        Returns:
            int: 成功设置的角色数量
        """
        count = 0

        for character_id, voice_data in character_voices.items():
            try:
                # 创建或更新档案
                profile = await self.get_profile(character_id)
                if not profile:
                    profile = await self.create_profile(
                        character_id=character_id,
                        character_name=voice_data.get("name", f"角色{character_id}"),
                        dominant_style=VoiceStyle(voice_data.get("style", "casual")),
                        personality_traits=voice_data.get("traits", []),
                        catchphrases=voice_data.get("catchphrases", [])
                    )

                # 添加样本
                samples = voice_data.get("samples", [])
                for sample in samples:
                    await self.add_sample(
                        character_id=character_id,
                        dialogue_sample=sample,
                        context="默认场景",
                        voice_style=profile.dominant_style
                    )

                # 添加到项目
                await self.add_character_to_project(project_id, character_id)

                count += 1

            except Exception as e:
                self.logger.error(f"设置角色语气失败 {character_id}: {e}")
                continue

        self.logger.info(f"批量设置角色语气完成: {count}/{len(character_voices)}")
        return count


# ==================== 全局实例 ====================

_persona_helper: Optional[PersonaHelper] = None


def get_persona_helper() -> PersonaHelper:
    """获取角色语气管理器单例"""
    global _persona_helper
    if _persona_helper is None:
        _persona_helper = PersonaHelper()
    return _persona_helper


# ==================== 便捷函数 ====================

async def create_character_profile(
    character_id: str,
    character_name: str,
    style: str = "casual",
    traits: List[str] = None,
    catchphrases: List[str] = None
) -> CharacterVoiceProfile:
    """创建角色语气档案"""
    helper = get_persona_helper()
    return await helper.create_profile(
        character_id=character_id,
        character_name=character_name,
        dominant_style=VoiceStyle(style),
        personality_traits=traits,
        catchphrases=catchphrases
    )


async def add_voice_sample(
    character_id: str,
    dialogue: str,
    context: str = "默认",
    style: str = "casual"
) -> bool:
    """添加语气样本"""
    helper = get_persona_helper()
    return await helper.add_sample(
        character_id=character_id,
        dialogue_sample=dialogue,
        context=context,
        voice_style=VoiceStyle(style)
    )


async def get_voice_prompt(
    character_ids: List[str],
    compact: bool = False
) -> str:
    """
    获取角色语气 Prompt

    Args:
        character_ids: 角色 ID 列表
        compact: 是否使用紧凑格式

    Returns:
        str: Prompt 格式的语气说明
    """
    helper = get_persona_helper()
    if compact:
        return await helper.format_compact_voice_prompt(character_ids)
    else:
        return await helper.format_voice_prompt(character_ids)

"""
风格分析器
分析用户修改AI生成内容的意图，提取用户写作风格特征

功能：
1. 对比AI原文与用户修改文
2. 提取修改意图（细节描写、情感表达、对话风格等）
3. 生成风格标签
4. 输出风格分析报告

代码作者：Claude
创建时间：2026年2月7日
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ModificationIntent(Enum):
    """修改意图分类"""
    ADD_DETAIL = "add_detail"              # 添加细节描写
    ENHANCE_EMOTION = "enhance_emotion"    # 增强情感表达
    CHANGE_DIALOGUE = "change_dialogue"    # 修改对话风格
    SIMPLIFY_LANGUAGE = "simplify_language" # 简化语言
    MAKE_VIVID = "make_vivid"              # 使表达更生动
    ADJUST_TONE = "adjust_tone"            # 调整语气
    ADD_METAPHOR = "add_metaphor"          # 添加比喻/修辞
    STRUCTURE_CHANGE = "structure_change"  # 结构调整


class StyleFeature(Enum):
    """风格特征标签"""
    DESCRIPTIVE = "descriptive"            # 描写性强
    EMOTIONAL = "emotional"                # 情感丰富
    CONCISE = "concise"                    # 简洁有力
    VIVID = "vivid"                        # 生动形象
    HUMOROUS = "humorous"                  # 幽默风趣
    FORMAL = "formal"                      # 正式庄重
    COLLOQUIAL = "colloquial"              # 口语化
    DRAMATIC = "dramatic"                  # 戏剧性强
    SUBTLE = "subtle"                      # 含蓄内敛
    METAPHORICAL = "metaphorical"          # 善用比喻


@dataclass
class Modification:
    """单次修改记录"""
    original_text: str
    modified_text: str
    intent: ModificationIntent
    confidence: float
    position: Tuple[int, int]  # (start, end)
    reasoning: str


@dataclass
class StyleAnalysisResult:
    """风格分析结果"""
    user_id: str
    session_id: str
    timestamp: str

    # 输入
    original_text: str
    modified_text: str

    # 分析结果
    modifications: List[Modification]
    detected_intents: List[ModificationIntent]
    style_features: List[StyleFeature]
    confidence_score: float

    # 提取的风格信息
    writing_patterns: Dict[str, Any]
    vocabulary_preferences: List[str]
    sentence_structure: str

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "original_text": self.original_text,
            "modified_text": self.modified_text,
            "modifications": [
                {
                    "original_text": m.original_text,
                    "modified_text": m.modified_text,
                    "intent": m.intent.value,
                    "confidence": m.confidence,
                    "position": m.position,
                    "reasoning": m.reasoning
                }
                for m in self.modifications
            ],
            "detected_intents": [i.value for i in self.detected_intents],
            "style_features": [f.value for f in self.style_features],
            "confidence_score": self.confidence_score,
            "writing_patterns": self.writing_patterns,
            "vocabulary_preferences": self.vocabulary_preferences,
            "sentence_structure": self.sentence_structure,
            "metadata": self.metadata
        }


class StyleAnalyzer:
    """
    风格分析器

    使用LLM分析用户修改内容的风格特征
    """

    def __init__(self, llm_client=None):
        """
        初始化风格分析器

        Args:
            llm_client: LLM客户端实例（可选）
        """
        self.llm_client = llm_client
        self.logger = logger

        # 分析提示词模板
        self.analysis_prompt_template = """你是一个专业的文本风格分析专家。请分析用户对AI生成内容的修改，提取用户的写作风格特征。

【AI原文】
{original_text}

【用户修改后】
{modified_text}

请从以下几个方面进行分析：

1. **修改意图识别**：
   - 添加细节描写（如：把"他很生气"改为"他额角的青筋暴起"）
   - 增强情感表达（如：添加心理描写、情感渲染）
   - 修改对话风格（如：使对话更口语化、更正式、更有个性）
   - 简化语言（如：删除冗余表达，使语言更简洁）
   - 使表达更生动（如：添加比喻、拟人等修辞手法）
   - 调整语气（如：从严肃改为轻松，从直白改为含蓄）
   - 添加比喻/修辞（如：使用明喻、暗喻、排比等）
   - 结构调整（如：改变句子顺序、重新组织段落）

2. **风格特征提取**：
   - 描写性强（注重细节描写）
   - 情感丰富（善于表达情感）
   - 简洁有力（言简意赅）
   - 生动形象（使用形象化语言）
   - 幽默风趣（带有幽默感）
   - 正式庄重（使用正式语言）
   - 口语化（使用日常口语）
   - 戏剧性强（有戏剧张力）
   - 含蓄内敛（表达含蓄）
   - 善用比喻（频繁使用比喻）

3. **写作模式识别**：
   - 句子长度偏好（短句/长句/混合）
   - 词汇选择偏好（具体/抽象/专业/通俗）
   - 标点符号使用特点
   - 段落结构特点

请以JSON格式返回分析结果：

```json
{{
  "modifications": [
    {{
      "original": "原文片段",
      "modified": "修改后片段",
      "intent": "修改意图",
      "reasoning": "分析理由"
    }}
  ],
  "detected_intents": ["intent1", "intent2"],
  "style_features": ["feature1", "feature2"],
  "writing_patterns": {{
    "sentence_length": "short/long/mixed",
    "vocabulary_type": "concrete/abstract/professional/casual",
    "punctuation_style": "描述标点使用特点",
    "paragraph_structure": "描述段落结构特点"
  }},
  "vocabulary_preferences": ["词汇1", "词汇2", "词汇3"],
  "confidence_score": 0.85
}}
```

注意：
1. detected_intents 必须从以下值中选择：add_detail, enhance_emotion, change_dialogue, simplify_language, make_vivid, adjust_tone, add_metaphor, structure_change
2. style_features 必须从以下值中选择：descriptive, emotional, concise, vivid, humorous, formal, colloquial, dramatic, subtle, metaphorical
3. confidence_score 应该是 0-1 之间的值，表示分析的可信度
"""

    async def analyze(
        self,
        original_text: str,
        modified_text: str,
        user_id: str,
        session_id: str
    ) -> StyleAnalysisResult:
        """
        分析风格修改

        Args:
            original_text: AI生成的原文
            modified_text: 用户修改后的文本
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            StyleAnalysisResult: 分析结果
        """
        try:
            # 如果有LLM客户端，使用智能分析
            if self.llm_client:
                return await self._llm_analyze(
                    original_text, modified_text, user_id, session_id
                )
            else:
                # 否则使用规则分析
                return self._rule_based_analyze(
                    original_text, modified_text, user_id, session_id
                )
        except Exception as e:
            self.logger.error(f"风格分析失败: {e}")
            # 返回一个基础的结果
            return self._create_fallback_result(
                original_text, modified_text, user_id, session_id
            )

    async def _llm_analyze(
        self,
        original_text: str,
        modified_text: str,
        user_id: str,
        session_id: str
    ) -> StyleAnalysisResult:
        """使用LLM进行智能分析"""
        try:
            # 构建提示词
            prompt = self.analysis_prompt_template.format(
                original_text=original_text,
                modified_text=modified_text
            )

            # 调用LLM
            messages = [
                {"role": "system", "content": "你是专业的文本风格分析专家。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm_client.chat(messages)

            # 解析JSON响应
            # 提取JSON部分（处理可能的markdown代码块）
            json_str = self._extract_json(response)
            analysis_data = json.loads(json_str)

            # 构建结果
            modifications = []
            for mod in analysis_data.get("modifications", []):
                modifications.append(Modification(
                    original_text=mod.get("original", ""),
                    modified_text=mod.get("modified", ""),
                    intent=ModificationIntent(mod.get("intent", "add_detail")),
                    confidence=0.8,
                    position=(0, 0),  # 简化处理
                    reasoning=mod.get("reasoning", "")
                ))

            detected_intents = [
                ModificationIntent(i) for i in analysis_data.get("detected_intents", [])
            ]
            style_features = [
                StyleFeature(f) for f in analysis_data.get("style_features", [])
            ]

            result = StyleAnalysisResult(
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                original_text=original_text,
                modified_text=modified_text,
                modifications=modifications,
                detected_intents=detected_intents,
                style_features=style_features,
                confidence_score=analysis_data.get("confidence_score", 0.7),
                writing_patterns=analysis_data.get("writing_patterns", {}),
                vocabulary_preferences=analysis_data.get("vocabulary_preferences", []),
                sentence_structure=analysis_data.get("writing_patterns", {}).get("sentence_length", "mixed")
            )

            self.logger.info(f"✅ LLM风格分析完成 (user: {user_id}, confidence: {result.confidence_score})")
            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"LLM返回的JSON解析失败: {e}")
            return self._rule_based_analyze(original_text, modified_text, user_id, session_id)
        except Exception as e:
            self.logger.error(f"LLM分析失败: {e}")
            return self._rule_based_analyze(original_text, modified_text, user_id, session_id)

    def _rule_based_analyze(
        self,
        original_text: str,
        modified_text: str,
        user_id: str,
        session_id: str
    ) -> StyleAnalysisResult:
        """基于规则的风格分析"""
        modifications = []
        detected_intents = []
        style_features = []

        # 规则1: 检测长度变化
        length_ratio = len(modified_text) / max(len(original_text), 1)
        if length_ratio > 1.3:
            detected_intents.append(ModificationIntent.ADD_DETAIL)
            style_features.append(StyleFeature.DESCRIPTIVE)
        elif length_ratio < 0.7:
            detected_intents.append(ModificationIntent.SIMPLIFY_LANGUAGE)
            style_features.append(StyleFeature.CONCISE)

        # 规则2: 检测情感词汇
        emotion_words = ["激动", "愤怒", "悲伤", "喜悦", "恐惧", "爱", "恨", "感动", "震撼"]
        modified_emotion_count = sum(1 for word in emotion_words if word in modified_text)
        original_emotion_count = sum(1 for word in emotion_words if word in original_text)
        if modified_emotion_count > original_emotion_count:
            detected_intents.append(ModificationIntent.ENHANCE_EMOTION)
            style_features.append(StyleFeature.EMOTIONAL)

        # 规则3: 检测引号（对话）
        if modified_text.count('"') > original_text.count('"') or modified_text.count('"') > original_text.count('"'):
            detected_intents.append(ModificationIntent.CHANGE_DIALOGUE)

        # 规则4: 检测比喻词
        metaphor_words = ["像", "如", "仿佛", "犹如", "好似", "如同"]
        if any(word in modified_text for word in metaphor_words):
            detected_intents.append(ModificationIntent.ADD_METAPHOR)
            style_features.append(StyleFeature.METAPHORICAL)

        # 规则5: 检测形容词和副词
        desc_suffixes = ["的", "地", "得"]
        desc_count = sum(1 for char in modified_text if char in desc_suffixes)
        if desc_count > len(modified_text) * 0.1:  # 超过10%
            style_features.append(StyleFeature.VIVID)

        # 如果没有检测到任何意图，添加默认值
        if not detected_intents:
            detected_intents.append(ModificationIntent.ADD_DETAIL)
        if not style_features:
            style_features.append(StyleFeature.DESCRIPTIVE)

        # 创建基础修改记录
        modifications.append(Modification(
            original_text=original_text[:100],
            modified_text=modified_text[:100],
            intent=detected_intents[0],
            confidence=0.6,
            position=(0, min(100, len(modified_text))),
            reasoning="基于规则的分析结果"
        ))

        result = StyleAnalysisResult(
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            original_text=original_text,
            modified_text=modified_text,
            modifications=modifications,
            detected_intents=detected_intents,
            style_features=style_features,
            confidence_score=0.6,
            writing_patterns={
                "sentence_length": "mixed",
                "vocabulary_type": "casual"
            },
            vocabulary_preferences=[],
            sentence_structure="mixed"
        )

        self.logger.info(f"✅ 规则风格分析完成 (user: {user_id})")
        return result

    def _create_fallback_result(
        self,
        original_text: str,
        modified_text: str,
        user_id: str,
        session_id: str
    ) -> StyleAnalysisResult:
        """创建兜底结果"""
        return StyleAnalysisResult(
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            original_text=original_text,
            modified_text=modified_text,
            modifications=[],
            detected_intents=[ModificationIntent.ADD_DETAIL],
            style_features=[StyleFeature.DESCRIPTIVE],
            confidence_score=0.3,
            writing_patterns={},
            vocabulary_preferences=[],
            sentence_structure="mixed"
        )

    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        # 尝试直接解析
        try:
            json.loads(text.strip())
            return text.strip()
        except:
            pass

        # 尝试提取markdown代码块
        import re
        pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

        # 尝试提取普通代码块
        pattern = r'```\s*([\s\S]*?)\s*```'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

        # 尝试提取花括号内容
        pattern = r'\{[\s\S]*\}'
        match = re.search(pattern, text)
        if match:
            return match.group(0)

        # 如果都失败了，返回原文本
        return text


# ==================== 全局实例 ====================

_style_analyzer: Optional[StyleAnalyzer] = None


def get_style_analyzer(llm_client=None) -> StyleAnalyzer:
    """获取风格分析器单例"""
    global _style_analyzer
    if _style_analyzer is None:
        _style_analyzer = StyleAnalyzer(llm_client=llm_client)
    return _style_analyzer


# ==================== 便捷函数 ====================

async def analyze_style_edit(
    original_text: str,
    modified_text: str,
    user_id: str,
    session_id: str,
    llm_client=None
) -> StyleAnalysisResult:
    """
    分析风格修改（便捷函数）

    Args:
        original_text: AI原文
        modified_text: 用户修改文
        user_id: 用户ID
        session_id: 会话ID
        llm_client: LLM客户端

    Returns:
        StyleAnalysisResult: 分析结果
    """
    analyzer = get_style_analyzer(llm_client)
    return await analyzer.analyze(original_text, modified_text, user_id, session_id)

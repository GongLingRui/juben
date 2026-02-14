"""
内容质量评估框架
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import re

@dataclass
class QualityScore:
    """质量分数数据类"""
    dimension: str  # 评估维度
    score: float    # 分数 (0-100)
    details: str    # 详细说明
    suggestions: List[str] = field(default_factory=list)  # 改进建议

@dataclass
class QualityReport:
    """质量评估报告"""
    overall_score: float  # 总分 (0-100)
    dimension_scores: List[QualityScore]  # 各维度分数
    strengths: List[str]  # 优势
    weaknesses: List[str]  # 不足
    improvement_suggestions: List[str]  # 改进建议
    pass_threshold: float = 60.0  # 及格线
    passed: bool = False  # 是否通过

    def __post_init__(self):
        self.passed = self.overall_score >= self.pass_threshold


class ContentQualityEvaluator:
    """
    内容质量评估器

    支持的评估维度：
    1. 受众匹配度
    2. 需求满足度
    3. 转化有效性
    4. 自然度 (避免AI痕迹)
    5. 可读性
    """

    # 质量标准权重（可配置）
    DEFAULT_WEIGHTS = {
        "audience_match": 0.2,      # 受众匹配度
        "need_satisfaction": 0.25,  # 需求满足度
        "conversion_effectiveness": 0.2,  # 转化有效性
        "naturalness": 0.2,        # 自然度
        "readability": 0.15,       # 可读性
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化评估器

        Args:
            weights: 自定义权重配置
        """
        self.weights = weights or self.DEFAULT_WEIGHTS

    def evaluate(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        评估内容质量

        Args:
            content: 要评估的内容
            context: 上下文信息
                - target_audience: 目标受众
                - requirements: 用户需求
                - content_type: 内容类型（剧本/大纲/人物小传等）
                - platform: 平台（短剧/长剧等）

        Returns:
            QualityReport: 质量评估报告
        """
        context = context or {}
        dimension_scores = []

        # 1. 受众匹配度评估
        dimension_scores.append(self._evaluate_audience_match(content, context))

        # 2. 需求满足度评估
        dimension_scores.append(self._evaluate_need_satisfaction(content, context))

        # 3. 转化有效性评估
        dimension_scores.append(self._evaluate_conversion_effectiveness(content, context))

        # 4. 自然度评估
        dimension_scores.append(self._evaluate_naturalness(content, context))

        # 5. 可读性评估
        dimension_scores.append(self._evaluate_readability(content, context))

        # 计算总分
        overall_score = sum(
            score.score * self.weights.get(score.dimension, 0.2)
            for score in dimension_scores
        )

        # 分析优势和不足
        strengths, weaknesses = self._analyze_strengths_weaknesses(dimension_scores)

        # 汇总改进建议
        improvement_suggestions = []
        for score in dimension_scores:
            if score.score < 60:  # 低于60分的维度
                improvement_suggestions.extend(score.suggestions)

        return QualityReport(
            overall_score=round(overall_score, 2),
            dimension_scores=dimension_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=improvement_suggestions
        )

    def _evaluate_audience_match(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估受众匹配度"""
        score = 70.0  # 基础分
        details = "内容基本符合一般受众需求"
        suggestions = []

        # 检查内容形式适配
        content_type = context.get("content_type", "剧本")
        if content_type in ["剧本", "script"]:
            # 剧本应该有对话和场景描述
            has_dialogue = bool(re.search(r'["「「].+?["」」]', content))
            has_scene_desc = bool(re.search(r'(场景|画面|镜头)', content))

            if has_dialogue and has_scene_desc:
                score += 15
                details = "剧本形式完整，包含对话和场景描述"
            else:
                score -= 10
                suggestions.append("添加更多对话内容")
                suggestions.append("补充场景描述")

        # 检查语言风格匹配
        target_audience = context.get("target_audience", "")
        if "年轻" in target_audience or "青少年" in target_audience:
            # 应该使用更活泼的语言
            if any(word in content for word in ["哎", "哇", "靠", "我去"]):
                score += 10
                details += "，语言风格符合年轻受众"
            else:
                suggestions.append("考虑加入更多年轻化的表达")

        return QualityScore(
            dimension="audience_match",
            score=min(100, max(0, score)),
            details=details,
            suggestions=suggestions
        )

    def _evaluate_need_satisfaction(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估需求满足度"""
        score = 60.0  # 基础分
        details = "内容基本满足需求"
        suggestions = []

        requirements = context.get("requirements", [])

        # 检查内容长度
        content_length = len(content)
        if content_length < 100:
            score -= 20
            suggestions.append("内容过短，需要更详细的描述")
        elif content_length > 2000:
            score -= 10
            suggestions.append("内容过长，可以适当精简")
        else:
            score += 10

        # 检查是否回应了具体需求
        if requirements:
            satisfied_count = 0
            for req in requirements:
                if any(keyword in content for keyword in req.split()):
                    satisfied_count += 1

            satisfaction_rate = satisfied_count / len(requirements)
            score += satisfaction_rate * 20
            details = f"满足了{satisfaction_rate*100:.0f}%的需求"
        else:
            score += 10

        return QualityScore(
            dimension="need_satisfaction",
            score=min(100, max(0, score)),
            details=details,
            suggestions=suggestions
        )

    def _evaluate_conversion_effectiveness(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估转化有效性（对短剧创作，关注情节吸引力）"""
        score = 65.0  # 基础分
        details = "内容具有一定的吸引力"
        suggestions = []

        # 检查是否有冲突/矛盾
        conflict_keywords = ["冲突", "矛盾", "争执", "对抗", "危机", "困难", "挑战"]
        has_conflict = any(kw in content for kw in conflict_keywords)

        if has_conflict:
            score += 15
            details = "包含戏剧冲突，增强吸引力"
        else:
            suggestions.append("考虑加入戏剧冲突以增强吸引力")

        # 检查是否有情感元素
        emotion_keywords = ["感动", "震撼", "惊喜", "温馨", "紧张", "恐惧", "愤怒"]
        has_emotion = any(kw in content for kw in emotion_keywords)

        if has_emotion:
            score += 10

        # 检查情节推进
        if "然后" in content or "接着" in content or "随后" in content:
            score += 10
            details += "，情节推进清晰"

        return QualityScore(
            dimension="conversion_effectiveness",
            score=min(100, max(0, score)),
            details=details,
            suggestions=suggestions
        )

    def _evaluate_naturalness(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估自然度（避免AI痕迹）"""
        score = 70.0  # 基础分
        details = "内容较为自然"
        suggestions = []

        # 检查过度结构化
        first_lines = content.split('\n')[:10]
        numbered_lines = sum(1 for line in first_lines if re.match(r'^\d+[.、]', line.strip()))

        if numbered_lines > 5:
            score -= 15
            suggestions.append("减少过度结构化的列表形式")
            details = "存在过度结构化的问题"
        else:
            score += 10

        # 检查emoji使用（如果适用）
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', content))

        if emoji_count == 0:
            score += 5
        elif emoji_count > len(content) / 50:  # emoji过多
            score -= 10
            suggestions.append("减少emoji使用，避免过度装饰")

        # 检查是否有"综上所述"、"首先其次"等AI常用词
        ai_phrases = ["综上所述", "总而言之", "首先，其次", "值得注意的是"]
        ai_phrase_count = sum(1 for phrase in ai_phrases if phrase in content)

        if ai_phrase_count > 2:
            score -= 15
            suggestions.append("避免使用过于正式的连接词")
            details = "存在明显的AI写作痕迹"
        else:
            score += 10

        return QualityScore(
            dimension="naturalness",
            score=min(100, max(0, score)),
            details=details,
            suggestions=suggestions
        )

    def _evaluate_readability(self, content: str, context: Dict[str, Any]) -> QualityScore:
        """评估可读性"""
        score = 70.0  # 基础分
        details = "内容可读性良好"
        suggestions = []

        # 检查段落长度
        paragraphs = content.split('\n\n')
        long_paragraphs = sum(1 for p in paragraphs if len(p) > 500)

        if long_paragraphs > len(paragraphs) / 2:
            score -= 15
            suggestions.append("部分段落过长，建议分段")
            details = "存在过长的段落"
        else:
            score += 10

        # 检查句子长度
        sentences = re.split(r'[。！？\n]', content)
        long_sentences = sum(1 for s in sentences if len(s) > 100)

        if long_sentences > len(sentences) / 3:
            score -= 10
            suggestions.append("部分句子过长，建议拆分")

        # 检查信息密度
        if len(content) > 0:
            avg_line_length = len(content) / len(content.split('\n'))
            if avg_line_length < 20:
                score -= 10
                suggestions.append("信息密度过低，需要更充实的内容")
            elif avg_line_length > 100:
                score -= 10
                suggestions.append("信息密度过高，需要分段表达")

        return QualityScore(
            dimension="readability",
            score=min(100, max(0, score)),
            details=details,
            suggestions=suggestions
        )

    def _analyze_strengths_weaknesses(
        self,
        dimension_scores: List[QualityScore]
    ) -> Tuple[List[str], List[str]]:
        """分析优势和不足"""
        strengths = []
        weaknesses = []

        for score in dimension_scores:
            if score.score >= 75:
                strengths.append(f"{score.details} ({score.score}分)")
            elif score.score < 60:
                weaknesses.append(f"{score.details} ({score.score}分)")

        if not strengths:
            strengths.append("各项指标表现均衡")
        if not weaknesses:
            weaknesses.append("无明显不足")

        return strengths, weaknesses

    def format_report(self, report: QualityReport) -> str:
        """
        格式化评估报告为可读文本

        Args:
            report: 质量评估报告

        Returns:
            str: 格式化的报告文本
        """
        lines = [
            "=== 内容质量评估报告 ===",
            f"\n总分: {report.overall_score:.1f}分",
            f"状态: {'✅ 通过' if report.passed else '❌ 未通过'} (及格线: {report.pass_threshold}分)",
            "\n--- 各维度评分 ---"
        ]

        for score in report.dimension_scores:
            dimension_name = {
                "audience_match": "受众匹配度",
                "need_satisfaction": "需求满足度",
                "conversion_effectiveness": "转化有效性",
                "naturalness": "自然度",
                "readability": "可读性"
            }.get(score.dimension, score.dimension)

            status_icon = "✅" if score.score >= 60 else "⚠️"
            lines.append(f"\n{status_icon} {dimension_name}: {score.score:.1f}分")
            lines.append(f"   {score.details}")

            if score.suggestions:
                lines.append("   改进建议:")
                for suggestion in score.suggestions:
                    lines.append(f"   - {suggestion}")

        lines.append("\n--- 优势分析 ---")
        for strength in report.strengths:
            lines.append(f"✓ {strength}")

        lines.append("\n--- 不足分析 ---")
        for weakness in report.weaknesses:
            lines.append(f"✗ {weakness}")

        if report.improvement_suggestions:
            lines.append("\n--- 综合改进建议 ---")
            for i, suggestion in enumerate(report.improvement_suggestions, 1):
                lines.append(f"{i}. {suggestion}")

        return "\n".join(lines)


# 全局评估器实例
_evaluator = None

def get_content_quality_evaluator() -> ContentQualityEvaluator:
    """获取内容质量评估器实例"""
    global _evaluator
    if _evaluator is None:
        _evaluator = ContentQualityEvaluator()
    return _evaluator


# 便捷函数
def evaluate_content_quality(
    content: str,
    context: Optional[Dict[str, Any]] = None
) -> QualityReport:
    """
    便捷函数：评估内容质量

    Args:
        content: 要评估的内容
        context: 上下文信息

    Returns:
        QualityReport: 质量评估报告
    """
    evaluator = get_content_quality_evaluator()
    return evaluator.evaluate(content, context)


def format_quality_report(report: QualityReport) -> str:
    """
    便捷函数：格式化评估报告

    Args:
        report: 质量评估报告

    Returns:
        str: 格式化的报告文本
    """
    evaluator = get_content_quality_evaluator()
    return evaluator.format_report(report)

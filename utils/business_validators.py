"""
业务规则验证器
专门用于短剧剧本的业务规则强制验证

代码作者：宫灵瑞
创建时间：2026年2月7日

验证器列表：
1. EmotionalSpringValidator - 情绪弹簧理论验证器
2. GoldenThreeSecondsValidator - 黄金三秒钩子验证器
3. FiveElementsValidator - 故事五元素验证器
"""
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """验证结果级别"""
    EXCELLENT = "excellent"      # 优秀
    GOOD = "good"               # 良好
    PASS = "pass"              # 及格
    FAIL = "fail"              # 不合格


@dataclass
class ValidationReport:
    """验证报告"""
    validator_name: str                # 验证器名称
    result: ValidationResult           # 验证结果
    score: float                       # 评分 (0-100)
    issues: List[str]                  # 发现的问题
    suggestions: List[str]             # 改进建议
    metadata: Dict[str, Any]           # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "validator_name": self.validator_name,
            "result": self.result.value,
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "metadata": self.metadata
        }


class EmotionalSpringValidator:
    """
    情绪弹簧理论验证器

    核心理论：
    每一集剧本的存在价值只有两个："压弹簧" 或 "放弹簧"
    - 压弹簧：积蓄观众负面情绪（愤怒、憋屈、紧张、好奇）
    - 放弹簧：瞬间释放积蓄的情绪（反转、打脸、真相大白）
    """

    def __init__(self):
        self.validator_name = "情绪弹簧验证器"

        # 压弹簧关键词
        self.tension_keywords = [
            "压抑", "憋屈", "愤怒", "不甘", "绝望", "痛苦", "挣扎",
            "危机", "威胁", "逼迫", "欺凌", "羞辱", "陷害", "误会",
            "紧绷", "窒息", "沉重", "煎熬", "紧张", "惊险", "危急",
            "委屈", "冤枉", "无力", "绝望", "崩溃", "承受", "忍受"
        ]

        # 放弹簧关键词
        self.release_keywords = [
            "爆发", "反击", "打脸", "反转", "爽快", "痛快", "解气",
            "真相大白", "逆袭", "成功", "胜利", "击败", "战胜",
            "释放", "酣畅淋漓", "扬眉吐气", "舒畅", "满足", "欣喜",
            "振奋", "报一箭之仇", "洗刷冤屈", "证明清白", "惩恶扬善"
        ]

    def validate(self, script: Dict[str, Any]) -> ValidationReport:
        """
        验证剧本是否符合情绪弹簧理论

        Args:
            script: 剧本数据，应包含 content 字段或相关结构

        Returns:
            ValidationReport: 验证报告
        """
        issues = []
        suggestions = []
        metadata = {}

        # 提取剧本内容
        content = self._extract_content(script)

        if not content:
            return ValidationReport(
                validator_name=self.validator_name,
                result=ValidationResult.FAIL,
                score=0.0,
                issues=["无法提取剧本内容"],
                suggestions=["请检查剧本数据格式"],
                metadata={}
            )

        # 统计压弹簧关键词
        tension_count = sum(1 for kw in self.tension_keywords if kw in content)
        tension_sentences = self._find_sentences_with_keywords(content, self.tension_keywords)

        # 统计放弹簧关键词
        release_count = sum(1 for kw in self.release_keywords if kw in content)
        release_sentences = self._find_sentences_with_keywords(content, self.release_keywords)

        # 分析情绪弹簧执行情况
        has_tension = tension_count > 0
        has_release = release_count > 0

        metadata["tension_count"] = tension_count
        metadata["release_count"] = release_count
        metadata["tension_examples"] = tension_sentences[:3]
        metadata["release_examples"] = release_sentences[:3]

        # 判断情绪类型
        if has_tension and has_release:
            # 两种都有，需要判断主次
            if tension_count > release_count * 1.5:
                spring_type = "压弹簧为主"
                score = 85.0
                result = ValidationResult.GOOD
            elif release_count > tension_count * 1.5:
                spring_type = "放弹簧为主"
                score = 90.0
                result = ValidationResult.EXCELLENT
            else:
                spring_type = "压放结合"
                score = 95.0
                result = ValidationResult.EXCELLENT
                suggestions.append("压放结合得很好，情绪曲线饱满")
        elif has_tension:
            spring_type = "纯压弹簧"
            score = 70.0
            result = ValidationResult.PASS
            issues.append("只有压弹簧没有放弹簧，观众情绪无法释放")
            suggestions.append("建议在结尾加入反转或打脸情节")
        elif has_release:
            spring_type = "纯放弹簧"
            score = 60.0
            result = ValidationResult.PASS
            issues.append("只有放弹簧没有压弹簧，缺乏情绪积蓄")
            suggestions.append("建议在前段增加压抑、误会等情节铺垫")
        else:
            spring_type = "无明确情绪"
            score = 30.0
            result = ValidationResult.FAIL
            issues.append("未检测到明显的压弹簧或放弹簧情节")
            suggestions.append("请明确这一集是压弹簧还是放弹簧")
            suggestions.append("压弹簧：增加主角被压制、反派嚣张等情节")
            suggestions.append("放弹簧：增加反转、打脸、真相大白等情节")

        metadata["spring_type"] = spring_type

        # 检查情绪强度
        if tension_count + release_count < 3:
            issues.append("情绪表达不够强烈")
            suggestions.append("建议增加更多情绪化台词和情节")
            score = max(score - 10, 0)

        return ValidationReport(
            validator_name=self.validator_name,
            result=result,
            score=score,
            issues=issues,
            suggestions=suggestions,
            metadata=metadata
        )

    def _extract_content(self, script: Dict[str, Any]) -> str:
        """提取剧本内容"""
        if isinstance(script, str):
            return script
        if "content" in script:
            return script["content"]
        if "text" in script:
            return script["text"]
        if "script" in script:
            return script["script"]
        return ""

    def _find_sentences_with_keywords(self, content: str, keywords: List[str]) -> List[str]:
        """找出包含关键词的句子"""
        sentences = re.split(r'[。！？\n]', content)
        matched = []
        for sent in sentences:
            if any(kw in sent for kw in keywords):
                matched.append(sent.strip())
        return matched


class GoldenThreeSecondsValidator:
    """
    黄金三秒钩子验证器

    核心理论：
    开篇3秒（或前3句话）必须抓住观众注意力
    - 设计强烈的情感冲击
    - 设置悬念或冲突
    - 确保观众产生观看欲望
    """

    def __init__(self):
        self.validator_name = "黄金三秒钩子验证器"

        # 吸引人的关键词
        self.hook_keywords = [
            "突然", "意外", "震惊", "惊呆", "不敢相信", "竟然",
            "居然", "意想不到", "突发", "猛然", "瞬间",
            "悬念", "疑惑", "谜团", "疑问", "困惑",
            "等等", "慢着", "不对", "奇怪",
            "直接", "狠狠", "当头一棒", "晴天霹雳"
        ]

        # 冲突关键词
        self.conflict_keywords = [
            "争吵", "打", "杀", "斗", "威胁", "逼迫",
            "决裂", "背叛", "欺骗", "陷害", "羞辱",
            "对抗", "冲突", "对立", "争执"
        ]

        # 吸引力的判断标准
        self.attractiveness_indicators = {
            "suspense": ["突然", "意外", "震惊", "没想到"],
            "conflict": ["争吵", "威胁", "逼迫", "决裂"],
            "emotion": ["痛苦", "绝望", "愤怒", "崩溃"],
            "mystery": ["奇怪", "不对", "疑惑", "谜团"],
            "action": ["直接", "狠狠", "瞬间", "猛然"]
        }

    def validate(self, script: Dict[str, Any]) -> ValidationReport:
        """
        验证剧本开篇是否具有足够的吸引力

        Args:
            script: 剧本数据

        Returns:
            ValidationReport: 验证报告
        """
        issues = []
        suggestions = []
        metadata = {}

        # 提取内容
        content = self._extract_content(script)
        if not content:
            return ValidationReport(
                validator_name=self.validator_name,
                result=ValidationResult.FAIL,
                score=0.0,
                issues=["无法提取剧本内容"],
                suggestions=["请检查剧本数据格式"],
                metadata={}
            )

        # 提取开篇（前3句话或前100字）
        opening = self._extract_opening(content)
        metadata["opening_text"] = opening

        # 分析开篇特征
        hook_score = 0
        hook_types_found = []

        # 1. 悬念检测
        if any(kw in opening for kw in self.attractiveness_indicators["suspense"]):
            hook_score += 25
            hook_types_found.append("悬念")

        # 2. 冲突检测
        if any(kw in opening for kw in self.attractiveness_indicators["conflict"]):
            hook_score += 25
            hook_types_found.append("冲突")

        # 3. 情绪检测
        if any(kw in opening for kw in self.attractiveness_indicators["emotion"]):
            hook_score += 20
            hook_types_found.append("强烈情绪")

        # 4. 神秘感检测
        if any(kw in opening for kw in self.attractiveness_indicators["mystery"]):
            hook_score += 15
            hook_types_found.append("神秘感")

        # 5. 行动力检测
        if any(kw in opening for kw in self.attractiveness_indicators["action"]):
            hook_score += 15
            hook_types_found.append("强动作")

        metadata["hook_types_found"] = hook_types_found
        metadata["hook_score"] = hook_score

        # 判断结果
        if hook_score >= 80:
            result = ValidationResult.EXCELLENT
            score = hook_score
        elif hook_score >= 60:
            result = ValidationResult.GOOD
            score = hook_score
        elif hook_score >= 40:
            result = ValidationResult.PASS
            score = hook_score
            issues.append("开篇吸引力一般，需要加强")
        else:
            result = ValidationResult.FAIL
            score = hook_score
            issues.append("开篇缺乏吸引力，无法在3秒内抓住观众")

        # 生成改进建议
        if not hook_types_found:
            suggestions.append("建议在开篇加入以下元素之一：")
            suggestions.append("1. 悬念：使用'突然'、'意外'等词汇制造意外感")
            suggestions.append("2. 冲突：直接进入人物矛盾或对抗")
            suggestions.append("3. 情绪：展现角色的强烈情感状态")
            suggestions.append("4. 神秘：设置疑问或谜团")
            suggestions.append("5. 行动：用强烈的动作描述开场")
        elif len(hook_types_found) == 1:
            suggestions.append(f"当前只有'{hook_types_found[0]}'元素，建议增加更多吸引力")

        return ValidationReport(
            validator_name=self.validator_name,
            result=result,
            score=score,
            issues=issues,
            suggestions=suggestions,
            metadata=metadata
        )

    def _extract_content(self, script: Dict[str, Any]) -> str:
        """提取剧本内容"""
        if isinstance(script, str):
            return script
        if "content" in script:
            return script["content"]
        if "text" in script:
            return script["text"]
        if "script" in script:
            return script["script"]
        return ""

    def _extract_opening(self, content: str, max_sentences: int = 3) -> str:
        """提取开篇部分"""
        # 按句子分割
        sentences = re.split(r'[。！？\n]', content)
        # 取前N句
        opening_sentences = [s.strip() for s in sentences[:max_sentences] if s.strip()]
        return "。".join(opening_sentences)


class FiveElementsValidator:
    """
    故事五元素验证器

    核心理论：
    完整的故事应包含五元素：
    1. 题材类型与创意提炼
    2. 故事梗概（800-2500字）
    3. 人物小传（至少8个人物）
    4. 人物关系（至少12对关系）
    5. 大情节点（按发展阶段排列）
    """

    def __init__(self):
        self.validator_name = "故事五元素验证器"

    def validate(self, analysis_result: Dict[str, Any]) -> ValidationReport:
        """
        验证故事分析是否包含完整的五元素

        Args:
            analysis_result: 故事分析结果

        Returns:
            ValidationReport: 验证报告
        """
        issues = []
        suggestions = []
        metadata = {}

        # 检查每个元素
        elements_status = {}
        score = 0
        max_score = 100

        # 1. 题材类型
        if "story_type" in analysis_result or "题材" in str(analysis_result):
            elements_status["题材类型"] = True
            score += 20
        else:
            elements_status["题材类型"] = False
            issues.append("缺少题材类型分析")

        # 2. 故事梗概
        story_summary = self._extract_element(analysis_result, ["story_summary", "summary", "梗概"])
        if story_summary and len(story_summary) >= 300:
            elements_status["故事梗概"] = True
            score += 20
        else:
            elements_status["故事梗概"] = False
            issues.append("故事梗概过短或缺失（建议800-2500字）")

        # 3. 人物小传
        characters = self._extract_element(analysis_result, ["characters", "character_profiles", "人物"])
        if characters:
            # 统计人物数量
            char_count = self._count_characters(characters)
            if char_count >= 8:
                elements_status["人物小传"] = True
                score += 20
            else:
                elements_status["人物小传"] = False
                issues.append(f"人物数量不足（当前{char_count}个，建议至少8个）")
        else:
            elements_status["人物小传"] = False
            issues.append("缺少人物小传")

        # 4. 人物关系
        relationships = self._extract_element(analysis_result, ["relationships", "character_relationships", "人物关系"])
        if relationships:
            # 统计关系对数
            rel_count = self._count_relationships(relationships)
            if rel_count >= 12:
                elements_status["人物关系"] = True
                score += 20
            else:
                elements_status["人物关系"] = False
                issues.append(f"人物关系对数不足（当前{rel_count}对，建议至少12对）")
        else:
            elements_status["人物关系"] = False
            issues.append("缺少人物关系分析")

        # 5. 大情节点
        plot_points = self._extract_element(analysis_result, ["plot_points", "major_plot_points", "情节点"])
        if plot_points:
            # 统计情节要点数量
            point_count = self._count_plot_points(plot_points)
            if point_count >= 5:
                elements_status["大情节点"] = True
                score += 20
            else:
                elements_status["大情节点"] = False
                issues.append(f"情节点数量不足（当前{point_count}个，建议至少5个）")
        else:
            elements_status["大情节点"] = False
            issues.append("缺少大情节点分析")

        metadata["elements_status"] = elements_status
        metadata["completion_rate"] = sum(elements_status.values()) / 5 * 100

        # 判断结果
        completion_rate = sum(elements_status.values()) / 5
        if completion_rate >= 1.0:
            result = ValidationResult.EXCELLENT
        elif completion_rate >= 0.8:
            result = ValidationResult.GOOD
        elif completion_rate >= 0.6:
            result = ValidationResult.PASS
        else:
            result = ValidationResult.FAIL

        # 生成建议
        if result != ValidationResult.EXCELLENT:
            missing_elements = [name for name, status in elements_status.items() if not status]
            if missing_elements:
                suggestions.append(f"需要补充以下元素：{', '.join(missing_elements)}")

        return ValidationReport(
            validator_name=self.validator_name,
            result=result,
            score=float(score),
            issues=issues,
            suggestions=suggestions,
            metadata=metadata
        )

    def _extract_element(self, data: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """提取指定元素"""
        for key in keys:
            if key in data:
                value = data[key]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict):
                    return str(value)
                elif isinstance(value, list):
                    return "\n".join(str(item) for item in value)
        return None

    def _count_characters(self, characters_text: str) -> int:
        """统计人物数量"""
        # 简单统计：按行或按特定标记分割
        lines = characters_text.split("\n")
        count = 0
        for line in lines:
            # 查找包含角色名的行
            if re.match(r'^\s*[-\d]+\s*[\.、)]?\s*\w+', line):
                count += 1
        return max(count, len(re.findall(r'人物|角色|character', characters_text, re.I)))

    def _count_relationships(self, relationships_text: str) -> int:
        """统计关系对数"""
        # 查找关系描述
        relationship_patterns = [
            r'\w+[-—→与和]\w+',  # A- B, A与B
            r'是.{0,20}的',         # A是B的...
            r'父子|母女|夫妻|兄弟|姐妹|恋人|朋友|敌人|对手'
        ]
        count = 0
        for pattern in relationship_patterns:
            count += len(re.findall(pattern, relationships_text))
        return max(count, len(re.findall(r'关系|relationship', relationships_text, re.I)))

    def _count_plot_points(self, plot_text: str) -> int:
        """统计情节要点数量"""
        # 按编号或标记分割
        patterns = [
            r'^\s*[-\d]+\s*[\.、)]',
            r'第[一二三四五六七八九十\d]+[章节幕集]',
            r'情节点|情节'
        ]
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, plot_text, re.M)
            count += len(matches)
        return max(count, len(re.findall(r'\n+', plot_text)) + 1)


class BusinessValidatorSuite:
    """
    业务规则验证器套件

    整合所有业务规则验证器，提供统一的验证接口
    """

    def __init__(self):
        self.emotional_spring_validator = EmotionalSpringValidator()
        self.golden_three_seconds_validator = GoldenThreeSecondsValidator()
        self.five_elements_validator = FiveElementsValidator()

    def validate_all(
        self,
        script: Dict[str, Any],
        analysis_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ValidationReport]:
        """
        执行所有验证

        Args:
            script: 剧本数据
            analysis_result: 故事分析结果（可选，用于五元素验证）

        Returns:
            Dict[str, ValidationReport]: 各验证器的报告
        """
        results = {}

        # 情绪弹簧验证
        results["emotional_spring"] = self.emotional_spring_validator.validate(script)

        # 黄金三秒验证
        results["golden_three_seconds"] = self.golden_three_seconds_validator.validate(script)

        # 五元素验证（如果有分析结果）
        if analysis_result:
            results["five_elements"] = self.five_elements_validator.validate(analysis_result)

        return results

    def get_overall_score(self, reports: Dict[str, ValidationReport]) -> float:
        """获取总体评分"""
        if not reports:
            return 0.0
        return sum(report.score for report in reports.values()) / len(reports)

    def get_overall_result(self, reports: Dict[str, ValidationReport]) -> ValidationResult:
        """获取总体结果"""
        if not reports:
            return ValidationResult.FAIL

        # 如果有任何一个FAIL，总体为FAIL
        if any(r.result == ValidationResult.FAIL for r in reports.values()):
            return ValidationResult.FAIL

        # 如果所有都是EXCELLENT或GOOD
        if all(r.result in [ValidationResult.EXCELLENT, ValidationResult.GOOD] for r in reports.values()):
            return ValidationResult.GOOD

        return ValidationResult.PASS

    def generate_summary_report(self, reports: Dict[str, ValidationReport]) -> str:
        """生成汇总报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("业务规则验证汇总报告")
        lines.append("=" * 60)

        overall_score = self.get_overall_score(reports)
        overall_result = self.get_overall_result(reports)

        lines.append(f"\n总体评分: {overall_score:.1f}/100")
        lines.append(f"总体结果: {overall_result.value.upper()}")
        lines.append("")

        for name, report in reports.items():
            lines.append(f"\n【{report.validator_name}】")
            lines.append(f"评分: {report.score:.1f}/100")
            lines.append(f"结果: {report.result.value.upper()}")

            if report.issues:
                lines.append("问题:")
                for issue in report.issues:
                    lines.append(f"  - {issue}")

            if report.suggestions:
                lines.append("建议:")
                for suggestion in report.suggestions:
                    lines.append(f"  + {suggestion}")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)


# 便捷函数
def validate_script(
    script: Dict[str, Any],
    analysis_result: Optional[Dict[str, Any]] = None,
    return_summary: bool = True
) -> Any:
    """
    验证剧本的业务规则符合性

    Args:
        script: 剧本数据
        analysis_result: 故事分析结果（可选）
        return_summary: 是否返回汇总报告文本

    Returns:
        如果 return_summary=True，返回报告文本
        否则返回验证报告字典
    """
    suite = BusinessValidatorSuite()
    reports = suite.validate_all(script, analysis_result)

    if return_summary:
        return suite.generate_summary_report(reports)
    else:
        return {name: report.to_dict() for name, report in reports.items()}

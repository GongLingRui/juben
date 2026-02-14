"""
竖屏短剧评估Agent
 专注于故事文本评估和打分

业务处理逻辑：
1. 输入处理：接收竖屏短剧故事文本，支持多种输入格式
2. 深度评估：对故事文本进行深度评估与打分
3. 多维度分析：从核心爽点、故事类型、人物设定等维度进行专业分析
4. 市场竞争力分析：分析故事在竖屏短剧市场的竞争力
5. 开发价值评估：评估故事的影视开发价值和潜力
6. 优化建议：提供具体的优化建议和改进方向
7. 文件处理：支持文件内容提取和处理
8. 输出格式化：返回结构化的评估结果和建议
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

try:
    from .base_juben_agent import BaseJubenAgent
    from ..utils.intent_recognition import IntentRecognizer
    from ..utils.url_extractor import URLExtractor
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.base_juben_agent import BaseJubenAgent
    from utils.intent_recognition import IntentRecognizer
    from utils.url_extractor import URLExtractor


# ==================== 数据模型 ====================

class ScoreCategory(Enum):
    """评测维度"""
    LOGIC = "logic"
    CHARACTER = "character"
    HOOK = "hook"
    DIALOGUE = "dialogue"
    PACING = "pacing"
    EMOTION = "emotion"
    CREATIVITY = "creativity"
    COMMERCIAL = "commercial"


@dataclass
class EvaluationResult:
    """评测结果"""
    overall_score: float
    scores: Dict[str, float]
    reasons: Dict[str, str]
    overall_reason: str
    suggestions: List[str]
    strengths: List[str]
    weaknesses: List[str]
    commercial_potential: float
    target_audience_match: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ComparisonResult:
    """对比评测结果"""
    version_a: Dict[str, Any]
    version_b: Dict[str, Any]
    winner: str  # "A", "B", "TIE"
    score_delta: Dict[str, float]
    overall_delta: float
    comparison_summary: str
    recommendation: str
    compared_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class ShortDramaEvaluationAgent(BaseJubenAgent):
    """
    竖屏短剧评估Agent
    
    功能：
    1. 故事文本深度评估与打分
    2. 多维度专业分析（核心爽点、故事类型、人物设定等）
    3. 市场竞争力分析
    4. 开发价值评估
    5. 优化建议提供
    6. 文件内容提取和处理
    """
    
    def __init__(self):
        super().__init__("short_drama_evaluation", model_provider="zhipu")
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化专用组件
        self.intent_recognizer = IntentRecognizer()
        self.url_extractor = URLExtractor()
        
        # 评估维度配置
        self.evaluation_dimensions = {
            "core_satisfaction": "核心爽点",
            "story_type": "故事类型", 
            "character_setting": "人物设定",
            "character_relationship": "人物关系",
            "plot_bridge": "情节桥段"
        }
        
        # 评分标准
        self.scoring_criteria = {
            "excellent": {"min": 8.5, "max": 10.0, "description": "优秀，可直接开发"},
            "potential": {"min": 8.0, "max": 8.4, "description": "有潜力，需修改后开发"},
            "average": {"min": 7.5, "max": 7.9, "description": "一般，需大幅修改"},
            "poor": {"min": 0.0, "max": 7.4, "description": "较差，开发价值低"}
        }
        
        self.logger.info("竖屏短剧评估Agent初始化完成")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理竖屏短剧评估请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            user_input = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            self.logger.info(f"开始处理短剧评估请求: {user_input}")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system", "📊 开始分析您的短剧评估需求...")
            
            # 1. 意图识别
            yield await self._emit_event("system", "🔍 正在分析您的评估意图...")
            intent_result = await self._analyze_intent(user_input)
            yield await self._emit_event("system", f"✅ 意图识别完成: {intent_result['intent']}")
            
            # 2. URL提取和内容获取
            urls = self.url_extractor.extract_urls(user_input)
            url_contents = []
            if urls:
                yield await self._emit_event("system", f"📎 发现{len(urls)}个链接，正在提取内容...")
                url_contents = await self._extract_url_contents(urls)
                yield await self._emit_event("system", "✅ URL内容提取完成")
            
            # 3. 信息收集
            search_results = {}
            knowledge_results = {}
            
            # 网络搜索
            if intent_result.get("needs_web_search", False):
                yield await self._emit_event("system", "🌐 正在搜索最新市场信息...")
                search_query = self._build_search_query(user_input, intent_result)
                search_results = await self._search_web(search_query)
                yield await self._emit_event("system", "✅ 网络搜索完成")
            
            # 知识库检索
            if intent_result.get("needs_knowledge_base", False):
                yield await self._emit_event("system", "📚 正在检索高能短剧库...")
                knowledge_query = self._build_knowledge_query(user_input, intent_result)
                knowledge_results = await self._search_knowledge_base(knowledge_query)
                yield await self._emit_event("system", "✅ 知识库检索完成")
            
            # 4. 构建上下文
            context_data = {
                "user_input": user_input,
                "intent": intent_result,
                "search_results": search_results,
                "knowledge_results": knowledge_results,
                "url_contents": url_contents,
                "user_id": user_id,
                "session_id": session_id,
                "history": context.get("history", []) if context else []
            }
            
            # 5. 生成评估报告
            yield await self._emit_event("system", "📋 正在生成专业的评估报告...")
            
            async for chunk in self._generate_evaluation_response(context_data):
                yield chunk
            
            # 6. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
            # 7. 发送完成事件
            yield await self._emit_event("system", "🎯 短剧评估报告生成完成！")
            
        except Exception as e:
            self.logger.error(f"处理请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户评估意图"""
        try:
            # 评估相关的意图识别
            intent_result = await self.intent_recognizer.analyze(user_input)
            
            # 根据评估需求调整意图
            if "评估" in user_input or "打分" in user_input or "分析" in user_input:
                intent_result.update({
                    "intent": "story_evaluation",
                    "needs_knowledge_base": True,
                    "needs_web_search": True
                })
            elif "爽点" in user_input or "核心" in user_input:
                intent_result.update({
                    "intent": "core_satisfaction_analysis",
                    "needs_knowledge_base": True,
                    "needs_web_search": False
                })
            elif "人物" in user_input or "角色" in user_input:
                intent_result.update({
                    "intent": "character_analysis",
                    "needs_knowledge_base": True,
                    "needs_web_search": False
                })
            elif "情节" in user_input or "剧情" in user_input:
                intent_result.update({
                    "intent": "plot_analysis",
                    "needs_knowledge_base": True,
                    "needs_web_search": False
                })
            elif "市场" in user_input or "竞品" in user_input:
                intent_result.update({
                    "intent": "market_analysis",
                    "needs_knowledge_base": True,
                    "needs_web_search": True
                })
            
            return intent_result
        except Exception as e:
            self.logger.error(f"意图识别失败: {e}")
            return {
                "intent": "story_evaluation",
                "confidence": 0.5,
                "needs_web_search": True,
                "needs_knowledge_base": True
            }
    
    async def _extract_url_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """提取URL内容"""
        contents = []
        for url in urls:
            try:
                content = await self.url_extractor.extract_content(url)
                contents.append(content)
            except Exception as e:
                self.logger.error(f"提取URL内容失败 {url}: {e}")
                contents.append({
                    "url": url,
                    "success": False,
                    "error": str(e)
                })
        return contents
    
    def _build_search_query(self, user_input: str, intent_result: Dict[str, Any]) -> str:
        """构建搜索查询"""
        intent = intent_result.get("intent", "story_evaluation")
        
        if intent == "story_evaluation":
            return f"{user_input} 竖屏短剧 市场分析 爆款案例"
        elif intent == "core_satisfaction_analysis":
            return f"{user_input} 核心爽点 情绪设计"
        elif intent == "character_analysis":
            return f"{user_input} 人物设定 角色塑造"
        elif intent == "plot_analysis":
            return f"{user_input} 情节设计 剧情结构"
        elif intent == "market_analysis":
            return f"{user_input} 竖屏短剧市场 竞品分析"
        else:
            return user_input
    
    def _build_knowledge_query(self, user_input: str, intent_result: Dict[str, Any]) -> str:
        """构建知识库查询"""
        intent = intent_result.get("intent", "story_evaluation")
        
        if intent == "story_evaluation":
            return f"{user_input} 评估标准 评分体系"
        elif intent == "core_satisfaction_analysis":
            return f"{user_input} 爽点设计 情绪控制"
        elif intent == "character_analysis":
            return f"{user_input} 人物设定 角色功能"
        elif intent == "plot_analysis":
            return f"{user_input} 情节桥段 剧情节奏"
        elif intent == "market_analysis":
            return f"{user_input} 市场趋势 爆款特征"
        else:
            return user_input
    
    async def _generate_evaluation_response(self, context_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """生成评估响应"""
        try:
            # 构建提示词
            prompt = self._build_evaluation_prompt(context_data)
            
            # 构建消息
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 获取用户ID和会话ID
            user_id = context_data.get("user_id", "unknown")
            session_id = context_data.get("session_id", "unknown")
            
            # 流式调用LLM（带追踪）
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成评估响应失败: {e}")
            yield await self._emit_event("error", f"生成响应失败: {str(e)}")
    
    def _build_evaluation_prompt(self, context_data: Dict[str, Any]) -> str:
        """
        构建评估提示词（健壮版）

        说明：
        - 对 context_data 中的各字段做类型检查，避免出现如 slice(None, 3, None) 这类错误；
        - 任意一处上下文结构异常时，会记录日志并退化为最小可用 Prompt，而不是抛出异常阻断评估。
        """
        try:
            user_input = context_data.get("user_input", "")
            intent = context_data.get("intent") or {}
            if not isinstance(intent, dict):
                intent = {}

            search_results = context_data.get("search_results") or {}
            if not isinstance(search_results, dict):
                search_results = {}

            knowledge_results = context_data.get("knowledge_results") or {}
            if not isinstance(knowledge_results, dict):
                knowledge_results = {}

            url_contents = context_data.get("url_contents") or []
            if not isinstance(url_contents, list):
                url_contents = []

            history = context_data.get("history") or []

            # 构建用户查询部分
            user_query_section = f"""
## 用户评估需求
{user_input}

## 需求分析
- 评估类型: {intent.get('intent', 'unknown')}
- 置信度: {intent.get('confidence', 0)}

## 互联网搜索信息
"""

            # 添加搜索结果
            results_list = search_results.get("results") if search_results.get("success") else None
            if isinstance(results_list, list) and results_list:
                user_query_section += "\n### 最新市场信息\n"
                for i, result in enumerate(results_list[:3], 1):
                    if not isinstance(result, dict):
                        continue
                    user_query_section += f"{i}. {result.get('title', '')}\n"
                    content_snippet = str(result.get("content", ""))[:200]
                    if content_snippet:
                        user_query_section += f"   {content_snippet}...\n"

            # 添加知识库结果
            kb_list = knowledge_results.get("results") if knowledge_results.get("success") else None
            if isinstance(kb_list, list) and kb_list:
                user_query_section += "\n### 高能短剧库语义搜索结果\n"
                for i, result in enumerate(kb_list[:3], 1):
                    if not isinstance(result, dict):
                        continue
                    user_query_section += f"{i}. {result.get('title', '')}\n"
                    content_snippet = str(result.get("content", ""))[:200]
                    if content_snippet:
                        user_query_section += f"   {content_snippet}...\n"

            # 添加URL内容
            if url_contents:
                user_query_section += "\n### 用户上传文件内容\n"
                for i, content in enumerate(url_contents[:2], 1):
                    if not isinstance(content, dict):
                        continue
                    if content.get("success"):
                        user_query_section += f"{i}. {content.get('url', '')}\n"
                        content_snippet = str(content.get("content", ""))[:200]
                        if content_snippet:
                            user_query_section += f"   {content_snippet}...\n"

            # 添加对话历史（兼容多种类型，避免切片错误）
            if history:
                try:
                    if isinstance(history, list):
                        recent_history = history[-3:]  # 只显示最近3条
                        if recent_history:
                            user_query_section += "\n### 用户对话历史\n"
                            for i, hist in enumerate(recent_history, 1):
                                user_query_section += f"{i}. {hist}\n"
                except Exception as e:
                    # 历史记录异常不影响主流程
                    self.logger.warning(f"处理历史对话时出错，已忽略: {e}")

            # 将用户查询部分添加到系统提示词后面
            full_prompt = f"{self.system_prompt}\n\n{user_query_section}"

            return full_prompt

        except Exception as e:
            # 任何构建 Prompt 的异常都不应该阻塞评估，退化为简单 Prompt
            self.logger.error(f"构建评估提示词失败，使用降级Prompt: {e}")
            user_input = context_data.get("user_input", "")
            return f"{self.system_prompt}\n\n请根据以下内容生成短剧专业评估报告：\n\n{user_input}"
    
    def extract_scores_from_response(self, response_text: str) -> Dict[str, float]:
        """从响应中提取评分"""
        scores = {}
        
        # 匹配评分模式
        score_pattern = r'(\w+)[：:]\s*评分[：:]\s*([0-9.]+)'
        matches = re.findall(score_pattern, response_text)
        
        for dimension, score_str in matches:
            try:
                score = float(score_str)
                if 0 <= score <= 10:
                    scores[dimension] = score
            except ValueError:
                continue
        
        return scores
    
    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算综合评分"""
        if not scores:
            return 0.0
        
        # 各维度权重
        weights = {
            "核心爽点": 0.3,
            "故事类型": 0.2,
            "人物设定": 0.2,
            "人物关系": 0.15,
            "情节桥段": 0.15
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, score in scores.items():
            weight = weights.get(dimension, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def get_score_level(self, score: float) -> str:
        """获取评分等级"""
        if score >= 8.5:
            return "excellent"
        elif score >= 8.0:
            return "potential"
        elif score >= 7.5:
            return "average"
        else:
            return "poor"

    # ==================== 🆕 结构化评测方法 ====================

    async def evaluate_content(
        self,
        content: str,
        evaluation_type: str = "full",
        target_audience: str = "大众",
        metadata: Dict[str, Any] = None
    ) -> EvaluationResult:
        """
        评测剧本内容（结构化评分）

        Args:
            content: 剧本内容
            evaluation_type: 评测类型 (full=全面, quick=快速)
            target_audience: 目标受众
            metadata: 元数据

        Returns:
            EvaluationResult: 包含 scores, reasons, suggestions 的评测结果
        """
        try:
            # 构建结构化评测提示词
            eval_prompt = self._build_structured_evaluation_prompt(
                content=content,
                evaluation_type=evaluation_type,
                target_audience=target_audience
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": eval_prompt}
            ]

            # 调用LLM进行评测
            response = await self._call_llm(messages, user_id="system", session_id="evaluation")

            # 解析评测结果
            result = self._parse_structured_evaluation_response(response, metadata or {})

            # 保存评测结果
            await self._save_evaluation_result(result)

            return result

        except Exception as e:
            self.logger.error(f"结构化评测失败: {e}")
            # 返回默认评测结果
            return self._create_default_evaluation(content)

    def _build_structured_evaluation_prompt(
        self,
        content: str,
        evaluation_type: str,
        target_audience: str
    ) -> str:
        """构建结构化评测提示词"""
        categories_desc = "\n".join([
            f"- **logic (逻辑性)**: 情节发展是否合理、前后是否自洽",
            f"- **character (人设一致性)**: 角色性格、行为是否符合设定",
            f"- **hook (爆点设计)**: 开篇是否有吸引力、是否有情绪爆点",
            f"- **dialogue (对话质量)**: 对白是否生动、符合角色特点",
            f"- **pacing (节奏把控)**: 节奏是否紧凑、是否有拖沓",
            f"- **emotion (情感张力)**: 情感表达是否到位、是否有感染力",
            f"- **creativity (创意新颖性)**: 是否有创新、是否避免套路化",
            f"- **commercial (商业价值)**: 是否符合市场需求、是否有传播潜力"
        ])

        if evaluation_type == "quick":
            quick_note = "\n【快速评测模式】请给出简洁但准确的评分和建议。"
        else:
            quick_note = "\n【全面评测模式】请给出详细的分析和具体的改进建议。"

        prompt = f"""
作为资深剧本监制，请对以下短剧剧本进行专业评测：

【目标受众】{target_audience}

【评测维度】
{categories_desc}

【待评测剧本】
{content}

{quick_note}

请严格按照以下JSON格式返回评测结果：
{{
  "scores": {{
    "logic": 评分(1-10),
    "character": 评分(1-10),
    "hook": 评分(1-10),
    "dialogue": 评分(1-10),
    "pacing": 评分(1-10),
    "emotion": 评分(1-10),
    "creativity": 评分(1-10),
    "commercial": 评分(1-10)
  }},
  "reasons": {{
    "logic": "逻辑性评分理由",
    "character": "人设一致性评分理由",
    "hook": "爆点设计评分理由",
    "dialogue": "对话质量评分理由",
    "pacing": "节奏把控评分理由",
    "emotion": "情感张力评分理由",
    "creativity": "创意新颖性评分理由",
    "commercial": "商业价值评分理由"
  }},
  "overall_score": 总体评分(1-10, 可为小数),
  "overall_reason": "总体评价（200字以内）",
  "strengths": ["优点1", "优点2", "优点3"],
  "weaknesses": ["不足1", "不足2", "不足3"],
  "suggestions": ["建议1", "建议2", "建议3"],
  "commercial_potential": 商业潜力评分(1-10),
  "target_audience_match": 受众匹配度评分(1-10)
}}

请只返回JSON，不要包含其他说明文字。
"""
        return prompt

    def _parse_structured_evaluation_response(
        self,
        response: str,
        metadata: Dict[str, Any]
    ) -> EvaluationResult:
        """解析结构化评测响应"""
        try:
            # 尝试提取JSON
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            data = json.loads(response)

            # 计算总体评分（如果未提供）
            if "overall_score" not in data:
                scores = data.get("scores", {})
                weights = {
                    "logic": 1.0,
                    "character": 1.2,
                    "hook": 1.5,
                    "dialogue": 1.0,
                    "pacing": 1.1,
                    "emotion": 1.2,
                    "creativity": 0.8,
                    "commercial": 1.3
                }
                overall_score = sum(
                    scores.get(cat, 5) * weights.get(cat, 1.0)
                    for cat in weights.keys()
                ) / sum(weights.values())
                data["overall_score"] = round(overall_score, 1)

            result = EvaluationResult(
                overall_score=data.get("overall_score", 0.0),
                scores=data.get("scores", {}),
                reasons=data.get("reasons", {}),
                overall_reason=data.get("overall_reason", ""),
                suggestions=data.get("suggestions", []),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                commercial_potential=data.get("commercial_potential", 0.0),
                target_audience_match=data.get("target_audience_match", 0.0),
                metadata=metadata
            )

            self.logger.info(f"✅ 结构化评测完成: 总体评分 {result.overall_score}")
            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return self._create_default_evaluation("")
        except Exception as e:
            self.logger.error(f"解析评测响应失败: {e}")
            return self._create_default_evaluation("")

    def _create_default_evaluation(self, content: str) -> EvaluationResult:
        """创建默认评测结果"""
        return EvaluationResult(
            overall_score=5.0,
            scores={cat.value: 5.0 for cat in ScoreCategory},
            reasons={cat.value: "未能完成评测" for cat in ScoreCategory},
            overall_reason="评测系统出现错误，无法给出准确评分",
            suggestions=["请稍后重试", "检查剧本格式是否正确"],
            strengths=[],
            weaknesses=[],
            commercial_potential=5.0,
            target_audience_match=5.0,
            metadata={"error": "default_evaluation"}
        )

    # ==================== 🆕 对比评测方法 ====================

    async def evaluate_comparison(
        self,
        content_a: str,
        content_b: str,
        target_audience: str = "大众"
    ) -> ComparisonResult:
        """
        对比评测两个版本

        Args:
            content_a: 版本A内容
            content_b: 版本B内容
            target_audience: 目标受众

        Returns:
            ComparisonResult: 对比结果
        """
        try:
            self.logger.info("🔄 开始对比评测...")

            # 并发评测两个版本
            result_a, result_b = await asyncio.gather(
                self.evaluate_content(content_a, "quick", target_audience, {"version": "A"}),
                self.evaluate_content(content_b, "quick", target_audience, {"version": "B"})
            )

            # 计算分差
            score_delta = {}
            for category in result_a.scores.keys():
                if category in result_b.scores:
                    score_delta[category] = result_b.scores[category] - result_a.scores[category]

            overall_delta = result_b.overall_score - result_a.overall_score

            # 判断胜者
            if overall_delta > 0.5:
                winner = "B"
            elif overall_delta < -0.5:
                winner = "A"
            else:
                winner = "TIE"

            # 生成对比总结
            comparison_summary = await self._generate_comparison_summary(
                result_a, result_b, score_delta, overall_delta, winner
            )

            # 生成推荐
            recommendation = self._generate_recommendation(
                result_a, result_b, winner, overall_delta
            )

            comparison_result = ComparisonResult(
                version_a=result_a.to_dict(),
                version_b=result_b.to_dict(),
                winner=winner,
                score_delta=score_delta,
                overall_delta=overall_delta,
                comparison_summary=comparison_summary,
                recommendation=recommendation
            )

            # 保存对比结果
            await self._save_comparison_result(comparison_result)

            return comparison_result

        except Exception as e:
            self.logger.error(f"对比评测失败: {e}")
            raise

    async def _generate_comparison_summary(
        self,
        result_a: EvaluationResult,
        result_b: EvaluationResult,
        score_delta: Dict[str, float],
        overall_delta: float,
        winner: str
    ) -> str:
        """生成对比总结"""
        # 找出最大优势和最大劣势的差异
        max_advantage = max(score_delta.items(), key=lambda x: x[1], default=("N/A", 0))
        max_disadvantage = min(score_delta.items(), key=lambda x: x[1], default=("N/A", 0))

        summary_parts = [
            f"## 对比评测总结",
            f"",
            f"**总体评分**: 版本A {result_a.overall_score:.1f}分 vs 版本B {result_b.overall_score:.1f}分",
            f"**分差**: {abs(overall_delta):.1f}分",
            f"**胜出**: 版本{winner if winner != 'TIE' else '平局'}",
            f"",
            f"**主要差异**:"
        ]

        category_names = {
            "logic": "逻辑性",
            "character": "人设一致性",
            "hook": "爆点设计",
            "dialogue": "对话质量",
            "pacing": "节奏把控",
            "emotion": "情感张力",
            "creativity": "创意新颖性",
            "commercial": "商业价值"
        }

        if max_advantage[0] != "N/A" and max_advantage[1] > 1:
            summary_parts.append(f"- 版本B 在「{category_names.get(max_advantage[0], max_advantage[0])}」上领先 {max_advantage[1]:.1f} 分")

        if max_disadvantage[0] != "N/A" and max_disadvantage[1] < -1:
            summary_parts.append(f"- 版本A 在「{category_names.get(max_disadvantage[0], max_disadvantage[0])}」上领先 {abs(max_disadvantage[1]):.1f} 分")

        summary_parts.append(f"")
        summary_parts.append(f"**版本A特点**: {', '.join(result_a.strengths[:3]) if result_a.strengths else '无明显优势'}")
        summary_parts.append(f"**版本B特点**: {', '.join(result_b.strengths[:3]) if result_b.strengths else '无明显特点'}")

        return "\n".join(summary_parts)

    def _generate_recommendation(
        self,
        result_a: EvaluationResult,
        result_b: EvaluationResult,
        winner: str,
        overall_delta: float
    ) -> str:
        """生成推荐意见"""
        if winner == "A":
            base = f"推荐使用版本A。"
            if overall_delta > 2:
                base += f" 版本A在各方面表现显著优于版本B（领先{overall_delta:.1f}分）。"
            else:
                base += f" 版本A略优于版本B，但差异不大（领先{overall_delta:.1f}分）。"

            if result_a.suggestions:
                base += f"\n\n建议优化：{result_a.suggestions[0]}"

        elif winner == "B":
            base = f"推荐使用版本B。"
            if overall_delta > 2:
                base += f" 版本B在各方面表现显著优于版本A（领先{overall_delta:.1f}分）。"
            else:
                base += f" 版本B略优于版本A，但差异不大（领先{overall_delta:.1f}分）。"

            if result_b.suggestions:
                base += f"\n\n建议优化：{result_b.suggestions[0]}"
        else:
            base = "两个版本评分相近，建议根据具体需求选择："
            base += f"\n\n- 版本A优势：{', '.join(result_a.strengths[:2]) if result_a.strengths else '无明显特点'}"
            base += f"\n- 版本B优势：{', '.join(result_b.strengths[:2]) if result_b.strengths else '无明显特点'}"

        return base

    # ==================== 🆕 持久化方法 ====================

    async def _save_evaluation_result(self, result: EvaluationResult) -> bool:
        """保存评测结果到 ProjectFile"""
        try:
            from utils.storage_manager import get_project_file_manager
            import uuid

            file_manager = get_project_file_manager()

            # 生成评测记录ID
            evaluation_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

            # 保存评测数据
            evaluation_data = {
                "evaluation_id": evaluation_id,
                "result": result.to_dict(),
                "created_at": datetime.now().isoformat()
            }

            # 使用 ProjectFile 保存
            file_id = await file_manager.save_project_file(
                project_id="evaluation_history",
                file_type="evaluation",
                content=json.dumps(evaluation_data, ensure_ascii=False, indent=2),
                filename=f"{evaluation_id}.json",
                metadata={"evaluation_id": evaluation_id}
            )

            self.logger.info(f"💾 评测结果已保存: {evaluation_id} ({file_id})")
            return True

        except Exception as e:
            self.logger.warning(f"保存评测结果失败: {e}")
            return False

    async def _save_comparison_result(self, result: ComparisonResult) -> bool:
        """保存对比评测结果到 ProjectFile"""
        try:
            from utils.storage_manager import get_project_file_manager
            import uuid

            file_manager = get_project_file_manager()

            # 生成对比评测记录ID
            comparison_id = f"compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

            # 保存对比数据
            comparison_data = {
                "comparison_id": comparison_id,
                "result": result.to_dict(),
                "created_at": datetime.now().isoformat()
            }

            # 使用 ProjectFile 保存
            file_id = await file_manager.save_project_file(
                project_id="comparison_history",
                file_type="comparison",
                content=json.dumps(comparison_data, ensure_ascii=False, indent=2),
                filename=f"{comparison_id}.json",
                metadata={"comparison_id": comparison_id}
            )

            self.logger.info(f"💾 对比评测结果已保存: {comparison_id} ({file_id})")
            return True

        except Exception as e:
            self.logger.warning(f"保存对比评测结果失败: {e}")
            return False

    async def get_evaluation_history(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取评测历史记录

        Args:
            limit: 返回记录数量

        Returns:
            List[Dict]: 评测历史列表
        """
        try:
            from utils.storage_manager import get_project_file_manager
            file_manager = get_project_file_manager()

            # 获取评测历史文件
            files = await file_manager.list_project_files("evaluation_history", limit=limit)

            history = []
            for file_info in files:
                content = await file_manager.get_project_file_content(file_info["file_id"])
                if content:
                    try:
                        data = json.loads(content)
                        history.append(data)
                    except json.JSONDecodeError:
                        continue

            return sorted(history, key=lambda x: x.get("created_at", ""), reverse=True)

        except Exception as e:
            self.logger.error(f"获取评测历史失败: {e}")
            return []

    # ==================== 🆕 便捷方法 ====================

    async def quick_eval(self, content: str) -> float:
        """快速评测，返回总体评分"""
        result = await self.evaluate_content(content, "quick")
        return result.overall_score

    async def batch_eval(self, contents: List[str]) -> List[EvaluationResult]:
        """批量评测多个剧本"""
        tasks = [
            self.evaluate_content(content, "quick")
            for content in contents
        ]
        return await asyncio.gather(*tasks)

    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "short_drama_evaluation",
            "description": "竖屏短剧评估专家，专注于故事文本评估、打分和市场分析",
            "role": "资深剧本监制",
            "capabilities": [
                "故事文本深度评估与打分",
                "多维度专业分析（核心爽点、故事类型、人物设定等）",
                "市场竞争力分析",
                "开发价值评估",
                "优化建议提供",
                "文件内容提取和处理"
            ],
            "evaluation_dimensions": list(self.evaluation_dimensions.values()),
            "scoring_criteria": self.scoring_criteria,
            "supported_evaluation_types": ["full", "quick", "compare"],
            "features": {
                "structured_evaluation": True,
                "comparison_evaluation": True,
                "persistence": True
            }
        })
        return base_info


# ==================== 全局实例 ====================

_evaluation_agent: Optional[ShortDramaEvaluationAgent] = None


def get_evaluation_agent() -> ShortDramaEvaluationAgent:
    """获取评测 Agent 单例"""
    global _evaluation_agent
    if _evaluation_agent is None:
        _evaluation_agent = ShortDramaEvaluationAgent()
    return _evaluation_agent


# 向后兼容的全局实例
evaluation_agent: ShortDramaEvaluationAgent = get_evaluation_agent()


# ==================== 便捷函数 ====================

async def evaluate_drama(content: str, evaluation_type: str = "full") -> EvaluationResult:
    """评测短剧剧本"""
    agent = get_evaluation_agent()
    return await agent.evaluate_content(content, evaluation_type)


async def compare_dramas(content_a: str, content_b: str) -> ComparisonResult:
    """对比评测两个短剧剧本"""
    agent = get_evaluation_agent()
    return await agent.evaluate_comparison(content_a, content_b)

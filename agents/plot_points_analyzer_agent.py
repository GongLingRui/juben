from typing import AsyncGenerator, Dict, Any, Optional, List
import json
import re

"""
故事五元素工作流 - 大情节点分析智能体
 专门用于分析故事中的主要情节点
作为故事五元素分析系统的专业子智能体之一

业务处理逻辑：
1. 输入处理：接收故事文本或input字段，支持长文本处理
2. 结构分析：深入分析故事文本内容，梳理主要脉络和故事结构
3. 情节点提取：识别和提取故事中的关键情节点
4. 情节点总结：为每个情节点生成详细描述（每个不超过150字）
5. 阶段排列：按发展阶段（阶段一到阶段四）排列情节点
6. 质量控制：避免幻觉，严格按照原文分析，无遗漏
7. 输出格式化：返回结构化的大情节点分析数据
8. Agent as Tool：支持被其他智能体调用，上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent


class PlotPointsAnalyzerAgent(BaseJubenAgent):
    """大情节点分析智能体类"""

    def __init__(self, model_provider: str = "zhipu"):
        """初始化情节点分析智能体"""
        super().__init__(
            agent_name="plot_points_analyzer_agent",
            model_provider=model_provider
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理情节点分析请求（主入口）

        Args:
            request_data: 请求数据
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        async for event in self.process_plot_analysis(request_data, context):
            yield event

    async def process_plot_analysis(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        处理大情节点分析请求

        Args:
            request_data: 请求数据
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        # 提取请求信息
        input_text = request_data.get("input", "")
        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"
        parent_agent = context.get("parent_agent", "") if context else ""
        tool_call = context.get("tool_call", False) if context else False

        if tool_call:
            self.logger.info(f"🔧 Agent as Tool模式，父智能体: {parent_agent}")

        # 初始化Token累加器
        await self.initialize_token_accumulator(user_id, session_id)

        # 发送开始事件
        yield await self.emit_juben_event(
            "analysis_start",
            "开始分析大情节点...",
            {"stage": "init"}
        )

        try:
            # 第一步：预处理文本
            yield await self.emit_juben_event(
                "preprocessing",
                "正在预处理文本...",
                {"stage": "preprocessing"}
            )

            processed_text = await self._preprocess_text(input_text)

            # 第二步：分析故事结构
            yield await self.emit_juben_event(
                "analyzing_structure",
                "正在分析故事结构...",
                {"stage": "structure_analysis"}
            )

            structure_info = await self._analyze_story_structure(processed_text)

            # 第三步：提取情节点
            yield await self.emit_juben_event(
                "extracting_plot_points",
                "正在提取关键情节点...",
                {"stage": "extraction"}
            )

            plot_points = await self._extract_plot_points(processed_text, structure_info)

            # 第四步：组织情节点
            yield await self.emit_juben_event(
                "organizing_plot_points",
                "正在组织情节点...",
                {"stage": "organization"}
            )

            organized_points = await self._organize_plot_points_by_stage(plot_points)

            # 第五步：生成总结
            yield await self.emit_juben_event(
                "generating_summary",
                "正在生成分析总结...",
                {"stage": "summary"}
            )

            summary = await self._generate_analysis_summary(organized_points)

            # 第六步：格式化输出
            yield await self.emit_juben_event(
                "formatting_output",
                "正在格式化输出...",
                {"stage": "formatting"}
            )

            formatted_output = self._format_plot_points_output(organized_points, summary)

            # 保存输出
            await self.auto_save_output(
                output_content=formatted_output,
                user_id=user_id,
                session_id=session_id,
                file_type="json"
            )

            # 发送完成事件
            yield await self.emit_juben_event(
                "analysis_complete",
                formatted_output,
                {
                    "stage": "complete",
                    "plot_points_count": len(organized_points.get("stages", [])),
                    "summary": summary
                }
            )

        except Exception as e:
            self.logger.error(f"情节点分析失败: {e}")
            yield await self.emit_juben_event(
                "analysis_error",
                f"分析失败: {str(e)}",
                {"stage": "error", "error": str(e)}
            )

    async def _preprocess_text(self, text: str) -> str:
        """
        预处理文本
        - 清理多余空格和换行
        - 识别章节/场景标记
        - 统一标点符号
        """
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text)
        # 保留段落结构
        text = re.sub(r'([。！？；])\s+', r'\1\n', text)
        return text.strip()

    async def _analyze_story_structure(self, text: str) -> Dict[str, Any]:
        """
        分析故事结构
        - 识别开头、发展、高潮、结局
        - 检测转折点
        - 识别主要冲突
        """
        structure_prompt = f"""请分析以下故事文本的结构，识别：
1. 开头部分（背景介绍、人物登场）
2. 发展部分（冲突建立、情节推进）
3. 高潮部分（冲突爆发、关键转折）
4. 结局部分（问题解决、收尾）

故事文本：
{text[:5000]}

请以JSON格式返回分析结果：
{{
    "stages": {{
        "opening": "开头部分的简要描述",
        "development": "发展部分的简要描述",
        "climax": "高潮部分的简要描述",
        "resolution": "结局部分的简要描述"
    }},
    "key_conflicts": ["主要冲突1", "主要冲突2"],
    "turning_points": ["转折点1", "转折点2"]
}}"""

        messages = [
            {"role": "system", "content": "你是一个专业的故事结构分析专家。"},
            {"role": "user", "content": structure_prompt}
        ]

        try:
            response = await self._call_llm(messages, user_id="analysis", session_id="structure")
            # 尝试解析JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            self.logger.warning(f"结构分析解析失败: {e}")

        # 返回默认结构
        return {
            "stages": {
                "opening": "故事开头",
                "development": "故事发展",
                "climax": "故事高潮",
                "resolution": "故事结局"
            },
            "key_conflicts": [],
            "turning_points": []
        }

    async def _extract_plot_points(self, text: str, structure_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提取情节点
        - 识别关键事件
        - 提取重要转折
        - 标记人物决策点
        """
        extraction_prompt = f"""请从以下故事文本中提取关键情节点。

故事结构信息：
{json.dumps(structure_info, ensure_ascii=False, indent=2)}

故事文本：
{text[:8000]}

请提取8-12个关键情节点，每个情节点包括：
- 阶段（opening/development/climax/resolution）
- 标题（简短描述）
- 描述（不超过150字的详细说明）
- 重要性评分（1-10）

请以JSON格式返回：
[
    {{
        "stage": "development",
        "title": "情节点标题",
        "description": "详细描述（不超过150字）",
        "importance": 8
    }}
]"""

        messages = [
            {"role": "system", "content": "你是一个专业的情节点提取专家。"},
            {"role": "user", "content": extraction_prompt}
        ]

        try:
            response = await self._call_llm(messages, user_id="analysis", session_id="extraction")
            # 尝试解析JSON数组
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                plot_points = json.loads(json_match.group())
                return plot_points
        except Exception as e:
            self.logger.warning(f"情节点提取解析失败: {e}")

        return []

    async def _organize_plot_points_by_stage(self, plot_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按阶段组织情节点
        - 将情节点按故事阶段分组
        - 确保时间顺序
        - 添加阶段统计
        """
        stages = {
            "阶段一：开端": {
                "code": "opening",
                "description": "故事背景、人物介绍、初始状态",
                "points": []
            },
            "阶段二：发展": {
                "code": "development",
                "description": "冲突建立、情节推进、矛盾升级",
                "points": []
            },
            "阶段三：高潮": {
                "code": "climax",
                "description": "冲突爆发、关键转折、决定性时刻",
                "points": []
            },
            "阶段四：结局": {
                "code": "resolution",
                "description": "问题解决、收尾、新状态",
                "points": []
            }
        }

        # 按重要性排序并分组
        sorted_points = sorted(plot_points, key=lambda x: x.get("importance", 5), reverse=True)

        for point in sorted_points:
            stage_code = point.get("stage", "development")
            for stage_name, stage_info in stages.items():
                if stage_info["code"] == stage_code:
                    stage_info["points"].append({
                        "title": point.get("title", ""),
                        "description": point.get("description", ""),
                        "importance": point.get("importance", 5)
                    })
                    break

        return {
            "stages": stages,
            "total_points": len(plot_points),
            "stage_distribution": {
                stage_name: len(stage_info["points"])
                for stage_name, stage_info in stages.items()
            }
        }

    async def _generate_analysis_summary(self, organized_points: Dict[str, Any]) -> str:
        """
        生成分析总结
        - 概括情节点分布
        - 识别关键转折
        - 评估故事节奏
        """
        stages = organized_points.get("stages", {})
        distribution = organized_points.get("stage_distribution", {})

        summary_parts = []

        # 阶段分布
        summary_parts.append("## 情节点分布")
        for stage_name, count in distribution.items():
            if count > 0:
                summary_parts.append(f"- {stage_name}：{count}个关键情节点")

        # 关键情节点
        summary_parts.append("\n## 关键情节点")
        for stage_name, stage_info in stages.items():
            top_points = sorted(
                stage_info["points"],
                key=lambda x: x.get("importance", 0),
                reverse=True
            )[:2]
            for point in top_points:
                summary_parts.append(f"- {point['title']}（重要性：{point['importance']}/10）")

        return "\n".join(summary_parts)

    def _format_plot_points_output(self, organized_points: Dict[str, Any], summary: str) -> Dict[str, Any]:
        """
        格式化情节点输出
        - 结构化数据
        - Markdown格式
        - 统计信息
        """
        return {
            "analysis_type": "大情节点分析",
            "total_points": organized_points.get("total_points", 0),
            "stage_distribution": organized_points.get("stage_distribution", {}),
            "stages": organized_points.get("stages", {}),
            "summary": summary,
            "metadata": {
                "agent": "plot_points_analyzer_agent",
                "format_version": "1.0"
            }
        }
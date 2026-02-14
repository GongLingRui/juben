
"""
思维导图生成智能体

功能目标：
1. 先使用大语言模型对输入文本进行整体总结与关键信息提取；
2. 再将提取出的主题和要点转换为前端可渲染的思维导图 JSON 结构。
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题，兼容直接运行
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent  # type: ignore


class MindMapAgent(BaseJubenAgent):
    """
    思维导图生成智能体

    流程：
    1. 使用大模型对输入文本做整体摘要与关键信息提取；
    2. 将提取出的主题与要点转换为前端可渲染的思维导图 JSON 结构。
    """

    def __init__(self, model_provider: str = "zhipu"):
        super().__init__("mind_map_agent", model_provider)

        # 覆盖默认系统提示词：明确「先总结，再提取结构」的工作方式
        self.system_prompt = (
            "你是一名专业的思维导图专家，擅长从长文本中先进行总结，"
            "再提炼出清晰的层级结构，用于生成思维导图。"
        )
        self.logger.info("思维导图智能体初始化完成")

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理思维导图生成请求（流式返回系统进度 + 最终思维导图JSON）
        """
        try:
            input_text = request_data.get("input", "") or ""
            if not isinstance(input_text, str):
                input_text = str(input_text)

            user_id = (context or {}).get("user_id", "unknown")
            session_id = (context or {}).get("session_id", "unknown")

            self.logger.info(f"开始处理思维导图请求，文本长度: {len(input_text)}")

            # 初始化 Token 统计
            await self.initialize_token_accumulator(user_id, session_id)

            # 步骤 1：整体摘要与主题提取（由大语言模型完成）
            yield await self._emit_event("system", "🧠 正在对文本进行整体理解与总结...")
            summary_struct = await self._summarize_and_extract_topics(
                input_text, user_id, session_id
            )
            yield await self._emit_event("system", "✅ 摘要与关键主题提取完成")

            # 步骤 2：根据摘要结构构建思维导图数据（由代码完成映射）
            yield await self._emit_event("system", "🗺️ 正在根据摘要生成思维导图结构...")
            mind_map = self._build_mind_map_from_summary(summary_struct, input_text)
            mind_map_str = json.dumps(mind_map, ensure_ascii=False, indent=2)
            yield await self._emit_event("system", "✅ 思维导图结构生成完成")

            # 输出最终结果：一个符合前端 `MindMapData` 结构的 JSON 字符串
            # 前端会使用 parseMindMap() 解析并渲染为思维导图
            yield await self._emit_event("message", mind_map_str)

            # 可选：输出 Token 计费信息
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                billing_msg = (
                    f"📊 Token消耗: {billing_summary['total_tokens']} tokens, "
                    f"积分扣减: {billing_summary['deducted_points']} 积分"
                )
                yield await self._emit_event("billing", billing_msg)

        except Exception as e:
            self.logger.error(f"思维导图生成失败: {e}")
            yield await self._emit_event("error", f"思维导图生成失败: {str(e)}")

    async def _summarize_and_extract_topics(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        使用大语言模型先做摘要，再提取适合做思维导图的主题与要点。

        返回结构示例：
        {
          "title": "思维导图标题",
          "summary": "整体摘要",
          "topics": [
            {
              "title": "主题名称",
              "points": ["要点1", "要点2", "..."]
            }
          ]
        }
        """
        prompt = (
            "请先阅读下面的【输入文本】，在心中完成以下思考步骤，"
            "但最终【只输出一个严格的 JSON 对象，不要输出任何解释性文字】：\n\n"
            "1. 用不超过 200 字给出文本的中文整体摘要；\n"
            "2. 基于摘要，提取 3-7 个适合作为思维导图一级节点的主题（如：故事阶段、人物关系、主要冲突等）；\n"
            "3. 每个主题下提取 3-8 条关键要点，作为二级节点。\n\n"
            "输出 JSON 的格式必须严格如下（字段名必须完全一致）：\n"
            "{\n"
            '  "title": "思维导图总标题（尽量简短）",\n'
            '  "summary": "整体摘要",\n'
            '  "topics": [\n'
            "    {\n"
            '      "title": "主题名称",\n'
            '      "points": ["要点1", "要点2"]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "注意：\n"
            "- 只允许出现 title、summary、topics、title、points 这些字段；\n"
            "- 保证返回的是合法 JSON，最外层是一个对象；\n"
            "- 不要使用 ```json 代码块，不要添加多余注释或自然语言。\n\n"
            f"【输入文本】\n{input_text}"
        )

        messages = [{"role": "user", "content": prompt}]

        # 使用带重试和结构化输出守卫的 LLM 调用，期望返回 JSON 字符串
        response = await self._call_llm_with_retry(
            messages,
            user_id=user_id,
            session_id=session_id,
            expect_json=True,
        )

        try:
            data = json.loads(response)
            if not isinstance(data, dict):
                raise ValueError("summary response is not an object")
            return data
        except Exception as e:
            # 降级策略：解析失败时，仍然构造一个简单的结构，避免前端崩溃
            self.logger.warning(f"解析摘要结构失败，将使用降级策略: {e}")
            safe_snippet = (
                response if isinstance(response, str) else str(response)
            ).strip()
            if len(safe_snippet) > 200:
                safe_snippet = safe_snippet[:200] + "..."

            return {
                "title": "思维导图",
                "summary": safe_snippet,
                "topics": [
                    {
                        "title": "主要内容",
                        "points": [safe_snippet] if safe_snippet else [],
                    }
                ],
            }

    def _build_mind_map_from_summary(
        self,
        summary_struct: Dict[str, Any],
        original_text: str,
    ) -> Dict[str, Any]:
        """
        将摘要结构映射为前端需要的 MindMapData 结构：
        {
          "title": "...",
          "nodes": [
            { "name": "主题", "children": [ { "name": "要点" }, ... ] }
          ]
        }
        """
        # 决定导图标题：优先使用结构中的 title，其次 summary，再次原文前几十字
        title = (
            (summary_struct.get("title") or "").strip()
            or (summary_struct.get("summary") or "").strip()[:30]
            or (original_text or "").strip()[:20]
            or "思维导图"
        )

        topics = summary_struct.get("topics") or []
        nodes: List[Dict[str, Any]] = []

        if isinstance(topics, list):
            for topic in topics:
                if not isinstance(topic, dict):
                    continue
                topic_nodes = self._build_nodes_from_topic(topic)
                if topic_nodes:
                    nodes.extend(topic_nodes)

        if not nodes:
            # 冗余兜底，避免前端解析失败
            nodes = [{"name": "主要内容"}]

        return {
            "title": title,
            "nodes": nodes,
        }

    def _build_nodes_from_topic(self, topic: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将一个主题字典递归转换为 MindMapNode 列表。

        支持字段：
        - title: 主题名称
        - points: [字符串...]  -> 叶子节点
        - children / subtopics: [topic 对象...] -> 递归子主题
        """
        if not isinstance(topic, dict):
            return []

        title = str(topic.get("title") or "").strip()
        if not title:
            return []

        node: Dict[str, Any] = {"name": title}
        children: List[Dict[str, Any]] = []

        # 二级：要点 -> 叶子节点
        points = topic.get("points") or []
        if isinstance(points, list):
            for p in points:
                p_text = str(p).strip()
                if p_text:
                    children.append({"name": p_text})

        # 三级及以下：children / subtopics -> 递归子主题
        subtopics = topic.get("children") or topic.get("subtopics") or []
        if isinstance(subtopics, list):
            for child_topic in subtopics:
                if not isinstance(child_topic, dict):
                    continue
                sub_nodes = self._build_nodes_from_topic(child_topic)
                children.extend(sub_nodes)

        if children:
            node["children"] = children

        return [node]

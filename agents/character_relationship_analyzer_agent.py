from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple
import json
import re

"""
故事五元素工作流 - 人物关系分析智能体
 专门用于分析故事中人物之间的关系
作为故事五元素分析系统的专业子智能体之一

业务处理逻辑：
1. 输入处理：接收故事文本或input字段，支持多种输入格式
2. 人物识别：识别故事中的主要人物和重要配角
3. 关系分析：分析人物间的各种关系类型（家庭、友情、恋爱、工作、对抗等）
4. 关系总结：为每对人物关系生成详细的关系描述和内容总结
5. 质量控制：确保至少分析12对关系，分析全面、准确、细致
6. 输出格式化：返回结构化的人物关系分析数据
7. Agent as Tool：支持被其他智能体调用，上下文隔离

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


class CharacterRelationshipAnalyzerAgent(BaseJubenAgent):
    """人物关系分析智能体类"""

    # 关系类型定义
    RELATIONSHIP_TYPES = {
        "family": "家庭关系",
        "romantic": "恋爱关系",
        "friendship": "友情关系",
        "work": "工作/同事关系",
        "antagonistic": "对抗/敌对关系",
        "mentor": "师徒/指导关系",
        "rival": "竞争关系",
        "ally": "盟友关系",
        "stranger": "陌生人关系",
        "other": "其他关系"
    }

    def __init__(self, model_provider: str = "zhipu"):
        """初始化人物关系分析智能体"""
        super().__init__(
            agent_name="character_relationship_analyzer_agent",
            model_provider=model_provider
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理人物关系分析请求（主入口）

        Args:
            request_data: 请求数据
            context: 上下文信息

        Yields:
            Dict: 流式响应事件
        """
        async for event in self.process_relationship_analysis(request_data, context):
            yield event

    async def process_relationship_analysis(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        处理人物关系分析请求

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
            "开始分析人物关系...",
            {"stage": "init"}
        )

        try:
            # 第一步：识别人物
            yield await self.emit_juben_event(
                "identifying_characters",
                "正在识别故事中的人物...",
                {"stage": "character_identification"}
            )

            characters = await self._identify_characters(input_text)

            # 第二步：分析人物关系
            yield await self.emit_juben_event(
                "analyzing_relationships",
                f"正在分析{len(characters)}个人物之间的关系...",
                {"stage": "relationship_analysis", "character_count": len(characters)}
            )

            relationships = await self._analyze_relationships(input_text, characters)

            # 第三步：丰富关系详情
            yield await self.emit_juben_event(
                "enriching_details",
                "正在丰富关系详情...",
                {"stage": "detail_enrichment"}
            )

            enriched_relationships = await self._enrich_relationship_details(
                input_text, characters, relationships
            )

            # 第四步：构建关系网络
            yield await self.emit_juben_event(
                "building_network",
                "正在构建人物关系网络...",
                {"stage": "network_building"}
            )

            relationship_network = self._build_relationship_network(characters, enriched_relationships)

            # 第五步：生成分析报告
            yield await self.emit_juben_event(
                "generating_report",
                "正在生成分析报告...",
                {"stage": "report_generation"}
            )

            report = await self._generate_relationship_report(
                characters, enriched_relationships, relationship_network
            )

            # 第六步：格式化输出
            yield await self.emit_juben_event(
                "formatting_output",
                "正在格式化输出...",
                {"stage": "formatting"}
            )

            formatted_output = self._format_relationship_output(
                characters, enriched_relationships, relationship_network, report
            )

            # 保存结构化 JSON 输出，用于项目文件/笔记等后续使用
            await self.auto_save_output(
                output_content=formatted_output,
                user_id=user_id,
                session_id=session_id,
                file_type="json"
            )

            # 为前端聊天窗口准备一段可直接展示的文本结果
            if isinstance(formatted_output, dict):
                # 优先使用 summary_report 作为人类可读报告
                display_text = formatted_output.get("summary_report") or ""
                if not display_text:
                    # 回退为美化后的 JSON 文本，保证前端不会显示空内容
                    display_text = json.dumps(formatted_output, ensure_ascii=False, indent=2)
            else:
                display_text = str(formatted_output)

            # 发送完成事件：
            # - data 使用可展示的文本，便于 StreamingText 拼接渲染
            # - metadata 保留完整的结构化结果，方便前端或其他模块使用
            yield await self.emit_juben_event(
                "analysis_complete",
                display_text,
                {
                    "stage": "complete",
                    "character_count": len(characters),
                    "relationship_count": len(enriched_relationships),
                    "report": report,
                    "structured_result": formatted_output,
                }
            )

        except Exception as e:
            self.logger.error(f"人物关系分析失败: {e}")
            yield await self.emit_juben_event(
                "analysis_error",
                f"分析失败: {str(e)}",
                {"stage": "error", "error": str(e)}
            )

    async def _identify_characters(self, text: str) -> List[Dict[str, Any]]:
        """
        识别故事中的人物
        - 主要人物（主角、重要配角）
        - 次要人物（配角、反派）
        - 人物特征和角色定位
        """
        identification_prompt = f"""请从以下故事文本中识别所有重要人物。

故事文本：
{text[:5000]}

请识别并提取：
1. 主要人物（主角、核心配角）
2. 次要人物（配角、反派、其他）
3. 每个人物的简要描述（角色定位、性格特点）

请以JSON格式返回：
{{
    "main_characters": [
        {{
            "name": "人物姓名",
            "role": "主角/配角/反派",
            "description": "简要描述（50字以内）",
            "importance": 8
        }}
    ],
    "minor_characters": [
        {{
            "name": "人物姓名",
            "role": "配角",
            "description": "简要描述（30字以内）",
            "importance": 5
        }}
    ]
}}"""

        messages = [
            {"role": "system", "content": "你是一个专业的人物识别专家。"},
            {"role": "user", "content": identification_prompt}
        ]

        try:
            response = await self._call_llm(messages, user_id="analysis", session_id="character_identification")
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                characters = []
                characters.extend(result.get("main_characters", []))
                characters.extend(result.get("minor_characters", []))
                return characters
        except Exception as e:
            self.logger.warning(f"人物识别解析失败: {e}")

        return []

    async def _analyze_relationships(
        self,
        text: str,
        characters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        分析人物之间的关系
        - 识别人物间的直接关系
        - 推断潜在关系
        - 评估关系强度
        """
        # 生成人物对组合
        character_pairs = []
        for i in range(len(characters)):
            for j in range(i + 1, len(characters)):
                character_pairs.append((characters[i], characters[j]))

        analysis_prompt = f"""请分析以下人物对之间的关系。

人物列表：
{json.dumps(characters, ensure_ascii=False, indent=2)}

故事文本：
{text[:8000]}

请为每一对有交互或关联的人物分析：
1. 关系类型（family/romantic/friendship/work/antagonistic/mentor/rival/ally/stranger/other）
2. 关系描述（100字以内）
3. 关系强度（1-10，10表示关系最紧密/最重要）
4. 关系发展阶段（初期/发展期/稳定期/变化期/结束期）

请以JSON格式返回，至少分析12对关系：
[
    {{
        "character1": "人物1姓名",
        "character2": "人物2姓名",
        "relationship_type": "romantic",
        "description": "关系描述",
        "strength": 9,
        "stage": "发展期",
        "key_events": ["关键事件1", "关键事件2"]
    }}
]"""

        messages = [
            {"role": "system", "content": "你是一个专业的人物关系分析专家。"},
            {"role": "user", "content": analysis_prompt}
        ]

        try:
            response = await self._call_llm(messages, user_id="analysis", session_id="relationship_analysis")
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                relationships = json.loads(json_match.group())
                return relationships
        except Exception as e:
            self.logger.warning(f"关系分析解析失败: {e}")

        return []

    async def _enrich_relationship_details(
        self,
        text: str,
        characters: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        丰富关系详情
        - 添加关系演变历史
        - 标记关键转折点
        - 分析情感倾向
        """
        if not relationships:
            return []

        enriched = []
        for rel in relationships:
            enriched_rel = rel.copy()

            # 添加关系类型的中文名称
            rel_type = rel.get("relationship_type", "other")
            enriched_rel["relationship_type_cn"] = self.RELATIONSHIP_TYPES.get(
                rel_type, "其他关系"
            )

            # 分析情感倾向
            description = rel.get("description", "")
            enriched_rel["sentiment"] = self._analyze_relationship_sentiment(description)

            enriched.append(enriched_rel)

        return enriched

    def _analyze_relationship_sentiment(self, description: str) -> str:
        """分析关系的情感倾向"""
        positive_keywords = ["爱", "喜欢", "支持", "帮助", "亲密", "信任", "友谊", "温暖"]
        negative_keywords = ["恨", "讨厌", "敌对", "冲突", "矛盾", "背叛", "冷漠", "疏远"]

        positive_count = sum(1 for kw in positive_keywords if kw in description)
        negative_count = sum(1 for kw in negative_keywords if kw in description)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _build_relationship_network(
        self,
        characters: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建人物关系网络
        - 生成节点和边
        - 计算网络指标
        - 识别关键人物
        """
        nodes = []
        edges = []

        # 创建节点
        for char in characters:
            nodes.append({
                "id": char.get("name", ""),
                "label": char.get("name", ""),
                "role": char.get("role", ""),
                "importance": char.get("importance", 5),
                "description": char.get("description", "")
            })

        # 创建边
        for rel in relationships:
            edges.append({
                "source": rel.get("character1", ""),
                "target": rel.get("character2", ""),
                "label": rel.get("relationship_type_cn", ""),
                "strength": rel.get("strength", 5),
                "type": rel.get("relationship_type", "other"),
                "sentiment": rel.get("sentiment", "neutral")
            })

        # 计算节点度数（连接数）
        node_degree = {}
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            node_degree[source] = node_degree.get(source, 0) + 1
            node_degree[target] = node_degree.get(target, 0) + 1

        # 识别关键人物（度数最高的前3名）
        sorted_nodes = sorted(node_degree.items(), key=lambda x: x[1], reverse=True)
        key_characters = [name for name, _ in sorted_nodes[:3]]

        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_degrees": node_degree,
                "key_characters": key_characters
            }
        }

    async def _generate_relationship_report(
        self,
        characters: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        network: Dict[str, Any]
    ) -> str:
        """
        生成人物关系分析报告
        - 关系统计
        - 关键关系总结
        - 网络特征分析
        """
        report_parts = []

        # 统计信息
        report_parts.append("## 人物关系分析报告")
        report_parts.append(f"\n### 人物统计")
        report_parts.append(f"- 总人物数：{len(characters)}")
        report_parts.append(f"- 总关系对数：{len(relationships)}")

        # 按关系统计
        rel_type_count = {}
        for rel in relationships:
            rel_type = rel.get("relationship_type_cn", "其他关系")
            rel_type_count[rel_type] = rel_type_count.get(rel_type, 0) + 1

        report_parts.append(f"\n### 关系类型分布")
        for rel_type, count in sorted(rel_type_count.items(), key=lambda x: x[1], reverse=True):
            report_parts.append(f"- {rel_type}：{count}对")

        # 关键人物
        key_chars = network.get("statistics", {}).get("key_characters", [])
        if key_chars:
            report_parts.append(f"\n### 关键人物（连接数最多）")
            for char in key_chars:
                degree = network["statistics"]["node_degrees"].get(char, 0)
                report_parts.append(f"- {char}：{degree}个关系")

        # 重要关系（强度>=8）
        strong_relationships = [r for r in relationships if r.get("strength", 0) >= 8]
        if strong_relationships:
            report_parts.append(f"\n### 重要关系")
            for rel in sorted(strong_relationships, key=lambda x: x.get("strength", 0), reverse=True)[:5]:
                report_parts.append(
                    f"- {rel.get('character1')} ↔ {rel.get('character2')}："
                    f"{rel.get('relationship_type_cn')}（强度：{rel.get('strength')}/10）"
                )

        return "\n".join(report_parts)

    def _format_relationship_output(
        self,
        characters: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        network: Dict[str, Any],
        report: str
    ) -> Dict[str, Any]:
        """
        格式化人物关系输出
        """
        return {
            "analysis_type": "人物关系分析",
            "characters": characters,
            "relationships": relationships,
            "relationship_network": network,
            "summary_report": report,
            "metadata": {
                "agent": "character_relationship_analyzer_agent",
                "format_version": "1.0",
                "relationship_types": self.RELATIONSHIP_TYPES
            }
        }
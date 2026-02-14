from typing import AsyncGenerator, Dict, Any, Optional

"""
故事五元素工作流 - 题材类型分析智能体
 提供题材类型与创意提炼服务
作为故事五元素分析系统的专业子智能体之一

业务处理逻辑：
1. 输入处理：接收故事文本或input字段，支持多种输入格式
2. 类型分析：分析故事的类型与叙事主题（爱情、冒险、科幻、恐怖等）
3. 结构分析：提炼故事的情节结构特点和发展脉络
4. 创意提炼：总结故事的核心创意和独特之处
5. 亮点总结：提炼故事的主要亮点和吸引力要素
6. 质量控制：确保分析全面、准确，覆盖四个分析维度
7. 输出格式化：返回结构化的题材类型分析数据
8. Agent as Tool：支持被其他智能体调用，上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.base_juben_agent import BaseJubenAgent

class StoryTypeAnalyzerAgent(BaseJubenAgent):
    """
    题材类型分析智能体 - 故事五元素分析系统的专业子智能体
    
    核心功能：
    1. 分析故事的类型与叙事主题
    2. 提炼故事的情节结构特点
    3. 总结故事的核心创意
    4. 提炼故事的主要亮点
    5. 支持Agent as Tool机制，可被其他智能体调用
    
    作为故事五元素工作流中的专业子智能体，专门负责题材类型分析任务
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        super().__init__("story_type_analyzer", model_provider)
        
        # 工作流配置
        self.workflow_type = "story_five_elements"
        self.sub_agent_type = "story_type_analyzer"
        self.analysis_dimensions = ["类型与主题", "情节结构", "核心创意", "故事亮点"]
        self.story_themes = ["爱情", "冒险", "科幻", "恐怖", "喜剧", "悬疑", "动作", "历史"]
        
        self.logger.info("🎭 题材类型分析智能体初始化完成")
        self.logger.info(f"📋 工作流类型: {self.workflow_type}")
        self.logger.info(f"🎯 子智能体类型: {self.sub_agent_type}")
        self.logger.info(f"📊 配置: 分析维度{len(self.analysis_dimensions)}个，支持{len(self.story_themes)}种主题类型")
    
    def _load_story_type_analyzer_prompt(self) -> str:
        """加载题材类型分析提示词"""
        return """
## Profile:
- role: 资深的故事编剧
- language: 中文
- description: 根据给出的文本，准确地总结出文本故事的类型与结构，提炼故事的结构特点、核心创意及主要亮点。

## Definition
- "故事类型"是一个戏剧概念，指描述和分类不同类型故事的方式或方法。它涉及到对故事元素、情节结构、主题、风格等方面进行归类和解释，以便更好地理解和分析故事。一般以主题及情节结构来对故事进行分析。主题一般包含爱情、冒险、科幻、恐怖、喜剧等。情节结构例如传统的三幕剧结构（起始、发展、高潮）或五幕剧结构（引子、升华、转折、高潮、结局）。

## Constrains：
- 请严格按照故事原文所表达的内容来总结故事类型与主题。
- 故事类型为词语或短语，不要用句子表示。

## Skills：
- 善于分析、提炼故事的类型、创意、亮点。
- 善于对故事类型的定义进行充分的理解，并准确分析故事文本的类型。
- 善于把握故事的情节结构，并作出准确地判断与分析。
- 善于通过故事文本的上下文关系，对故事文本中表述重复、混乱、断裂的部分进行梳理，从而总结出准确的故事信息。

## Goals:
- 对提供的故事文本进行阅读与理解，总结其主要的故事类型，分析其情节结构、核心创意与故事亮点。

## Workflows
- 第一步，对提供的故事文本进行充分的阅读与理解。
- 第二步，根据「Definition」中有关故事类型的介绍，总结该故事主要的故事类型与叙事主题。
- 第三步，对该故事的基本结构进行分析与总结。
- 第四步，总结提炼故该事的核心创意。
- 第五步，总结提炼该故事的主要亮点。

## Outputformate：
【类型与主题】：<总结故事文本的类型与叙事主题。>
【情节结构】：<总结提炼故事文本的主要情节结构，以Markdown的格式进行呈现。>
【核心创意】：<总结提炼故事文本的核心创意，以Markdown的格式进行呈现。>
【故事亮点】：<总结提炼故事文本的主要亮点，以Markdown的格式进行呈现 。>
"""
    
    async def analyze_story_type(self, story_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析故事类型（便于作为普通工具函数调用）

        内部复用流式的 process_request，将所有内容块拼接成一个字符串返回。
        """
        try:
            request_data = {
                "input": story_text,
                "story_text": story_text,
            }

            chunks: list[str] = []
            async for event in self.process_request(request_data, context):
                if event.get("event_type") == "llm_chunk":
                    data = event.get("data", "")
                    if isinstance(data, str):
                        chunks.append(data)

            return {
                "success": True,
                "analysis_result": "".join(chunks),
                "story_text": story_text,
            }

        except Exception as e:
            self.logger.error(f"故事类型分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis_result": "",
                "story_text": story_text,
            }

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理故事类型分析请求（流式版本）

        注意：
        - 返回的是异步生成器，供 BaseJubenAgent 的增强上下文流程和 StoryFiveElements 子调用使用；
        - 统一通过 _emit_event 输出事件，event_type 为 'llm_chunk'。
        """
        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"

        # story_text 优先级：request_data.story_text > request_data.input > request_data.query
        story_text = (
            request_data.get("story_text")
            or request_data.get("input")
            or request_data.get("query")
            or ""
        )

        # 初始化 Token 统计
        await self.initialize_token_accumulator(user_id, session_id)

        try:
            await self._emit_event(
                "system",
                "📖 正在分析故事类型与主题...",
                {"agent": "story_type_analyzer"},
            )

            system_prompt = self._load_story_type_analyzer_prompt()
            user_prompt = f"用户输入如下\n-----------------\n{story_text}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # 流式调用LLM，使其适配所有使用 async for 的路径
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                if chunk:
                    yield await self._emit_event("llm_chunk", chunk)

            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event(
                    "billing",
                    f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分",
                )

            yield await self._emit_event("system", "✅ 故事类型分析完成")

        except Exception as e:
            self.logger.error(f"处理故事类型分析请求失败: {str(e)}")
            yield await self._emit_event("error", f"故事类型分析失败: {str(e)}")
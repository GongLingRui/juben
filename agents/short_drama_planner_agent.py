"""
竖屏短剧策划Agent
专业的竖屏短剧策划助手，基于爆款引擎理论

业务处理逻辑：
1. 输入处理：接收策划需求，支持多种输入格式和文件引用
2. 情绪价值分析：基于情绪价值第一性原理进行深度分析
3. 钩子设计：应用黄金三秒钩子法则设计开头吸引力
4. 结构设计：使用期待-压抑-爆发三幕式结构设计故事框架
5. 人设设计：基于人设即容器理论进行角色设计
6. 商业化优化：应用商业化卡点逻辑优化故事结构
7. 智能体协作：使用Agent as Tool机制调用其他专业智能体
8. 上下文隔离：确保智能体调用的独立性和准确性
9. 输出格式化：生成完整的竖屏短剧策划方案

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import json
import re

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


class ShortDramaPlannerAgent(BaseJubenAgent):
    """
    竖屏短剧策划Agent - 支持Agent as Tool机制
    
    核心功能：
    1. 情绪价值第一性原理分析
    2. 黄金三秒钩子法则应用
    3. 期待-压抑-爆发三幕式结构设计
    4. 人设即容器理论指导
    5. 商业化卡点逻辑优化
    6. Agent as Tool: 调用其他智能体作为工具
    7. 模块化外包: 智能体间相互调用，上下文隔离
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        """初始化竖屏短剧策划Agent"""
        super().__init__("short_drama_planner", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化意图识别器
        self.intent_recognizer = IntentRecognizer()
        
        # 初始化URL提取器
        self.url_extractor = URLExtractor()
        
        # Agent as Tool机制 - 子智能体注册表（延迟加载）
        self.sub_agents = {}
        
        # 可调用的工具智能体映射
        self.available_tools = {
            "websearch": "网络搜索工具",
            "knowledge": "知识库查询工具", 
            "creator": "创作助手工具",
            "evaluation": "评估分析工具",
            "file_reference": "文件引用解析工具"
        }
        
        self.logger.info("竖屏短剧策划Agent初始化完成（支持Agent as Tool机制）")
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理竖屏短剧策划请求

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
            model = context.get("model") if context else None  # 获取模型参数

            self.logger.info(f"开始处理短剧策划请求: {user_input}, model: {model}")

            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始处理事件
            yield await self._emit_event("system", "🎬 开始分析您的短剧策划需求...")

            # 1. 意图识别
            yield await self._emit_event("system", "🔍 正在分析您的需求意图...")
            intent_result = await self._analyze_intent(user_input)
            yield await self._emit_event("system", f"✅ 意图识别完成: {intent_result['intent']}")

            # 2. URL提取（如果有）
            urls = self.url_extractor.extract_urls(user_input)
            if urls:
                yield await self._emit_event("system", f"📎 发现{len(urls)}个链接，正在提取内容...")
                url_contents = await self._extract_url_contents(urls)
                yield await self._emit_event("system", "✅ URL内容提取完成")
            else:
                url_contents = []

            # 3. 智能工具调用 - Agent as Tool机制
            search_results = {}
            knowledge_results = {}
            tool_results = {}

            # 根据意图决定调用哪些工具智能体
            # 将用户输入添加到意图结果中
            intent_result["user_input"] = user_input
            tools_to_call = self._determine_tools_to_call(intent_result)

            for tool_name in tools_to_call:
                yield await self._emit_event("system", f"🔧 调用 {self.available_tools[tool_name]}...")

                # 调用工具智能体
                tool_result = await self._call_agent_as_tool(tool_name, user_input, intent_result, context)
                tool_results[tool_name] = tool_result

                # 根据工具类型存储结果
                if tool_name == "websearch":
                    search_results = tool_result
                elif tool_name == "knowledge":
                    knowledge_results = tool_result

                yield await self._emit_event("system", f"✅ {self.available_tools[tool_name]} 调用完成")

            # 4. 构建上下文
            context_data = {
                "user_input": user_input,
                "intent": intent_result,
                "search_results": search_results,
                "knowledge_results": knowledge_results,
                "tool_results": tool_results,
                "url_contents": url_contents,
                "user_id": user_id,
                "session_id": session_id,
                "model": model  # 传递模型参数
            }

            # 5. 生成策划方案
            yield await self._emit_event("system", "🎭 正在生成专业的短剧策划方案...")

            async for chunk in self._generate_planning_response(context_data):
                yield chunk

            # 6. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")

            # 7. 发送完成事件
            yield await self._emit_event("system", "🎉 短剧策划方案生成完成！")

        except Exception as e:
            self.logger.error(f"处理请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        try:
            intent_result = await self.intent_recognizer.analyze(user_input)
            return intent_result
        except Exception as e:
            self.logger.error(f"意图识别失败: {e}")
            return {
                "intent": "creation_assistance",
                "confidence": 0.5,
                "needs_web_search": False,
                "needs_knowledge_base": True
            }
    
    async def _extract_url_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """提取URL内容"""
        contents = []
        for url in urls:
            try:
                content = await self.url_extractor.extract_content(url)
                contents.append({
                    "url": url,
                    "content": content,
                    "success": True
                })
            except Exception as e:
                self.logger.error(f"URL内容提取失败 {url}: {e}")
                contents.append({
                    "url": url,
                    "content": "",
                    "success": False,
                    "error": str(e)
                })
        return contents
    
    def _build_search_query(self, user_input: str, intent_result: Dict[str, Any]) -> str:
        """构建搜索查询"""
        intent = intent_result.get("intent", "")
        
        if intent == "web_search":
            return user_input
        elif intent == "creation_assistance":
            # 为创作辅助添加市场相关关键词
            return f"{user_input} 短剧市场趋势 热门题材"
        else:
            return user_input
    
    def _build_knowledge_query(self, user_input: str, intent_result: Dict[str, Any]) -> str:
        """构建知识库查询"""
        intent = intent_result.get("intent", "")
        
        if intent == "knowledge_base":
            return user_input
        elif intent == "creation_assistance":
            # 为创作辅助添加技巧相关关键词
            return f"{user_input} 创作技巧 剧本结构"
        else:
            return user_input
    
    async def _generate_planning_response(self, context_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """生成策划响应"""
        try:
            # 构建提示词
            prompt = self._build_planning_prompt(context_data)

            # 构建消息
            messages = [
                {"role": "user", "content": prompt}
            ]

            # 获取用户ID、会话ID和模型
            user_id = context_data.get("user_id", "unknown")
            session_id = context_data.get("session_id", "unknown")
            model = context_data.get("model")  # 获取模型参数

            # 流式调用LLM（带追踪）
            if model:
                async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id, model=model):
                    yield await self._emit_event("llm_chunk", chunk)
            else:
                async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                    yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成策划响应失败: {e}")
            yield await self._emit_event("error", f"生成响应失败: {str(e)}")
    
    def _build_planning_prompt(self, context_data: Dict[str, Any]) -> str:
        """构建策划提示词"""
        user_input = context_data["user_input"]
        intent = context_data["intent"]
        search_results = context_data.get("search_results", {})
        knowledge_results = context_data.get("knowledge_results", {})
        tool_results = context_data.get("tool_results", {})
        url_contents = context_data.get("url_contents", [])
        
        # 构建用户查询部分
        user_query_section = f"""
## 用户需求
{user_input}

## 需求分析
- 意图类型: {intent.get('intent', 'unknown')}
- 置信度: {intent.get('confidence', 0)}

## 市场信息
"""
        
        # 添加搜索结果
        if search_results.get("success") and search_results.get("results"):
            user_query_section += "\n### 最新市场动态\n"
            for i, result in enumerate(search_results["results"][:3], 1):
                user_query_section += f"{i}. {result.get('title', '')}\n"
                user_query_section += f"   {result.get('content', '')[:200]}...\n"
        
        # 添加知识库结果
        if knowledge_results.get("success") and knowledge_results.get("results"):
            user_query_section += "\n### 专业知识参考\n"
            for i, result in enumerate(knowledge_results["results"][:3], 1):
                user_query_section += f"{i}. {result.get('title', '')}\n"
                user_query_section += f"   {result.get('content', '')[:200]}...\n"
        
        # 添加工具调用结果
        if tool_results:
            user_query_section += "\n### 智能工具分析结果\n"
            for tool_name, tool_result in tool_results.items():
                if tool_result.get("success"):
                    user_query_section += f"#### {self.available_tools.get(tool_name, tool_name)}\n"
                    user_query_section += f"{tool_result.get('result', '')[:500]}...\n"
        
        # 添加URL内容
        if url_contents:
            user_query_section += "\n### 参考资料\n"
            for i, content in enumerate(url_contents[:2], 1):
                if content.get("success"):
                    user_query_section += f"{i}. {content.get('url', '')}\n"
                    user_query_section += f"   {content.get('content', '')[:200]}...\n"
        
        # 将用户查询部分添加到系统提示词后面
        full_prompt = f"{self.system_prompt}\n\n{user_query_section}"
        
        return full_prompt
    
    def _determine_tools_to_call(self, intent_result: Dict[str, Any]) -> List[str]:
        """根据意图结果确定需要调用的工具智能体"""
        tools = []
        
        # 根据意图类型决定调用哪些工具
        intent = intent_result.get("intent", "")
        user_input = intent_result.get("user_input", "")
        
        # 检测文件引用
        if self._has_file_references(user_input):
            tools.append("file_reference")
        
        if intent == "web_search" or intent_result.get("needs_web_search", False):
            tools.append("websearch")
        
        if intent == "knowledge_base" or intent_result.get("needs_knowledge_base", False):
            tools.append("knowledge")
        
        # 如果是创作相关，默认调用知识库工具
        if intent == "creation_assistance":
            tools.extend(["knowledge", "websearch"])
        
        # 去重并返回
        return list(set(tools))
    
    def _has_file_references(self, text: str) -> bool:
        """检测文本中是否包含文件引用"""
        if not text:
            return False
        
        # 检测@符号引用
        at_ref_pattern = r'@(file\d+|image\d+|document\d+|pdf\d+|excel\d+|audio\d+|video\d+)'
        if re.search(at_ref_pattern, text, re.IGNORECASE):
            return True
        
        # 检测自然语言引用
        natural_patterns = [
            r"第([一二三四五六七八九十\d]+)个文件",
            r"最新上传的(.+)",
            r"刚才上传的(.+)",
            r"那个(.+)文件",
            r"我的(.+)文件",
            r"(.+)文件"
        ]
        
        for pattern in natural_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    async def _call_agent_as_tool(self, tool_name: str, user_input: str, intent_result: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        调用其他智能体作为工具 - Agent as Tool机制的核心实现（增强版：带超时和重试）

        Args:
            tool_name: 工具智能体名称
            user_input: 用户输入
            intent_result: 意图识别结果
            context: 上下文信息

        Returns:
            Dict: 工具调用结果
        """
        import asyncio

        try:
            # ========== 参数验证 ==========
            if not user_input or not isinstance(user_input, str):
                return {
                    "success": False,
                    "error": f"无效的用户输入: {type(user_input).__name__}",
                    "tool_name": tool_name
                }

            # 获取工具智能体实例
            tool_agent = await self._get_tool_agent(tool_name)
            if not tool_agent:
                return {
                    "success": False,
                    "error": f"无法获取工具智能体: {tool_name}",
                    "tool_name": tool_name
                }

            # 构建工具调用请求
            tool_request = {
                "input": user_input,
                "query": user_input  # 兼容不同的参数名
            }

            # 创建独立的工具调用上下文（上下文隔离）
            tool_context = {
                "user_id": context.get("user_id", "unknown") if context else "unknown",
                "session_id": context.get("session_id", "unknown") if context else "unknown",
                "parent_agent": "short_drama_planner",
                "tool_call": True,
                "original_context": context
            }

            # 调用工具智能体并收集结果（带超时）
            tool_results = []

            async def collect_results():
                async for event in tool_agent.process_request(tool_request, tool_context):
                    # 收集LLM响应内容
                    if event.get("event_type") == "llm_chunk":
                        tool_results.append(event.get("data", ""))

            # 使用超时控制
            try:
                await asyncio.wait_for(collect_results(), timeout=120)
            except asyncio.TimeoutError:
                self.logger.error(f"工具智能体 {tool_name} 调用超时(120秒)")
                return {
                    "success": False,
                    "error": f"工具调用超时(120秒): {tool_name}",
                    "tool_name": tool_name
                }

            # 整合工具调用结果
            combined_result = "".join(tool_results)

            return {
                "success": True,
                "tool_name": tool_name,
                "result": combined_result,
                "tool_agent": tool_name
            }

        except ValueError as e:
            self.logger.error(f"工具调用参数错误: {e}")
            return {
                "success": False,
                "error": f"参数错误: {str(e)}",
                "tool_name": tool_name
            }
        except Exception as e:
            self.logger.error(f"调用工具智能体 {tool_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    async def _get_tool_agent(self, agent_name: str):
        """获取工具智能体实例（延迟加载）"""
        if agent_name not in self.sub_agents:
            try:
                if agent_name == "websearch":
                    from .websearch_agent import WebSearchAgent
                    self.sub_agents[agent_name] = WebSearchAgent()
                elif agent_name == "knowledge":
                    from .knowledge_agent import KnowledgeAgent
                    self.sub_agents[agent_name] = KnowledgeAgent()
                elif agent_name == "creator":
                    from .short_drama_creator_agent import ShortDramaCreatorAgent
                    self.sub_agents[agent_name] = ShortDramaCreatorAgent()
                elif agent_name == "evaluation":
                    from .short_drama_evaluation_agent import ShortDramaEvaluationAgent
                    self.sub_agents[agent_name] = ShortDramaEvaluationAgent()
                elif agent_name == "file_reference":
                    from .file_reference_agent import FileReferenceAgent
                    self.sub_agents[agent_name] = FileReferenceAgent()
                else:
                    self.logger.error(f"未知的工具智能体类型: {agent_name}")
                    return None
                
                self.logger.info(f"工具智能体 {agent_name} 加载成功")
                
            except Exception as e:
                self.logger.error(f"加载工具智能体 {agent_name} 失败: {e}")
                return None
        
        return self.sub_agents[agent_name]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "short_drama_planner",
            "capabilities": [
                "情绪价值分析",
                "黄金三秒钩子设计",
                "三幕式结构规划",
                "人设容器设计",
                "商业化卡点设置",
                "专业策划方案生成",
                "Agent as Tool机制",
                "智能体间相互调用"
            ],
            "supported_intents": [
                "creation_assistance",
                "web_search",
                "knowledge_base",
                "url_extraction"
            ],
            "available_tools": self.available_tools,
            "agent_as_tool_enabled": True
        })
        return base_info

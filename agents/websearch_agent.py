"""
竖屏短剧网络检索智能体
 专注于网络搜索和信息检索

业务处理逻辑：
1. 输入处理：接收搜索查询请求，支持多种搜索格式
2. 意图识别：使用IntentRecognizer分析搜索意图和关键词
3. URL提取：从查询中提取相关的URL链接信息
4. 网络搜索：执行网络搜索，获取相关的网页内容
5. 内容解析：解析搜索结果，提取有用的信息
6. 信息过滤：根据搜索意图过滤和排序搜索结果
7. 内容生成：基于搜索结果生成结构化的回答
8. 上下文管理：维护搜索历史和上下文信息
9. 输出格式化：返回结构化的网络搜索结果
10. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
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


class WebSearchAgent(BaseJubenAgent):
    """
    竖屏短剧网络检索智能体
    
    功能：
    1. 智谱AI网络搜索
    2. 搜索结果智能总结
    3. 多阶段搜索流程
    4. 搜索结果格式化
    5. 信息提取和整理
    """
    
    def __init__(self):
        super().__init__("websearch", model_provider="zhipu")
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 初始化专用组件
        self.intent_recognizer = IntentRecognizer()
        self.url_extractor = URLExtractor()
        
        # 搜索配置
        self.search_config = {
            "default_count": 5,
            "max_count": 10,
            "timeout": 30
        }
        
        self.logger.info("竖屏短剧网络检索智能体初始化完成")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理网络搜索请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            query = request_data.get("query", request_data.get("input", ""))
            instruction = request_data.get("instruction", query)
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            count = request_data.get("count", self.search_config["default_count"])
            
            self.logger.info(f"开始处理网络搜索请求: {instruction}")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system", f"🔍 开始网络搜索: {instruction}")
            
            # 1. 意图识别
            yield await self._emit_event("system", "🔍 正在分析搜索意图...")
            intent_result = await self._analyze_intent(instruction)
            yield await self._emit_event("system", f"✅ 意图识别完成: {intent_result['intent']}")
            
            # 2. URL提取和内容获取
            urls = self.url_extractor.extract_urls(instruction)
            url_contents = []
            if urls:
                yield await self._emit_event("system", f"📎 发现{len(urls)}个链接，正在提取内容...")
                url_contents = await self._extract_url_contents(urls)
                yield await self._emit_event("system", "✅ URL内容提取完成")
            
            # 3. 网络搜索
            yield await self._emit_event("system", "🌐 正在搜索网络信息...")
            search_results = await self._execute_web_search(instruction, count=count)
            yield await self._emit_event("system", "✅ 网络搜索完成")
            
            # 4. 格式化搜索结果
            formatted_results = self._format_search_results(search_results, instruction)
            
            # 5. 发送原始搜索结果
            yield await self._emit_event("search_results", formatted_results)
            
            # 6. 智能总结搜索结果
            if formatted_results:
                yield await self._emit_event("system", "📝 正在分析和总结搜索结果...")
                
                async for chunk in self._generate_search_summary(instruction, search_results, user_id, session_id):
                    yield chunk
                
                yield await self._emit_event("system", "✅ 搜索结果总结完成")
            
            # 7. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
            # 8. 发送完成事件
            yield await self._emit_event("system", "🎯 网络搜索任务完成！")
            
        except Exception as e:
            self.logger.error(f"处理网络搜索请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户搜索意图"""
        try:
            # 搜索相关的意图识别
            intent_result = await self.intent_recognizer.analyze(user_input)
            
            # 根据搜索需求调整意图
            if "搜索" in user_input or "查找" in user_input or "寻找" in user_input:
                intent_result.update({
                    "intent": "web_search",
                    "needs_web_search": True,
                    "needs_knowledge_base": False
                })
            elif "新闻" in user_input or "最新" in user_input or "资讯" in user_input:
                intent_result.update({
                    "intent": "news_search",
                    "needs_web_search": True,
                    "needs_knowledge_base": False
                })
            elif "市场" in user_input or "趋势" in user_input or "分析" in user_input:
                intent_result.update({
                    "intent": "market_search",
                    "needs_web_search": True,
                    "needs_knowledge_base": True
                })
            
            return intent_result
        except Exception as e:
            self.logger.error(f"意图识别失败: {e}")
            return {
                "intent": "web_search",
                "confidence": 0.5,
                "needs_web_search": True,
                "needs_knowledge_base": False
            }
    
    async def _extract_url_contents(
        self,
        urls: List[str],
        timeout: int = 15,
        max_retries: int = 2,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        提取URL内容（增强版：带超时、重试和并行处理）

        Args:
            urls: URL列表
            timeout: 单个URL超时时间（秒）
            max_retries: 最大重试次数
            parallel: 是否并行处理

        Returns:
            List[Dict]: 提取结果列表
        """
        import asyncio

        if not urls:
            return []

        async def extract_single_url(url: str) -> Dict[str, Any]:
            """提取单个URL的内容"""
            for attempt in range(max_retries + 1):
                try:
                    self.logger.debug(f"提取URL内容(尝试{attempt + 1}): {url}")

                    # 使用asyncio.wait_for实现超时
                    async def do_extract():
                        return await self.url_extractor.extract_content(url)

                    result = await asyncio.wait_for(do_extract(), timeout=timeout)

                    # 验证返回结果
                    if result is None:
                        raise ValueError("extract_content返回None")

                    # 确保有url字段
                    if isinstance(result, dict):
                        result["url"] = url
                        result["success"] = True
                    else:
                        result = {
                            "url": url,
                            "success": True,
                            "content": str(result)
                        }

                    self.logger.info(f"URL内容提取成功: {url}")
                    return result

                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        self.logger.warning(f"URL提取超时({timeout}s): {url}, 重试{attempt + 1}/{max_retries}")
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        self.logger.error(f"URL提取超时({timeout}s): {url}, 已达最大重试次数")
                        return {
                            "url": url,
                            "success": False,
                            "error": f"提取超时({timeout}秒)"
                        }

                except ValueError as e:
                    self.logger.error(f"URL提取参数错误: {url}, {e}")
                    return {
                        "url": url,
                        "success": False,
                        "error": f"参数错误: {str(e)}"
                    }

                except Exception as e:
                    if attempt < max_retries:
                        self.logger.warning(f"URL提取失败(尝试{attempt + 1}): {url}, {e}")
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        self.logger.error(f"URL提取最终失败: {url}, {e}")
                        return {
                            "url": url,
                            "success": False,
                            "error": str(e)
                        }

        # 并行或串行处理
        if parallel and len(urls) > 1:
            tasks = [extract_single_url(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理可能的异常
            contents = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"URL处理异常: {urls[i]}, {result}")
                    contents.append({
                        "url": urls[i],
                        "success": False,
                        "error": f"处理异常: {str(result)}"
                    })
                else:
                    contents.append(result)
        else:
            # 串行处理
            contents = []
            for url in urls:
                result = await extract_single_url(url)
                contents.append(result)

        # 统计结果
        success_count = sum(1 for c in contents if c.get("success", False))
        self.logger.info(f"URL内容提取完成: 成功{success_count}/{len(urls)}")

        return contents
    
    async def _execute_web_search(self, query: str, count: int = 5) -> Dict[str, Any]:
        """执行网络搜索"""
        try:
            self.logger.info(f"开始网络搜索: query={query}, count={count}")
            result = await self._search_web(query, count=count)
            self.logger.info(f"网络搜索完成: success={result.get('success', True)}")
            return result
        except Exception as e:
            self.logger.error(f"网络搜索失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_search_results(self, search_results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """格式化搜索结果"""
        formatted_results = []
        
        if not search_results.get("success", True):
            return formatted_results
        
        # 根据搜索结果格式进行处理
        results_data = search_results.get("search_results", {})
        content = results_data.get("content", {})
        
        if isinstance(content, dict):
            search_result_list = content.get("search_result", [])
        else:
            # 如果是对象，尝试获取search_result属性
            search_result_list = getattr(content, "search_result", [])
        
        for i, result in enumerate(search_result_list):
            if isinstance(result, dict):
                formatted_result = {
                    "id": f"search_result_{i+1}",
                    "type": "web_search",
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "url": result.get("link", ""),
                    "publish_date": result.get("publish_date", ""),
                    "icon": result.get("icon", ""),
                    "media": result.get("media", "")
                }
            else:
                # 如果是对象，使用getattr获取属性
                formatted_result = {
                    "id": f"search_result_{i+1}",
                    "type": "web_search",
                    "title": getattr(result, "title", ""),
                    "content": getattr(result, "content", ""),
                    "url": getattr(result, "link", ""),
                    "publish_date": getattr(result, "publish_date", ""),
                    "icon": getattr(result, "icon", ""),
                    "media": getattr(result, "media", "")
                }
            
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _extract_search_content(self, search_results: Dict[str, Any]) -> str:
        """从搜索结果中提取文本内容用于总结"""
        content_list = []
        
        results_data = search_results.get("search_results", {})
        content = results_data.get("content", {})
        
        if isinstance(content, dict):
            search_result_list = content.get("search_result", [])
        else:
            search_result_list = getattr(content, "search_result", [])
        
        if not search_result_list:
            return "无搜索结果"
        
        for i, result in enumerate(search_result_list):
            if isinstance(result, dict):
                title = result.get("title", "")
                content_text = result.get("content", "")
                publish_date = result.get("publish_date", "")
            else:
                title = getattr(result, "title", "")
                content_text = getattr(result, "content", "")
                publish_date = getattr(result, "publish_date", "")
            
            result_text = f"搜索结果{i+1}:\n标题: {title}\n发布时间: {publish_date}\n内容: {content_text}\n"
            content_list.append(result_text)
        
        return "\n".join(content_list)
    
    def _build_summary_prompt(self, original_query: str, search_content: str) -> str:
        """构建搜索总结的用户提示词"""
        return f"""用户搜索需求: {original_query}

以下是网络搜索返回的结果:
{search_content}

请根据用户的搜索需求，将上述搜索结果整理为数个有用的信息块。每个信息块应该有完整的时间、来龙去脉，而不是碎片化的信息。使用合适的颗粒度进行整理。

要求：
1. 保持信息的准确性和完整性
2. 按照时间顺序或逻辑顺序组织信息
3. 突出与搜索需求最相关的内容
4. 避免重复信息
5. 提供清晰的标题和内容
"""
    
    async def _generate_search_summary(self, query: str, search_results: Dict[str, Any], user_id: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """生成搜索总结"""
        try:
            # 构建总结提示词
            search_content = self._extract_search_content(search_results)
            user_prompt = self._build_summary_prompt(query, search_content)
            
            # 构建消息
            messages = [
                {"role": "user", "content": user_prompt}
            ]
            
            # 流式调用LLM（带追踪）
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成搜索总结失败: {e}")
            yield await self._emit_event("error", f"生成总结失败: {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "websearch",
            "description": "竖屏短剧网络检索智能体，专注于网络搜索和信息检索",
            "capabilities": [
                "智谱AI网络搜索",
                "搜索结果智能总结",
                "多阶段搜索流程",
                "搜索结果格式化",
                "信息提取和整理"
            ],
            "search_config": self.search_config
        })
        return base_info

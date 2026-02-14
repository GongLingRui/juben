"""
文本处理评估智能体
基于agent as tool机制，实现智能体间的模块化外包和上下文隔离
"""
import asyncio
import json
import re
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from .base_juben_agent import BaseJubenAgent


class TextProcessorEvaluationAgent(BaseJubenAgent):
    """
    文本处理评估智能体
    
    功能：
    1. 文本拼接：将多个字符串变量格式化为指定格式
    2. 文本截断：根据最大长度截断文本内容
    3. 文本格式化：统一处理文本格式
    """
    
    def __init__(self):
        super().__init__("text_processor_evaluation_agent")
        self.logger.info("📝 文本处理评估智能体初始化完成")
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理文本处理请求
        
        Args:
            request_data: 包含文本处理参数的请求数据
            context: 上下文信息
            
        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 提取请求参数
            operation = request_data.get("operation", "concat")  # concat 或 truncate
            text_input = request_data.get("input", "")
            max_length = request_data.get("max_length", 10000)
            
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system_message", "📝 开始处理文本...")
            
            # 对于拼接操作，提取各个字符串参数
            if operation == "concat":
                name = request_data.get("name", "")
                ip_type = request_data.get("type", "")
                author = request_data.get("author", "")
                
                # 执行文本拼接
                result = await self._concat_text(name, ip_type, author)
                
            elif operation == "truncate":
                # 执行文本截断
                result = await self._truncate_text(text_input, max_length)
            
            else:
                raise ValueError(f"不支持的文本处理操作: {operation}")
            
            # 发送处理结果
            yield await self._emit_event("llm_chunk", result)
            
            # 发送完成事件
            yield await self._emit_event("system_message", "✅ 文本处理完成")
            
            # 保存处理结果
            await self.save_chat_message(
                user_id, session_id, "text_processing", 
                result, {"operation": operation, "agent": self.agent_name}
            )
            
        except Exception as e:
            self.logger.error(f"❌ 文本处理失败: {e}")
            yield await self._emit_event("error", f"文本处理失败: {str(e)}")
    
    async def _concat_text(self, name: str, ip_type: str, author: str) -> str:
        """
        执行文本拼接操作
        
        Args:
            name: 作品名称
            ip_type: IP类型
            author: 作者
            
        Returns:
            str: 拼接后的文本
        """
        try:
            # 按照指定格式拼接：`{{IP类型}} 《{{作品名}}》 {{作者}}`
            result = f"{ip_type} 《{name}》 {author}"
            
            self.logger.info(f"📝 文本拼接完成: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 文本拼接失败: {e}")
            return f"{ip_type} 《{name}》 {author}"  # 回退到简单拼接
    
    async def _truncate_text(self, text_input: str, max_length: int) -> str:
        """
        执行文本截断操作（增强版：带参数验证）

        Args:
            text_input: 输入文本
            max_length: 最大长度

        Returns:
            str: 截断后的文本
        """
        try:
            # ========== 参数验证 ==========
            if not text_input or not isinstance(text_input, str):
                return ""

            if max_length <= 0:
                self.logger.warning(f"max_length参数不合法({max_length})，使用默认值10000")
                max_length = 10000

            # 如果文本长度小于等于最大长度，直接返回
            if len(text_input) <= max_length:
                return text_input

            # 截断文本
            truncated_text = text_input[:max_length]

            # 尝试在句号、感叹号或问号处截断，避免截断句子
            last_sentence_end = max(
                truncated_text.rfind('。'),
                truncated_text.rfind('！'),
                truncated_text.rfind('？'),
                truncated_text.rfind('.'),
                truncated_text.rfind('!'),
                truncated_text.rfind('?')
            )

            if last_sentence_end > max_length * 0.8:  # 如果句号位置在80%以内，则在此处截断
                truncated_text = truncated_text[:last_sentence_end + 1]

            self.logger.info(f"📝 文本截断完成: 原始长度={len(text_input)}, 截断后长度={len(truncated_text)}")
            return truncated_text

        except ValueError as e:
            self.logger.error(f"❌ 文本截断参数错误: {e}")
            # 降级处理：使用安全的截断
            safe_length = max(1, min(max_length if max_length > 0 else 10000, len(text_input)))
            return text_input[:safe_length] if text_input else ""
        except Exception as e:
            self.logger.error(f"❌ 文本截断失败: {e}")
            # 降级处理：使用安全的截断
            safe_length = max(1, min(max_length if max_length > 0 else 10000, len(text_input)))
            return text_input[:safe_length] if text_input else ""

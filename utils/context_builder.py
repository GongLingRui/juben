"""
Juben上下文构建器
 ，提供智能上下文构建能力
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

try:
    from ..utils.logger import JubenLogger
    from ..utils.storage_manager import get_storage
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from utils.logger import JubenLogger
    from utils.storage_manager import get_storage


class JubenContextBuilder:
    """
    Juben上下文构建器
    
    核心功能：
    1. 智能上下文构建
    2. Notes系统集成
    3. 文件引用处理
    4. 对话历史管理
    5. 上下文压缩和优化
    """
    
    def __init__(self):
        self.logger = JubenLogger("ContextBuilder")
        self.storage_manager = get_storage()
        
        self.logger.info("上下文构建器初始化完成")
    
    async def build_action_context(
        self,
        user_id: str,
        session_id: str,
        instruction: str,
        action: str = "action",
        auto_mode: bool = False,
        user_selections: Optional[List[str]] = None
    ) -> str:
        """构建所有agent通用的简洁格式提示词"""
        try:
            context_parts = []
            
            # 1. 基础指令
            context_parts.append(f"## 当前任务")
            context_parts.append(f"指令: {instruction}")
            context_parts.append(f"操作类型: {action}")
            
            # 2. 用户选择的内容
            if user_selections:
                context_parts.append(f"\n## 用户选择的内容")
                for selection in user_selections:
                    context_parts.append(f"- {selection}")
            
            # 3. 相关Notes
            notes_context = await self._build_notes_context(user_id, session_id, action)
            if notes_context:
                context_parts.append(f"\n## 相关Notes")
                context_parts.append(notes_context)
            
            # 4. 对话历史（最近几条）
            chat_history = await self._build_chat_history(user_id, session_id, limit=3)
            if chat_history:
                context_parts.append(f"\n## 对话历史")
                context_parts.append(chat_history)
            
            # 5. 文件引用
            file_refs = await self._build_file_references(user_id, session_id)
            if file_refs:
                context_parts.append(f"\n## 文件引用")
                context_parts.append(file_refs)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"构建上下文失败: {e}")
            return f"## 当前任务\n指令: {instruction}\n操作类型: {action}"
    
    async def build_full_context(
        self,
        user_id: str,
        session_id: str,
        base_prompt: str,
        current_query: str,
        include_user_queue: bool = True,
        include_notes: bool = True,
        include_files: bool = True,
        selected_notes: Optional[List[str]] = None,
        include_chat_history: bool = False,
        include_orchestrator_timeline: bool = False
    ) -> str:
        """构建包含上下文的完整提示词"""
        try:
            context_parts = []
            
            # 1. 基础提示词
            context_parts.append(base_prompt)
            
            # 2. 当前查询
            context_parts.append(f"\n## 当前查询")
            context_parts.append(current_query)
            
            # 3. 用户消息队列
            if include_user_queue:
                user_queue = await self._build_user_queue(user_id, session_id)
                if user_queue:
                    context_parts.append(f"\n## 用户消息队列")
                    context_parts.append(user_queue)
            
            # 4. Notes信息
            if include_notes:
                notes_context = await self._build_notes_context(user_id, session_id, None, selected_notes)
                if notes_context:
                    context_parts.append(f"\n## Notes信息")
                    context_parts.append(notes_context)
            
            # 5. 文件引用
            if include_files:
                file_refs = await self._build_file_references(user_id, session_id)
                if file_refs:
                    context_parts.append(f"\n## 文件引用")
                    context_parts.append(file_refs)
            
            # 6. 对话历史
            if include_chat_history:
                chat_history = await self._build_chat_history(user_id, session_id, limit=10)
                if chat_history:
                    context_parts.append(f"\n## 对话历史")
                    context_parts.append(chat_history)
            
            # 7. Orchestrator时间线
            if include_orchestrator_timeline:
                timeline = await self._build_orchestrator_timeline(user_id, session_id)
                if timeline:
                    context_parts.append(f"\n## Orchestrator时间线")
                    context_parts.append(timeline)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"构建完整上下文失败: {e}")
            return f"{base_prompt}\n\n## 当前查询\n{current_query}"
    
    async def _build_notes_context(
        self, 
        user_id: str, 
        session_id: str, 
        action: Optional[str] = None,
        selected_notes: Optional[List[str]] = None
    ) -> str:
        """构建Notes上下文"""
        try:
            notes = await self.storage_manager.get_notes(user_id, session_id, action)
            if not notes:
                return ""
            
            context_parts = []
            for note in notes:
                # 如果指定了selected_notes，只包含选中的notes
                if selected_notes and note.get('name') not in selected_notes:
                    continue
                
                select_status = "✅" if note.get('select_status', 0) == 1 else "⭕"
                name = note.get('name', '')
                title = note.get('title', '')
                context = note.get('context', '')
                note_action = note.get('action', '')
                
                context_parts.append(f"- {select_status} [{note_action}] {name}: {title}")
                if context:
                    context_parts.append(f"  {context}")
            
            return "\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            self.logger.error(f"构建Notes上下文失败: {e}")
            return ""
    
    async def _build_user_queue(self, user_id: str, session_id: str) -> str:
        """构建用户消息队列"""
        try:
            # 这里需要实现用户消息队列的获取逻辑
            # 暂时返回空字符串
            return ""
        except Exception as e:
            self.logger.error(f"构建用户消息队列失败: {e}")
            return ""
    
    async def _build_chat_history(self, user_id: str, session_id: str, limit: int = 10) -> str:
        """构建对话历史"""
        try:
            messages = await self.storage_manager.get_chat_messages(user_id, session_id, limit)
            if not messages:
                return ""
            
            context_parts = []
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                timestamp = msg.get('timestamp', '')
                
                context_parts.append(f"[{role}] {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"构建对话历史失败: {e}")
            return ""
    
    async def _build_file_references(self, user_id: str, session_id: str) -> str:
        """构建文件引用"""
        try:
            # 这里需要实现文件引用的获取逻辑
            # 暂时返回空字符串
            return ""
        except Exception as e:
            self.logger.error(f"构建文件引用失败: {e}")
            return ""
    
    async def _build_orchestrator_timeline(self, user_id: str, session_id: str) -> str:
        """构建Orchestrator时间线"""
        try:
            # 这里需要实现Orchestrator时间线的获取逻辑
            # 暂时返回空字符串
            return ""
        except Exception as e:
            self.logger.error(f"构建Orchestrator时间线失败: {e}")
            return ""
    
    async def compress_context(self, context: str, max_length: int = 4000) -> str:
        """压缩上下文，保持重要信息"""
        try:
            if len(context) <= max_length:
                return context
            
            # 简单的压缩策略：保留开头和结尾
            half_length = max_length // 2
            compressed = context[:half_length] + "\n\n[... 上下文已压缩 ...]\n\n" + context[-half_length:]
            
            self.logger.info(f"上下文已压缩: {len(context)} -> {len(compressed)}")
            return compressed
            
        except Exception as e:
            self.logger.error(f"压缩上下文失败: {e}")
            return context
    
    async def extract_key_information(self, context: str) -> Dict[str, Any]:
        """从上下文中提取关键信息"""
        try:
            key_info = {
                'total_length': len(context),
                'has_notes': 'Notes信息' in context,
                'has_files': '文件引用' in context,
                'has_chat_history': '对话历史' in context,
                'has_timeline': 'Orchestrator时间线' in context,
                'sections': []
            }
            
            # 提取各个部分
            sections = context.split('\n## ')
            for section in sections:
                if section.strip():
                    key_info['sections'].append(section.strip())
            
            return key_info
            
        except Exception as e:
            self.logger.error(f"提取关键信息失败: {e}")
            return {'error': str(e)}
    
    async def optimize_context_for_llm(self, context: str, llm_max_tokens: int = 4000) -> str:
        """为LLM优化上下文"""
        try:
            # 估算token数量（简单估算：1个中文字符约等于1个token）
            estimated_tokens = len(context)
            
            if estimated_tokens <= llm_max_tokens:
                return context
            
            # 如果超出限制，进行压缩
            target_length = int(llm_max_tokens * 0.8)  # 留出20%的缓冲
            optimized = await self.compress_context(context, target_length)
            
            self.logger.info(f"上下文已优化: {estimated_tokens} -> {len(optimized)} tokens")
            return optimized
            
        except Exception as e:
            self.logger.error(f"优化上下文失败: {e}")
            return context


# 全局上下文构建器实例
_juben_context_builder = None

def get_juben_context_builder() -> JubenContextBuilder:
    """获取上下文构建器实例"""
    global _juben_context_builder
    if _juben_context_builder is None:
        _juben_context_builder = JubenContextBuilder()
    return _juben_context_builder

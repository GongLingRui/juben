"""
上下文管理器集成Mixin
===================

将EnhancedContextManager的功能集成到BaseJubenAgent中

使用方式：
```python
class MyAgent(BaseJubenAgent, ContextManagementMixin):
    def __init__(self):
        super().__init__("my_agent")
        # ... 其他初始化

    async def process_request(self, request_data, context=None):
        # 自动享受增强的上下文管理
        user_id = request_data.get("user_id", "unknown")
        session_id = request_data.get("session_id", "unknown")

        # 重建优化的上下文
        messages = await self.rebuild_optimized_context(
            session_id, user_id, request_data.get("input", "")
        )

        # 正常调用LLM
        response = await self._call_llm(messages, user_id, session_id)
```
"""
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    from .enhanced_context_manager import (
        EnhancedContextManager,
        get_enhanced_context_manager,
        MemoryLevel,
        ChunkType
    )
    from .logger import JubenLogger
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from enhanced_context_manager import (
        EnhancedContextManager,
        get_enhanced_context_manager,
        MemoryLevel,
        ChunkType
    )
    from logger import JubenLogger


class ContextManagementMixin:
    """
    上下文管理Mixin类

    提供增强的上下文管理功能，可以混入到任何Agent中
    """

    def __init__(self, *args, **kwargs):
        # 延迟初始化，避免循环导入
        self._context_manager: Optional[EnhancedContextManager] = None
        self._context_manager_initialized = False
        # 只在有父类需要参数时才调用 super().__init__()
        # 这样可以避免在多重继承链中出现 TypeError
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            # 如果父类是 object 或不需要参数，忽略错误
            pass

    async def _get_context_manager(self) -> EnhancedContextManager:
        """获取上下文管理器（延迟初始化）"""
        if self._context_manager is None:
            self._context_manager = get_enhanced_context_manager()
            if not self._context_manager_initialized:
                await self._context_manager.initialize()
                self._context_manager_initialized = True
        return self._context_manager

    # ==================== 上下文重建 ====================

    async def rebuild_optimized_context(
        self,
        session_id: str,
        user_id: str,
        new_message: str,
        include_system_prompt: bool = True,
        extra_messages: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        重建优化的上下文（核心方法）

        这个方法会：
        1. 自动应用滚动窗口压缩
        2. 智能摘要历史对话
        3. 保留关键信息锚点
        4. 确保不超过token限制

        Args:
            session_id: 会话ID
            user_id: 用户ID
            new_message: 新消息内容
            include_system_prompt: 是否包含系统提示词

        Returns:
            优化后的消息列表
        """
        context_manager = await self._get_context_manager()

        system_prompt = self.system_prompt if include_system_prompt else ""

        messages = await context_manager.rebuild_context_for_llm(
            session_id=session_id,
            user_id=user_id,
            system_prompt=system_prompt,
            new_message=new_message,
            extra_messages=extra_messages
        )

        self.logger.info(f"重建优化上下文: {len(messages)}条消息")
        return messages

    async def add_message_to_context(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加消息到上下文（自动应用滚动窗口）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            metadata: 元数据

        Returns:
            是否添加成功
        """
        context_manager = await self._get_context_manager()

        message = {
            "role": role,
            "content": content,
            "timestamp": context_manager.count_tokens(content),
            **(metadata or {})
        }

        return await context_manager.add_to_context(
            session_id=session_id,
            user_id=user_id,
            message=message
        )

    # ==================== 语义分块 ====================

    async def chunk_long_content(
        self,
        content: str,
        chunk_type: str = "dialogue"
    ) -> List[Dict[str, Any]]:
        """
        对长内容进行语义分块

        Args:
            content: 长文本内容
            chunk_type: 分块类型 (dialogue/scene/plot_point/action)

        Returns:
            分块结果列表
        """
        context_manager = await self._get_context_manager()

        try:
            chunk_type_enum = ChunkType(chunk_type)
            chunks = await context_manager.semantic_chunk(content, chunk_type_enum)

            return [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "type": chunk.chunk_type.value,
                    "tokens": chunk.token_count,
                    "importance": chunk.importance,
                    "keywords": chunk.keywords,
                    "characters": chunk.characters
                }
                for chunk in chunks
            ]
        except ValueError:
            self.logger.warning(f"未知的分块类型: {chunk_type}")
            return []

    # ==================== 剧本记忆 ====================

    async def create_script_memory(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """创建剧本记忆"""
        context_manager = await self._get_context_manager()
        memory = await context_manager.create_script_memory(user_id, session_id)
        return {
            "session_id": memory.session_id,
            "user_id": memory.user_id,
            "created_at": memory.created_at
        }

    async def update_character(
        self,
        user_id: str,
        session_id: str,
        character_name: str,
        description: Optional[str] = None,
        personality: Optional[str] = None,
        background: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        更新角色信息

        Args:
            user_id: 用户ID
            session_id: 会话ID
            character_name: 角色名
            description: 角色描述
            personality: 性格特点
            background: 背景故事
            **kwargs: 其他属性

        Returns:
            是否更新成功
        """
        context_manager = await self._get_context_manager()

        info = {"name": character_name, **kwargs}
        if description:
            info["description"] = description
        if personality:
            info["personality"] = personality
        if background:
            info["background"] = background

        await context_manager.update_character_info(user_id, session_id, character_name, info)
        return True

    async def add_plot_thread(
        self,
        user_id: str,
        session_id: str,
        plot_description: str,
        status: str = "active"
    ) -> bool:
        """添加情节线"""
        context_manager = await self._get_context_manager()
        await context_manager.add_plot_thread(user_id, session_id, plot_description, status)
        return True

    async def get_script_summary(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """获取剧本上下文摘要"""
        context_manager = await self._get_context_manager()
        return await context_manager.get_script_context_summary(user_id, session_id)

    async def get_graph_summary(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """获取图结构摘要"""
        context_manager = await self._get_context_manager()
        return await context_manager.get_graph_context_summary(user_id, session_id)

    # ==================== 上下文健康 ====================

    async def get_context_health_report(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取上下文健康报告"""
        context_manager = await self._get_context_manager()
        return await context_manager.get_context_health(session_id, user_id)

    async def should_compress_context(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """检查是否需要压缩上下文"""
        health = await self.get_context_health_report(session_id, user_id)

        # 根据健康报告判断
        status = health.get("status", "")
        usage_ratio_str = health.get("usage_ratio", "0%")

        # 解析使用率
        try:
            usage_ratio = float(usage_ratio_str.rstrip('%')) / 100
        except:
            usage_ratio = 0

        return status == "warning" or usage_ratio > 0.8

    # ==================== Token计算 ====================

    def count_tokens(self, text: str) -> int:
        """计算文本的token数（使用增强计数器）"""
        # 这里可以使用同步方法，因为只是计算
        import re

        if not text:
            return 0

        # 中文：约1字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # 英文/数字：约4字符=1token
        other_chars = len(text) - chinese_chars

        return chinese_chars + max(1, other_chars // 4)

    def estimate_context_tokens(
        self,
        messages: List[Dict[str, Any]]
    ) -> int:
        """估算消息列表的总token数"""
        return sum(
            self.count_tokens(msg.get("content", "")) + 5  # +5 for role/metadata
            for msg in messages
        )

    # ==================== 辅助方法 ====================

    async def log_context_status(
        self,
        session_id: str,
        user_id: str
    ):
        """记录上下文状态到日志"""
        health = await self.get_context_health_report(session_id, user_id)

        self.logger.info(f"上下文健康状态 [{user_id}/{session_id}]:")
        self.logger.info(f"  状态: {health.get('status', 'unknown')}")
        self.logger.info(f"  Token使用: {health.get('usage_ratio', 'N/A')}")
        self.logger.info(f"  消息数: {health.get('message_count', 0)}")
        self.logger.info(f"  压缩次数: {health.get('compression_count', 0)}")

        recommendations = health.get('recommendations', [])
        if recommendations:
            self.logger.info("  建议:")
            for rec in recommendations:
                self.logger.info(f"    {rec}")

    async def force_compress_context(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        强制压缩上下文

        当上下文接近上限时，可以手动触发此方法
        """
        context_manager = await self._get_context_manager()

        # 添加一个触发消息来激活压缩
        await context_manager.add_to_context(
            session_id=session_id,
            user_id=user_id,
            message={
                "role": "system",
                "content": "[触发压缩]",
                "force_compress": True
            }
        )

        return await self.get_context_health_report(session_id, user_id)

    # ==================== 内部笔记管理（新增） ====================

    async def add_note(
        self,
        session_id: str,
        user_id: str,
        note_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加内部笔记（不发送给LLM）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            note_type: 笔记类型
            content: 内容
            metadata: 元数据

        Returns:
            是否添加成功
        """
        context_manager = await self._get_context_manager()
        return await context_manager.add_internal_note(
            session_id, user_id, note_type, content, metadata
        )

    async def get_notes(
        self,
        session_id: str,
        user_id: str,
        note_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取内部笔记"""
        context_manager = await self._get_context_manager()
        return await context_manager.get_internal_notes(
            session_id, user_id, note_type, limit
        )

    async def clear_notes(
        self,
        session_id: str,
        user_id: str,
        note_type: Optional[str] = None
    ) -> int:
        """清除内部笔记"""
        context_manager = await self._get_context_manager()
        return await context_manager.clear_internal_notes(
            session_id, user_id, note_type
        )

    # ==================== 草稿纸管理（新增） ====================

    async def add_to_scratchpad(
        self,
        session_id: str,
        user_id: str,
        content: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加到草稿纸

        Args:
            session_id: 会话ID
            user_id: 用户ID
            content: 内容
            importance: 重要性 (0-1)
            tags: 标签
            metadata: 元数据

        Returns:
            是否添加成功
        """
        context_manager = await self._get_context_manager()
        return await context_manager.add_to_scratchpad(
            session_id, user_id, content, importance, tags, metadata
        )

    async def select_from_scratchpad(
        self,
        session_id: str,
        user_id: str,
        current_task: str,
        max_items: int = 5,
        min_importance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        从草稿纸选择相关信息

        Args:
            session_id: 会话ID
            user_id: 用户ID
            current_task: 当前任务描述
            max_items: 最大返回数量
            min_importance: 最小重要性阈值

        Returns:
            选中的条目
        """
        context_manager = await self._get_context_manager()
        return await context_manager.select_from_scratchpad(
            session_id, user_id, current_task, max_items, min_importance
        )

    async def clear_scratchpad(
        self,
        session_id: str,
        user_id: str
    ) -> int:
        """清空草稿纸"""
        context_manager = await self._get_context_manager()
        return await context_manager.clear_scratchpad(session_id, user_id)

    # ==================== 子任务隔离（新增） ====================

    async def store_subtask_result(
        self,
        session_id: str,
        user_id: str,
        subtask_id: str,
        result: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        存储子任务结果（隔离）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            subtask_id: 子任务ID
            result: 结果
            metadata: 元数据

        Returns:
            是否存储成功
        """
        context_manager = await self._get_context_manager()
        return await context_manager.store_subtask_result(
            session_id, user_id, subtask_id, result, metadata
        )

    async def get_subtask_result(
        self,
        session_id: str,
        user_id: str,
        subtask_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取子任务结果"""
        context_manager = await self._get_context_manager()
        return await context_manager.get_subtask_result(
            session_id, user_id, subtask_id
        )

    async def list_subtask_results(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """列出所有子任务结果"""
        context_manager = await self._get_context_manager()
        return await context_manager.list_subtask_results(session_id, user_id)

    # ==================== 便捷方法：子任务调用（新增） ====================

    async def call_subagent_isolated(
        self,
        agent: Any,
        request_data: Dict[str, Any],
        subtask_id: str,
        user_id: str,
        session_id: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        调用子智能体（带隔离）

        子任务结果会自动存储到internal_notes中，不会直接混入主对话

        Args:
            agent: 子智能体实例
            request_data: 请求数据
            subtask_id: 子任务ID
            user_id: 用户ID
            session_id: 会话ID
            timeout: 超时时间

        Returns:
            子任务结果
        """
        import asyncio

        try:
            # 准备子任务上下文
            subtask_context = {
                "user_id": user_id,
                "session_id": session_id,
                "parent_agent": self.agent_name if hasattr(self, 'agent_name') else "unknown",
                "subtask_id": subtask_id,
                "tool_call": True
            }

            # 记录开始时间
            start_time = datetime.now()

            # 调用子智能体（带超时）
            results = []

            async def collect_results():
                async for event in agent.process_request(request_data, subtask_context):
                    if event.get("event_type") == "llm_chunk":
                        results.append(event.get("data", ""))

            await asyncio.wait_for(collect_results(), timeout=timeout)

            # 计算耗时
            elapsed = (datetime.now() - start_time).total_seconds()

            # 整合结果
            combined_result = "".join(results)

            # 存储到子任务结果（隔离）
            await self.store_subtask_result(
                session_id, user_id, subtask_id,
                {
                    "success": True,
                    "result": combined_result,
                    "agent": agent.agent_name if hasattr(agent, 'agent_name') else str(agent),
                    "elapsed_time": elapsed
                },
                metadata={
                    "request": request_data,
                    "timeout": timeout,
                    "completed_at": datetime.now().isoformat()
                }
            )

            # 同时添加到内部笔记
            await self.add_note(
                session_id, user_id, "subtask_result",
                f"子任务 {subtask_id} 完成，耗时 {elapsed:.2f}s",
                metadata={
                    "subtask_id": subtask_id,
                    "agent": agent.agent_name if hasattr(agent, 'agent_name') else str(agent),
                    "elapsed_time": elapsed
                }
            )

            return {
                "success": True,
                "subtask_id": subtask_id,
                "result": combined_result,
                "elapsed_time": elapsed
            }

        except asyncio.TimeoutError:
            error_msg = f"子任务 {subtask_id} 超时({timeout}s)"

            # 存储失败结果
            await self.store_subtask_result(
                session_id, user_id, subtask_id,
                {
                    "success": False,
                    "error": error_msg,
                    "agent": agent.agent_name if hasattr(agent, 'agent_name') else str(agent)
                }
            )

            return {
                "success": False,
                "subtask_id": subtask_id,
                "error": error_msg
            }

        except Exception as e:
            error_msg = f"子任务 {subtask_id} 失败: {str(e)}"

            # 存储失败结果
            await self.store_subtask_result(
                session_id, user_id, subtask_id,
                {
                    "success": False,
                    "error": str(e),
                    "agent": agent.agent_name if hasattr(agent, 'agent_name') else str(agent)
                }
            )

            return {
                "success": False,
                "subtask_id": subtask_id,
                "error": str(e)
            }

    # ==================== RAG自动加载（新增） ====================

    async def rebuild_context_with_rag(
        self,
        session_id: str,
        user_id: str,
        system_prompt: str,
        new_message: str,
        enable_auto_rag: bool = True,
        max_rag_items: int = 3,
        extra_messages: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        重建上下文（带RAG自动加载）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            system_prompt: 系统提示词
            new_message: 新消息
            enable_auto_rag: 是否启用自动RAG
            max_rag_items: 最大RAG条目数

        Returns:
            包含RAG内容的完整上下文
        """
        context_manager = await self._get_context_manager()
        return await context_manager.rebuild_context_with_rag(
            session_id, user_id, system_prompt, new_message,
            enable_auto_rag, max_rag_items=max_rag_items, extra_messages=extra_messages
        )

    async def auto_load_rag(
        self,
        session_id: str,
        user_id: str,
        query: str,
        top_k: int = 3,
        collection: str = "script_segments"
    ) -> List[Dict[str, Any]]:
        """
        自动加载RAG内容

        Args:
            session_id: 会话ID
            user_id: 用户ID
            query: 查询内容
            top_k: 返回数量
            collection: 集合名称

        Returns:
            RAG检索结果
        """
        context_manager = await self._get_context_manager()
        return await context_manager.auto_load_rag_context(
            session_id, user_id, query,
            enable_rag=True, enable_hybrid=True,
            top_k=top_k, collection=collection
        )

    # ==================== 智能选择（新增） ====================

    async def smart_select_context(
        self,
        session_id: str,
        user_id: str,
        current_task: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        智能选择上下文（综合选择）

        整合所有选择策略：
        1. 从草稿纸选择
        2. 从长期记忆选择
        3. 从RAG选择

        Args:
            session_id: 会话ID
            user_id: 用户ID
            current_task: 当前任务
            sources: 数据源 (scratchpad|memory|rag|all)

        Returns:
            选择的上下文
        """
        context_manager = await self._get_context_manager()
        return await context_manager.smart_select_context(
            session_id, user_id, current_task, sources
        )


class LongScriptAgentMixin(ContextManagementMixin):
    """
    长剧本专用Mixin

    继承自ContextManagementMixin，添加更多剧本特定功能
    """

    async def process_long_script(
        self,
        script_content: str,
        user_id: str,
        session_id: str,
        analysis_type: str = "full"
    ) -> Any:
        """
        处理长剧本

        Args:
            script_content: 剧本内容
            user_id: 用户ID
            session_id: 会话ID
            analysis_type: 分析类型 (full/plot/characters/scenes)

        Returns:
            分析结果
        """
        # 1. 首先检查内容长度
        token_count = self.count_tokens(script_content)

        self.logger.info(f"开始处理长剧本: 约{token_count} tokens")

        if token_count < 10000:
            # 短剧本，直接处理
            return await self._process_short_script(script_content, user_id, session_id)
        else:
            # 长剧本，使用分块处理
            return await self._process_chunked_script(
                script_content, user_id, session_id, analysis_type
            )

    async def _process_short_script(
        self,
        script_content: str,
        user_id: str,
        session_id: str
    ):
        """处理短剧本"""
        # 直接添加到上下文并分析
        await self.add_message_to_context(
            session_id, user_id, "user", script_content
        )

        # 重建优化的上下文
        messages = await self.rebuild_optimized_context(
            session_id, user_id, script_content
        )

        # 调用LLM分析
        return await self._call_llm(messages, user_id, session_id)

    async def _process_chunked_script(
        self,
        script_content: str,
        user_id: str,
        session_id: str,
        analysis_type: str
    ):
        """分块处理长剧本"""
        # 1. 语义分块
        chunks = await self.chunk_long_content(script_content, "scene")

        self.logger.info(f"剧本分为 {len(chunks)} 个场景块")

        # 2. 逐块处理
        results = []
        for i, chunk in enumerate(chunks):
            self.logger.info(f"处理场景块 {i+1}/{len(chunks)}: {chunk['id']}")

            # 为每个块创建上下文
            chunk_messages = await self.rebuild_optimized_context(
                session_id, user_id, f"【场景{ i+1}分析】{chunk['content'][:500]}..."
            )

            # 添加系统提示
            chunk_messages.insert(0, {
                "role": "system",
                "content": f"""你是专业的剧本分析师。请分析以下场景块（{i+1}/{len(chunks)}）：

场景内容：
{chunk['content']}

请提供：
1. 场景概要（50字内）
2. 主要角色
3. 关键动作/对话
4. 情节推进作用
5. 与整体剧本的关系
"""
            })

            # 调用LLM
            result = await self._call_llm(chunk_messages, user_id, session_id)
            results.append({
                "chunk_id": chunk['id'],
                "chunk_index": i,
                "analysis": result,
                "tokens": chunk['tokens']
            })

        # 3. 整合结果
        summary = await self._integrate_chunk_results(results, user_id, session_id)

        return {
            "total_chunks": len(chunks),
            "chunk_analyses": results,
            "integrated_summary": summary
        }

    async def _integrate_chunk_results(
        self,
        results: List[Dict[str, Any]],
        user_id: str,
        session_id: str
    ) -> str:
        """整合分块分析结果"""
        # 构建整合提示
        all_analyses = "\n\n".join([
            f"## 场景{i+1}分析\n{r['analysis']}"
            for i, r in enumerate(results)
        ])

        integrate_prompt = f"""请整合以下各场景的分析，生成完整的剧本分析报告：

{all_analyses}

请提供：
1. 整体剧情概要
2. 主要角色关系
3. 情节发展脉络
4. 关键转折点
5. 剧本评价与建议
"""

        # 使用独立的上下文调用LLM
        response = await self._call_llm(
            [{"role": "user", "content": integrate_prompt}],
            user_id,
            session_id
        )

        return response


# ==================== 便捷函数 ====================

async def rebuild_context_with_health_check(
    agent: Any,
    session_id: str,
    user_id: str,
    new_message: str
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    重建上下文并附带健康检查

    Returns:
        (优化后的消息列表, 健康报告)
    """
    # 检查agent是否具有context management功能
    if not hasattr(agent, 'rebuild_optimized_context'):
        raise AttributeError("Agent需要混入ContextManagementMixin")

    # 重建上下文
    messages = await agent.rebuild_optimized_context(
        session_id, user_id, new_message
    )

    # 获取健康报告
    health = await agent.get_context_health_report(session_id, user_id)

    return messages, health


async def safe_process_long_content(
    agent: Any,
    content: str,
    user_id: str,
    session_id: str,
    max_tokens: int = 100000
) -> str:
    """
    安全地处理长内容

    自动检测内容长度，决定是否需要分块处理

    Returns:
        处理结果
    """
    if not hasattr(agent, 'count_tokens'):
        raise AttributeError("Agent需要混入ContextManagementMixin")

    token_count = agent.count_tokens(content)

    if token_count <= max_tokens:
        # 直接处理
        messages = await agent.rebuild_optimized_context(
            session_id, user_id, content
        )
        return await agent._call_llm(messages, user_id, session_id)
    else:
        # 需要分块
        chunks = await agent.chunk_long_content(content, "dialogue")

        # 处理第一个块
        first_chunk = chunks[0]
        messages = await agent.rebuild_optimized_context(
            session_id, user_id, first_chunk['content']
        )

        return await agent._call_llm(messages, user_id, session_id)

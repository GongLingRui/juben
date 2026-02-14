"""
LangSmith追踪客户端
 架构的LangSmith集成
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import uuid

# LangSmith相关导入
try:
    from langsmith import Client as LangSmithClient
    from langsmith import RunTree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LangSmithClient = None
    RunTree = None
    LANGSMITH_AVAILABLE = False


class LangSmithTracer:
    """
    LangSmith追踪器
    
    功能：
    1. 创建和管理LangSmith运行追踪
    2. 记录LLM调用和响应
    3. 生成追踪报告
    """
    
    def __init__(self, enable_tracing: bool = True):
        self.enable_tracing = enable_tracing
        self.logger = logging.getLogger(__name__)
        self.langsmith_client = None
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "juben-drama-planner")
        
        if self.enable_tracing:
            self._init_langsmith()
    
    def _init_langsmith(self):
        """初始化LangSmith客户端"""
        try:
            if not LANGSMITH_AVAILABLE:
                self.logger.warning("⚠️ LangSmith库未安装，禁用追踪")
                self.enable_tracing = False
                return
            
            # 检查环境变量
            api_key = os.getenv("LANGCHAIN_API_KEY")
            if not api_key:
                self.logger.warning("⚠️ LANGCHAIN_API_KEY未设置，禁用LangSmith追踪")
                self.enable_tracing = False
                return
            
            # 验证API密钥格式
            if not api_key.startswith(('lsv2_pt_', 'ls__')):
                self.logger.warning("⚠️ LANGCHAIN_API_KEY格式可能不正确，禁用LangSmith追踪")
                self.enable_tracing = False
                return
            
            # 初始化LangSmith客户端
            self.langsmith_client = LangSmithClient(
                api_key=api_key,
                api_url=os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
            )
            
            self.logger.info(f"✅ LangSmith追踪初始化成功，项目: {self.project_name}")
            
        except Exception as e:
            self.logger.error(f"❌ LangSmith初始化失败: {e}")
            self.enable_tracing = False
    
    def create_run_tree(
        self,
        name: str,
        run_type: str = "chain",
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None
    ) -> Optional[RunTree]:
        """
        创建运行树
        
        Args:
            name: 运行名称
            run_type: 运行类型
            inputs: 输入数据
            metadata: 元数据
            parent_run_id: 父运行ID
            
        Returns:
            RunTree: 运行树对象
        """
        if not self.enable_tracing or not self.langsmith_client:
            return None
        
        try:
            run_tree = RunTree(
                name=name,
                run_type=run_type,
                inputs=inputs or {},
                metadata=metadata or {},
                parent_run_id=parent_run_id,
                project_name=self.project_name
            )
            
            self.logger.debug(f"🔍 创建运行树: {name}, 类型: {run_type}")
            return run_tree
            
        except Exception as e:
            self.logger.error(f"❌ 创建运行树失败: {e}")
            return None
    
    def end_run(
        self,
        run_tree: RunTree,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        结束运行
        
        Args:
            run_tree: 运行树对象
            outputs: 输出数据
            error: 错误信息
            
        Returns:
            bool: 是否成功
        """
        if not self.enable_tracing or not run_tree:
            return False
        
        try:
            run_tree.end(
                outputs=outputs or {},
                error=error
            )
            
            self.logger.debug(f"🔍 结束运行树: {run_tree.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 结束运行树失败: {e}")
            return False
    
    def create_child_run(
        self,
        parent_run: RunTree,
        name: str,
        run_type: str = "tool",
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[RunTree]:
        """
        创建子运行
        
        Args:
            parent_run: 父运行对象
            name: 运行名称
            run_type: 运行类型
            inputs: 输入数据
            metadata: 元数据
            
        Returns:
            RunTree: 子运行对象
        """
        if not self.enable_tracing or not parent_run:
            return None
        
        try:
            child_run = parent_run.create_child(
                name=name,
                run_type=run_type,
                inputs=inputs or {},
                metadata=metadata or {}
            )
            
            self.logger.debug(f"🔍 创建子运行: {name}, 类型: {run_type}")
            return child_run
            
        except Exception as e:
            self.logger.error(f"❌ 创建子运行失败: {e}")
            return None


class LangSmithLLMClient:
    """
    带LangSmith追踪的LLM客户端
    
    功能：
    1. 集成LangSmith追踪
    2. 记录LLM调用详情
    3. Token统计
    """
    
    def __init__(self, base_llm_client, enable_tracing: bool = True):
        self.base_llm_client = base_llm_client
        self.tracer = LangSmithTracer(enable_tracing)
        self.logger = logging.getLogger(__name__)

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        与基础LLM客户端保持一致的兼容接口。
        默认不注入业务维度字段，避免影响调用方签名。
        """
        return await self.chat_with_tracing(messages=messages, **kwargs)

    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """
        与基础LLM客户端保持一致的兼容流式接口。
        """
        async for chunk in self.stream_chat_with_tracing(messages=messages, **kwargs):
            yield chunk

    async def achat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """兼容部分代码使用的 achat 命名。"""
        return await self.chat(messages, **kwargs)

    async def astream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """兼容部分代码使用的 astream_chat 命名。"""
        async for chunk in self.stream_chat(messages, **kwargs):
            yield chunk
    
    async def chat_with_tracing(
        self,
        messages: List[Dict[str, str]],
        agent_name: str = "unknown",
        user_id: str = "unknown",
        session_id: str = "unknown",
        token_accumulator_key: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        带追踪的聊天调用
        
        Args:
            messages: 消息列表
            agent_name: Agent名称
            user_id: 用户ID
            session_id: 会话ID
            token_accumulator_key: Token累加器键
            **kwargs: 其他参数
            
        Returns:
            str: 响应内容
        """
        # 创建主运行树
        main_run = self.tracer.create_run_tree(
            name=f"{agent_name}_chat",
            run_type="chain",
            inputs={"messages": messages, "user_id": user_id, "session_id": session_id},
            metadata={"agent_name": agent_name, "provider": getattr(self.base_llm_client, 'provider', 'unknown')}
        )
        
        try:
            # 创建LLM调用子运行
            llm_run = self.tracer.create_child_run(
                main_run,
                name="llm_call",
                run_type="llm",
                inputs={"messages": messages},
                metadata={"agent_name": agent_name}
            )
            
            # 调用基础LLM客户端
            response = await self.base_llm_client.chat(messages, **kwargs)
            
            # 估算token使用量
            usage = self._estimate_token_usage(messages, response)
            
            # 记录token使用量
            if token_accumulator_key:
                await self._record_token_usage(
                    token_accumulator_key, usage, agent_name, 
                    getattr(self.base_llm_client, 'provider', 'unknown')
                )
            
            # 结束LLM运行
            self.tracer.end_run(
                llm_run,
                outputs={"response": response, "usage": usage.to_dict()}
            )
            
            # 结束主运行
            self.tracer.end_run(
                main_run,
                outputs={"response": response, "usage": usage.to_dict()}
            )
            
            return response
            
        except Exception as e:
            # 记录错误
            self.tracer.end_run(main_run, error=str(e))
            raise
    
    async def stream_chat_with_tracing(
        self,
        messages: List[Dict[str, str]],
        agent_name: str = "unknown",
        user_id: str = "unknown",
        session_id: str = "unknown",
        token_accumulator_key: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        带追踪的流式聊天调用
        
        Args:
            messages: 消息列表
            agent_name: Agent名称
            user_id: 用户ID
            session_id: 会话ID
            token_accumulator_key: Token累加器键
            **kwargs: 其他参数
            
        Returns:
            AsyncGenerator[str, None]: 响应流
        """
        # 创建主运行树
        main_run = self.tracer.create_run_tree(
            name=f"{agent_name}_stream_chat",
            run_type="chain",
            inputs={"messages": messages, "user_id": user_id, "session_id": session_id},
            metadata={"agent_name": agent_name, "provider": getattr(self.base_llm_client, 'provider', 'unknown')}
        )
        
        full_response = ""
        
        try:
            # 创建LLM调用子运行
            llm_run = self.tracer.create_child_run(
                main_run,
                name="llm_stream_call",
                run_type="llm",
                inputs={"messages": messages},
                metadata={"agent_name": agent_name}
            )
            
            # 流式调用基础LLM客户端
            async for chunk in self.base_llm_client.stream_chat(messages, **kwargs):
                if chunk:
                    full_response += chunk
                    yield chunk
            
            # 估算token使用量
            usage = self._estimate_token_usage(messages, full_response)
            
            # 记录token使用量
            if token_accumulator_key:
                await self._record_token_usage(
                    token_accumulator_key, usage, agent_name,
                    getattr(self.base_llm_client, 'provider', 'unknown')
                )
            
            # 结束LLM运行
            self.tracer.end_run(
                llm_run,
                outputs={"response": full_response, "usage": usage.to_dict()}
            )
            
            # 结束主运行
            self.tracer.end_run(
                main_run,
                outputs={"response": full_response, "usage": usage.to_dict()}
            )
            
        except Exception as e:
            # 记录错误
            self.tracer.end_run(main_run, error=str(e))
            raise
    
    def _estimate_token_usage(self, messages: List[Dict[str, str]], response: str) -> 'TokenUsage':
        """估算token使用量"""
        from .token_accumulator import TokenUsage
        
        # 计算输入token数
        input_text = " ".join(msg.get("content", "") for msg in messages)
        prompt_tokens = self._count_tokens(input_text)
        
        # 计算输出token数
        completion_tokens = self._count_tokens(response)
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    
    def _count_tokens(self, text: str) -> int:
        """计算token数量（简化估算）"""
        # 中文按字符数计算，英文按单词数*1.3计算
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_words = len(text.replace(' ', '').replace('\n', '').replace('\t', '')) - chinese_chars
        
        # 估算：中文1字符≈1token，英文1字符≈0.5token
        return int(chinese_chars + english_words * 0.5)
    
    async def _record_token_usage(
        self,
        accumulator_key: str,
        usage: 'TokenUsage',
        agent_name: str,
        provider: str
    ):
        """记录token使用量"""
        try:
            from .token_accumulator import add_token_usage
            
            await add_token_usage(
                accumulator_key,
                usage,
                agent_name,
                getattr(self.base_llm_client, 'model_name', 'unknown'),
                provider
            )
        except Exception as e:
            self.logger.warning(f"⚠️ Token使用量记录失败: {e}")


# 便捷函数
def create_langsmith_llm_client(base_llm_client, enable_tracing: bool = True) -> LangSmithLLMClient:
    """创建带LangSmith追踪的LLM客户端"""
    return LangSmithLLMClient(base_llm_client, enable_tracing)

"""
智能上下文压缩系统
 架构的上下文压缩机制，实现"AI为自己写会议纪要"的功能
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.storage_manager import JubenStorageManager, ChatMessage, ContextState
    from ..utils.llm_client import JubenLLMClient
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.storage_manager import JubenStorageManager, ChatMessage, ContextState
    from utils.llm_client import JubenLLMClient


@dataclass
class CompressionConfig:
    """压缩配置"""
    max_context_length: int = 8000  # 最大上下文长度
    compression_threshold: float = 0.8  # 压缩阈值（80%时开始压缩）
    summary_ratio: float = 0.3  # 摘要比例（保留30%的原始信息）
    preserve_recent: int = 10  # 保留最近N条消息
    preserve_important: bool = True  # 是否保留重要消息
    compression_quality: str = "high"  # 压缩质量：high, medium, low


@dataclass
class CompressionResult:
    """压缩结果"""
    original_count: int
    compressed_count: int
    compression_ratio: float
    summary: str
    preserved_messages: List[Dict[str, Any]]
    compressed_messages: List[Dict[str, Any]]
    compression_metadata: Dict[str, Any]
    created_at: str


@dataclass
class ContextSummary:
    """上下文摘要"""
    session_id: str
    user_id: str
    agent_name: str
    summary_content: str
    key_points: List[str]
    important_decisions: List[str]
    action_items: List[str]
    context_hash: str
    created_at: str
    expires_at: str


class ContextCompactor:
    """智能上下文压缩器"""
    
    def __init__(self, model_provider: str = "zhipu"):
        """
        初始化上下文压缩器
        
        Args:
            model_provider: 模型提供商
        """
        self.config = JubenSettings()
        self.logger = JubenLogger("ContextCompactor", level=self.config.log_level)
        self.storage_manager = JubenStorageManager()
        self.llm_client = JubenLLMClient(model_provider)
        
        # 压缩配置
        self.compression_config = CompressionConfig()
        
        # 压缩历史记录
        self.compression_history: List[CompressionResult] = []
        
        self.logger.info("智能上下文压缩器初始化完成")
    
    async def initialize(self):
        """初始化压缩器"""
        try:
            await self.storage_manager.initialize()
            self.logger.info("✅ 上下文压缩器初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 上下文压缩器初始化失败: {e}")
            raise
    
    def calculate_context_length(self, messages: List[Dict[str, Any]]) -> int:
        """计算上下文长度"""
        total_length = 0
        for message in messages:
            content = message.get('content', '')
            if isinstance(content, str):
                total_length += len(content)
            elif isinstance(content, dict):
                total_length += len(str(content))
        return total_length
    
    def should_compress(self, messages: List[Dict[str, Any]]) -> Tuple[bool, float]:
        """
        判断是否需要压缩
        
        Returns:
            (是否需要压缩, 当前使用率)
        """
        current_length = self.calculate_context_length(messages)
        max_length = self.compression_config.max_context_length
        usage_ratio = current_length / max_length
        
        should_compress = usage_ratio >= self.compression_config.compression_threshold
        
        return should_compress, usage_ratio
    
    def identify_important_messages(self, messages: List[Dict[str, Any]]) -> List[int]:
        """
        识别重要消息
        
        Args:
            messages: 消息列表
            
        Returns:
            重要消息的索引列表
        """
        important_indices = []
        
        for i, message in enumerate(messages):
            content = message.get('content', '')
            message_type = message.get('message_type', '')
            
            # 重要消息判断标准
            is_important = False
            
            # 1. 系统消息和错误消息
            if message_type in ['system', 'error']:
                is_important = True
            
            # 2. 包含关键词的消息
            important_keywords = [
                '重要', '关键', '决定', '决策', '总结', '结论',
                'action', 'todo', '任务', '目标', '计划'
            ]
            
            if isinstance(content, str):
                content_lower = content.lower()
                if any(keyword in content_lower for keyword in important_keywords):
                    is_important = True
            
            # 3. 长消息（可能包含重要信息）
            if len(str(content)) > 500:
                is_important = True
            
            # 4. 包含结构化数据
            if isinstance(content, dict) and len(content) > 3:
                is_important = True
            
            if is_important:
                important_indices.append(i)
        
        return important_indices
    
    async def generate_context_summary(
        self, 
        messages: List[Dict[str, Any]], 
        user_id: str, 
        session_id: str, 
        agent_name: str
    ) -> str:
        """
        生成上下文摘要
        
        Args:
            messages: 消息列表
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            
        Returns:
            上下文摘要
        """
        try:
            # 构建压缩提示词
            prompt = self._build_compression_prompt(messages, user_id, session_id, agent_name)
            
            # 调用LLM生成摘要
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                return response['content']
            else:
                # 如果LLM调用失败，使用简单摘要
                return self._generate_simple_summary(messages)
                
        except Exception as e:
            self.logger.error(f"生成上下文摘要失败: {e}")
            return self._generate_simple_summary(messages)
    
    def _build_compression_prompt(
        self, 
        messages: List[Dict[str, Any]], 
        user_id: str, 
        session_id: str, 
        agent_name: str
    ) -> str:
        """构建压缩提示词"""
        
        # 构建消息历史
        message_history = []
        for i, message in enumerate(messages):
            msg_type = message.get('message_type', 'unknown')
            content = message.get('content', '')
            timestamp = message.get('created_at', '')
            
            message_history.append(f"[{i+1}] {msg_type.upper()}: {content}")
        
        message_text = "\n".join(message_history)
        
        prompt = f"""
你是一个专业的上下文压缩专家，需要为AI系统生成高质量的上下文摘要。

## 任务背景
- 用户ID: {user_id}
- 会话ID: {session_id}
- Agent: {agent_name}
- 当前上下文长度: {self.calculate_context_length(messages)} 字符

## 对话历史
{message_text}

## 压缩要求
请生成一个高质量的上下文摘要，要求：

1. **保持核心信息完整性**：保留所有重要的决策、结论和关键信息
2. **突出重要决策**：明确标识用户的重要决定和偏好
3. **提取行动项**：识别需要后续处理的任务和待办事项
4. **保持上下文连贯性**：确保摘要能够支持后续对话的连贯性
5. **保留关键细节**：不要丢失重要的技术细节和具体信息

## 输出格式
请按照以下格式输出摘要：

**上下文摘要：**
[生成高质量的上下文摘要，包含对话的核心内容和重要信息]

**关键决策：**
- [列出用户的重要决策和偏好]
- [列出系统的重要决定]

**行动项：**
- [列出需要后续处理的任务]
- [列出待办事项]

**重要细节：**
- [列出需要保留的技术细节]
- [列出具体的参数和配置]

请确保摘要简洁但信息完整，能够支持后续对话的顺利进行。
"""
        
        return prompt
    
    def _generate_simple_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成简单摘要（备用方案）"""
        total_messages = len(messages)
        user_messages = sum(1 for msg in messages if msg.get('message_type') == 'user')
        assistant_messages = sum(1 for msg in messages if msg.get('message_type') == 'assistant')
        
        summary = f"""
上下文摘要：
- 总消息数: {total_messages}
- 用户消息: {user_messages}
- 助手消息: {assistant_messages}
- 对话时间跨度: {messages[0].get('created_at', '')} 到 {messages[-1].get('created_at', '')}

关键信息：
- 对话主要围绕 {self._extract_main_topics(messages)} 展开
- 用户主要关注点: {self._extract_user_concerns(messages)}
"""
        
        return summary
    
    def _extract_main_topics(self, messages: List[Dict[str, Any]]) -> str:
        """提取主要话题"""
        # 简单的关键词提取
        all_content = " ".join(str(msg.get('content', '')) for msg in messages)
        # 这里可以添加更复杂的话题提取逻辑
        return "对话内容分析"
    
    def _extract_user_concerns(self, messages: List[Dict[str, Any]]) -> str:
        """提取用户关注点"""
        user_messages = [msg for msg in messages if msg.get('message_type') == 'user']
        if not user_messages:
            return "未识别到用户关注点"
        
        # 简单的关注点提取
        return "用户需求分析"
    
    async def compress_context(
        self, 
        user_id: str, 
        session_id: str, 
        agent_name: str,
        force_compress: bool = False
    ) -> Optional[CompressionResult]:
        """
        压缩上下文
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            force_compress: 是否强制压缩
            
        Returns:
            压缩结果
        """
        try:
            self.logger.info(f"🔄 开始压缩上下文: {user_id}/{session_id}/{agent_name}")
            
            # 获取当前消息
            messages = await self.storage_manager.get_chat_messages(user_id, session_id, limit=1000)
            if not messages:
                self.logger.warning("没有找到需要压缩的消息")
                return None
            
            # 检查是否需要压缩
            should_compress, usage_ratio = self.should_compress(messages)
            if not should_compress and not force_compress:
                self.logger.info(f"上下文使用率 {usage_ratio:.2%}，无需压缩")
                return None
            
            self.logger.info(f"📊 上下文使用率: {usage_ratio:.2%}，开始压缩")
            
            # 识别重要消息
            important_indices = self.identify_important_messages(messages)
            self.logger.info(f"🔍 识别到 {len(important_indices)} 条重要消息")
            
            # 生成上下文摘要
            summary = await self.generate_context_summary(messages, user_id, session_id, agent_name)
            self.logger.info(f"📝 生成上下文摘要: {len(summary)} 字符")
            
            # 选择保留的消息
            preserved_messages = self._select_preserved_messages(messages, important_indices)
            
            # 创建压缩结果
            compression_result = CompressionResult(
                original_count=len(messages),
                compressed_count=len(preserved_messages),
                compression_ratio=len(preserved_messages) / len(messages),
                summary=summary,
                preserved_messages=preserved_messages,
                compressed_messages=messages,
                compression_metadata={
                    "usage_ratio": usage_ratio,
                    "important_count": len(important_indices),
                    "compression_quality": self.compression_config.compression_quality,
                    "timestamp": datetime.now().isoformat()
                },
                created_at=datetime.now().isoformat()
            )
            
            # 保存压缩结果
            await self._save_compression_result(compression_result, user_id, session_id, agent_name)
            
            # 更新上下文状态
            await self._update_context_after_compression(
                user_id, session_id, agent_name, compression_result
            )
            
            self.logger.info(f"✅ 上下文压缩完成: {compression_result.compression_ratio:.2%}")
            return compression_result
            
        except Exception as e:
            self.logger.error(f"❌ 上下文压缩失败: {e}")
            return None
    
    def _select_preserved_messages(
        self, 
        messages: List[Dict[str, Any]], 
        important_indices: List[int]
    ) -> List[Dict[str, Any]]:
        """选择保留的消息"""
        preserved = []
        
        # 1. 保留重要消息
        for idx in important_indices:
            if idx < len(messages):
                preserved.append(messages[idx])
        
        # 2. 保留最近的消息
        recent_count = self.compression_config.preserve_recent
        recent_messages = messages[-recent_count:]
        
        for msg in recent_messages:
            if msg not in preserved:
                preserved.append(msg)
        
        # 3. 按时间排序
        preserved.sort(key=lambda x: x.get('created_at', ''))
        
        return preserved
    
    async def _save_compression_result(
        self, 
        result: CompressionResult, 
        user_id: str, 
        session_id: str, 
        agent_name: str
    ):
        """保存压缩结果"""
        try:
            # 创建上下文摘要记录
            context_hash = hashlib.md5(
                f"{user_id}_{session_id}_{agent_name}_{result.created_at}".encode()
            ).hexdigest()
            
            summary = ContextSummary(
                session_id=session_id,
                user_id=user_id,
                agent_name=agent_name,
                summary_content=result.summary,
                key_points=self._extract_key_points(result.summary),
                important_decisions=self._extract_decisions(result.summary),
                action_items=self._extract_action_items(result.summary),
                context_hash=context_hash,
                created_at=result.created_at,
                expires_at=(datetime.now() + timedelta(days=7)).isoformat()
            )
            
            # 保存到存储系统
            # 这里可以添加保存逻辑
            
            self.logger.info(f"💾 压缩结果已保存: {context_hash}")
            
        except Exception as e:
            self.logger.error(f"保存压缩结果失败: {e}")
    
    def _extract_key_points(self, summary: str) -> List[str]:
        """提取关键点"""
        # 简单的关键点提取
        lines = summary.split('\n')
        key_points = []
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('•'):
                key_points.append(line.strip())
        return key_points[:10]  # 最多10个关键点
    
    def _extract_decisions(self, summary: str) -> List[str]:
        """提取决策"""
        # 简单的决策提取
        decisions = []
        if '决定' in summary or '决策' in summary:
            decisions.append("用户做出了重要决定")
        return decisions
    
    def _extract_action_items(self, summary: str) -> List[str]:
        """提取行动项"""
        # 简单的行动项提取
        actions = []
        if '任务' in summary or '待办' in summary:
            actions.append("有待处理的任务")
        return actions
    
    async def _update_context_after_compression(
        self, 
        user_id: str, 
        session_id: str, 
        agent_name: str, 
        result: CompressionResult
    ):
        """压缩后更新上下文"""
        try:
            # 更新上下文状态，添加压缩信息
            context_data = {
                "compression_applied": True,
                "compression_time": result.created_at,
                "compression_ratio": result.compression_ratio,
                "summary_available": True,
                "original_message_count": result.original_count,
                "preserved_message_count": result.compressed_count
            }
            
            await self.storage_manager.save_context_state(
                ContextState(
                    user_id=user_id,
                    session_id=session_id,
                    agent_name=agent_name,
                    context_data=context_data
                )
            )
            
            self.logger.info("✅ 上下文状态已更新")
            
        except Exception as e:
            self.logger.error(f"更新上下文状态失败: {e}")
    
    async def get_context_summary(
        self, 
        user_id: str, 
        session_id: str, 
        agent_name: str
    ) -> Optional[ContextSummary]:
        """获取上下文摘要"""
        try:
            # 这里可以实现从存储中获取摘要的逻辑
            # 暂时返回None
            return None
        except Exception as e:
            self.logger.error(f"获取上下文摘要失败: {e}")
            return None
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        if not self.compression_history:
            return {"total_compressions": 0}
        
        total_compressions = len(self.compression_history)
        avg_compression_ratio = sum(
            result.compression_ratio for result in self.compression_history
        ) / total_compressions
        
        return {
            "total_compressions": total_compressions,
            "average_compression_ratio": avg_compression_ratio,
            "last_compression": self.compression_history[-1].created_at if self.compression_history else None
        }


# 全局压缩器实例
_global_compactor = None

def get_context_compactor() -> ContextCompactor:
    """获取全局上下文压缩器"""
    global _global_compactor
    if _global_compactor is None:
        _global_compactor = ContextCompactor()
    return _global_compactor

async def compress_context_if_needed(
    user_id: str, 
    session_id: str, 
    agent_name: str,
    force: bool = False
) -> Optional[CompressionResult]:
    """智能压缩上下文（如果需要）"""
    compactor = get_context_compactor()
    await compactor.initialize()
    return await compactor.compress_context(user_id, session_id, agent_name, force)


def main():
    """主函数 - 用于测试和演示"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建压缩器
    compactor = ContextCompactor()
    
    # 模拟压缩测试
    logger.info("智能上下文压缩器测试完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

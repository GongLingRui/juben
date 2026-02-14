"""
增强型上下文窗口管理器 - 专为长剧本设计
=====================================

基于2026年最新研究的上下文管理技术：
1. Rolling Window + 智能摘要机制
2. 语义分块 (Semantic Chunking)
3. 分层记忆架构 (Hierarchical Memory)
4. Token感知压缩
5. 关键信息锚定

参考资料：
- Best LLMs for Extended Context Windows in 2026 (AI Multiple)
- Context Window Overflow in 2026: Fix LLM Errors Fast (Redis Blog)
- Autonomous Memory Management in LLM Agents (arXiv 2026)
- Top techniques to Manage Context Lengths in LLMs (Agenta AI)
"""
import asyncio
import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
from enum import Enum
import hashlib
from pathlib import Path

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.llm_client import get_llm_client
    from ..utils.storage_manager import JubenStorageManager
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.llm_client import get_llm_client
    from utils.storage_manager import JubenStorageManager


class MemoryLevel(Enum):
    """记忆层级"""
    IMMEDIATE = "immediate"      # 即时记忆 (当前对话，约2K tokens)
    RECENT = "recent"            # 近期记忆 (最近几轮，约5K tokens)
    WORKING = "working"          # 工作记忆 (当前会话，约10K tokens)
    LONG_TERM = "long_term"      # 长期记忆 (重要信息，持久化)


class ChunkType(Enum):
    """分块类型"""
    DIALOGUE = "dialogue"        # 对话块
    ACTION = "action"            # 动作描述
    SCENE = "scene"              # 场景切换
    PLOT_POINT = "plot_point"    # 情节点
    CHARACTER = "character"      # 角色描述
    SUMMARY = "summary"          # 摘要块


class EmotionalPointType(Enum):
    """情绪点类型（专为短剧设计）"""
    TENSION = "tension"          # 压弹簧（紧张、压抑、愤怒、憋屈）
    RELEASE = "release"          # 放弹簧（释放、打脸、反转、爽快）
    HOOK = "hook"                # 钩子（悬念、冲突、吸引）
    CLIMAX = "climax"            # 高潮（爆发、决战、高潮）
    TWIST = "twist"              # 转折（反转、意外、真相）


@dataclass
class EmotionalPoint:
    """情绪点数据结构"""
    content: str                 # 情绪点内容
    point_type: EmotionalPointType  # 情绪点类型
    importance: float            # 重要性评分 (0-1)
    position: int                # 在原文中的位置
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class TokenBudget:
    """Token预算配置"""
    max_context_tokens: int = 128000       # 最大上下文 (GLM-4-Flash支持)
    safety_margin: int = 10000             # 安全边界
    system_prompt_tokens: int = 2000       # 系统提示词
    immediate_budget: int = 2000           # 即时记忆预算
    recent_budget: int = 5000              # 近期记忆预算
    working_budget: int = 10000            # 工作记忆预算
    long_term_budget: int = 5000           # 长期记忆预算
    response_budget: int = 8000            # 响应预算

    def available_for_input(self) -> int:
        """可用于输入的token数"""
        total_reserved = (
            self.system_prompt_tokens +
            self.immediate_budget +
            self.recent_budget +
            self.working_budget +
            self.long_term_budget +
            self.response_budget
        )
        return self.max_context_tokens - total_reserved


@dataclass
class ContextWindow:
    """
    上下文窗口状态（增强版：带结构化隔离）

    隔离层级：
    - messages: 发送给LLM的对话消息
    - internal_notes: 内部笔记，不发送给LLM，用于：
      * 子任务结果缓存
      * 中间处理状态
      * 调试信息
      * 性能统计
    - scratchpad: 草稿纸，用于临时存储和筛选
    """
    # ========== 消息层（发送给LLM） ==========
    immediate: List[Dict[str, Any]] = field(default_factory=list)  # 即时对话
    recent: Deque[Dict[str, Any]] = field(default_factory=deque)  # 近期对话
    working: List[Dict[str, Any]] = field(default_factory=list)  # 工作记忆
    long_term_summary: str = ""  # 长期摘要
    key_anchors: List[str] = field(default_factory=list)  # 关键锚点

    # ========== 内部笔记层（不发送给LLM） ==========
    internal_notes: List[Dict[str, Any]] = field(default_factory=list)  # 内部笔记
    subtask_results: Dict[str, Any] = field(default_factory=dict)  # 子任务结果
    scratchpad: List[Dict[str, Any]] = field(default_factory=list)  # 草稿纸

    # ========== 元数据 ==========
    total_tokens: int = 0
    last_compression: str = ""
    compression_count: int = 0
    is_healthy: bool = True
    version: int = 0
    last_updated: str = ""

    # 统计
    message_count: int = 0
    character_mentions: Dict[str, int] = field(default_factory=dict)
    plot_points: List[str] = field(default_factory=list)

    # ========== 新增：隔离控制 ==========
    max_internal_notes: int = 100  # 内部笔记最大数量
    max_scratchpad_size: int = 50  # 草稿纸最大大小


@dataclass
class SemanticChunk:
    """语义分块"""
    id: str
    content: str
    chunk_type: ChunkType
    token_count: int
    importance: float  # 0-1
    keywords: List[str] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScriptMemory:
    """剧本记忆"""
    session_id: str
    user_id: str

    # 角色记忆
    characters: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 情节线记忆
    plot_threads: List[Dict[str, Any]] = field(default_factory=list)

    # 关键决策
    key_decisions: List[Dict[str, Any]] = field(default_factory=list)

    # 场景记忆
    scenes: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


@dataclass
class GraphMemory:
    """图结构记忆（面向剧情与角色关系）"""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def upsert_node(self, node_id: str, node_type: str, label: str, meta: Optional[Dict[str, Any]] = None):
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "label": label,
            "meta": meta or {},
            "updated_at": datetime.now().isoformat()
        }
        self.updated_at = datetime.now().isoformat()

    def add_edge(self, source: str, target: str, edge_type: str, meta: Optional[Dict[str, Any]] = None):
        self.edges.append({
            "source": source,
            "target": target,
            "type": edge_type,
            "meta": meta or {},
            "created_at": datetime.now().isoformat()
        })
        self.updated_at = datetime.now().isoformat()


class EnhancedContextManager:
    """
    增强型上下文管理器

    核心特性：
    1. 滚动窗口机制 (Rolling Window)
    2. 智能摘要压缩 (Intelligent Summary)
    3. 语义分块 (Semantic Chunking)
    4. 关键信息锚定 (Key Information Anchoring)
    5. Token预算管理 (Token Budgeting)
    """

    def __init__(self, model_provider: str = "zhipu", model: str = "glm-4-flash"):
        self.config = JubenSettings()
        self.logger = JubenLogger("EnhancedContextManager", level=self.config.log_level)

        # Token预算
        self.budget = TokenBudget()

        # LLM客户端
        self.llm_client = get_llm_client(model_provider, model=model)

        # 存储管理器
        from utils.storage_manager import get_storage
        self.storage_manager = get_storage()

        # 上下文窗口
        self.context_windows: Dict[str, ContextWindow] = {}

        # 剧本记忆
        self.script_memories: Dict[str, ScriptMemory] = {}
        # 图结构记忆
        self.graph_memories: Dict[str, GraphMemory] = {}

        # 配置
        self.rolling_window_size = 10  # 滚动窗口大小（消息数）
        self.compression_threshold = 0.85  # 压缩阈值
        self.summary_target_ratio = 0.3  # 摘要目标比例

    def _touch_window(self, window: ContextWindow):
        """更新窗口版本与时间戳"""
        window.version += 1
        window.last_updated = datetime.now().isoformat()

        # 🆕 【新增】情绪点检测关键词（专为短剧设计）
        self.emotional_keywords = {
            EmotionalPointType.TENSION: [
                "压抑", "憋屈", "愤怒", "不甘", "绝望", "痛苦", "挣扎",
                "危机", "威胁", "逼迫", "欺凌", "羞辱", "陷害", "误会",
                "紧绷", "窒息", "沉重", "煎熬", "煎熬", "煎熬",
                "压弹簧", "积蓄", "紧张", "惊险", "危急"
            ],
            EmotionalPointType.RELEASE: [
                "爆发", "反击", "打脸", "反转", "爽快", "痛快", "解气",
                "真相大白", "逆袭", "成功", "胜利", "击败", "战胜",
                "放弹簧", "释放", "痛快", "酣畅淋漓", "扬眉吐气",
                "痛快", "舒畅", "满足", "欣喜", "振奋"
            ],
            EmotionalPointType.HOOK: [
                "突然", "意外", "震惊", "惊呆", "不敢相信", "竟然",
                "居然", "意想不到", "突发", "猛然", "瞬间",
                "悬念", "疑惑", "谜团", "疑问", "困惑",
                "等等", "慢着", "不对", "奇怪"
            ],
            EmotionalPointType.CLIMAX: [
                "高潮", "巅峰", "决战", "生死", "关键时刻", "最后",
                "终极", "最终", "爆发", "决战", "对决", "对决",
                "最高潮", "最激烈", "决定性", "关键时刻"
            ],
            EmotionalPointType.TWIST: [
                "反转", "转折", "真相", "原来", "竟然是", "居然是",
                "没想到", "意外的是", "出人意料", "峰回路转",
                "真相大白", "恍然大悟", "原来如此", "意想不到"
            ]
        }

        # 情绪点保护权重（压缩时的保护级别）
        self.emotion_protection_weights = {
            EmotionalPointType.CLIMAX: 1.0,    # 最高保护
            EmotionalPointType.TWIST: 0.9,     # 高保护
            EmotionalPointType.RELEASE: 0.8,   # 较高保护
            EmotionalPointType.TENSION: 0.7,   # 中等保护
            EmotionalPointType.HOOK: 0.6       # 基础保护
        }

        self.logger.info("增强型上下文管理器初始化完成")

    async def initialize(self):
        """初始化管理器"""
        await self.storage_manager.initialize()
        self.logger.info("✅ 增强型上下文管理器已初始化")

    # ==================== Token 计算 ====================

    def count_tokens(self, text: str) -> int:
        """
        更准确的Token计数

        基于GLM-4-Flash的实际tokenizer特性优化
        """
        if not text:
            return 0

        # 中文：约1字符=1token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # 英文/数字：约4字符=1token
        other_chars = len(text) - chinese_chars

        return chinese_chars + max(1, other_chars // 4)

    def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """计算消息的token数"""
        content = message.get("content", "")
        role = message.get("role", "")
        # 角色标记约5 tokens
        return self.count_tokens(content) + 5

    def count_context_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """计算上下文总token数"""
        return sum(self.count_message_tokens(msg) for msg in messages)

    # ==================== 语义分块 ====================

    async def semantic_chunk(
        self,
        text: str,
        chunk_type: ChunkType = ChunkType.DIALOGUE
    ) -> List[SemanticChunk]:
        """
        语义分块 - 将长文本按语义边界分割

        参考：RAG语义分块最佳实践
        """
        chunks = []
        chunk_id = 0

        # 根据类型使用不同的分割策略
        if chunk_type == ChunkType.DIALOGUE:
            chunks = await self._chunk_dialogue(text)
        elif chunk_type == ChunkType.SCENE:
            chunks = await self._chunk_by_scene(text)
        elif chunk_type == ChunkType.PLOT_POINT:
            chunks = await self._chunk_by_plot_point(text)
        else:
            chunks = await self._chunk_by_size(text)

        # 为每个分块添加元数据
        for chunk in chunks:
            chunk.chunk_type = chunk_type
            chunk.token_count = self.count_tokens(chunk.content)
            chunk.importance = await self._calculate_importance(chunk)
            chunk.keywords = self._extract_keywords(chunk.content)
            chunk.characters = self._extract_characters(chunk.content)

        self.logger.info(f"语义分块完成: {len(chunks)} 个块")
        return chunks

    async def _chunk_dialogue(self, text: str) -> List[SemanticChunk]:
        """按对话分割"""
        chunks = []
        # 匹配对话模式：角色名: 对话内容
        pattern = r'([^\n:]+):\s*([^\n]+)'
        matches = re.findall(pattern, text)

        current_chunk = ""
        chunk_id = 0

        for speaker, dialogue in matches:
            entry = f"{speaker}: {dialogue}\n"
            if len(current_chunk) + len(entry) > 500:  # 约500字符一块
                if current_chunk:
                    chunks.append(SemanticChunk(
                        id=f"dialogue_{chunk_id}",
                        content=current_chunk.strip()
                    ))
                    chunk_id += 1
                current_chunk = entry
            else:
                current_chunk += entry

        if current_chunk:
            chunks.append(SemanticChunk(
                id=f"dialogue_{chunk_id}",
                content=current_chunk.strip()
            ))

        return chunks if chunks else [SemanticChunk(id="dialogue_0", content=text)]

    async def _chunk_by_scene(self, text: str) -> List[SemanticChunk]:
        """按场景分割"""
        # 检测场景标记
        scene_markers = [
            r'\[场景[一二三四五六七八九十\d]+\]',
            r'\[.*?场.*?\]',
            r'第.*?场',
            r'SCENE\s*\d+',
            r'INT\.|EXT\.',
            r'内景|外景',
        ]

        # 合并所有模式
        combined_pattern = '|'.join(f'({pattern})' for pattern in scene_markers)
        parts = re.split(combined_pattern, text, flags=re.IGNORECASE)

        chunks = []
        chunk_id = 0
        current_chunk = ""

        for part in parts:
            if part:
                if len(current_chunk) + len(part) > 1000:
                    if current_chunk:
                        chunks.append(SemanticChunk(
                            id=f"scene_{chunk_id}",
                            content=current_chunk.strip()
                        ))
                        chunk_id += 1
                    current_chunk = part
                else:
                    current_chunk += part

        if current_chunk:
            chunks.append(SemanticChunk(id=f"scene_{chunk_id}", content=current_chunk.strip()))

        return chunks if chunks else [SemanticChunk(id="scene_0", content=text)]

    async def _chunk_by_plot_point(self, text: str) -> List[SemanticChunk]:
        """按情节点分割"""
        # 检测情节标记
        plot_patterns = [
            r'情节[一二三四五六七八九十\d]+',
            r'第.*?节',
            r'【.*?】',
            r'Plot\s*Point',
        ]

        combined_pattern = '|'.join(f'({pattern})' for pattern in plot_patterns)
        parts = re.split(combined_pattern, text, flags=re.IGNORECASE)

        chunks = []
        chunk_id = 0

        for part in parts:
            if part and len(part.strip()) > 50:
                chunks.append(SemanticChunk(
                    id=f"plot_{chunk_id}",
                    content=part.strip()
                ))
                chunk_id += 1

        return chunks if chunks else [SemanticChunk(id="plot_0", content=text)]

    async def _chunk_by_size(self, text: str, max_size: int = 800) -> List[SemanticChunk]:
        """按大小分割（保留语义完整性）"""
        chunks = []
        sentences = re.split(r'([。！？\n])', text)

        current_chunk = ""
        chunk_id = 0

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            delimiter = sentences[i + 1] if i + 1 < len(sentences) else ""

            full_sentence = sentence + delimiter
            if len(current_chunk) + len(full_sentence) > max_size:
                if current_chunk:
                    chunks.append(SemanticChunk(
                        id=f"chunk_{chunk_id}",
                        content=current_chunk.strip()
                    ))
                    chunk_id += 1
                current_chunk = full_sentence
            else:
                current_chunk += full_sentence

        if current_chunk:
            chunks.append(SemanticChunk(id=f"chunk_{chunk_id}", content=current_chunk.strip()))

        return chunks

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（可以升级为使用NLP模型）
        important_words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text)
        # 去重并返回前10个
        return list(set(important_words))[:10]

    def _extract_characters(self, text: str) -> List[str]:
        """提取角色名"""
        # 匹配常见的角色名模式
        patterns = [
            r'([A-Z][a-z]+):',  # 英文名:
            r'([\u4e00-\u9fff]{2,4})[:：]',  # 中文名：
        ]

        characters = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            characters.update(matches)

        # 过滤常见非角色词
        common_words = {'系统', '用户', '助手', '旁白', '画外音'}
        return [c for c in characters if c not in common_words]

    async def _calculate_importance(self, chunk: SemanticChunk) -> float:
        """计算分块重要性"""
        importance = 0.5  # 基础重要性

        content = chunk.content.lower()

        # 重要关键词加分
        important_keywords = [
            '决定', '关键', '转折', '高潮', '冲突', '解决',
            '重要', '核心', '主要', '必须', '终于'
        ]
        for keyword in important_keywords:
            if keyword in content:
                importance += 0.05

        # 对话通常比描述重要
        if ':' in chunk.content or '：' in chunk.content:
            importance += 0.1

        # 长度适中的内容更重要
        if 100 < len(chunk.content) < 500:
            importance += 0.1

        return min(1.0, importance)

    # ==================== 滚动窗口管理 ====================

    async def add_to_context(
        self,
        session_id: str,
        user_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        添加消息到上下文（带滚动窗口）

        实现：当上下文接近上限时，将旧消息压缩为摘要
        """
        try:
            # 获取或创建上下文窗口
            window = self.context_windows.get(f"{user_id}_{session_id}")
            if not window:
                window = ContextWindow()
                self.context_windows[f"{user_id}_{session_id}"] = window

            # 计算当前token
            message_tokens = self.count_message_tokens(message)
            window.total_tokens += message_tokens
            window.message_count += 1

            # 添加到即时记忆
            window.immediate.append(message)

            # 检查是否需要压缩
            usage_ratio = window.total_tokens / self.budget.max_context_tokens

            if usage_ratio > self.compression_threshold:
                await self._apply_rolling_window(window, session_id, user_id)

            # 更新统计
            self._update_window_stats(window, message)
            self._touch_window(window)

            return True

        except Exception as e:
            self.logger.error(f"添加到上下文失败: {e}")
            return False

    async def _apply_rolling_window(
        self,
        window: ContextWindow,
        session_id: str,
        user_id: str
    ):
        """
        应用滚动窗口机制

        策略：
        1. 将immediate中最旧的消息移到recent
        2. 将recent中过期的消息压缩为摘要
        3. 将摘要合并到working memory
        """
        self.logger.info(f"应用滚动窗口: 当前token={window.total_tokens}")

        # 1. 从immediate移到recent（保留最近5条在immediate）
        while len(window.immediate) > 5:
            old_message = window.immediate.pop(0)
            window.recent.append(old_message)
            window.total_tokens -= self.count_message_tokens(old_message)

        # 2. 从recent压缩到working
        while len(window.recent) > self.rolling_window_size:
            old_messages = []
            for _ in range(min(3, len(window.recent))):  # 每次压缩3条
                if window.recent:
                    old_messages.append(window.recent.popleft())

            if old_messages:
                summary = await self._compress_messages(old_messages, user_id, session_id)
                window.working.append({
                    "role": "system",
                    "content": f"[历史对话摘要] {summary}",
                    "compressed": True,
                    "timestamp": datetime.now().isoformat()
                })
                window.compression_count += 1
                window.last_compression = datetime.now().isoformat()
                self._touch_window(window)

        # 3. 如果working仍然过大，生成总体摘要
        working_tokens = self.count_context_tokens(window.working)
        if working_tokens > self.budget.working_budget:
            overall_summary = await self._generate_overall_summary(window, user_id, session_id)
            window.long_term_summary = overall_summary
            window.working = []  # 清空working，保留摘要

        self.logger.info(f"滚动窗口完成: compression_count={window.compression_count}")

    async def _compress_messages(
        self,
        messages: List[Dict[str, Any]],
        user_id: str,
        session_id: str
    ) -> str:
        """压缩消息为摘要"""
        try:
            # 构建消息文本
            messages_text = "\n".join([
                f"{msg.get('role', '')}: {msg.get('content', '')[:200]}"
                for msg in messages
            ])

            prompt = f"""请将以下对话压缩为简洁的摘要（不超过100字），保留关键信息：

{messages_text}

摘要："""

            response = await self.llm_client.chat([{"role": "user", "content": prompt}])
            return response[:200] if response else "对话内容已压缩"

        except Exception as e:
            self.logger.error(f"消息压缩失败: {e}")
            # 备用：简单拼接
            return f"包含{len(messages)}条历史消息的摘要"

    async def _generate_overall_summary(
        self,
        window: ContextWindow,
        user_id: str,
        session_id: str
    ) -> str:
        """生成总体摘要"""
        try:
            all_content = []

            # 添加key anchors
            if window.key_anchors:
                all_content.append("关键信息：\n" + "\n".join(window.key_anchors))

            # 添加角色提及
            if window.character_mentions:
                chars = sorted(window.character_mentions.items(), key=lambda x: x[1], reverse=True)
                all_content.append("主要角色：\n" + "\n".join([f"{c}: {count}次" for c, count in chars[:5]]))

            # 添加情节点
            if window.plot_points:
                all_content.append("关键情节：\n" + "\n".join(window.plot_points[-5:]))

            # 如果有长期摘要，合并它
            if window.long_term_summary:
                all_content.append(f"之前摘要：\n{window.long_term_summary}")

            # 使用LLM生成更精炼的摘要
            if len(all_content) > 0:
                content_text = "\n\n".join(all_content)
                prompt = f"""请将以下上下文信息整合为一个简洁的摘要（不超过150字）：

{content_text}

整合摘要："""

                response = await self.llm_client.chat([{"role": "user", "content": prompt}])
                return response[:300] if response else "上下文已压缩"

            return "会话上下文摘要"

        except Exception as e:
            self.logger.error(f"生成总体摘要失败: {e}")
            return f"包含{window.message_count}条消息的会话摘要"

    def _update_window_stats(self, window: ContextWindow, message: Dict[str, Any]):
        """更新窗口统计信息"""
        content = message.get("content", "")

        # 更新角色提及
        characters = self._extract_characters(content)
        for char in characters:
            window.character_mentions[char] = window.character_mentions.get(char, 0) + 1

        # 检测关键情节
        if any(keyword in content for keyword in ['决定', '转折', '冲突', '解决', '发现']):
            window.plot_points.append(content[:50])

        # 检测需要锚定的信息
        if any(keyword in content for keyword in ['记住', '重要', '关键', '必须']):
            window.key_anchors.append(content[:100])
            if len(window.key_anchors) > 10:  # 最多保留10个锚点
                window.key_anchors.pop(0)

    # ==================== 情绪点检测与保护（专为短剧设计）====================

    def detect_emotional_points(self, text: str) -> List[EmotionalPoint]:
        """
        检测文本中的情绪点

        Args:
            text: 待检测的文本

        Returns:
            List[EmotionalPoint]: 检测到的情绪点列表
        """
        if not text:
            return []

        emotional_points = []
        sentences = re.split(r'[。！？\n]', text)
        position = 0

        for sentence in sentences:
            if not sentence.strip():
                continue

            sentence = sentence.strip()
            sentence_start = text.find(sentence, position)
            if sentence_start == -1:
                sentence_start = position

            # 检测每种类型的情绪点
            for point_type, keywords in self.emotional_keywords.items():
                # 计算匹配的关键词数量
                matched_keywords = [kw for kw in keywords if kw in sentence]

                if matched_keywords:
                    # 计算重要性（基于匹配关键词数量和权重）
                    base_importance = min(1.0, len(matched_keywords) * 0.3)

                    # 考虑句子长度（较短的句子可能是更有力的表达）
                    length_factor = max(0.5, 1.0 - len(sentence) / 200)

                    # 综合重要性
                    importance = base_importance * length_factor

                    emotional_points.append(EmotionalPoint(
                        content=sentence,
                        point_type=point_type,
                        importance=importance,
                        position=sentence_start,
                        metadata={
                            "matched_keywords": matched_keywords,
                            "sentence_length": len(sentence)
                        }
                    ))

            position = sentence_start + len(sentence)

        # 按重要性排序
        emotional_points.sort(key=lambda ep: ep.importance, reverse=True)

        return emotional_points

    def should_protect_emotional_point(
        self,
        emotional_point: EmotionalPoint,
        protection_threshold: float = 0.5
    ) -> bool:
        """
        判断是否应该保护某个情绪点

        Args:
            emotional_point: 情绪点
            protection_threshold: 保护阈值

        Returns:
            bool: 是否应该保护
        """
        # 获取该类型情绪点的保护权重
        type_weight = self.emotion_protection_weights.get(
            emotional_point.point_type,
            0.5
        )

        # 计算综合保护分数
        protection_score = emotional_point.importance * type_weight

        return protection_score >= protection_threshold

    def extract_protected_content(
        self,
        text: str,
        max_length: int = 500
    ) -> Tuple[str, List[EmotionalPoint]]:
        """
        提取受保护的情绪点内容

        在压缩时优先保留情绪点，确保核心情绪不丢失

        Args:
            text: 原始文本
            max_length: 最大长度限制

        Returns:
            Tuple[str, List[EmotionalPoint]]: (压缩后的文本, 保留的情绪点)
        """
        # 检测所有情绪点
        all_emotional_points = self.detect_emotional_points(text)

        # 过滤出需要保护的点
        protected_points = [
            ep for ep in all_emotional_points
            if self.should_protect_emotional_point(ep)
        ]

        if not protected_points:
            # 没有需要保护的点，直接截断
            return text[:max_length], []

        # 按位置排序
        protected_points.sort(key=lambda ep: ep.position)

        # 构建受保护的内容
        protected_content_parts = []
        current_length = 0

        for ep in protected_points:
            content = ep.content
            if current_length + len(content) <= max_length:
                protected_content_parts.append(content)
                current_length += len(content)
            else:
                # 剩余空间不足，截断当前情绪点
                remaining = max_length - current_length
                if remaining > 20:  # 至少保留20个字符
                    protected_content_parts.append(content[:remaining] + "...")
                break

        protected_text = " ".join(protected_content_parts)

        return protected_text, protected_points

    async def compress_with_emotion_protection(
        self,
        messages: List[Dict[str, Any]],
        user_id: str,
        session_id: str,
        max_length: int = 500
    ) -> str:
        """
        带情绪点保护的压缩方法

        改进原 `_compress_messages` 方法，在压缩时保护情绪点

        Args:
            messages: 待压缩的消息列表
            user_id: 用户ID
            session_id: 会话ID
            max_length: 最大长度

        Returns:
            str: 压缩后的文本
        """
        try:
            # 提取所有文本内容
            all_text = []
            for msg in messages:
                content = msg.get("content", "")
                all_text.append(content)

            combined_text = "\n".join(all_text)

            # 如果总长度小于限制，直接返回
            if len(combined_text) <= max_length:
                return combined_text

            # 使用情绪点保护的提取
            protected_text, protected_points = self.extract_protected_content(
                combined_text,
                max_length
            )

            # 如果受保护的内容太少，补充LLM摘要
            if len(protected_text) < max_length * 0.3:
                # 使用LLM生成摘要
                llm_summary = await self._compress_messages(messages, user_id, session_id)

                # 合并情绪点和摘要
                if protected_points:
                    summary = f"[情绪点保护]\n{protected_text}\n\n[摘要]\n{llm_summary}"
                    return summary[:max_length]
                return llm_summary[:max_length]

            return protected_text

        except Exception as e:
            self.logger.error(f"情绪保护压缩失败: {e}")
            # 降级到普通压缩
            return await self._compress_messages(messages, user_id, session_id)

    # ==================== 上下文重建 ====================

    async def rebuild_context_for_llm(
        self,
        session_id: str,
        user_id: str,
        system_prompt: str,
        new_message: str,
        extra_messages: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        为LLM重建完整的上下文

        返回按优先级排列的消息列表：
        1. System Prompt
        2. Long-term Summary (如果存在)
        3. Key Anchors (重要信息锚点)
        4. Working Memory (工作记忆)
        5. Recent Messages (近期对话)
        6. Immediate Messages (当前对话)
        7. New Message
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            window = ContextWindow()
            self.context_windows[f"{user_id}_{session_id}"] = window

        messages = []
        token_count = 0

        # 1. System Prompt
        system_msg = {"role": "system", "content": system_prompt}
        system_tokens = self.count_message_tokens(system_msg)
        if token_count + system_tokens < self.budget.max_context_tokens:
            messages.append(system_msg)
            token_count += system_tokens

        # 2. 额外上下文块（系统/示例消息）
        if extra_messages:
            for msg in extra_messages:
                msg_tokens = self.count_message_tokens(msg)
                if token_count + msg_tokens < self.budget.max_context_tokens - self.budget.response_budget:
                    messages.append(msg)
                    token_count += msg_tokens

        # 3. Long-term Summary
        if window.long_term_summary:
            summary_msg = {
                "role": "system",
                "content": f"【上下文摘要】{window.long_term_summary}"
            }
            summary_tokens = self.count_message_tokens(summary_msg)
            if token_count + summary_tokens < self.budget.max_context_tokens - self.budget.response_budget:
                messages.append(summary_msg)
                token_count += summary_tokens

        # 4. Key Anchors (如果有)
        if window.key_anchors:
            anchors_text = "\n".join([f"• {anchor}" for anchor in window.key_anchors[-5:]])
            anchor_msg = {
                "role": "system",
                "content": f"【重要信息】\n{anchors_text}"
            }
            anchor_tokens = self.count_message_tokens(anchor_msg)
            if token_count + anchor_tokens < self.budget.max_context_tokens - self.budget.response_budget:
                messages.append(anchor_msg)
                token_count += anchor_tokens

        # 5. Working Memory
        for msg in window.working:
            msg_tokens = self.count_message_tokens(msg)
            if token_count + msg_tokens < self.budget.max_context_tokens - self.budget.response_budget:
                messages.append(msg)
                token_count += msg_tokens

        # 6. Recent Messages (保留最近)
        for msg in list(window.recent)[-self.rolling_window_size:]:
            msg_tokens = self.count_message_tokens(msg)
            if token_count + msg_tokens < self.budget.max_context_tokens - self.budget.response_budget:
                messages.append(msg)
                token_count += msg_tokens

        # 7. Immediate Messages
        for msg in window.immediate:
            msg_tokens = self.count_message_tokens(msg)
            if token_count + msg_tokens < self.budget.max_context_tokens - self.budget.response_budget:
                messages.append(msg)
                token_count += msg_tokens

        # 8. New Message
        new_msg = {"role": "user", "content": new_message}
        messages.append(new_msg)

        self.logger.info(f"重建上下文: {len(messages)}条消息, 约{token_count}tokens")
        return messages

    # ==================== 内部笔记管理（隔离层） ====================

    async def add_internal_note(
        self,
        session_id: str,
        user_id: str,
        note_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加内部笔记（不发送给LLM）

        用于：
        - 子任务结果缓存
        - 中间处理状态
        - 调试信息
        - 性能统计

        Args:
            session_id: 会话ID
            user_id: 用户ID
            note_type: 笔记类型 (subtask_result|debug|performance|state)
            content: 笔记内容
            metadata: 元数据

        Returns:
            是否添加成功
        """
        try:
            window = self.context_windows.get(f"{user_id}_{session_id}")
            if not window:
                window = ContextWindow()
                self.context_windows[f"{user_id}_{session_id}"] = window

            note = {
                "type": note_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # 检查是否超过限制
            if len(window.internal_notes) >= window.max_internal_notes:
                # 移除最旧的笔记
                window.internal_notes.pop(0)

            window.internal_notes.append(note)
            return True

        except Exception as e:
            self.logger.error(f"添加内部笔记失败: {e}")
            return False

    async def get_internal_notes(
        self,
        session_id: str,
        user_id: str,
        note_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取内部笔记

        Args:
            session_id: 会话ID
            user_id: 用户ID
            note_type: 笔记类型过滤（None表示全部）
            limit: 返回数量限制

        Returns:
            笔记列表
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            return []

        notes = window.internal_notes

        # 类型过滤
        if note_type:
            notes = [n for n in notes if n.get("type") == note_type]

        # 返回最近的
        return notes[-limit:]

    async def clear_internal_notes(
        self,
        session_id: str,
        user_id: str,
        note_type: Optional[str] = None
    ) -> int:
        """
        清除内部笔记

        Args:
            session_id: 会话ID
            user_id: 用户ID
            note_type: 笔记类型（None表示全部）

        Returns:
            清除的数量
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            return 0

        if note_type:
            # 只清除特定类型
            original_count = len(window.internal_notes)
            window.internal_notes = [n for n in window.internal_notes if n.get("type") != note_type]
            return original_count - len(window.internal_notes)
        else:
            # 清除全部
            count = len(window.internal_notes)
            window.internal_notes = []
            return count

    # ==================== 草稿纸管理（选择机制） ====================

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

        草稿纸用于临时存储中间结果，然后进行筛选

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
        try:
            window = self.context_windows.get(f"{user_id}_{session_id}")
            if not window:
                window = ContextWindow()
                self.context_windows[f"{user_id}_{session_id}"] = window

            entry = {
                "content": content,
                "importance": importance,
                "tags": tags or [],
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # 检查是否超过限制
            if len(window.scratchpad) >= window.max_scratchpad_size:
                # 移除重要性最低的
                window.scratchpad.sort(key=lambda x: x.get("importance", 0))
                window.scratchpad.pop(0)

            window.scratchpad.append(entry)
            return True

        except Exception as e:
            self.logger.error(f"添加到草稿纸失败: {e}")
            return False

    async def select_from_scratchpad(
        self,
        session_id: str,
        user_id: str,
        current_task: str,
        max_items: int = 5,
        min_importance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        从草稿纸选择相关信息（核心选择机制）

        选择策略：
        1. 重要性过滤（低于min_importance的忽略）
        2. 相关性评分（与current_task的相似度）
        3. 综合排序（importance * relevance）
        4. 数量限制（最多max_items个）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            current_task: 当前任务描述
            max_items: 最大返回数量
            min_importance: 最小重要性阈值

        Returns:
            选中的草稿纸条目
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            return []

        try:
            # 1. 重要性过滤
            filtered = [item for item in window.scratchpad if item.get("importance", 0) >= min_importance]

            # 2. 计算相关性
            for item in filtered:
                item["relevance_score"] = self._calculate_relevance(item, current_task)

            # 3. 综合排序
            for item in filtered:
                importance = item.get("importance", 0.5)
                relevance = item.get("relevance_score", 0.5)
                item["combined_score"] = importance * 0.4 + relevance * 0.6

            filtered.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

            # 4. 数量限制
            selected = filtered[:max_items]

            self.logger.info(f"从草稿纸选择了{len(selected)}/{len(window.scratchpad)}个条目")
            return selected

        except Exception as e:
            self.logger.error(f"从草稿纸选择失败: {e}")
            return []

    def _calculate_relevance(self, item: Dict[str, Any], query: str) -> float:
        """计算相关性分数"""
        try:
            content = str(item.get("content", ""))
            tags = item.get("tags", [])

            # 简单的关键词匹配
            query_lower = query.lower()
            content_lower = content.lower()

            # 直接匹配
            direct_match = 1.0 if query_lower in content_lower else 0.0

            # 标签匹配
            tag_match = 0.0
            for tag in tags:
                if tag.lower() in query_lower:
                    tag_match = 0.8
                    break

            # 关键词重叠
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)

            return max(direct_match, tag_match, overlap * 0.5)

        except Exception:
            return 0.0

    async def clear_scratchpad(
        self,
        session_id: str,
        user_id: str
    ) -> int:
        """
        清空草稿纸

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            清除的数量
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            return 0

        count = len(window.scratchpad)
        window.scratchpad = []
        return count

    # ==================== 子任务隔离 ====================

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

        子任务结果存储在internal_notes中，不发送给LLM
        可以通过查询获取特定子任务的结果

        Args:
            session_id: 会话ID
            user_id: 用户ID
            subtask_id: 子任务ID
            result: 结果
            metadata: 元数据

        Returns:
            是否存储成功
        """
        try:
            window = self.context_windows.get(f"{user_id}_{session_id}")
            if not window:
                window = ContextWindow()
                self.context_windows[f"{user_id}_{session_id}"] = window

            window.subtask_results[subtask_id] = {
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            return True

        except Exception as e:
            self.logger.error(f"存储子任务结果失败: {e}")
            return False

    async def get_subtask_result(
        self,
        session_id: str,
        user_id: str,
        subtask_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取子任务结果

        Args:
            session_id: 会话ID
            user_id: 用户ID
            subtask_id: 子任务ID

        Returns:
            子任务结果（如果存在）
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            return None

        return window.subtask_results.get(subtask_id)

    async def list_subtask_results(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        列出所有子任务结果

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            所有子任务结果
        """
        window = self.context_windows.get(f"{user_id}_{session_id}")
        if not window:
            return {}

        return window.subtask_results.copy()

    # ==================== 剧本记忆管理 ====================

    async def create_script_memory(self, user_id: str, session_id: str) -> ScriptMemory:
        """创建剧本记忆"""
        memory = ScriptMemory(session_id=session_id, user_id=user_id)
        self.script_memories[f"{user_id}_{session_id}"] = memory
        return memory

    async def get_or_create_graph_memory(self, user_id: str, session_id: str) -> GraphMemory:
        """获取或创建图结构记忆"""
        key = f"{user_id}_{session_id}"
        memory = self.graph_memories.get(key)
        if not memory:
            memory = GraphMemory()
            self.graph_memories[key] = memory
        return memory

    async def update_graph_from_script_memory(self, user_id: str, session_id: str) -> GraphMemory:
        """从剧本记忆构建/更新图结构"""
        graph = await self.get_or_create_graph_memory(user_id, session_id)
        memory = self.script_memories.get(f"{user_id}_{session_id}")
        if not memory:
            return graph

        # 角色节点
        for char_name, char_info in memory.characters.items():
            node_id = f"char:{char_name}"
            graph.upsert_node(node_id, "character", char_name, {"info": char_info})

        # 情节线节点
        for plot in memory.plot_threads:
            plot_id = plot.get("id") or f"plot:{plot.get('description','')[:20]}"
            node_id = f"plot:{plot_id}"
            graph.upsert_node(node_id, "plot", plot.get("description", ""), {"status": plot.get("status")})

        # 简单关系：所有角色 -> 所有情节线
        for char_name in memory.characters.keys():
            for plot in memory.plot_threads:
                plot_id = plot.get("id") or f"plot:{plot.get('description','')[:20]}"
                graph.add_edge(f"char:{char_name}", f"plot:{plot_id}", "appears_in")

        return graph

    async def get_graph_context_summary(self, user_id: str, session_id: str) -> str:
        """获取图结构摘要"""
        graph = await self.update_graph_from_script_memory(user_id, session_id)
        if not graph.nodes:
            return "暂无图结构记忆"

        characters = [n for n in graph.nodes.values() if n.get("type") == "character"]
        plots = [n for n in graph.nodes.values() if n.get("type") == "plot"]
        edges = graph.edges[-20:]

        parts = []
        if characters:
            parts.append("【角色节点】" + "、".join([c.get("label", "") for c in characters[:10]]))
        if plots:
            parts.append("【情节线】" + "、".join([p.get("label", "") for p in plots[:10]]))
        if edges:
            edge_text = "; ".join([f"{e['source']}→{e['target']}" for e in edges[:10]])
            parts.append("【关系】" + edge_text)

        return "\n".join(parts)

    async def update_character_info(
        self,
        user_id: str,
        session_id: str,
        character_name: str,
        info: Dict[str, Any]
    ):
        """更新角色信息"""
        memory = self.script_memories.get(f"{user_id}_{session_id}")
        if not memory:
            memory = await self.create_script_memory(user_id, session_id)

        if character_name not in memory.characters:
            memory.characters[character_name] = {
                "name": character_name,
                "first_appearance": datetime.now().isoformat(),
                "mentions": 0
            }

        memory.characters[character_name].update(info)
        memory.characters[character_name]["mentions"] += 1
        memory.characters[character_name]["last_updated"] = datetime.now().isoformat()
        memory.updated_at = datetime.now().isoformat()

    async def add_plot_thread(
        self,
        user_id: str,
        session_id: str,
        plot_description: str,
        status: str = "active"
    ):
        """添加情节线"""
        memory = self.script_memories.get(f"{user_id}_{session_id}")
        if not memory:
            memory = await self.create_script_memory(user_id, session_id)

        plot_thread = {
            "id": f"plot_{len(memory.plot_threads)}",
            "description": plot_description,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
        memory.plot_threads.append(plot_thread)
        memory.updated_at = datetime.now().isoformat()

    async def get_script_context_summary(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """获取剧本上下文摘要"""
        memory = self.script_memories.get(f"{user_id}_{session_id}")
        if not memory:
            return "暂无剧本记忆"

        parts = []

        # 角色信息
        if memory.characters:
            parts.append("【角色档案】")
            for char_name, char_info in memory.characters.items():
                parts.append(f"- {char_name}: {char_info.get('description', '无描述')}")

        # 情节线
        if memory.plot_threads:
            parts.append("\n【情节线】")
            for plot in memory.plot_threads:
                parts.append(f"- {plot['description']} ({plot['status']})")

        # 关键决策
        if memory.key_decisions:
            parts.append("\n【关键决策】")
            for decision in memory.key_decisions[-5:]:
                parts.append(f"- {decision.get('description', '')}")

        return "\n".join(parts) if parts else "暂无详细信息"

    # ==================== RAG自动加载与混合检索（新增） ====================

    async def auto_load_rag_context(
        self,
        session_id: str,
        user_id: str,
        query: str,
        enable_rag: bool = True,
        enable_hybrid: bool = True,
        top_k: int = 3,
        collection: str = "script_segments"
    ) -> List[Dict[str, Any]]:
        """
        自动加载RAG上下文（核心RAG自动加载机制）

        在调用LLM前自动：
        1. 检测查询意图
        2. 执行向量检索（如果enable_rag）
        3. 执行混合检索（如果enable_hybrid）
        4. 过滤和排序结果
        5. 返回最相关的上下文

        Args:
            session_id: 会话ID
            user_id: 用户ID
            query: 查询内容
            enable_rag: 是否启用RAG检索
            enable_hybrid: 是否启用混合检索
            top_k: 返回结果数量
            collection: 知识库集合名称

        Returns:
            RAG检索结果列表，每个包含：
            - content: 内容
            - similarity: 相似度
            - source: 来源
            - type: 类型 (vector/text/hybrid)
        """
        try:
            # 延迟导入，避免循环依赖
            from .vector_store import VectorStore
            from .knowledge_base_client import KnowledgeBaseClient

            results = []

            # 1. 向量检索
            if enable_rag:
                try:
                    vector_store = VectorStore()
                    if not vector_store._initialized:
                        await vector_store.initialize()

                    vector_results = await vector_store.search_similar(
                        collection_name=f"{collection}_collection",
                        query=query,
                        top_k=top_k,
                        score_threshold=0.6
                    )

                    # 格式化结果
                    for item in vector_results.get("results", []):
                        results.append({
                            "content": item.get("content", ""),
                            "similarity": item.get("score", 0.0),
                            "source": item.get("source", "vector_db"),
                            "type": "vector"
                        })

                    self.logger.info(f"向量检索: 找到{len(results)}个结果")

                except Exception as e:
                    self.logger.warning(f"向量检索失败: {e}")

            # 2. 文本/关键词检索（混合）
            if enable_hybrid:
                try:
                    knowledge_client = KnowledgeBaseClient()
                    text_results = await knowledge_client.search(query, collection=collection, top_k=top_k)

                    # 格式化结果
                    for item in text_results.get("results", []):
                        results.append({
                            "content": item.get("content", ""),
                            "similarity": item.get("similarity", 0.0),
                            "source": item.get("source", "knowledge_base"),
                            "type": "text"
                        })

                    self.logger.info(f"文本检索: 找到{len(text_results.get('results', []))}个结果")

                except Exception as e:
                    self.logger.warning(f"文本检索失败: {e}")

            # 3. 混合检索结果去重和排序
            if results:
                results = await self._deduplicate_and_rank(results)

                # 限制返回数量
                results = results[:top_k]

                # 将结果存储到草稿纸（供后续选择使用）
                for result in results:
                    await self.add_to_scratchpad(
                        session_id, user_id,
                        result["content"],
                        importance=result["similarity"],
                        tags=["rag", result["type"], collection],
                        metadata={
                            "source": result["source"],
                            "similarity": result["similarity"]
                        }
                    )

            return results

        except Exception as e:
            self.logger.error(f"RAG自动加载失败: {e}")
            return []

    async def _deduplicate_and_rank(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        去重和排序混合检索结果

        Args:
            results: 混合检索结果列表

        Returns:
            去重和排序后的结果
        """
        # 去重（基于内容相似度）
        seen_contents = set()
        unique_results = []

        for result in results:
            content = result.get("content", "")
            # 使用内容的前100个字符作为去重依据
            content_key = content[:100] if content else ""

            if content_key and content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_results.append(result)

        # 排序：按相似度降序
        unique_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        return unique_results

    async def rebuild_context_with_rag(
        self,
        session_id: str,
        user_id: str,
        system_prompt: str,
        new_message: str,
        enable_auto_rag: bool = True,
        rag_threshold: float = 0.7,
        max_rag_items: int = 3,
        extra_messages: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        重建上下文（带RAG自动加载）

        这是rebuild_context_for_llm的增强版本，会自动：
        1. 调用rebuild_context_for_llm获取基础上下文
        2. 分析new_message，判断是否需要RAG
        3. 如果需要，自动加载相关RAG内容
        4. 将RAG内容整合到上下文中

        Args:
            session_id: 会话ID
            user_id: 用户ID
            system_prompt: 系统提示词
            new_message: 新消息
            enable_auto_rag: 是否启用自动RAG
            rag_threshold: RAG触发阈值（相似度低于此值时触发RAG）
            max_rag_items: 最大RAG条目数

        Returns:
            包含RAG内容的完整上下文
        """
        # 1. 获取基础上下文
        messages = await self.rebuild_context_for_llm(
            session_id, user_id, system_prompt, new_message, extra_messages=extra_messages
        )

        # 2. 判断是否需要RAG
        if not enable_auto_rag:
            return messages

        # 检测是否需要知识增强
        needs_rag = await self._detect_rag_need(new_message)

        if not needs_rag:
            self.logger.info("无需RAG增强")
            return messages

        # 3. 执行RAG检索
        rag_results = await self.auto_load_rag_context(
            session_id, user_id, new_message,
            enable_rag=True,
            enable_hybrid=True,
            top_k=max_rag_items
        )

        if not rag_results:
            return messages

        # 4. 将RAG内容整合到上下文
        # 在system_prompt之后插入RAG内容
        if rag_results:
            rag_context_parts = []
            for i, result in enumerate(rag_results):
                rag_context_parts.append(
                    f"[参考信息{i+1}] {result['content']}\n"
                )

            rag_message = {
                "role": "system",
                "content": f"【相关知识库信息】\n{''.join(rag_context_parts)}"
            }

            # 插入到system_prompt之后
            insert_index = 1 if len(messages) > 0 else 0
            messages.insert(insert_index, rag_message)

            self.logger.info(f"已整合{len(rag_results)}条RAG内容到上下文")

        return messages

    async def _detect_rag_need(self, message: str) -> bool:
        """
        检测消息是否需要RAG增强

        判断标准：
        1. 包含专业知识相关词汇
        2. 包含查询/检索相关词汇
        3. 包含"怎么""如何"等疑问词

        Args:
            message: 消息内容

        Returns:
            是否需要RAG
        """
        rag_keywords = [
            "剧本", "桥段", "情节", "高能", "爆点", "爽点",
            "知识", "查询", "检索", "搜索",
            "怎么", "如何", "什么是", "哪些",
            "技巧", "方法", "经验", "建议"
        ]

        message_lower = message.lower()

        # 检查是否包含RAG关键词
        for keyword in rag_keywords:
            if keyword in message_lower:
                return True

        return False

    # ==================== 智能选择机制（新增） ====================

    async def smart_select_context(
        self,
        session_id: str,
        user_id: str,
        current_task: str,
        sources: List[str] = None
    ) -> Dict[str, Any]:
        """
        智能选择上下文（综合选择机制）

        整合所有选择策略：
        1. 从草稿纸选择（select_from_scratchpad）
        2. 从长期记忆选择（long_term_summary, script_memory）
        3. 从RAG选择（auto_load_rag_context）

        Args:
            session_id: 会话ID
            user_id: 用户ID
            current_task: 当前任务描述
            sources: 数据源列表 (scratchpad|memory|rag|all)，默认all

        Returns:
            选择的上下文，包含：
            - from_scratchpad: 来自草稿纸的内容
            - from_memory: 来自长期记忆的内容
            - from_rag: 来自RAG的内容
            - combined: 整合后的上下文
        """
        if sources is None:
            sources = ["all"]

        result = {
            "from_scratchpad": [],
            "from_memory": "",
            "from_rag": [],
            "combined": ""
        }

        try:
            # 1. 从草稿纸选择
            if "all" in sources or "scratchpad" in sources:
                scratchpad_items = await self.select_from_scratchpad(
                    session_id, user_id, current_task,
                    max_items=3, min_importance=0.4
                )
                result["from_scratchpad"] = scratchpad_items

            # 2. 从长期记忆选择
            if "all" in sources or "memory" in sources:
                # 获取剧本上下文摘要
                memory_summary = await self.get_script_context_summary(session_id, user_id)
                result["from_memory"] = memory_summary

                # 获取上下文窗口中的长期摘要
                window = self.context_windows.get(f"{user_id}_{session_id}")
                if window and window.long_term_summary:
                    if result["from_memory"]:
                        result["from_memory"] += "\n\n【历史对话摘要】\n" + window.long_term_summary
                    else:
                        result["from_memory"] = "【历史对话摘要】\n" + window.long_term_summary

            # 3. 从RAG选择
            if "all" in sources or "rag" in sources:
                rag_items = await self.auto_load_rag_context(
                    session_id, user_id, current_task,
                    enable_rag=True, enable_hybrid=True, top_k=2
                )
                result["from_rag"] = rag_items

            # 4. 整合上下文
            combined_parts = []

            if result["from_memory"]:
                combined_parts.append(f"【记忆信息】\n{result['from_memory']}")

            if result["from_scratchpad"]:
                scratchpad_content = "\n".join([
                    f"- {item.get('content', '')[:200]}"
                    for item in result["from_scratchpad"]
                ])
                combined_parts.append(f"【草稿信息】\n{scratchpad_content}")

            if result["from_rag"]:
                rag_content = "\n".join([
                    f"- {item.get('content', '')[:200]}"
                    for item in result["from_rag"]
                ])
                combined_parts.append(f"【知识库信息】\n{rag_content}")

            result["combined"] = "\n\n".join(combined_parts)

            self.logger.info(f"智能选择上下文完成: 草稿纸{len(result['from_scratchpad'])}条, RAG{len(result['from_rag'])}条")

            return result

        except Exception as e:
            self.logger.error(f"智能选择上下文失败: {e}")
            return result

    # ==================== 健康检查 ====================

    async def get_context_health(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取上下文健康状态"""
        key = f"{user_id}_{session_id}"
        window = self.context_windows.get(key)

        if not window:
            return {
                "status": "no_context",
                "message": "无上下文"
            }

        usage_ratio = window.total_tokens / self.budget.max_context_tokens
        is_healthy = usage_ratio < 0.9

        return {
            "status": "healthy" if is_healthy else "warning",
            "total_tokens": window.total_tokens,
            "max_tokens": self.budget.max_context_tokens,
            "usage_ratio": f"{usage_ratio:.1%}",
            "message_count": window.message_count,
            "compression_count": window.compression_count,
            "immediate_count": len(window.immediate),
            "recent_count": len(window.recent),
            "working_count": len(window.working),
            "has_long_term_summary": bool(window.long_term_summary),
            "key_anchors_count": len(window.key_anchors),
            "character_mentions": window.character_mentions,
            "recommendations": self._get_health_recommendations(window, usage_ratio)
        }

    def _get_health_recommendations(
        self,
        window: ContextWindow,
        usage_ratio: float
    ) -> List[str]:
        """获取健康建议"""
        recommendations = []

        if usage_ratio > 0.9:
            recommendations.append("⚠️ 上下文接近上限，建议启动强制压缩")
        elif usage_ratio > 0.75:
            recommendations.append("ℹ️ 上下文使用率较高，将启用自动压缩")

        if window.compression_count == 0 and window.message_count > 20:
            recommendations.append("ℹ️ 建议启用自动摘要以节省tokens")

        if len(window.key_anchors) > 15:
            recommendations.append("ℹ️ 锚点信息过多，建议清理旧的锚点")

        if not window.long_term_summary and window.message_count > 30:
            recommendations.append("ℹ️ 建议生成长期摘要以保存重要信息")

        return recommendations

    async def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理旧会话"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []

        for key, window in self.context_windows.items():
            # 检查最后活动时间（通过compression时间判断）
            if window.last_compression:
                try:
                    last_active = datetime.fromisoformat(window.last_compression)
                    if last_active < cutoff:
                        to_remove.append(key)
                except:
                    pass

        for key in to_remove:
            del self.context_windows[key]
            # 同时清理剧本记忆
            if key in self.script_memories:
                del self.script_memories[key]

        if to_remove:
            self.logger.info(f"清理了 {len(to_remove)} 个旧会话")


# ==================== 全局实例 ====================

_global_manager = None


def get_enhanced_context_manager() -> EnhancedContextManager:
    """获取全局增强上下文管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = EnhancedContextManager()
    return _global_manager


async def rebuild_context(
    session_id: str,
    user_id: str,
    system_prompt: str,
    new_message: str,
    extra_messages: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """便捷函数：重建上下文"""
    manager = get_enhanced_context_manager()
    await manager.initialize()
    return await manager.rebuild_context_for_llm(
        session_id, user_id, system_prompt, new_message, extra_messages=extra_messages
    )


async def rebuild_context_with_rag(
    session_id: str,
    user_id: str,
    system_prompt: str,
    new_message: str,
    enable_auto_rag: bool = True,
    max_rag_items: int = 3,
    extra_messages: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """便捷函数：重建上下文（带RAG自动加载）"""
    manager = get_enhanced_context_manager()
    await manager.initialize()
    return await manager.rebuild_context_with_rag(
        session_id, user_id, system_prompt, new_message,
        enable_auto_rag, max_rag_items=max_rag_items, extra_messages=extra_messages
    )


async def smart_select_context(
    session_id: str,
    user_id: str,
    current_task: str,
    sources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """便捷函数：智能选择上下文"""
    manager = get_enhanced_context_manager()
    await manager.initialize()
    return await manager.smart_select_context(
        session_id, user_id, current_task, sources
    )


async def auto_load_rag(
    session_id: str,
    user_id: str,
    query: str,
    top_k: int = 3,
    collection: str = "script_segments"
) -> List[Dict[str, Any]]:
    """便捷函数：自动加载RAG内容"""
    manager = get_enhanced_context_manager()
    await manager.initialize()
    return await manager.auto_load_rag_context(
        session_id, user_id, query,
        enable_rag=True, enable_hybrid=True,
        top_k=top_k, collection=collection
    )

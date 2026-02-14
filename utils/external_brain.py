"""
外部大脑系统 - 为AI配备外部大脑
 架构的外部记忆和知识管理系统
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import uuid

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.storage_manager import JubenStorageManager, Note
    from ..utils.llm_client import JubenLLMClient
    from ..utils.vector_store import VectorStore
    from ..utils.reflexion_mechanism import ReflexionMechanism, get_reflexion_mechanism
    from ..utils.generative_agents import GenerativeAgents, get_generative_agents
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.storage_manager import JubenStorageManager, Note
    from utils.llm_client import JubenLLMClient
    from utils.vector_store import VectorStore
    from utils.reflexion_mechanism import ReflexionMechanism, get_reflexion_mechanism
    from utils.generative_agents import GenerativeAgents, get_generative_agents


@dataclass
class KnowledgeNode:
    """知识节点"""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    importance: int  # 1-10
    created_at: str
    updated_at: str
    access_count: int = 0
    last_accessed: Optional[str] = None
    related_nodes: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.related_nodes is None:
            self.related_nodes = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DecisionRecord:
    """决策记录"""
    id: str
    decision: str
    context: str
    reasoning: str
    outcome: Optional[str] = None
    confidence: float = 0.0  # 0-1
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = None
    related_decisions: List[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if self.tags is None:
            self.tags = []
        if self.related_decisions is None:
            self.related_decisions = []


@dataclass
class MemoryFragment:
    """记忆片段"""
    id: str
    content: str
    memory_type: str  # fact, experience, skill, preference
    importance: int  # 1-10
    emotional_weight: float = 0.0  # 0-1
    created_at: str = ""
    last_accessed: Optional[str] = None
    access_count: int = 0
    associations: List[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.associations is None:
            self.associations = []


@dataclass
class BrainState:
    """大脑状态"""
    user_id: str
    session_id: str
    agent_name: str
    active_memories: List[str]
    current_focus: str
    learning_mode: bool
    memory_consolidation_needed: bool
    last_consolidation: str
    brain_health_score: float  # 0-1
    created_at: str = ""
    updated_at: str = ""


class ExternalBrain:
    """外部大脑系统"""
    
    def __init__(self, model_provider: str = "zhipu"):
        """
        初始化外部大脑系统
        
        Args:
            model_provider: 模型提供商
        """
        self.config = JubenSettings()
        self.logger = JubenLogger("ExternalBrain", level=self.config.log_level)
        self.storage_manager = JubenStorageManager()
        self.llm_client = JubenLLMClient(model_provider)
        self.vector_store = VectorStore()
        
        # 大脑状态
        self.brain_states: Dict[str, BrainState] = {}
        self.knowledge_graph: Dict[str, KnowledgeNode] = {}
        self.decision_history: List[DecisionRecord] = []
        self.memory_fragments: Dict[str, MemoryFragment] = {}
        
        # 学习配置
        self.learning_config = {
            "auto_learn": True,
            "consolidation_threshold": 10,  # 10个新记忆后触发巩固
            "importance_threshold": 5,  # 重要性阈值
            "memory_decay_days": 30,  # 记忆衰减天数
            "max_memories_per_user": 1000  # 每用户最大记忆数
        }
        
        # 集成反思机制和生成式智能体
        self.reflexion_mechanism = get_reflexion_mechanism()
        self.generative_agents = get_generative_agents()
        
        self.logger.info("外部大脑系统初始化完成")
    
    async def initialize(self):
        """初始化外部大脑"""
        try:
            await self.storage_manager.initialize()
            await self.vector_store.initialize()
            
            # 初始化反思机制
            await self.reflexion_mechanism.initialize()
            
            # 初始化生成式智能体
            await self.generative_agents.initialize()
            
            self.logger.info("✅ 外部大脑系统初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 外部大脑系统初始化失败: {e}")
            raise
    
    async def learn_from_interaction(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        interaction_data: Dict[str, Any]
    ) -> bool:
        """
        从交互中学习
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            interaction_data: 交互数据
            
        Returns:
            是否成功学习
        """
        try:
            self.logger.info(f"🧠 开始学习: {user_id}/{session_id}/{agent_name}")
            
            # 1. 提取关键信息
            key_info = await self._extract_key_information(interaction_data)
            if not key_info:
                self.logger.warning("未提取到关键信息，跳过学习")
                return False
            
            # 2. 创建知识节点
            knowledge_node = await self._create_knowledge_node(key_info, user_id)
            if knowledge_node:
                await self._store_knowledge_node(knowledge_node)
                self.logger.info(f"📚 创建知识节点: {knowledge_node.title}")
            
            # 3. 记录决策
            if key_info.get('decisions'):
                for decision in key_info['decisions']:
                    decision_record = await self._create_decision_record(decision, user_id, session_id)
                    if decision_record:
                        self.decision_history.append(decision_record)
                        self.logger.info(f"🎯 记录决策: {decision_record.decision}")
            
            # 4. 创建记忆片段
            memory_fragment = await self._create_memory_fragment(key_info, user_id, session_id)
            if memory_fragment:
                self.memory_fragments[memory_fragment.id] = memory_fragment
                self.logger.info(f"💭 创建记忆片段: {memory_fragment.memory_type}")
            
            # 5. 更新大脑状态
            await self._update_brain_state(user_id, session_id, agent_name, key_info)
            
            # 6. 记录观察到生成式智能体
            await self._log_observation_to_generative_agents(
                user_id, session_id, agent_name, key_info, interaction_data
            )
            
            # 7. 检查是否需要记忆巩固
            if await self._should_consolidate_memories(user_id):
                await self._consolidate_memories(user_id)
            
            self.logger.info("✅ 学习完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 学习失败: {e}")
            return False
    
    async def _extract_key_information(self, interaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取关键信息"""
        try:
            # 构建信息提取提示词
            prompt = self._build_information_extraction_prompt(interaction_data)
            
            # 调用LLM提取信息
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.3
            )
            
            if response and response.get('content'):
                # 解析LLM响应
                return self._parse_extracted_information(response['content'])
            else:
                # 使用简单提取方法
                return self._simple_information_extraction(interaction_data)
                
        except Exception as e:
            self.logger.error(f"提取关键信息失败: {e}")
            return None
    
    def _build_information_extraction_prompt(self, interaction_data: Dict[str, Any]) -> str:
        """构建信息提取提示词"""
        content = interaction_data.get('content', '')
        message_type = interaction_data.get('message_type', '')
        
        prompt = f"""
你是一个专业的信息提取专家，需要从AI交互中提取关键信息并结构化存储。

## 交互数据
- 消息类型: {message_type}
- 内容: {content}
- 时间: {interaction_data.get('created_at', '')}

## 提取任务
请从以上交互中提取以下信息：

1. **关键事实**：用户提到的具体事实、数据、信息
2. **用户偏好**：用户的喜好、习惯、倾向
3. **决策记录**：用户做出的决定和选择
4. **学习内容**：用户学到的新知识或技能
5. **情感信息**：用户的情感状态和反应
6. **行动意图**：用户想要执行的动作或计划

## 输出格式
请按照以下JSON格式输出：

```json
{{
    "facts": ["事实1", "事实2"],
    "preferences": ["偏好1", "偏好2"],
    "decisions": [
        {{
            "decision": "决策内容",
            "context": "决策背景",
            "reasoning": "决策理由",
            "confidence": 0.8
        }}
    ],
    "learnings": ["学习内容1", "学习内容2"],
    "emotions": ["情感1", "情感2"],
    "intentions": ["意图1", "意图2"],
    "importance": 7,
    "category": "知识类别",
    "tags": ["标签1", "标签2"]
}}
```

请确保提取的信息准确、有用，并且结构化程度高。
"""
        
        return prompt
    
    def _parse_extracted_information(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM提取的信息"""
        try:
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # 如果没有找到JSON，使用简单解析
                return self._simple_parse_response(llm_response)
        except Exception as e:
            self.logger.error(f"解析提取信息失败: {e}")
            return self._simple_parse_response(llm_response)
    
    def _simple_parse_response(self, response: str) -> Dict[str, Any]:
        """简单解析响应"""
        return {
            "facts": [response[:100]],  # 简单截取
            "preferences": [],
            "decisions": [],
            "learnings": [],
            "emotions": [],
            "intentions": [],
            "importance": 5,
            "category": "general",
            "tags": ["auto_extracted"]
        }
    
    def _simple_information_extraction(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """简单信息提取（备用方案）"""
        content = str(interaction_data.get('content', ''))
        
        return {
            "facts": [content[:200]] if content else [],
            "preferences": [],
            "decisions": [],
            "learnings": [],
            "emotions": [],
            "intentions": [],
            "importance": 3,
            "category": "interaction",
            "tags": ["simple_extraction"]
        }
    
    async def _create_knowledge_node(
        self, 
        key_info: Dict[str, Any], 
        user_id: str
    ) -> Optional[KnowledgeNode]:
        """创建知识节点"""
        try:
            if not key_info.get('facts') and not key_info.get('learnings'):
                return None
            
            # 合并事实和学习内容
            all_content = []
            if key_info.get('facts'):
                all_content.extend(key_info['facts'])
            if key_info.get('learnings'):
                all_content.extend(key_info['learnings'])
            
            if not all_content:
                return None
            
            # 创建知识节点
            node_id = str(uuid.uuid4())
            content = " | ".join(all_content[:5])  # 最多5个内容
            
            knowledge_node = KnowledgeNode(
                id=node_id,
                title=f"知识节点_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                content=content,
                category=key_info.get('category', 'general'),
                tags=key_info.get('tags', []),
                importance=key_info.get('importance', 5),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                metadata={
                    "user_id": user_id,
                    "extraction_method": "llm_extraction",
                    "source": "interaction"
                }
            )
            
            return knowledge_node
            
        except Exception as e:
            self.logger.error(f"创建知识节点失败: {e}")
            return None
    
    async def _store_knowledge_node(self, knowledge_node: KnowledgeNode):
        """存储知识节点"""
        try:
            # 存储到内存
            self.knowledge_graph[knowledge_node.id] = knowledge_node
            
            # 存储到向量数据库
            await self.vector_store.add_document(
                id=knowledge_node.id,
                content=knowledge_node.content,
                metadata={
                    "title": knowledge_node.title,
                    "category": knowledge_node.category,
                    "tags": knowledge_node.tags,
                    "importance": knowledge_node.importance,
                    "created_at": knowledge_node.created_at
                }
            )
            
            # 存储到持久化存储
            note = Note(
                id=knowledge_node.id,
                user_id=knowledge_node.metadata.get('user_id', ''),
                title=knowledge_node.title,
                content=knowledge_node.content,
                note_type="knowledge_node",
                tags=knowledge_node.tags,
                metadata=knowledge_node.metadata
            )
            
            await self.storage_manager.save_note(note)
            
            self.logger.info(f"💾 知识节点已存储: {knowledge_node.id}")
            
        except Exception as e:
            self.logger.error(f"存储知识节点失败: {e}")
    
    async def _create_decision_record(
        self, 
        decision_data: Dict[str, Any], 
        user_id: str, 
        session_id: str
    ) -> Optional[DecisionRecord]:
        """创建决策记录"""
        try:
            if not decision_data.get('decision'):
                return None
            
            decision_record = DecisionRecord(
                id=str(uuid.uuid4()),
                decision=decision_data['decision'],
                context=decision_data.get('context', ''),
                reasoning=decision_data.get('reasoning', ''),
                confidence=decision_data.get('confidence', 0.5),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                tags=["decision", "user_choice"],
                metadata={
                    "user_id": user_id,
                    "session_id": session_id,
                    "source": "interaction"
                }
            )
            
            return decision_record
            
        except Exception as e:
            self.logger.error(f"创建决策记录失败: {e}")
            return None
    
    async def _create_memory_fragment(
        self, 
        key_info: Dict[str, Any], 
        user_id: str, 
        session_id: str
    ) -> Optional[MemoryFragment]:
        """创建记忆片段"""
        try:
            # 确定记忆类型
            memory_type = "fact"
            if key_info.get('preferences'):
                memory_type = "preference"
            elif key_info.get('learnings'):
                memory_type = "skill"
            elif key_info.get('emotions'):
                memory_type = "experience"
            
            # 选择最重要的内容作为记忆
            content = ""
            if key_info.get('facts'):
                content = key_info['facts'][0]
            elif key_info.get('preferences'):
                content = key_info['preferences'][0]
            elif key_info.get('learnings'):
                content = key_info['learnings'][0]
            
            if not content:
                return None
            
            memory_fragment = MemoryFragment(
                id=str(uuid.uuid4()),
                content=content,
                memory_type=memory_type,
                importance=key_info.get('importance', 5),
                emotional_weight=0.5,  # 默认情感权重
                created_at=datetime.now().isoformat(),
                metadata={
                    "user_id": user_id,
                    "session_id": session_id,
                    "category": key_info.get('category', 'general'),
                    "tags": key_info.get('tags', [])
                }
            )
            
            return memory_fragment
            
        except Exception as e:
            self.logger.error(f"创建记忆片段失败: {e}")
            return None
    
    async def _update_brain_state(
        self, 
        user_id: str, 
        session_id: str, 
        agent_name: str, 
        key_info: Dict[str, Any]
    ):
        """更新大脑状态"""
        try:
            brain_key = f"{user_id}_{session_id}_{agent_name}"
            
            if brain_key not in self.brain_states:
                # 创建新的大脑状态
                self.brain_states[brain_key] = BrainState(
                    user_id=user_id,
                    session_id=session_id,
                    agent_name=agent_name,
                    active_memories=[],
                    current_focus="",
                    learning_mode=True,
                    memory_consolidation_needed=False,
                    last_consolidation=datetime.now().isoformat(),
                    brain_health_score=1.0,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
            
            # 更新大脑状态
            brain_state = self.brain_states[brain_key]
            brain_state.updated_at = datetime.now().isoformat()
            
            # 更新当前焦点
            if key_info.get('intentions'):
                brain_state.current_focus = key_info['intentions'][0]
            
            # 检查是否需要记忆巩固
            if len(self.memory_fragments) >= self.learning_config['consolidation_threshold']:
                brain_state.memory_consolidation_needed = True
            
            # 更新大脑健康分数
            brain_state.brain_health_score = self._calculate_brain_health_score(brain_state)
            
            self.logger.info(f"🧠 大脑状态已更新: {brain_key}")
            
        except Exception as e:
            self.logger.error(f"更新大脑状态失败: {e}")
    
    def _calculate_brain_health_score(self, brain_state: BrainState) -> float:
        """计算大脑健康分数"""
        try:
            # 基础分数
            base_score = 1.0
            
            # 根据记忆数量调整
            memory_count = len(self.memory_fragments)
            if memory_count > 0:
                memory_score = min(1.0, memory_count / 100)  # 100个记忆为满分
            else:
                memory_score = 0.5
            
            # 根据学习模式调整
            learning_bonus = 0.1 if brain_state.learning_mode else 0.0
            
            # 综合分数
            health_score = (base_score + memory_score + learning_bonus) / 3
            
            return min(1.0, max(0.0, health_score))
            
        except Exception as e:
            self.logger.error(f"计算大脑健康分数失败: {e}")
            return 0.5
    
    async def _should_consolidate_memories(self, user_id: str) -> bool:
        """检查是否需要记忆巩固"""
        try:
            # 检查记忆数量
            user_memories = [
                mem for mem in self.memory_fragments.values()
                if mem.metadata.get('user_id') == user_id
            ]
            
            if len(user_memories) >= self.learning_config['consolidation_threshold']:
                return True
            
            # 检查时间间隔
            brain_key = f"{user_id}_*_*"
            for key, brain_state in self.brain_states.items():
                if key.startswith(f"{user_id}_"):
                    last_consolidation = datetime.fromisoformat(brain_state.last_consolidation)
                    if (datetime.now() - last_consolidation).days >= 1:  # 至少1天
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查记忆巩固需求失败: {e}")
            return False
    
    async def _consolidate_memories(self, user_id: str):
        """巩固记忆"""
        try:
            self.logger.info(f"🔄 开始记忆巩固: {user_id}")
            
            # 获取用户的所有记忆
            user_memories = [
                mem for mem in self.memory_fragments.values()
                if mem.metadata.get('user_id') == user_id
            ]
            
            if not user_memories:
                return
            
            # 按重要性排序
            user_memories.sort(key=lambda x: x.importance, reverse=True)
            
            # 保留最重要的记忆
            important_memories = user_memories[:50]  # 保留前50个重要记忆
            
            # 删除不重要的记忆
            for memory in user_memories[50:]:
                if memory.id in self.memory_fragments:
                    del self.memory_fragments[memory.id]
            
            # 更新大脑状态
            brain_key = f"{user_id}_*_*"
            for key, brain_state in self.brain_states.items():
                if key.startswith(f"{user_id}_"):
                    brain_state.memory_consolidation_needed = False
                    brain_state.last_consolidation = datetime.now().isoformat()
            
            self.logger.info(f"✅ 记忆巩固完成: 保留 {len(important_memories)} 个重要记忆")
            
        except Exception as e:
            self.logger.error(f"记忆巩固失败: {e}")
    
    async def retrieve_relevant_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 10
    ) -> List[MemoryFragment]:
        """检索相关记忆"""
        try:
            # 使用向量搜索
            search_results = await self.vector_store.search(
                query=query,
                limit=limit,
                filter_metadata={"user_id": user_id}
            )
            
            relevant_memories = []
            for result in search_results:
                memory_id = result.get('id')
                if memory_id in self.memory_fragments:
                    memory = self.memory_fragments[memory_id]
                    # 更新访问统计
                    memory.access_count += 1
                    memory.last_accessed = datetime.now().isoformat()
                    relevant_memories.append(memory)
            
            self.logger.info(f"🔍 检索到 {len(relevant_memories)} 个相关记忆")
            return relevant_memories
            
        except Exception as e:
            self.logger.error(f"检索相关记忆失败: {e}")
            return []
    
    async def get_brain_summary(self, user_id: str) -> Dict[str, Any]:
        """获取大脑摘要"""
        try:
            # 统计记忆数量
            user_memories = [
                mem for mem in self.memory_fragments.values()
                if mem.metadata.get('user_id') == user_id
            ]
            
            # 统计知识节点
            user_knowledge = [
                node for node in self.knowledge_graph.values()
                if node.metadata.get('user_id') == user_id
            ]
            
            # 统计决策记录
            user_decisions = [
                decision for decision in self.decision_history
                if decision.metadata.get('user_id') == user_id
            ]
            
            # 计算大脑健康分数
            brain_health = 0.0
            for key, brain_state in self.brain_states.items():
                if key.startswith(f"{user_id}_"):
                    brain_health = max(brain_health, brain_state.brain_health_score)
            
            summary = {
                "user_id": user_id,
                "total_memories": len(user_memories),
                "total_knowledge": len(user_knowledge),
                "total_decisions": len(user_decisions),
                "brain_health_score": brain_health,
                "memory_types": {},
                "knowledge_categories": {},
                "recent_activity": [],
                "created_at": datetime.now().isoformat()
            }
            
            # 统计记忆类型
            for memory in user_memories:
                memory_type = memory.memory_type
                summary["memory_types"][memory_type] = summary["memory_types"].get(memory_type, 0) + 1
            
            # 统计知识类别
            for knowledge in user_knowledge:
                category = knowledge.category
                summary["knowledge_categories"][category] = summary["knowledge_categories"].get(category, 0) + 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"获取大脑摘要失败: {e}")
            return {"error": str(e)}
    
    async def _log_observation_to_generative_agents(
        self,
        user_id: str,
        session_id: str,
        agent_name: str,
        key_info: Dict[str, Any],
        interaction_data: Dict[str, Any]
    ):
        """记录观察到生成式智能体"""
        try:
            # 确定观察内容
            content = interaction_data.get('user_input', '') or interaction_data.get('content', '')
            if not content:
                return
            
            # 确定观察来源
            source = "user_input" if 'user_input' in interaction_data else "system_response"
            
            # 确定重要性
            importance = key_info.get('importance', 5)
            
            # 确定类别
            category = key_info.get('category', 'interaction')
            
            # 确定标签
            tags = key_info.get('tags', [])
            
            # 记录观察
            await self.generative_agents.log_observation(
                content=content,
                source=source,
                importance=importance,
                category=category,
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                tags=tags,
                metadata={
                    'key_info': key_info,
                    'interaction_data': interaction_data
                }
            )
            
            self.logger.info(f"📝 记录观察到生成式智能体: {user_id}")
            
        except Exception as e:
            self.logger.error(f"记录观察到生成式智能体失败: {e}")
    
    async def detect_and_learn_from_failure(
        self,
        action: str,
        expected_result: str,
        actual_result: str,
        context: Dict[str, Any],
        user_id: str,
        session_id: str,
        agent_name: str
    ) -> bool:
        """
        检测失败并学习
        
        Args:
            action: 执行的动作
            expected_result: 期望结果
            actual_result: 实际结果
            context: 上下文信息
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            
        Returns:
            是否检测到失败并学习
        """
        try:
            # 使用反思机制检测失败
            failure_event = await self.reflexion_mechanism.detect_failure(
                action=action,
                expected_result=expected_result,
                actual_result=actual_result,
                context=context,
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name
            )
            
            if failure_event:
                self.logger.info(f"🔍 检测到失败并学习: {failure_event.id}")
                return True
            else:
                self.logger.info("✅ 未检测到失败")
                return False
                
        except Exception as e:
            self.logger.error(f"失败检测和学习失败: {e}")
            return False
    
    async def get_applicable_reflection_rules(
        self,
        action: str,
        context: Dict[str, Any],
        user_id: str
    ) -> List[Any]:
        """获取适用的反思规则"""
        try:
            return await self.reflexion_mechanism.get_applicable_rules(action, context)
        except Exception as e:
            self.logger.error(f"获取反思规则失败: {e}")
            return []
    
    async def get_user_insights(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Any]:
        """获取用户洞察"""
        try:
            return await self.generative_agents.get_user_insights(user_id, limit)
        except Exception as e:
            self.logger.error(f"获取用户洞察失败: {e}")
            return []
    
    async def get_enhanced_brain_summary(self, user_id: str) -> Dict[str, Any]:
        """获取增强的大脑摘要"""
        try:
            # 获取基础大脑摘要
            basic_summary = await self.get_brain_summary(user_id)
            
            # 获取反思摘要
            reflexion_summary = await self.reflexion_mechanism.get_reflection_summary(user_id)
            
            # 获取合成摘要
            synthesis_summary = await self.generative_agents.get_synthesis_summary(user_id)
            
            # 合并摘要
            enhanced_summary = {
                **basic_summary,
                "reflexion": reflexion_summary,
                "synthesis": synthesis_summary,
                "enhanced_features": {
                    "reflexion_enabled": True,
                    "generative_agents_enabled": True,
                    "failure_detection": True,
                    "insight_generation": True
                }
            }
            
            return enhanced_summary
            
        except Exception as e:
            self.logger.error(f"获取增强大脑摘要失败: {e}")
            return {"error": str(e)}


# 全局外部大脑实例
_global_brain = None

def get_external_brain() -> ExternalBrain:
    """获取全局外部大脑"""
    global _global_brain
    if _global_brain is None:
        _global_brain = ExternalBrain()
    return _global_brain

async def learn_from_interaction(
    user_id: str,
    session_id: str,
    agent_name: str,
    interaction_data: Dict[str, Any]
) -> bool:
    """从交互中学习（便捷函数）"""
    brain = get_external_brain()
    await brain.initialize()
    return await brain.learn_from_interaction(user_id, session_id, agent_name, interaction_data)


def main():
    """主函数 - 用于测试和演示"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建外部大脑
    brain = ExternalBrain()
    
    # 模拟学习测试
    logger.info("外部大脑系统测试完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

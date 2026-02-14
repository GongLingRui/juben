"""
Generative Agents机制 - 从观察中总结，合成洞察
基于周期性的观察总结和洞察合成系统
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
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.storage_manager import JubenStorageManager, Note
    from utils.llm_client import JubenLLMClient
    from utils.vector_store import VectorStore


@dataclass
class ObservationLog:
    """观察日志"""
    id: str
    timestamp: str
    content: str
    source: str  # user_input, system_response, interaction, etc.
    importance: int  # 1-10
    category: str
    tags: List[str]
    user_id: str
    session_id: str
    agent_name: str
    metadata: Dict[str, Any]


@dataclass
class SynthesisInsight:
    """合成洞察"""
    id: str
    insight_type: str  # pattern, trend, behavior, preference, etc.
    title: str
    description: str
    evidence: List[str]  # 支撑证据
    confidence: float  # 0-1
    importance: int  # 1-10
    created_at: str
    updated_at: str
    tags: List[str]
    related_observations: List[str]  # 相关观察ID
    user_id: str
    metadata: Dict[str, Any]


@dataclass
class SynthesisSession:
    """合成会话"""
    id: str
    user_id: str
    start_time: str
    end_time: str
    observations_processed: int
    insights_generated: int
    synthesis_method: str
    quality_score: float  # 0-1
    status: str  # active, completed, failed
    metadata: Dict[str, Any]


class GenerativeAgents:
    """Generative Agents机制"""
    
    def __init__(self, model_provider: str = "zhipu"):
        """
        初始化Generative Agents机制
        
        Args:
            model_provider: 模型提供商
        """
        self.config = JubenSettings()
        self.logger = JubenLogger("GenerativeAgents", level=self.config.log_level)
        self.storage_manager = JubenStorageManager()
        self.llm_client = JubenLLMClient(model_provider)
        self.vector_store = VectorStore()
        
        # 观察和洞察状态
        self.observation_logs: Dict[str, ObservationLog] = {}
        self.synthesis_insights: Dict[str, SynthesisInsight] = {}
        self.synthesis_sessions: Dict[str, SynthesisSession] = {}
        
        # 合成配置
        self.synthesis_config = {
            "auto_synthesis": True,
            "synthesis_interval_hours": 24,  # 合成间隔（小时）
            "min_observations_for_synthesis": 10,  # 最少观察数量
            "insight_confidence_threshold": 0.6,  # 洞察置信度阈值
            "max_insights_per_session": 20,  # 每次合成最大洞察数
            "observation_retention_days": 30  # 观察保留天数
        }
        
        self.logger.info("Generative Agents机制初始化完成")
    
    async def initialize(self):
        """初始化Generative Agents机制"""
        try:
            await self.storage_manager.initialize()
            await self.vector_store.initialize()
            self.logger.info("✅ Generative Agents机制初始化成功")
        except Exception as e:
            self.logger.error(f"❌ Generative Agents机制初始化失败: {e}")
            raise
    
    async def log_observation(
        self,
        content: str,
        source: str,
        importance: int,
        category: str,
        user_id: str,
        session_id: str,
        agent_name: str,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ObservationLog:
        """
        记录观察日志
        
        Args:
            content: 观察内容
            source: 观察来源
            importance: 重要性（1-10）
            category: 类别
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            tags: 标签
            metadata: 元数据
            
        Returns:
            观察日志对象
        """
        try:
            # 创建观察日志
            observation = ObservationLog(
                id=str(uuid.uuid4()),
                timestamp=datetime.now().isoformat(),
                content=content,
                source=source,
                importance=importance,
                category=category,
                tags=tags or [],
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                metadata=metadata or {}
            )
            
            # 存储观察日志
            self.observation_logs[observation.id] = observation
            
            # 存储到持久化存储
            await self._store_observation(observation)
            
            # 检查是否需要触发合成
            if await self._should_trigger_synthesis(user_id):
                await self._trigger_synthesis(user_id)
            
            self.logger.info(f"📝 记录观察: {observation.id}")
            return observation
            
        except Exception as e:
            self.logger.error(f"记录观察失败: {e}")
            raise
    
    async def _store_observation(self, observation: ObservationLog):
        """存储观察日志"""
        try:
            # 存储到向量数据库
            await self.vector_store.add_document(
                id=observation.id,
                content=observation.content,
                metadata={
                    "timestamp": observation.timestamp,
                    "source": observation.source,
                    "importance": observation.importance,
                    "category": observation.category,
                    "tags": observation.tags,
                    "user_id": observation.user_id,
                    "session_id": observation.session_id,
                    "agent_name": observation.agent_name
                }
            )
            
            # 存储到持久化存储
            note = Note(
                id=observation.id,
                user_id=observation.user_id,
                title=f"观察_{observation.category}_{observation.timestamp}",
                content=observation.content,
                note_type="observation",
                tags=observation.tags,
                metadata={
                    "source": observation.source,
                    "importance": observation.importance,
                    "category": observation.category,
                    "session_id": observation.session_id,
                    "agent_name": observation.agent_name,
                    "timestamp": observation.timestamp
                }
            )
            
            await self.storage_manager.save_note(note)
            
        except Exception as e:
            self.logger.error(f"存储观察失败: {e}")
    
    async def _should_trigger_synthesis(self, user_id: str) -> bool:
        """检查是否需要触发合成"""
        try:
            # 获取用户的观察数量
            user_observations = [
                obs for obs in self.observation_logs.values()
                if obs.user_id == user_id
            ]
            
            # 检查观察数量
            if len(user_observations) >= self.synthesis_config['min_observations_for_synthesis']:
                return True
            
            # 检查时间间隔
            if user_observations:
                latest_observation = max(user_observations, key=lambda x: x.timestamp)
                latest_time = datetime.fromisoformat(latest_observation.timestamp)
                if (datetime.now() - latest_time).total_seconds() >= \
                   self.synthesis_config['synthesis_interval_hours'] * 3600:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查合成触发条件失败: {e}")
            return False
    
    async def _trigger_synthesis(self, user_id: str):
        """触发合成流程"""
        try:
            self.logger.info(f"🔄 触发合成流程: {user_id}")
            
            # 创建合成会话
            synthesis_session = SynthesisSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                start_time=datetime.now().isoformat(),
                end_time="",
                observations_processed=0,
                insights_generated=0,
                synthesis_method="llm_synthesis",
                quality_score=0.0,
                status="active",
                metadata={}
            )
            
            self.synthesis_sessions[synthesis_session.id] = synthesis_session
            
            # 执行合成流程
            await self._execute_synthesis(synthesis_session)
            
        except Exception as e:
            self.logger.error(f"触发合成流程失败: {e}")
    
    async def _execute_synthesis(self, synthesis_session: SynthesisSession):
        """执行合成流程"""
        try:
            self.logger.info(f"🧠 开始合成流程: {synthesis_session.id}")
            
            # 1. 收集相关观察
            relevant_observations = await self._collect_relevant_observations(synthesis_session.user_id)
            synthesis_session.observations_processed = len(relevant_observations)
            
            if not relevant_observations:
                self.logger.warning("没有找到相关观察，跳过合成")
                return
            
            # 2. 生成观察总结
            observation_summary = await self._generate_observation_summary(relevant_observations)
            
            # 3. 生成洞察
            insights = await self._generate_insights(observation_summary, relevant_observations)
            
            # 4. 存储洞察
            for insight in insights:
                self.synthesis_insights[insight.id] = insight
                await self._store_insight(insight)
                synthesis_session.insights_generated += 1
            
            # 5. 更新合成会话
            synthesis_session.end_time = datetime.now().isoformat()
            synthesis_session.status = "completed"
            synthesis_session.quality_score = self._calculate_synthesis_quality(insights)
            
            # 6. 存储合成会话
            await self._store_synthesis_session(synthesis_session)
            
            self.logger.info(f"✅ 合成流程完成: 生成 {len(insights)} 个洞察")
            
        except Exception as e:
            self.logger.error(f"执行合成流程失败: {e}")
            synthesis_session.status = "failed"
            synthesis_session.end_time = datetime.now().isoformat()
    
    async def _collect_relevant_observations(self, user_id: str) -> List[ObservationLog]:
        """收集相关观察"""
        try:
            # 获取用户的所有观察
            user_observations = [
                obs for obs in self.observation_logs.values()
                if obs.user_id == user_id
            ]
            
            # 按重要性排序
            user_observations.sort(key=lambda x: x.importance, reverse=True)
            
            # 限制数量
            max_observations = 50
            relevant_observations = user_observations[:max_observations]
            
            self.logger.info(f"📊 收集到 {len(relevant_observations)} 个相关观察")
            return relevant_observations
            
        except Exception as e:
            self.logger.error(f"收集相关观察失败: {e}")
            return []
    
    async def _generate_observation_summary(self, observations: List[ObservationLog]) -> str:
        """生成观察总结"""
        try:
            # 构建观察总结提示词
            prompt = self._build_observation_summary_prompt(observations)
            
            # 调用LLM生成总结
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                return response['content']
            else:
                return self._simple_observation_summary(observations)
                
        except Exception as e:
            self.logger.error(f"生成观察总结失败: {e}")
            return self._simple_observation_summary(observations)
    
    def _build_observation_summary_prompt(self, observations: List[ObservationLog]) -> str:
        """构建观察总结提示词"""
        # 准备观察数据
        observation_data = []
        for obs in observations[:20]:  # 限制数量
            observation_data.append({
                "timestamp": obs.timestamp,
                "content": obs.content,
                "source": obs.source,
                "importance": obs.importance,
                "category": obs.category,
                "tags": obs.tags
            })
        
        prompt = f"""
你是一个专业的观察总结专家，需要从大量观察中提炼核心动态和模式。

## 观察数据
{json.dumps(observation_data, ensure_ascii=False, indent=2)}

## 任务要求
请分析以上观察数据，生成一个综合总结，包括：

1. **核心动态**: 观察中体现的主要趋势和变化
2. **关键模式**: 重复出现的行为模式和规律
3. **重要事件**: 具有特殊意义的事件和转折点
4. **用户特征**: 从观察中推断出的用户特征和偏好
5. **系统表现**: 系统在不同情况下的表现特点

## 输出要求
请生成一个结构化的总结，突出重点，避免冗余，确保总结具有洞察价值。

总结应该：
- 简洁明了，重点突出
- 基于数据，有理有据
- 具有前瞻性，能够指导未来行动
- 体现用户和系统的互动模式
"""
        
        return prompt
    
    def _simple_observation_summary(self, observations: List[ObservationLog]) -> str:
        """简单观察总结（备用方案）"""
        # 按类别统计
        category_stats = {}
        for obs in observations:
            category = obs.category
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1
        
        # 按重要性统计
        high_importance = [obs for obs in observations if obs.importance >= 7]
        
        summary = f"""
观察总结：
- 总观察数: {len(observations)}
- 高重要性观察: {len(high_importance)}
- 类别分布: {category_stats}
- 时间范围: {observations[0].timestamp if observations else 'N/A'} 到 {observations[-1].timestamp if observations else 'N/A'}
"""
        
        return summary
    
    async def _generate_insights(
        self, 
        observation_summary: str, 
        observations: List[ObservationLog]
    ) -> List[SynthesisInsight]:
        """生成洞察"""
        try:
            # 构建洞察生成提示词
            prompt = self._build_insight_generation_prompt(observation_summary, observations)
            
            # 调用LLM生成洞察
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.4
            )
            
            if response and response.get('content'):
                # 解析洞察
                insights_data = self._parse_insights_response(response['content'])
                return self._create_insights_from_data(insights_data, observations)
            else:
                return self._create_default_insights(observations)
                
        except Exception as e:
            self.logger.error(f"生成洞察失败: {e}")
            return self._create_default_insights(observations)
    
    def _build_insight_generation_prompt(
        self, 
        observation_summary: str, 
        observations: List[ObservationLog]
    ) -> str:
        """构建洞察生成提示词"""
        # 准备观察样本
        sample_observations = observations[:10]  # 取前10个观察作为样本
        
        prompt = f"""
你是一个专业的洞察生成专家，需要从观察总结中提炼有价值的洞察。

## 观察总结
{observation_summary}

## 观察样本
{json.dumps([{
    "timestamp": obs.timestamp,
    "content": obs.content,
    "source": obs.source,
    "importance": obs.importance,
    "category": obs.category
} for obs in sample_observations], ensure_ascii=False, indent=2)}

## 任务要求
基于以上信息，生成3-5个有价值的洞察，每个洞察应该：

1. **洞察类型**: 明确洞察的类型（模式、趋势、行为、偏好等）
2. **洞察标题**: 简洁明了的标题
3. **洞察描述**: 详细的描述和解释
4. **支撑证据**: 具体的证据和例子
5. **置信度**: 对洞察准确性的评估（0-1）
6. **重要性**: 洞察的重要性（1-10）

## 输出格式
请按照以下JSON格式输出：

```json
{{
    "insights": [
        {{
            "insight_type": "模式/趋势/行为/偏好",
            "title": "洞察标题",
            "description": "洞察详细描述",
            "evidence": ["证据1", "证据2"],
            "confidence": 0.8,
            "importance": 8
        }}
    ]
}}
```

请确保洞察具有：
- 实用性和可操作性
- 基于数据的准确性
- 对未来行动的指导价值
- 体现用户和系统的深层特征
"""
        
        return prompt
    
    def _parse_insights_response(self, llm_response: str) -> Dict[str, Any]:
        """解析洞察响应"""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                return self._simple_parse_insights_response(llm_response)
        except Exception as e:
            self.logger.error(f"解析洞察响应失败: {e}")
            return self._simple_parse_insights_response(llm_response)
    
    def _simple_parse_insights_response(self, response: str) -> Dict[str, Any]:
        """简单解析洞察响应"""
        return {
            "insights": [
                {
                    "insight_type": "模式",
                    "title": "用户行为模式",
                    "description": response[:200],
                    "evidence": ["观察数据"],
                    "confidence": 0.6,
                    "importance": 6
                }
            ]
        }
    
    def _create_insights_from_data(
        self, 
        insights_data: Dict[str, Any], 
        observations: List[ObservationLog]
    ) -> List[SynthesisInsight]:
        """从数据创建洞察"""
        insights = []
        
        for insight_data in insights_data.get('insights', []):
            insight = SynthesisInsight(
                id=str(uuid.uuid4()),
                insight_type=insight_data.get('insight_type', 'general'),
                title=insight_data.get('title', '未命名洞察'),
                description=insight_data.get('description', ''),
                evidence=insight_data.get('evidence', []),
                confidence=insight_data.get('confidence', 0.5),
                importance=insight_data.get('importance', 5),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                tags=['synthesis', 'auto_generated'],
                related_observations=[obs.id for obs in observations[:5]],  # 关联前5个观察
                user_id=observations[0].user_id if observations else 'unknown',
                metadata={
                    'synthesis_method': 'llm_generated',
                    'observation_count': len(observations)
                }
            )
            insights.append(insight)
        
        return insights
    
    def _create_default_insights(self, observations: List[ObservationLog]) -> List[SynthesisInsight]:
        """创建默认洞察"""
        if not observations:
            return []
        
        # 基于观察数据创建简单洞察
        insight = SynthesisInsight(
            id=str(uuid.uuid4()),
            insight_type="模式",
            title="用户行为模式分析",
            description=f"基于 {len(observations)} 个观察的用户行为模式分析",
            evidence=[obs.content for obs in observations[:3]],
            confidence=0.5,
            importance=6,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=['synthesis', 'default'],
            related_observations=[obs.id for obs in observations[:5]],
            user_id=observations[0].user_id,
            metadata={
                'synthesis_method': 'default_generated',
                'observation_count': len(observations)
            }
        )
        
        return [insight]
    
    async def _store_insight(self, insight: SynthesisInsight):
        """存储洞察"""
        try:
            # 存储到向量数据库
            await self.vector_store.add_document(
                id=insight.id,
                content=f"{insight.title}: {insight.description}",
                metadata={
                    "insight_type": insight.insight_type,
                    "confidence": insight.confidence,
                    "importance": insight.importance,
                    "user_id": insight.user_id,
                    "created_at": insight.created_at
                }
            )
            
            # 存储到持久化存储
            note = Note(
                id=insight.id,
                user_id=insight.user_id,
                title=f"洞察_{insight.title}",
                content=insight.description,
                note_type="synthesis_insight",
                tags=insight.tags,
                metadata={
                    "insight_type": insight.insight_type,
                    "confidence": insight.confidence,
                    "importance": insight.importance,
                    "evidence": insight.evidence,
                    "related_observations": insight.related_observations,
                    "created_at": insight.created_at
                }
            )
            
            await self.storage_manager.save_note(note)
            
        except Exception as e:
            self.logger.error(f"存储洞察失败: {e}")
    
    async def _store_synthesis_session(self, session: SynthesisSession):
        """存储合成会话"""
        try:
            note = Note(
                id=session.id,
                user_id=session.user_id,
                title=f"合成会话_{session.start_time}",
                content=json.dumps(asdict(session), ensure_ascii=False, indent=2),
                note_type="synthesis_session",
                tags=['synthesis', 'session'],
                metadata={
                    "user_id": session.user_id,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "status": session.status,
                    "quality_score": session.quality_score
                }
            )
            
            await self.storage_manager.save_note(note)
            
        except Exception as e:
            self.logger.error(f"存储合成会话失败: {e}")
    
    def _calculate_synthesis_quality(self, insights: List[SynthesisInsight]) -> float:
        """计算合成质量分数"""
        try:
            if not insights:
                return 0.0
            
            # 基于洞察的置信度和重要性计算质量分数
            total_score = 0.0
            for insight in insights:
                score = (insight.confidence + insight.importance / 10.0) / 2.0
                total_score += score
            
            quality_score = total_score / len(insights)
            return min(1.0, max(0.0, quality_score))
            
        except Exception as e:
            self.logger.error(f"计算合成质量分数失败: {e}")
            return 0.5
    
    async def get_user_insights(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[SynthesisInsight]:
        """获取用户洞察"""
        try:
            user_insights = [
                insight for insight in self.synthesis_insights.values()
                if insight.user_id == user_id
            ]
            
            # 按重要性和置信度排序
            user_insights.sort(
                key=lambda x: (x.importance, x.confidence), 
                reverse=True
            )
            
            return user_insights[:limit]
            
        except Exception as e:
            self.logger.error(f"获取用户洞察失败: {e}")
            return []
    
    async def get_synthesis_summary(self, user_id: str) -> Dict[str, Any]:
        """获取合成摘要"""
        try:
            # 统计观察数量
            user_observations = [
                obs for obs in self.observation_logs.values()
                if obs.user_id == user_id
            ]
            
            # 统计洞察数量
            user_insights = [
                insight for insight in self.synthesis_insights.values()
                if insight.user_id == user_id
            ]
            
            # 统计合成会话
            user_sessions = [
                session for session in self.synthesis_sessions.values()
                if session.user_id == user_id
            ]
            
            summary = {
                "user_id": user_id,
                "total_observations": len(user_observations),
                "total_insights": len(user_insights),
                "total_sessions": len(user_sessions),
                "insight_types": {},
                "recent_insights": [],
                "synthesis_quality": 0.0,
                "created_at": datetime.now().isoformat()
            }
            
            # 统计洞察类型
            for insight in user_insights:
                insight_type = insight.insight_type
                summary["insight_types"][insight_type] = \
                    summary["insight_types"].get(insight_type, 0) + 1
            
            # 最近洞察
            recent_insights = sorted(
                user_insights,
                key=lambda x: x.created_at,
                reverse=True
            )[:5]
            summary["recent_insights"] = [
                {
                    "id": i.id,
                    "title": i.title,
                    "type": i.insight_type,
                    "confidence": i.confidence,
                    "importance": i.importance
                }
                for i in recent_insights
            ]
            
            # 计算合成质量
            if user_sessions:
                quality_scores = [s.quality_score for s in user_sessions if s.quality_score > 0]
                if quality_scores:
                    summary["synthesis_quality"] = sum(quality_scores) / len(quality_scores)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"获取合成摘要失败: {e}")
            return {"error": str(e)}


# 全局Generative Agents实例
_global_generative_agents = None

def get_generative_agents() -> GenerativeAgents:
    """获取全局Generative Agents"""
    global _global_generative_agents
    if _global_generative_agents is None:
        _global_generative_agents = GenerativeAgents()
    return _global_generative_agents


async def log_observation(
    content: str,
    source: str,
    importance: int,
    category: str,
    user_id: str,
    session_id: str,
    agent_name: str,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None
) -> ObservationLog:
    """记录观察（便捷函数）"""
    agents = get_generative_agents()
    await agents.initialize()
    return await agents.log_observation(
        content, source, importance, category, user_id, session_id, agent_name, tags, metadata
    )


def main():
    """主函数 - 用于测试和演示"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建Generative Agents
    agents = GenerativeAgents()
    
    # 模拟观察记录测试
    logger.info("Generative Agents机制测试完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

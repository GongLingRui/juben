"""
用户反馈与数据收集管理器
实现反馈闭环和黄金样本库

功能：
1. AgentFeedback: 反馈数据模型
2. FeedbackManager: 反馈数据管理（MongoDB/PostgreSQL）
3. GoldSampleManager: 黄金样本库管理（Milvus）

代码作者：Claude
创建时间：2026年2月7日
"""

import json
import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


# ==================== 反馈数据模型 ====================

class FeedbackType(Enum):
    """反馈类型"""
    LIKE = "like"               # 点赞
    DISLIKE = "dislike"         # 点踩
    RATING = "rating"           # 评分
    REFINEMENT = "refinement"   # 编辑修改
    SKIP = "skip"               # 跳过


class FeedbackSource(Enum):
    """反馈来源"""
    CHAT = "chat"               # 聊天界面
    EDITOR = "editor"           # 编辑器
    WORKFLOW = "workflow"       # 工作流
    API = "api"                 # API调用


@dataclass
class AgentFeedback:
    """
    Agent 反馈数据模型

    字段：
    - trace_id: 关联一次生成的唯一标识
    - agent_name: Agent 名称
    - user_input: 用户输入
    - ai_output: AI 输出
    - user_rating: 用户评分 (1-5)
    - user_edit_text: 用户修改后的文本
    - feedback_type: 反馈类型
    - feedback_source: 反馈来源
    - edit_distance: 编辑距离（衡量修改幅度）
    - is_gold_sample: 是否为黄金样本
    """
    # 核心字段
    trace_id: str
    agent_name: str
    user_input: str
    ai_output: str

    # 反馈字段
    feedback_type: FeedbackType
    feedback_source: FeedbackSource
    user_rating: Optional[int] = None              # 1-5 评分
    user_edit_text: Optional[str] = None           # 用户修改后的文本

    # 分析字段
    edit_distance: Optional[int] = None            # 编辑距离
    edit_ratio: Optional[float] = None             # 修改比例
    similarity_score: Optional[float] = None       # 相似度

    # 黄金样本标记
    is_gold_sample: bool = False
    gold_sample_reason: Optional[str] = None

    # 元数据
    user_id: str = "unknown"
    session_id: str = "unknown"
    project_id: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 附加信息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['feedback_type'] = self.feedback_type.value
        data['feedback_source'] = self.feedback_source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentFeedback':
        """从字典创建"""
        if isinstance(data.get('feedback_type'), str):
            data['feedback_type'] = FeedbackType(data['feedback_type'])
        if isinstance(data.get('feedback_source'), str):
            data['feedback_source'] = FeedbackSource(data['feedback_source'])
        return cls(**data)

    def calculate_edit_metrics(self) -> Tuple[int, float]:
        """
        计算编辑距离和修改比例

        Returns:
            Tuple[int, float]: (编辑距离, 修改比例)
        """
        if not self.user_edit_text:
            return 0, 0.0

        # 使用 Levenshtein 距离计算编辑距离
        distance = self._levenshtein_distance(self.ai_output, self.user_edit_text)
        max_len = max(len(self.ai_output), len(self.user_edit_text), 1)
        ratio = distance / max_len

        self.edit_distance = distance
        self.edit_ratio = ratio
        self.similarity_score = 1.0 - ratio

        return distance, ratio

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算 Levenshtein 距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


# ==================== 反馈管理器 ====================

class FeedbackManager:
    """
    反馈管理器

    负责存储和查询反馈数据
    支持 MongoDB 和 PostgreSQL
    """

    def __init__(self, mongo_client=None, postgres_client=None):
        """
        初始化反馈管理器

        Args:
            mongo_client: MongoDB 客户端
            postgres_client: PostgreSQL 客户端
        """
        self.mongo_client = mongo_client
        self.postgres_client = postgres_client
        self.logger = logger

        # 配置
        self.mongo_db_name = "juben_feedback"
        self.mongo_collection = "agent_feedback"
        self.postgres_table = "agent_feedback"

        # 使用 MongoDB 作为默认
        self.use_mongo = mongo_client is not None

    async def save_feedback(self, feedback: AgentFeedback) -> bool:
        """
        保存反馈

        Args:
            feedback: 反馈对象

        Returns:
            bool: 是否保存成功
        """
        try:
            # 计算编辑指标
            feedback.calculate_edit_metrics()

            # 判断是否为黄金样本
            self._evaluate_gold_sample(feedback)

            if self.use_mongo:
                return await self._save_to_mongo(feedback)
            else:
                return await self._save_to_postgres(feedback)

        except Exception as e:
            self.logger.error(f"保存反馈失败: {e}")
            return False

    async def _save_to_mongo(self, feedback: AgentFeedback) -> bool:
        """保存到 MongoDB"""
        try:
            db = self.mongo_client[self.mongo_db_name]
            collection = db[self.mongo_collection]

            data = feedback.to_dict()
            data['created_at'] = datetime.now()

            await collection.insert_one(data)

            self.logger.info(f"✅ 反馈已保存到 MongoDB (trace: {feedback.trace_id})")
            return True

        except Exception as e:
            self.logger.error(f"保存到 MongoDB 失败: {e}")
            return False

    async def _save_to_postgres(self, feedback: AgentFeedback) -> bool:
        """保存到 PostgreSQL"""
        try:
            async with self.postgres_client.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO agent_feedback (
                        trace_id, agent_name, user_input, ai_output,
                        feedback_type, feedback_source, user_rating,
                        user_edit_text, edit_distance, edit_ratio,
                        similarity_score, is_gold_sample, gold_sample_reason,
                        user_id, session_id, project_id, timestamp, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    feedback.trace_id, feedback.agent_name, feedback.user_input,
                    feedback.ai_output, feedback.feedback_type.value,
                    feedback.feedback_source.value, feedback.user_rating,
                    feedback.user_edit_text, feedback.edit_distance,
                    feedback.edit_ratio, feedback.similarity_score,
                    feedback.is_gold_sample, feedback.gold_sample_reason,
                    feedback.user_id, feedback.session_id, feedback.project_id,
                    feedback.timestamp, json.dumps(feedback.metadata)
                ))

            await self.postgres_client.commit()

            self.logger.info(f"✅ 反馈已保存到 PostgreSQL (trace: {feedback.trace_id})")
            return True

        except Exception as e:
            self.logger.error(f"保存到 PostgreSQL 失败: {e}")
            await self.postgres_client.rollback()
            return False

    async def get_feedback(
        self,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        is_gold_sample: Optional[bool] = None,
        limit: int = 100
    ) -> List[AgentFeedback]:
        """
        获取反馈列表

        Args:
            trace_id: 追踪ID
            user_id: 用户ID
            agent_name: Agent名称
            is_gold_sample: 是否为黄金样本
            limit: 返回数量

        Returns:
            List[AgentFeedback]: 反馈列表
        """
        try:
            if self.use_mongo:
                return await self._get_from_mongo(
                    trace_id, user_id, agent_name, is_gold_sample, limit
                )
            else:
                return await self._get_from_postgres(
                    trace_id, user_id, agent_name, is_gold_sample, limit
                )

        except Exception as e:
            self.logger.error(f"获取反馈失败: {e}")
            return []

    async def _get_from_mongo(
        self,
        trace_id: Optional[str],
        user_id: Optional[str],
        agent_name: Optional[str],
        is_gold_sample: Optional[bool],
        limit: int
    ) -> List[AgentFeedback]:
        """从 MongoDB 获取"""
        try:
            db = self.mongo_client[self.mongo_db_name]
            collection = db[self.mongo_collection]

            query = {}
            if trace_id:
                query['trace_id'] = trace_id
            if user_id:
                query['user_id'] = user_id
            if agent_name:
                query['agent_name'] = agent_name
            if is_gold_sample is not None:
                query['is_gold_sample'] = is_gold_sample

            cursor = collection.find(query).sort('created_at', -1).limit(limit)
            results = []

            async for doc in cursor:
                doc.pop('_id', None)
                results.append(AgentFeedback.from_dict(doc))

            return results

        except Exception as e:
            self.logger.error(f"从 MongoDB 获取失败: {e}")
            return []

    async def _get_from_postgres(
        self,
        trace_id: Optional[str],
        user_id: Optional[str],
        agent_name: Optional[str],
        is_gold_sample: Optional[bool],
        limit: int
    ) -> List[AgentFeedback]:
        """从 PostgreSQL 获取"""
        try:
            async with self.postgres_client.cursor() as cursor:
                conditions = []
                params = []

                if trace_id:
                    conditions.append("trace_id = %s")
                    params.append(trace_id)
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                if agent_name:
                    conditions.append("agent_name = %s")
                    params.append(agent_name)
                if is_gold_sample is not None:
                    conditions.append("is_gold_sample = %s")
                    params.append(is_gold_sample)

                where_clause = " AND ".join(conditions) if conditions else "1=1"
                params.append(limit)

                await cursor.execute(f"""
                    SELECT * FROM agent_feedback
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, params)

                results = []
                rows = await cursor.fetchall()

                # 这里需要根据实际的列定义映射
                for row in rows:
                    # 简化处理，实际需要根据数据库结构
                    pass

                return results

        except Exception as e:
            self.logger.error(f"从 PostgreSQL 获取失败: {e}")
            return []

    def _evaluate_gold_sample(self, feedback: AgentFeedback) -> None:
        """
        评估是否为黄金样本

        条件：
        1. 用户评分 >= 4
        2. 或 用户未大幅修改（edit_ratio < 0.3）

        Args:
            feedback: 反馈对象
        """
        reasons = []

        # 条件1: 高评分
        if feedback.user_rating and feedback.user_rating >= 4:
            feedback.is_gold_sample = True
            reasons.append(f"高评分({feedback.user_rating}/5)")

        # 条件2: 低修改幅度
        if feedback.edit_ratio is not None and feedback.edit_ratio < 0.3:
            feedback.is_gold_sample = True
            reasons.append(f"低修改幅度({feedback.edit_ratio:.1%})")

        # 条件3: 点赞反馈
        if feedback.feedback_type == FeedbackType.LIKE:
            feedback.is_gold_sample = True
            reasons.append("用户点赞")

        if feedback.is_gold_sample and reasons:
            feedback.gold_sample_reason = ", ".join(reasons)
            self.logger.info(f"✅ 标记为黄金样本: {feedback.gold_sample_reason}")

    async def get_statistics(
        self,
        agent_name: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取反馈统计

        Args:
            agent_name: Agent名称（可选）
            days: 统计天数

        Returns:
            Dict: 统计信息
        """
        try:
            if not self.use_mongo:
                return {}

            db = self.mongo_client[self.mongo_db_name]
            collection = db[self.mongo_collection]

            # 计算时间范围
            start_date = datetime.now() - timedelta(days=days)

            # 构建查询
            query = {"created_at": {"$gte": start_date}}
            if agent_name:
                query["agent_name"] = agent_name

            # 统计
            total = await collection.count_documents(query)
            gold_samples = await collection.count_documents({
                **query,
                "is_gold_sample": True
            })

            # 按反馈类型统计
            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$feedback_type",
                    "count": {"$sum": 1}
                }}
            ]
            type_stats = {}
            async for doc in collection.aggregate(pipeline):
                type_stats[doc['_id']] = doc['count']

            # 按Agent统计
            if not agent_name:
                pipeline = [
                    {"$match": query},
                    {"$group": {
                        "_id": "$agent_name",
                        "count": {"$sum": 1},
                        "gold_count": {
                            "$sum": {"$cond": [{"$eq": ["$is_gold_sample", True]}, 1, 0]}
                        }
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
                agent_stats = []
                async for doc in collection.aggregate(pipeline):
                    agent_stats.append({
                        "agent_name": doc['_id'],
                        "total": doc['count'],
                        "gold_samples": doc['gold_count']
                    })
            else:
                agent_stats = []

            return {
                "period_days": days,
                "total_feedbacks": total,
                "gold_samples": gold_samples,
                "gold_ratio": gold_samples / total if total > 0 else 0,
                "by_type": type_stats,
                "by_agent": agent_stats
            }

        except Exception as e:
            self.logger.error(f"获取统计失败: {e}")
            return {}


# ==================== 黄金样本库管理器 ====================

@dataclass
class GoldSample:
    """黄金样本"""
    sample_id: str
    trace_id: str
    agent_name: str

    # 内容
    user_input: str
    ai_output: str
    feedback: AgentFeedback

    # 向量
    input_embedding: Optional[List[float]] = None
    output_embedding: Optional[List[float]] = None

    # 元数据
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    score: float = 1.0  # 质量分数


class GoldSampleManager:
    """
    黄金样本库管理器

    存储和管理高质量的成功案例
    用于后续的 Prompt 增强和 Few-Shot Learning
    """

    def __init__(self, milvus_client=None, embedding_client=None):
        """
        初始化黄金样本管理器

        Args:
            milvus_client: Milvus 客户端
            embedding_client: 嵌入向量客户端
        """
        self.milvus_client = milvus_client
        self.embedding_client = embedding_client
        self.logger = logger

        self.collection_name = "agent_success_cases"
        self.dimension = 768
        self._initialized = False

    async def _ensure_collection(self):
        """确保集合存在"""
        if self._initialized or not self.milvus_client:
            return

        try:
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility

            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.logger.info(f"✅ 加载黄金样本集合: {self.collection_name}")
            else:
                # 创建集合
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                    FieldSchema(name="sample_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="trace_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="agent_name", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="user_input", dtype=DataType.VARCHAR, max_length=8192),
                    FieldSchema(name="ai_output", dtype=DataType.VARCHAR, max_length=16384),
                    FieldSchema(name="user_rating", dtype=DataType.INT),
                    FieldSchema(name="feedback_type", dtype=DataType.VARCHAR, max_length=50),
                    FieldSchema(name="gold_reason", dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name="score", dtype=DataType.FLOAT),
                    FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=50),
                    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="input_embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                    FieldSchema(name="output_embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
                ]

                schema = CollectionSchema(fields, description="Agent黄金样本库")
                self.collection = Collection(name=self.collection_name, schema=schema)

                # 创建索引
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "IP",
                    "params": {"nlist": 128}
                }
                self.collection.create_index(field_name="input_embedding", index_params=index_params)
                self.collection.create_index(field_name="output_embedding", index_params=index_params)

                self.logger.info(f"✅ 创建黄金样本集合: {self.collection_name}")

            self._initialized = True

        except ImportError:
            self.logger.warning("pymilvus未安装，黄金样本库功能将不可用")
        except Exception as e:
            self.logger.error(f"初始化黄金样本集合失败: {e}")

    async def save_sample(self, feedback: AgentFeedback) -> Optional[str]:
        """
        保存黄金样本

        Args:
            feedback: 反馈对象（必须标记为黄金样本）

        Returns:
            Optional[str]: 样本ID，失败返回None
        """
        if not feedback.is_gold_sample:
            self.logger.warning("非黄金样本，跳过保存")
            return None

        try:
            await self._ensure_collection()

            if not self.embedding_client or not self.milvus_client:
                self.logger.warning("嵌入向量或Milvus客户端未配置")
                return None

            # 生成嵌入向量
            input_emb = await self._generate_embedding(feedback.user_input)
            output_emb = await self._generate_embedding(feedback.ai_output)

            if not input_emb or not output_emb:
                return None

            # 创建样本
            sample_id = f"gold_{uuid.uuid4().hex[:16]}"
            score = self._calculate_score(feedback)

            # 插入数据
            data = [
                [sample_id],
                [sample_id],
                [feedback.trace_id],
                [feedback.agent_name],
                [feedback.user_input],
                [feedback.ai_output],
                [feedback.user_rating or 5],
                [feedback.feedback_type.value],
                [feedback.gold_sample_reason or ""],
                [score],
                [feedback.timestamp],
                [feedback.user_id],
                [input_emb],
                [output_emb]
            ]

            self.collection.insert(data)
            self.collection.flush()

            self.logger.info(f"✅ 保存黄金样本 (sample: {sample_id}, agent: {feedback.agent_name}, score: {score:.2f})")
            return sample_id

        except Exception as e:
            self.logger.error(f"保存黄金样本失败: {e}")
            return None

    async def search_similar(
        self,
        query_input: str,
        agent_name: Optional[str] = None,
        top_k: int = 5
    ) -> List[GoldSample]:
        """
        搜索相似的成功案例

        Args:
            query_input: 查询输入
            agent_name: Agent名称（可选）
            top_k: 返回数量

        Returns:
            List[GoldSample]: 相似样本列表
        """
        try:
            await self._ensure_collection()

            if not self.embedding_client or not self.milvus_client:
                return []

            # 生成查询向量
            query_embedding = await self._generate_embedding(query_input)
            if not query_embedding:
                return []

            # 加载集合
            self.collection.load()

            # 构建搜索表达式
            expr = f"agent_name == '{agent_name}'" if agent_name else None

            # 执行搜索
            search_param = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }

            results = self.collection.search(
                data=[query_embedding],
                anns_field="input_embedding",
                param=search_param,
                limit=top_k,
                expr=expr,
                output_fields=["sample_id", "trace_id", "agent_name", "user_input", "ai_output", "score", "gold_reason"]
            )

            # 转换结果
            samples = []
            for hit in results[0]:
                samples.append(GoldSample(
                    sample_id=hit.entity.get("sample_id"),
                    trace_id=hit.entity.get("trace_id"),
                    agent_name=hit.entity.get("agent_name"),
                    user_input=hit.entity.get("user_input"),
                    ai_output=hit.entity.get("ai_output"),
                    feedback=AgentFeedback(
                        trace_id=hit.entity.get("trace_id"),
                        agent_name=hit.entity.get("agent_name"),
                        user_input=hit.entity.get("user_input"),
                        ai_output=hit.entity.get("ai_output"),
                        feedback_type=FeedbackType.LIKE,
                        feedback_source=FeedbackSource.API,
                        gold_sample_reason=hit.entity.get("gold_reason")
                    ),
                    score=hit.entity.get("score", 1.0)
                ))

            self.logger.info(f"✅ 搜索到 {len(samples)} 个相似样本")
            return samples

        except Exception as e:
            self.logger.error(f"搜索相似样本失败: {e}")
            return []

    async def get_samples_for_prompt(
        self,
        agent_name: str,
        current_input: str,
        count: int = 3
    ) -> List[Dict[str, str]]:
        """
        获取用于 Prompt 增强的样本

        Args:
            agent_name: Agent名称
            current_input: 当前输入
            count: 样本数量

        Returns:
            List[Dict]: 样本列表，格式: [{"input": "...", "output": "..."}]
        """
        samples = await self.search_similar(current_input, agent_name, top_k=count)

        return [
            {
                "input": sample.user_input,
                "output": sample.ai_output,
                "score": sample.score
            }
            for sample in samples
        ]

    def _calculate_score(self, feedback: AgentFeedback) -> float:
        """计算样本质量分数"""
        score = 1.0

        # 基于评分
        if feedback.user_rating:
            score = feedback.user_rating / 5.0

        # 基于修改幅度（修改越少越好）
        if feedback.edit_ratio is not None:
            score *= (1.0 - feedback.edit_ratio * 0.5)

        # 基于反馈类型
        if feedback.feedback_type == FeedbackType.LIKE:
            score *= 1.2
        elif feedback.feedback_type == FeedbackType.DISLIKE:
            score *= 0.5

        return min(max(score, 0.0), 1.0)

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成嵌入向量"""
        try:
            if not self.embedding_client:
                return None

            embedding = await self.embedding_client.embed(text)
            return embedding

        except Exception as e:
            self.logger.error(f"生成嵌入向量失败: {e}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """获取黄金样本统计"""
        try:
            await self._ensure_collection()

            if not self.milvus_client:
                return {}

            self.collection.load()

            # 获取总数
            total = self.collection.num_entities

            # 按 Agent 统计
            from pymilvus import utility
            # 这里简化处理，实际可以执行更复杂的聚合查询

            return {
                "total_samples": total,
                "collection_name": self.collection_name
            }

        except Exception as e:
            self.logger.error(f"获取统计失败: {e}")
            return {}


# ==================== 全局实例 ====================

_feedback_manager: Optional[FeedbackManager] = None
_gold_sample_manager: Optional[GoldSampleManager] = None


def get_feedback_manager(mongo_client=None, postgres_client=None) -> FeedbackManager:
    """获取反馈管理器单例"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager(
            mongo_client=mongo_client,
            postgres_client=postgres_client
        )
    return _feedback_manager


def get_gold_sample_manager(milvus_client=None, embedding_client=None) -> GoldSampleManager:
    """获取黄金样本管理器单例"""
    global _gold_sample_manager
    if _gold_sample_manager is None:
        _gold_sample_manager = GoldSampleManager(
            milvus_client=milvus_client,
            embedding_client=embedding_client
        )
    return _gold_sample_manager


# ==================== 便捷函数 ====================

async def record_feedback(
    trace_id: str,
    agent_name: str,
    user_input: str,
    ai_output: str,
    feedback_type: FeedbackType,
    user_rating: Optional[int] = None,
    user_edit_text: Optional[str] = None,
    user_id: str = "unknown",
    session_id: str = "unknown"
) -> bool:
    """
    记录反馈（便捷函数）

    Args:
        trace_id: 追踪ID
        agent_name: Agent名称
        user_input: 用户输入
        ai_output: AI输出
        feedback_type: 反馈类型
        user_rating: 用户评分
        user_edit_text: 用户修改后的文本
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        bool: 是否记录成功
    """
    feedback = AgentFeedback(
        trace_id=trace_id,
        agent_name=agent_name,
        user_input=user_input,
        ai_output=ai_output,
        feedback_type=feedback_type,
        feedback_source=FeedbackSource.CHAT,
        user_rating=user_rating,
        user_edit_text=user_edit_text,
        user_id=user_id,
        session_id=session_id
    )

    manager = get_feedback_manager()
    saved = await manager.save_feedback(feedback)

    # 如果是黄金样本，也保存到黄金样本库
    if saved and feedback.is_gold_sample:
        gold_manager = get_gold_sample_manager()
        await gold_manager.save_sample(feedback)

    return saved


async def record_refinement(
    trace_id: str,
    agent_name: str,
    original_text: str,
    modified_text: str,
    user_id: str = "unknown",
    session_id: str = "unknown"
) -> bool:
    """
    记录编辑修改（便捷函数）

    Args:
        trace_id: 追踪ID
        agent_name: Agent名称
        original_text: 原始文本
        modified_text: 修改后的文本
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        bool: 是否记录成功
    """
    feedback = AgentFeedback(
        trace_id=trace_id,
        agent_name=agent_name,
        user_input="",
        ai_output=original_text,
        feedback_type=FeedbackType.REFINEMENT,
        feedback_source=FeedbackSource.EDITOR,
        user_edit_text=modified_text,
        user_id=user_id,
        session_id=session_id
    )

    manager = get_feedback_manager()
    return await manager.save_feedback(feedback)


async def get_success_examples(
    agent_name: str,
    query_input: str,
    count: int = 3
) -> List[Dict[str, str]]:
    """
    获取成功案例（便捷函数）

    Args:
        agent_name: Agent名称
        query_input: 查询输入
        count: 数量

    Returns:
        List[Dict]: 成功案例列表
    """
    manager = get_gold_sample_manager()
    return await manager.get_samples_for_prompt(agent_name, query_input, count)


def generate_trace_id() -> str:
    """生成追踪ID"""
    import time
    timestamp = int(time.time() * 1000)
    unique = uuid.uuid4().hex[:8]
    return f"trace_{timestamp}_{unique}"


async def record_agent_success(
    trace_id: str,
    agent_name: str,
    user_input: str,
    ai_output: str,
    user_id: str = "unknown",
    session_id: str = "unknown"
) -> bool:
    """
    记录Agent成功案例（便捷函数）

    当Agent认为某次生成特别成功时，可以主动调用此函数记录。

    Args:
        trace_id: 追踪ID
        agent_name: Agent名称
        user_input: 用户输入
        ai_output: AI输出
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        bool: 是否记录成功
    """
    feedback = AgentFeedback(
        trace_id=trace_id,
        agent_name=agent_name,
        user_input=user_input,
        ai_output=ai_output,
        feedback_type=FeedbackType.LIKE,
        feedback_source=FeedbackSource.API,
        user_rating=5,  # 默认最高评分
        user_id=user_id,
        session_id=session_id
    )

    manager = get_feedback_manager()
    saved = await manager.save_feedback(feedback)

    # 如果是黄金样本，也保存到黄金样本库
    if saved and feedback.is_gold_sample:
        gold_manager = get_gold_sample_manager()
        await gold_manager.save_sample(feedback)

    return saved

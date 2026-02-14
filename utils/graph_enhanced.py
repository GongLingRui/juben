"""
生产级剧本创作图谱存储引擎 - 增强版
Enhanced Graph Database Manager for Screenplay Creation

基于2025年知识图谱最佳实践的增强实现：
1. 时间戳和版本控制
2. 性能监控和查询优化
3. 数据验证机制
4. 批量操作优化
5. GraphRAG集成支持
6. 备份恢复功能
7. 慢查询日志
8. 连接池健康检查

参考资源:
- Neo4j 2025最佳实践: https://neo4j.com/news/neo4j-good-practices/
- 生产级Neo4j调优: https://medium.com/@satanialish/the-production-ready-neo4j-guide-performance-tuning-and-best-practices-15b78a5fe229
- GraphRAG最佳实践: https://www.51cto.com/aigc/7892.html

作者：Claude
创建时间：2025-02-08
更新时间：2025-02-08
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict
import hashlib

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncManagedTransaction
from neo4j.exceptions import (
    ServiceUnavailable,
    TransientError,
    ClientError,
    SessionExpired,
    ConstraintError
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# 配置日志
logger = logging.getLogger(__name__)


# ============ 性能监控相关 ============

@dataclass
class QueryMetrics:
    """查询指标"""
    query: str
    parameters: Dict[str, Any]
    execution_time: float
    result_count: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


@dataclass
class PerformanceStats:
    """性能统计"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    slow_queries: int = 0  # 超过1秒的查询
    avg_query_time: float = 0.0
    max_query_time: float = 0.0
    min_query_time: float = float('inf')

    def update(self, metrics: QueryMetrics, slow_threshold: float = 1.0):
        """更新统计信息"""
        self.total_queries += 1
        if metrics.success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1

        # 更新查询时间统计
        self.max_query_time = max(self.max_query_time, metrics.execution_time)
        self.min_query_time = min(self.min_query_time, metrics.execution_time)

        # 计算新的平均值
        total_time = self.avg_query_time * (self.total_queries - 1) + metrics.execution_time
        self.avg_query_time = total_time / self.total_queries

        # 慢查询统计
        if metrics.execution_time > slow_threshold:
            self.slow_queries += 1
            logger.warning(
                f"慢查询检测: {metrics.query[:100]}... "
                f"执行时间: {metrics.execution_time:.3f}s"
            )


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.metrics: List[QueryMetrics] = []
        self.stats = PerformanceStats()
        self._lock = asyncio.Lock()

    async def record_query(
        self,
        query: str,
        parameters: Dict[str, Any],
        execution_time: float,
        result_count: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """记录查询指标"""
        metric = QueryMetrics(
            query=query,
            parameters=parameters,
            execution_time=execution_time,
            result_count=result_count,
            timestamp=datetime.now(timezone.utc),
            success=success,
            error_message=error_message
        )

        async with self._lock:
            self.metrics.append(metric)
            self.stats.update(metric, self.slow_query_threshold)

            # 只保留最近1000条记录
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            "total_queries": self.stats.total_queries,
            "successful_queries": self.stats.successful_queries,
            "failed_queries": self.stats.failed_queries,
            "slow_queries": self.stats.slow_queries,
            "avg_query_time": self.stats.avg_query_time,
            "max_query_time": self.stats.max_query_time,
            "min_query_time": self.stats.min_query_time if self.stats.min_query_time != float('inf') else 0.0,
            "success_rate": (
                self.stats.successful_queries / self.stats.total_queries * 100
                if self.stats.total_queries > 0 else 0
            ),
        }

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        sorted_queries = sorted(
            self.metrics,
            key=lambda m: m.execution_time,
            reverse=True
        )[:limit]

        return [
            {
                "query": m.query[:200],
                "execution_time": m.execution_time,
                "timestamp": m.timestamp.isoformat(),
                "result_count": m.result_count,
            }
            for m in sorted_queries
        ]


# ============ 数据验证相关 ============

class ValidationError(Exception):
    """数据验证错误"""
    pass


class DataValidator:
    """数据验证器"""

    @staticmethod
    def validate_character_id(character_id: str) -> bool:
        """验证角色ID格式"""
        if not character_id or not isinstance(character_id, str):
            raise ValidationError("character_id 必须是非空字符串")
        if len(character_id) > 100:
            raise ValidationError("character_id 长度不能超过100字符")
        return True

    @staticmethod
    def validate_character_name(name: str) -> bool:
        """验证角色名称"""
        if not name or not isinstance(name, str):
            raise ValidationError("name 必须是非空字符串")
        if len(name) > 200:
            raise ValidationError("name 长度不能超过200字符")
        return True

    @staticmethod
    def validate_arc_value(arc: float) -> bool:
        """验证成长曲线值"""
        if not isinstance(arc, (int, float)):
            raise ValidationError("arc 必须是数字")
        if not -100 <= arc <= 100:
            raise ValidationError("arc 值必须在 -100 到 100 之间")
        return True

    @staticmethod
    def validate_tension_score(score: float) -> bool:
        """验证张力得分"""
        if not isinstance(score, (int, float)):
            raise ValidationError("tension_score 必须是数字")
        if not 0 <= score <= 100:
            raise ValidationError("tension_score 值必须在 0 到 100 之间")
        return True

    @staticmethod
    def validate_sequence_number(seq: int) -> bool:
        """验证序号"""
        if not isinstance(seq, int) or seq < 1:
            raise ValidationError("sequence_number 必须是正整数")
        return True

    @staticmethod
    def validate_story_id(story_id: str) -> bool:
        """验证故事ID"""
        if not story_id or not isinstance(story_id, str):
            raise ValidationError("story_id 必须是非空字符串")
        return True


# ============ 批量操作优化 ============

@dataclass
class BatchOperationResult:
    """批量操作结果"""
    total: int = 0
    successful: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0


class BatchProcessor:
    """批量处理器 - 使用UNWIND优化批量操作"""

    @staticmethod
    async def batch_create_characters(
        session,
        characters: List[Dict[str, Any]]
    ) -> BatchOperationResult:
        """
        批量创建角色（使用UNWIND）

        性能优化：使用单个UNWIND语句代替多个CREATE语句
        """
        start_time = time.time()
        result = BatchOperationResult(total=len(characters))

        if not characters:
            return result

        query = """
        UNWIND $characters AS character
        MERGE (c:Character {character_id: character.character_id})
        SET c += character,
            c.updated_at = datetime()
        """

        try:
            await session.run(query, characters=characters)
            result.successful = len(characters)
        except Exception as e:
            result.failed = len(characters)
            result.errors.append(str(e))
            logger.error(f"批量创建角色失败: {e}")

        result.execution_time = time.time() - start_time
        return result

    @staticmethod
    async def batch_create_plot_nodes(
        session,
        plots: List[Dict[str, Any]]
    ) -> BatchOperationResult:
        """批量创建情节节点"""
        start_time = time.time()
        result = BatchOperationResult(total=len(plots))

        if not plots:
            return result

        query = """
        UNWIND $plots AS plot
        MERGE (p:PlotNode {plot_id: plot.plot_id})
        SET p += plot,
            p.updated_at = datetime()
        """

        try:
            await session.run(query, plots=plots)
            result.successful = len(plots)
        except Exception as e:
            result.failed = len(plots)
            result.errors.append(str(e))
            logger.error(f"批量创建情节节点失败: {e}")

        result.execution_time = time.time() - start_time
        return result

    @staticmethod
    async def batch_create_relationships(
        session,
        relationships: List[Dict[str, Any]]
    ) -> BatchOperationResult:
        """
        批量创建关系

        relationships: [
            {"type": "SOCIAL_BOND", "source": "char1", "target": "char2", "properties": {...}}
        ]
        """
        start_time = time.time()
        result = BatchOperationResult(total=len(relationships))

        if not relationships:
            return result

        # 按关系类型分组以提高性能
        grouped = defaultdict(list)
        for rel in relationships:
            grouped[rel["type"]].append(rel)

        for rel_type, rels in grouped.items():
            query = f"""
            UNWIND $rels AS rel
            MATCH (source), (target)
            WHERE source.character_id = rel.source AND target.character_id = rel.target
            MERGE (source)-[r:{rel_type}]->(target)
            SET r += rel.properties
            """

            try:
                await session.run(query, rels=rels)
                result.successful += len(rels)
            except Exception as e:
                result.failed += len(rels)
                result.errors.append(f"{rel_type}: {str(e)}")
                logger.error(f"批量创建关系 {rel_type} 失败: {e}")

        result.execution_time = time.time() - start_time
        return result


# ============ GraphRAG 集成支持 ============

class GraphRAGQuery:
    """GraphRAG查询构造器"""

    @staticmethod
    def get_context_for_entity(
        entity_id: str,
        entity_type: str,
        depth: int = 2,
        limit: int = 20
    ) -> str:
        """
        获取实体的上下文用于RAG

        Returns:
            Cypher查询字符串
        """
        if entity_type == "Character":
            return f"""
            MATCH (c:Character {{character_id: $entity_id}})-[r*1..{depth}]-(related)
            RETURN c, r, related
            LIMIT {limit}
            """
        elif entity_type == "PlotNode":
            return f"""
            MATCH (p:PlotNode {{plot_id: $entity_id}})-[r*1..{depth}]-(related)
            RETURN p, r, related
            LIMIT {limit}
            """
        else:
            return f"""
            MATCH (n)-[r*1..{depth}]-(related)
            WHERE n.id = $entity_id
            RETURN n, r, related
            LIMIT {limit}
            """

    @staticmethod
    def get_relevant_context(
        story_id: str,
        keywords: List[str],
        limit: int = 10
    ) -> str:
        """
        根据关键词获取相关上下文

        用于RAG检索增强生成
        """
        keyword_match = " AND ".join([f"toLower(n.description) CONTAINS toLower('{kw}')" for kw in keywords])

        return f"""
        MATCH (n)
        WHERE n.story_id = $story_id
          AND ({keyword_match})
        RETURN n
        LIMIT {limit}
        """


# ============ 备份恢复功能 ============

class GraphBackupManager:
    """图数据库备份管理器"""

    def __init__(self, graph_manager):
        self.graph_manager = graph_manager
        self.backup_dir = "graph_backups"

    async def create_backup(
        self,
        story_id: str,
        backup_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建故事备份

        备份内容：
        1. 所有节点数据
        2. 所有关系数据
        3. 元数据（时间戳、版本等）
        """
        if not backup_name:
            backup_name = f"backup_{story_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        start_time = time.time()

        # 导出所有节点
        nodes_query = """
        MATCH (n)
        WHERE n.story_id = $story_id
        RETURN n
        """

        # 导出所有关系
        rels_query = """
        MATCH (a)-[r]-(b)
        WHERE a.story_id = $story_id OR b.story_id = $story_id
        RETURN a, r, b
        """

        backup_data = {
            "backup_name": backup_name,
            "story_id": story_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nodes": [],
            "relationships": [],
        }

        try:
            async with self.graph_manager._get_session() as session:
                # 导出节点
                result = await session.run(nodes_query, story_id=story_id)
                async for record in result:
                    node = record["n"]
                    backup_data["nodes"].append({
                        "id": node.element_id,
                        "labels": list(node.labels),
                        "properties": dict(node)
                    })

                # 导出关系
                result = await session.run(rels_query, story_id=story_id)
                async for record in result:
                    rel = record["r"]
                    backup_data["relationships"].append({
                        "id": rel.element_id,
                        "type": rel.type,
                        "properties": dict(rel),
                        "source": record["a"].element_id,
                        "target": record["b"].element_id,
                    })

            execution_time = time.time() - start_time

            return {
                "success": True,
                "backup_name": backup_name,
                "nodes_count": len(backup_data["nodes"]),
                "relationships_count": len(backup_data["relationships"]),
                "execution_time": execution_time,
                "data": backup_data,
            }

        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }

    async def restore_backup(
        self,
        backup_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从备份数据恢复

        注意：这是破坏性操作，会覆盖现有数据
        """
        start_time = time.time()

        try:
            async with self.graph_manager._get_session() as session:
                # 删除现有数据
                await session.run(
                    "MATCH (n) WHERE n.story_id = $story_id DETACH DELETE n",
                    story_id=backup_data["story_id"]
                )

                # 恢复节点
                for node_data in backup_data["nodes"]:
                    labels = ":".join(node_data["labels"])
                    props = node_data["properties"]
                    prop_str = ", ".join([f"n.{k} = ${k}" for k in props.keys()])
                    query = f"CREATE (n:{labels} {{{prop_str}}})"
                    await session.run(query, **props)

                # 恢复关系
                for rel_data in backup_data["relationships"]:
                    query = f"""
                    MATCH (a), (b)
                    WHERE elementId(a) = $source AND elementId(b) = $target
                    CREATE (a)-[r:{rel_data['type']}]->(b)
                    SET r = $properties
                    """
                    await session.run(
                        query,
                        source=rel_data["source"],
                        target=rel_data["target"],
                        properties=rel_data["properties"]
                    )

            execution_time = time.time() - start_time

            return {
                "success": True,
                "nodes_restored": len(backup_data["nodes"]),
                "relationships_restored": len(backup_data["relationships"]),
                "execution_time": execution_time,
            }

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }


# ============ 增强版图数据库管理器 ============

class EnhancedGraphDBManager:
    """
    增强版图数据库管理器

    新增功能：
    1. 性能监控
    2. 数据验证
    3. 批量操作优化
    4. 时间戳和版本控制
    5. GraphRAG支持
    6. 备份恢复
    7. 慢查询日志
    8. 连接池健康检查
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "",
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        max_connection_lifetime: int = 3600,
        connection_acquisition_timeout: int = 60,
        max_transaction_retry_time: int = 30,
        enable_monitoring: bool = True,
        slow_query_threshold: float = 1.0,
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[AsyncDriver] = None

        # 连接池配置
        self.max_connection_pool_size = max_connection_pool_size
        self.max_connection_lifetime = max_connection_lifetime
        self.connection_acquisition_timeout = connection_acquisition_timeout
        self.max_transaction_retry_time = max_transaction_retry_time

        # 性能监控
        self.enable_monitoring = enable_monitoring
        self.performance_monitor = PerformanceMonitor(slow_query_threshold) if enable_monitoring else None

        # 数据验证器
        self.validator = DataValidator()

        # 批量处理器
        self.batch_processor = BatchProcessor()

        # 备份管理器
        self.backup_manager = None  # 在 initialize 中设置

        # 事务统计
        self._transaction_stats = {
            "total_transactions": 0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "retries": 0,
        }

        logger.info(f"EnhancedGraphDBManager 初始化: {uri}@{database}")

    async def initialize(self):
        """初始化连接池并创建Schema"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_pool_size=self.max_connection_pool_size,
                max_connection_lifetime=self.max_connection_lifetime,
                connection_acquisition_timeout=self.connection_acquisition_timeout,
                max_transaction_retry_time=self.max_transaction_retry_time,
            )

            await self.verify_connectivity()
            await self.create_enhanced_schema()

            # 初始化备份管理器
            self.backup_manager = GraphBackupManager(self)

            logger.info("EnhancedGraphDBManager 初始化完成")

        except Exception as e:
            logger.error(f"EnhancedGraphDBManager 初始化失败: {e}")
            raise

    async def close(self):
        """关闭连接池"""
        if self.driver:
            await self.driver.close()
            logger.info("EnhancedGraphDBManager 连接已关闭")

    @asynccontextmanager
    async def _get_session(self):
        """获取数据库会话"""
        if not self.driver:
            raise RuntimeError("Driver 未初始化，请先调用 initialize()")
        async with self.driver.session(database=self.database) as session:
            yield session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, TransientError, SessionExpired)),
    )
    async def verify_connectivity(self) -> bool:
        """验证数据库连接（带重试）"""
        try:
            async with self._get_session() as session:
                result = await session.run("RETURN 1 AS test")
                record = await result.single()
                if record and record["test"] == 1:
                    logger.info("Neo4j 连接验证成功")
                    return True
        except Exception as e:
            logger.error(f"Neo4j 连接验证失败: {e}")
            raise
        return False

    async def create_enhanced_schema(self):
        """
        创建增强版 Schema

        包含：
        1. 唯一性约束
        2. 属性索引
        3. 全文搜索索引
        4. 时间戳索引
        5. 版本控制支持
        """
        constraints_and_indexes = [
            # Character 节点
            "CREATE CONSTRAINT character_id_unique IF NOT EXISTS FOR (c:Character) REQUIRE c.character_id IS UNIQUE",
            "CREATE INDEX character_status_idx IF NOT EXISTS FOR (c:Character) WHERE c.status IS NOT NULL",
            "CREATE INDEX character_story_idx IF NOT EXISTS FOR (c:Character) WHERE c.story_id IS NOT NULL",
            "CREATE INDEX character_created_at_idx IF NOT EXISTS FOR (c:Character) WHERE c.created_at IS NOT NULL",
            "CREATE INDEX character_updated_at_idx IF NOT EXISTS FOR (c:Character) WHERE c.updated_at IS NOT NULL",
            "CREATE FULLTEXT INDEX character_fulltext IF NOT EXISTS FOR (c:Character) ON EACH [c.name, c.backstory]",

            # PlotNode 节点
            "CREATE CONSTRAINT plot_id_unique IF NOT EXISTS FOR (p:PlotNode) REQUIRE p.plot_id IS UNIQUE",
            "CREATE CONSTRAINT plot_story_sequence_unique IF NOT EXISTS FOR (p:PlotNode) REQUIRE (p.story_id, p.sequence_number) IS UNIQUE",
            "CREATE INDEX plot_story_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.story_id IS NOT NULL",
            "CREATE INDEX plot_sequence_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.sequence_number IS NOT NULL",
            "CREATE INDEX plot_tension_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.tension_score IS NOT NULL",
            "CREATE INDEX plot_created_at_idx IF NOT EXISTS FOR (p:PlotNode) WHERE p.created_at IS NOT NULL",
            "CREATE FULLTEXT INDEX plot_fulltext IF NOT EXISTS FOR (p:PlotNode) ON EACH [p.title, p.description]",

            # WorldRule 节点
            "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (w:WorldRule) REQUIRE w.rule_id IS UNIQUE",
            "CREATE INDEX rule_story_idx IF NOT EXISTS FOR (w:WorldRule) WHERE w.story_id IS NOT NULL",
            "CREATE INDEX rule_type_idx IF NOT EXISTS FOR (w:WorldRule) WHERE w.rule_type IS NOT NULL",
            "CREATE INDEX rule_created_at_idx IF NOT EXISTS FOR (w:WorldRule) WHERE w.created_at IS NOT NULL",
            "CREATE FULLTEXT INDEX rule_fulltext IF NOT EXISTS FOR (w:WorldRule) ON EACH [w.name, w.description]",

            # Location 节点
            "CREATE INDEX location_story_idx IF NOT EXISTS FOR (l:Location) WHERE l.story_id IS NOT NULL",
            "CREATE FULLTEXT INDEX location_fulltext IF NOT EXISTS FOR (l:Location) ON EACH [l.name, l.description]",

            # 关系索引
            "CREATE INDEX social_bond_trust_idx IF NOT EXISTS FOR ()-[r:SOCIAL_BOND]-() WHERE r.trust_level IS NOT NULL",
            "CREATE INDEX plot_influence_idx IF NOT EXISTS FOR ()-[r:INFLUENCES]-() WHERE r.strength IS NOT NULL",
        ]

        async with self._get_session() as session:
            for statement in constraints_and_indexes:
                try:
                    await session.run(statement)
                    logger.debug(f"Schema 创建成功: {statement[:50]}...")
                except ConstraintError as e:
                    logger.warning(f"约束已存在: {e}")
                except Exception as e:
                    logger.error(f"Schema 创建失败: {statement[:50]}... 错误: {e}")

        logger.info("增强版 Schema 创建完成")

    async def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None,
        fetch_all: bool = True
    ) -> Tuple[Any, float]:
        """
        执行Cypher查询（带性能监控）

        Returns:
            (result, execution_time)
        """
        if parameters is None:
            parameters = {}

        start_time = time.time()
        result_count = 0
        success = True
        error_message = None

        try:
            async with self._get_session() as session:
                result = await session.run(query, parameters)

                if fetch_all:
                    records = await result.data()
                    result_count = len(records)
                else:
                    records = result
                    result_count = await result.consume().__anext__()  # 获取统计信息

                execution_time = time.time() - start_time

                # 记录性能指标
                if self.performance_monitor:
                    await self.performance_monitor.record_query(
                        query=query,
                        parameters=parameters,
                        execution_time=execution_time,
                        result_count=result_count,
                        success=True
                    )

                return records, execution_time

        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)

            # 记录失败查询
            if self.performance_monitor:
                await self.performance_monitor.record_query(
                    query=query,
                    parameters=parameters,
                    execution_time=execution_time,
                    result_count=0,
                    success=False,
                    error_message=error_message
                )

            logger.error(f"查询执行失败: {query[:100]}... 错误: {e}")
            raise

    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        if not self.performance_monitor:
            return {"error": "性能监控未启用"}

        return self.performance_monitor.get_stats()

    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        if not self.performance_monitor:
            return []

        return self.performance_monitor.get_slow_queries(limit)

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态信息
        """
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_connected": False,
            "connection_pool_size": 0,
            "total_transactions": self._transaction_stats["total_transactions"],
        }

        try:
            async with self._get_session() as session:
                # 检查连接
                result = await session.run("RETURN 1 AS test")
                await result.single()
                health_status["database_connected"] = True

                # 获取连接池信息
                if hasattr(self.driver, '_pool'):
                    pool = self.driver._pool
                    health_status["connection_pool_size"] = getattr(pool, 'total_in_use', 0) + getattr(pool, 'total_idle', 0)

        except Exception as e:
            health_status["error"] = str(e)
            logger.error(f"健康检查失败: {e}")

        return health_status


# ============ 单例模式 ============

_instance: Optional[EnhancedGraphDBManager] = None
_lock = asyncio.Lock()


async def get_enhanced_graph_manager(
    uri: str = "bolt://localhost:7687",
    username: str = "neo4j",
    password: str = "",
    database: str = "neo4j",
    **kwargs
) -> EnhancedGraphDBManager:
    """
    获取增强版图数据库管理器单例

    Args:
        uri: Neo4j 连接 URI
        username: 数据库用户名
        password: 数据库密码
        database: 数据库名称
        **kwargs: 其他配置参数

    Returns:
        EnhancedGraphDBManager 实例
    """
    global _instance

    async with _lock:
        if _instance is None:
            _instance = EnhancedGraphDBManager(
                uri=uri,
                username=username,
                password=password,
                database=database,
                **kwargs
            )
            await _instance.initialize()

        return _instance


async def close_enhanced_graph_manager():
    """关闭增强版图数据库管理器"""
    global _instance

    async with _lock:
        if _instance is not None:
            await _instance.close()
            _instance = None

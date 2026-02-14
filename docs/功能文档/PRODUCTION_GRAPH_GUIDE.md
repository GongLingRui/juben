# 生产级剧本创作知识图谱系统完整指南

## 目录

1. [系统概述](#系统概述)
2. [核心特性](#核心特性)
3. [架构设计](#架构设计)
4. [快速开始](#快速开始)
5. [API参考](#api参考)
6. [最佳实践](#最佳实践)
7. [性能优化](#性能优化)
8. [故障排查](#故障排查)

---

## 系统概述

本系统是一个基于 Neo4j 的生产级剧本创作知识图谱平台，集成了 GraphRAG（图谱检索增强生成）技术，为剧本创作提供智能化的知识管理、逻辑一致性检测和内容生成能力。

### 技术栈

```
┌─────────────────────────────────────────────────────────────┐
│                     应用层 (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ 图谱可视化API  │  │ GraphRAG API │  │ 监控管理API     │  │
│  └───────────────┘  └──────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐                  │
│  │ GraphDBManager  │  │ LogicConsistency │                  │
│  │ (增强版)         │  │ Agent            │                  │
│  └─────────────────┘  └──────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│                   Neo4j 图数据库 (因果集群)                    │
│              - 核心服务器 (3+节点)                            │
│              - 只读副本 (可扩展)                              │
├─────────────────────────────────────────────────────────────┤
│              基础设施 (Kubernetes/Docker)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心特性

### 1. 增强版图数据库管理器 (`utils/graph_enhanced.py`)

#### 1.1 性能监控

```python
from utils.graph_enhanced import get_enhanced_graph_manager

# 初始化（启用性能监控）
manager = await get_enhanced_graph_manager(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your_password",
    enable_monitoring=True,
    slow_query_threshold=1.0  # 1秒以上的查询被视为慢查询
)

# 获取性能统计
stats = await manager.get_performance_stats()
print(f"总查询数: {stats['total_queries']}")
print(f"成功率: {stats['success_rate']:.2f}%")
print(f"平均查询时间: {stats['avg_query_time']:.3f}s")
print(f"慢查询数: {stats['slow_queries']}")

# 获取慢查询列表
slow_queries = await manager.get_slow_queries(limit=10)
for sq in slow_queries:
    print(f"查询: {sq['query']}")
    print(f"执行时间: {sq['execution_time']:.3f}s")
```

#### 1.2 数据验证

```python
from utils.graph_enhanced import DataValidator

validator = DataValidator()

# 验证角色数据
validator.validate_character_id("char_001")
validator.validate_character_name("张三")
validator.validate_arc_value(50.0)  # -100 到 100

# 验证情节数据
validator.validate_sequence_number(1)
validator.validate_tension_score(75.0)  # 0 到 100
```

#### 1.3 批量操作优化

```python
# 批量创建角色（使用 UNWIND 优化）
characters = [
    {"character_id": "char_001", "name": "张三", "story_id": "story_001", ...},
    {"character_id": "char_002", "name": "李四", "story_id": "story_001", ...},
    # ... 更多角色
]

async with manager._get_session() as session:
    result = await manager.batch_processor.batch_create_characters(
        session, characters
    )
    print(f"成功: {result.successful}, 失败: {result.failed}")
    print(f"执行时间: {result.execution_time:.3f}s")
```

#### 1.4 备份恢复

```python
# 创建备份
backup_result = await manager.backup_manager.create_backup(
    story_id="story_001",
    backup_name="backup_before_major_changes"
)

# 恢复备份
restore_result = await manager.backup_manager.restore_backup(
    backup_data=backup_result["data"]
)
```

### 2. GraphRAG 智能问答 (`agents/graph_rag_agent.py`)

#### 2.1 智能问答

```python
from agents.graph_rag_agent import GraphRAGAgent

agent = GraphRAGAgent()

# 问答
async for event in agent.process_request({
    "operation": "ask_question",
    "story_id": "story_001",
    "question": "张三和李四是什么关系？"
}):
    if event["event_type"] == "tool_complete":
        result = event["data"]["result"]
        print(f"答案: {result['answer']}")
        print(f"置信度: {result['confidence']}")
```

#### 2.2 实体分析

```python
# 分析实体
async for event in agent.process_request({
    "operation": "analyze_entity",
    "story_id": "story_001",
    "entity_id": "char_001",
    "entity_type": "Character",
    "depth": 2
}):
    if event["event_type"] == "tool_complete":
        result = event["data"]["result"]
        print(f"分析: {result['analysis']}")
```

#### 2.3 路径查找

```python
# 查找两个角色之间的关系路径
async for event in agent.process_request({
    "operation": "find_paths",
    "story_id": "story_001",
    "start_entity": "char_001",
    "end_entity": "char_003",
    "max_depth": 5
}):
    if event["event_type"] == "tool_complete":
        result = event["data"]["result"]
        for path in result["paths"]:
            print(" -> ".join(path["path"]))
```

### 3. 逻辑一致性检测

已有的 `LogicConsistencyAgent` 提供以下检测规则：

| 规则 ID | 名称 | 描述 | 严重程度 |
|---------|------|------|----------|
| `spatiotemporal` | 时空冲突检测 | 同一时间点，同一角色不能出现在两个地点 | CRITICAL |
| `character_status` | 角色状态检测 | 已死亡角色不能有后续行动 | CRITICAL |
| `motivation` | 动机缺失检测 | 重大事件需要有动机支持 | HIGH |
| `relationship` | 关系一致性检测 | 社交关系变化需要合理过渡 | MEDIUM |
| `knowledge` | 知识连续性检测 | 角色能力/记忆保持一致 | MEDIUM |
| `world_rule` | 世界观冲突检测 | 情节不能违反世界观规则 | HIGH |
| `plot_coherence` | 情节连贯性检测 | 相邻情节应有因果关系 | LOW |

---

## 架构设计

### Schema 设计

#### 节点类型

```cypher
// 角色节点
(:Character {
  character_id: string (UNIQUE),
  name: string,
  story_id: string,
  status: 'alive' | 'deceased' | 'missing' | 'unknown',
  location: string,
  persona: [string],  // 性格标签
  arc: float,         // 成长曲线 (-100 到 100)
  backstory: string,
  motivations: [string],
  flaws: [string],
  strengths: [string],
  created_at: datetime,
  updated_at: datetime
})

// 情节节点
(:PlotNode {
  plot_id: string (UNIQUE),
  story_id: string,
  title: string,
  description: string,
  sequence_number: int,
  tension_score: float (0-100),
  timestamp: datetime,
  chapter: int,
  characters_involved: [string],
  locations: [string],
  conflicts: [string],
  themes: [string],
  importance: float (0-100),
  created_at: datetime,
  updated_at: datetime
})

// 世界观规则
(:WorldRule {
  rule_id: string (UNIQUE),
  story_id: string,
  name: string,
  description: string,
  rule_type: string,
  severity: 'strict' | 'moderate' | 'flexible',
  consequences: [string],
  exceptions: [string],
  created_at: datetime,
  updated_at: datetime
})
```

#### 关系类型

```cypher
// 社交关系
(:Character)-[:SOCIAL_BOND {trust_level: float, bond_type: string, hidden_relation: bool}]->(:Character)

// 情节关系
(:PlotNode)-[:INFLUENCES {strength: float}]->(:PlotNode)
(:PlotNode)-[:NEXT]->(:PlotNode)
(:Character)-[:INVOLVED_IN]->(:PlotNode)
(:Character)-[:DRIVEN_BY]->(:Motivation)

// 世界关系
(:PlotNode)-[:VIOLATES]->(:WorldRule)
(:Character)-[:LOCATED_IN]->(:Location)
```

#### 索引策略

```cypher
// 唯一性约束
CREATE CONSTRAINT character_id_unique FOR (c:Character) REQUIRE c.character_id IS UNIQUE
CREATE CONSTRAINT plot_id_unique FOR (p:PlotNode) REQUIRE p.plot_id IS UNIQUE

// 属性索引
CREATE INDEX character_status_idx FOR (c:Character) WHERE c.status IS NOT NULL
CREATE INDEX plot_sequence_idx FOR (p:PlotNode) WHERE p.sequence_number IS NOT NULL
CREATE INDEX plot_tension_idx FOR (p:PlotNode) WHERE p.tension_score IS NOT NULL

// 全文搜索索引
CREATE FULLTEXT INDEX character_fulltext FOR (c:Character) ON EACH [c.name, c.backstory]
CREATE FULLTEXT INDEX plot_fulltext FOR (p:PlotNode) ON EACH [p.title, p.description]

// 时间戳索引
CREATE INDEX character_created_at_idx FOR (c:Character) WHERE c.created_at IS NOT NULL
CREATE INDEX character_updated_at_idx FOR (c:Character) WHERE c.updated_at IS NOT NULL
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install neo4j>=5.14.0 tenacity
```

### 2. 配置 Neo4j

```python
# config/graph_config.py
from pydantic_settings import BaseSettings

class GraphDBSettings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50
    NEO4J_ENABLE_MONITORING: bool = True
    NEO4J_SLOW_QUERY_THRESHOLD: float = 1.0

    class Config:
        env_file = ".env"
```

### 3. 初始化图数据库

```python
from utils.graph_enhanced import get_enhanced_graph_manager

async def init_graph():
    manager = await get_enhanced_graph_manager()
    print("图数据库初始化完成！")
    return manager

# 运行
import asyncio
asyncio.run(init_graph())
```

### 4. 创建第一个故事

```python
from utils.graph_manager import GraphDBManager, CharacterData, PlotNodeData

async def create_first_story():
    manager = GraphDBManager()
    await manager.initialize()

    # 创建角色
    character = CharacterData(
        character_id="char_001",
        name="张三",
        story_id="story_001",
        status="alive",
        persona=["勇敢", "正义"],
        arc=0.0
    )

    await manager.merge_story_element(
        element_type=NodeType.CHARACTER,
        element_data=character,
        version=1
    )

    # 创建情节
    plot = PlotNodeData(
        plot_id="plot_001",
        story_id="story_001",
        title="初入江湖",
        description="张三离开家乡，踏上复仇之路",
        sequence_number=1,
        tension_score=30.0
    )

    await manager.merge_story_element(
        element_type=NodeType.PLOT_NODE,
        element_data=plot,
        version=1
    )

    print("故事创建完成！")

asyncio.run(create_first_story())
```

---

## API 参考

### 增强图谱管理 API (`/graph-enhanced`)

#### 健康检查

```bash
GET /graph-enhanced/health
```

响应：
```json
{
  "timestamp": "2025-02-08T10:30:00Z",
  "database_connected": true,
  "connection_pool_size": 5,
  "total_transactions": 150
}
```

#### 性能统计

```bash
GET /graph-enhanced/performance/stats
```

响应：
```json
{
  "total_queries": 1000,
  "successful_queries": 985,
  "failed_queries": 15,
  "slow_queries": 5,
  "avg_query_time": 0.125,
  "max_query_time": 2.345,
  "min_query_time": 0.005,
  "success_rate": 98.5
}
```

#### 批量创建角色

```bash
POST /graph-enhanced/batch/characters
Content-Type: application/json

{
  "characters": [
    {
      "character_id": "char_001",
      "name": "张三",
      "story_id": "story_001",
      "status": "alive",
      "persona": ["勇敢", "正义"],
      "arc": 0.0
    }
  ],
  "validate": true
}
```

#### 创建备份

```bash
POST /graph-enhanced/backup/create
Content-Type: application/json

{
  "story_id": "story_001",
  "backup_name": "backup_before_major_changes"
}
```

### GraphRAG API (`/graph-rag`)

#### 智能问答

```bash
POST /graph-rag/ask
Content-Type: application/json

{
  "story_id": "story_001",
  "question": "张三和李四是什么关系？"
}
```

响应：
```json
{
  "question": "张三和李四是什么关系？",
  "answer": "根据图谱信息，张三和李四是师徒关系...",
  "confidence": 0.9,
  "context_summary": "## 相关实体\n- Character: 张三\n- Character: 李四\n...",
  "sources": ["graph_story_001"]
}
```

#### 实体分析

```bash
POST /graph-rag/analyze-entity
Content-Type: application/json

{
  "story_id": "story_001",
  "entity_id": "char_001",
  "entity_type": "Character",
  "depth": 2
}
```

#### 路径查找

```bash
POST /graph-rag/find-paths
Content-Type: application/json

{
  "story_id": "story_001",
  "start_entity": "char_001",
  "end_entity": "char_003",
  "max_depth": 5
}
```

---

## 最佳实践

### 1. Schema 设计原则

#### 查询驱动设计

在设计 Schema 之前，先明确查询需求：

```python
# ✅ 好的设计 - 优化常见查询
# 查询: 获取角色的所有情节
(:Character)-[:INVOLVED_IN]->(:PlotNode)

# ❌ 坏的设计 - 需要多次遍历
(:Character)-[:RELATION {type: "involved"}]->(:Intermediate)
(:Intermediate)-[:CONNECTED_TO]->(:PlotNode)
```

#### 避免超节点

```python
# ❌ 避免 - 所有情节都连接到一个"故事"节点
(:Story)-[:CONTAINS]->(:PlotNode)  # 可能导致超节点

# ✅ 推荐 - 使用 story_id 属性
(:PlotNode {story_id: "story_001"})
```

### 2. 查询优化

#### 使用参数化查询

```python
# ✅ 使用参数 - 可重用执行计划
query = "MATCH (c:Character {story_id: $story_id}) RETURN c"
await session.run(query, story_id="story_001")

# ❌ 字符串拼接 - 无法重用执行计划
query = f"MATCH (c:Character {{story_id: '{story_id}'}}) RETURN c"
await session.run(query)
```

#### 使用 EXPLAIN 和 PROFILE

```python
# 分析查询执行计划
result = await session.run(
    "EXPLAIN MATCH (c:Character)-[:INVOLVED_IN]->(p:PlotNode) RETURN c, p"
)
print(await result.data())

# 获取详细性能信息
result = await session.run(
    "PROFILE MATCH (c:Character)-[:INVOLVED_IN]->(p:PlotNode) RETURN c, p"
)
print(await result.data())
```

#### 限制返回结果

```python
# ✅ 使用 LIMIT
query = """
MATCH (c:Character)-[:INVOLVED_IN]->(p:PlotNode)
RETURN c, count(p) AS plot_count
ORDER BY plot_count DESC
LIMIT 10
"""

# ✅ 使用分页
query = """
MATCH (c:Character)
RETURN c
SKIP $skip LIMIT $limit
"""
```

### 3. 事务管理

#### 使用显式事务

```python
async with self._get_session() as session:
    async with session.begin_transaction() as tx:
        try:
            # 执行多个操作
            await tx.run(create_query, **params)
            await tx.run(update_query, **params)

            # 提交事务
            await tx.commit()
        except Exception as e:
            # 回滚事务
            await tx.rollback()
            raise
```

#### 避免大事务

```python
# ❌ 避免 - 一次插入太多数据
for i in range(10000):
    await session.run(create_query, data=data[i])

# ✅ 推荐 - 批量操作
for batch in batches(data, batch_size=100):
    await session.run(batch_query, batch=batch)
```

### 4. 连接池管理

#### 配置合理的连接池大小

```python
manager = EnhancedGraphDBManager(
    max_connection_pool_size=50,  # 根据并发量调整
    max_connection_lifetime=3600,   # 1小时
    connection_acquisition_timeout=60
)
```

#### 使用连接池监控

```python
# 获取连接池状态
health = await manager.health_check()
print(f"连接池大小: {health['connection_pool_size']}")
```

---

## 性能优化

### 1. 索引优化

#### 为常用查询创建索引

```python
# 查询: 按状态查询角色
# CREATE INDEX character_status_idx FOR (c:Character) WHERE c.status IS NOT NULL

# 查询: 按序列号查询情节
# CREATE INDEX plot_sequence_idx FOR (p:PlotNode) WHERE p.sequence_number IS NOT NULL

# 查询: 全文搜索
# CREATE FULLTEXT INDEX character_fulltext FOR (c:Character) ON EACH [c.name, c.backstory]
```

#### 监控索引使用情况

```bash
# 查看索引使用统计
CALL db.indexes() YIELD name, state, populationPercent, uniqueness
RETURN name, state, populationPercent, uniqueness
```

### 2. 查询优化

#### 使用 PROFILE 识别慢查询

```python
records, exec_time = await manager.execute_query("""
PROFILE MATCH (c:Character)-[r:INVOLVED_IN]->(p:PlotNode)
WHERE c.story_id = $story_id
RETURN c, p
""", {"story_id": "story_001"})
```

#### 优化深度遍历

```python
# ❌ 避免 - 可能产生大量结果
MATCH path = (c:Character)-[*5]-(related)
RETURN path

# ✅ 推荐 - 限制路径类型
MATCH path = (c:Character)-[:INVOLVED_IN|SOCIAL_BOND*1..3]-(related)
RETURN path
```

### 3. 批量操作优化

#### 使用 UNWIND 代替循环

```python
# ❌ 慢 - 执行 N 次查询
for character in characters:
    await session.run("CREATE (c:Character $props)", props=character)

# ✅ 快 - 执行 1 次查询
await session.run("""
UNWIND $characters AS character
CREATE (c:Character $props)
""", characters=characters)
```

---

## 故障排查

### 问题 1: 连接超时

**症状**: `ServiceUnavailable: Unable to acquire connection from pool`

**解决方案**:
1. 增加连接池大小
2. 减少连接获取超时时间
3. 检查是否有连接泄漏

```python
manager = EnhancedGraphDBManager(
    max_connection_pool_size=100,  # 增加
    connection_acquisition_timeout=120  # 增加
)
```

### 问题 2: 查询慢

**症状**: 查询执行时间超过 10 秒

**解决方案**:
1. 使用 PROFILE 分析查询
2. 添加缺失的索引
3. 重构查询逻辑
4. 使用 LIMIT 限制结果

```python
# 分析查询
records, exec_time = await manager.execute_query("""
PROFILE MATCH (c:Character)-[:INVOLVED_IN]->(p:PlotNode)
WHERE c.story_id = $story_id
RETURN c, p
LIMIT 100
""", {"story_id": "story_id"})
```

### 问题 3: 内存不足

**症状**: `OutOfMemoryError` 或 `Java heap space`

**解决方案**:
1. 减少 `result_count`
2. 使用分页
3. 增加 Neo4j 堆内存

```python
# 使用 LIMIT
records = await manager.execute_query("""
MATCH (n)
RETURN n
LIMIT 10000
""")
```

---

## 参考资源

### 官方文档
- [Neo4j 2025 操作手册](https://neo4j.ac.cn/docs/operations-manual/2025.05/introduction)
- [数据建模最佳实践](https://support.neo4j.com/s/article/360024789554-Data-Modeling-Best-Practices)
- [Neo4j 性能调优指南](https://medium.com/@satanialish/the-production-ready-neo4j-guide-performance-tuning-and-best-practices-15b78a5fe229)

### 社区资源
- [GraphRAG 最佳实践](https://www.51cto.com/aigc/7892.html)
- [Neo4j + LangChain 教程](https://adg.csdn.net/6970ab1e437a6b40336b21b2.html)
- [高可用集群架构](https://blog.csdn.net/sjdgehi/article/details/145980246)

### 项目文档
- [图数据库使用指南](./GRAPH_DATABASE_GUIDE.md)
- [逻辑一致性检测指南](./LOGIC_CONSISTENCY_AGENT.md)
- [Agent 开发指南](./AGENT_DEVELOPMENT.md)

---

## 更新日志

### v2.0.0 (2025-02-08)
- ✨ 新增增强版图数据库管理器
- ✨ 新增 GraphRAG 智能问答功能
- ✨ 新增性能监控和慢查询日志
- ✨ 新增数据验证机制
- ✨ 新增批量操作优化
- ✨ 新增备份恢复功能
- 🐛 修复连接池管理问题
- 📚 完善文档和示例

### v1.0.0 (2025-02-07)
- 🎉 初始版本发布
- ✨ 基础图数据库管理器
- ✨ 逻辑一致性检测 Agent
- ✨ 图谱可视化 API

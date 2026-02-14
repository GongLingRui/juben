# 剧本创作图谱存储引擎使用指南

## 📖 概述

生产级剧本创作图谱存储引擎基于 Neo4j 图数据库，专为剧本和小说创作设计。通过图结构管理角色、情节、世界观规则及其复杂的相互关系。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install neo4j>=5.14.0
```

### 2. 启动 Neo4j 数据库

使用 Docker 快速启动：

```bash
docker run -d \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    -e NEO4J_PLUGINS=["apoc"] \
    neo4j:5.14.0
```

### 3. 配置连接

在 `.env` 文件中配置：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

### 4. 基础使用

```python
from utils.graph_manager import (
    get_graph_manager,
    CharacterData,
    NodeType,
)

# 初始化
graph_manager = await get_graph_manager()

# 创建角色
character = CharacterData(
    character_id="char_001",
    name="林萧",
    story_id="story_001",
    persona=["勇敢", "正义"],
    arc=30.0,
)

await graph_manager.merge_story_element(
    element_type=NodeType.CHARACTER,
    element_data=character,
)
```

## 📊 数据模型

### 节点类型

#### 1. Character（角色节点）

| 属性 | 类型 | 说明 |
|------|------|------|
| character_id | str | 唯一标识 |
| name | str | 名称 |
| story_id | str | 所属故事 |
| status | CharacterStatus | 状态（alive/deceased/missing/unknown） |
| location | str | 当前位置 |
| persona | List[str] | 性格标签 |
| arc | float | 成长曲线值（-100到100） |
| backstory | str | 背景故事 |
| motivations | List[str] | 动机列表 |
| flaws | List[str] | 缺点列表 |
| strengths | List[str] | 优点列表 |
| first_appearance | int | 首次出现章节 |

#### 2. PlotNode（情节节点）

| 属性 | 类型 | 说明 |
|------|------|------|
| plot_id | str | 唯一标识 |
| story_id | str | 所属故事 |
| title | str | 标题 |
| description | str | 描述 |
| sequence_number | int | 序列号 |
| tension_score | float | 张力得分（0-100） |
| timestamp | datetime | 时间戳 |
| chapter | int | 所属章节 |
| characters_involved | List[str] | 涉及角色 |
| locations | List[str] | 地点列表 |
| conflicts | List[str] | 冲突列表 |
| themes | List[str] | 主题列表 |
| importance | float | 重要性得分（0-100） |

#### 3. WorldRule（世界观规则）

| 属性 | 类型 | 说明 |
|------|------|------|
| rule_id | str | 唯一标识 |
| story_id | str | 所属故事 |
| name | str | 规则名称 |
| description | str | 规则描述 |
| rule_type | str | 规则类型（magic/physics/social） |
| severity | str | 严格程度（strict/moderate/flexible） |
| consequences | List[str] | 违反后果 |
| exceptions | List[str] | 例外情况 |

### 关系类型

#### 1. SOCIAL_BOND（社交关系）

| 属性 | 类型 | 说明 |
|------|------|------|
| trust_level | int | 信任等级（-100到100） |
| bond_type | str | 关系类型（friend/enemy/family/romantic） |
| hidden_relation | str | 隐藏关系（剧透信息） |

#### 2. INFLUENCES（影响关系）

| 属性 | 类型 | 说明 |
|------|------|------|
| impact_score | float | 影响程度（0-100） |
| influence_type | str | 影响类型（direct/indirect/catalytic） |
| description | str | 影响描述 |

## 🔧 核心功能

### 1. 原子性操作

使用 `merge_story_element()` 确保实体唯一性：

```python
result = await graph_manager.merge_story_element(
    element_type=NodeType.CHARACTER,
    element_data=character,
    version=1,
)
# 返回: {"success": True, "element_id": "...", "created": True/False, ...}
```

### 2. 创建社交关系

```python
await graph_manager.create_social_bond(
    character_id_1="char_001",
    character_id_2="char_002",
    trust_level=85,
    bond_type="family",
    hidden_relation="师徒关系下的秘密",
)
```

### 3. 创建影响关系

```python
await graph_manager.create_influence(
    from_element_id="plot_001",
    to_element_id="plot_002",
    impact_score=80,
    influence_type="direct",
    description="第一个情节直接影响第二个情节",
)
```

### 4. 获取角色网络

```python
network = await graph_manager.get_character_network(
    character_id="char_001",
    depth=2,
    include_hidden=True,
)
# 返回社交网络和影响网络的完整信息
```

## 🌐 API 接口

### RESTful API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/graph/nodes/character` | 创建/更新角色 |
| POST | `/graph/nodes/plot` | 创建/更新情节 |
| POST | `/graph/nodes/rule` | 创建/更新世界观规则 |
| POST | `/graph/relationships/social` | 创建社交关系 |
| POST | `/graph/relationships/influence` | 创建影响关系 |
| GET | `/graph/nodes/character/{id}` | 获取角色详情 |
| POST | `/graph/network/character` | 获取角色网络 |
| GET | `/graph/nodes/story/{id}/plots` | 获取故事所有情节 |
| GET | `/graph/nodes/story/{id}/rules` | 获取世界观规则 |
| GET | `/graph/search/characters` | 搜索角色 |
| GET | `/graph/statistics/story/{id}` | 获取故事统计 |
| GET | `/graph/health` | 健康检查 |

### API 使用示例

```bash
# 创建角色
curl -X POST "http://localhost:8000/graph/nodes/character" \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_001",
    "name": "林萧",
    "story_id": "story_001",
    "persona": ["勇敢", "正义"],
    "arc": 30.0
  }'

# 获取角色网络
curl -X POST "http://localhost:8000/graph/network/character" \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_001",
    "depth": 2,
    "include_hidden": true
  }'
```

## 📈 高级功能

### 1. 批量操作

```python
# 批量创建角色
for i in range(100):
    character = CharacterData(
        character_id=f"char_{i:03d}",
        name=f"角色{i}",
        story_id="story_001",
        # ... 其他属性
    )
    await graph_manager.merge_story_element(
        element_type=NodeType.CHARACTER,
        element_data=character,
    )
```

### 2. 复杂查询

```python
# 按张力排序获取情节
plots = await graph_manager.get_plot_by_story(
    story_id="story_001",
    order_by="tension_score",
)

# 搜索高成长值角色
characters = await graph_manager.search_characters(
    story_id="story_001",
    min_arc=50,
    limit=10,
)
```

### 3. 统计分析

```python
stats = await graph_manager.get_story_statistics("story_001")
# 返回角色数、情节数、关系数、平均张力等统计信息
```

## 🔍 Cypher 查询示例

### 查找角色的所有社交关系

```cypher
MATCH (c:Character {character_id: "char_001"})-[r:SOCIAL_BOND]-(connected)
RETURN c, r, connected
```

### 查找高张力情节路径

```cypher
MATCH path = (p1:PlotNode)-[:INFLUENCES*]->(p2:PlotNode)
WHERE p1.story_id = "story_001"
  AND ALL(p IN nodes(path) WHERE p.tension_score > 70)
RETURN path
ORDER BY length(path) DESC
LIMIT 5
```

### 查找角色成长轨迹

```cypher
MATCH (c:Character {character_id: "char_001"})
MATCH (c)-[:INVOLVED_IN]->(p:PlotNode)
RETURN p.chapter, p.title, p.importance
ORDER BY p.chapter ASC
```

### 查找违反世界观的情节

```cypher
MATCH (p:PlotNode)-[:VIOLATES]->(r:WorldRule)
RETURN p.title, r.name, r.consequences
```

## ⚡ 性能优化

### 1. 连接池配置

```python
graph_manager = GraphDBManager(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your_password",
    max_connection_pool_size=50,      # 增大连接池
    max_connection_lifetime=3600,      # 1小时
    connection_acquisition_timeout=60, # 60秒超时
)
```

### 2. 使用索引

系统自动创建以下索引：

- `character_id`（唯一）
- `(story_id, name)` 组合唯一
- `status`, `location`, `arc` 属性索引
- `plot_id`（唯一）
- `(story_id, sequence_number)` 组合唯一
- `tension_score`, `importance`, `chapter` 属性索引
- 全文搜索索引

### 3. 批处理建议

```python
# 使用异步并发
import asyncio

async def batch_create(characters):
    tasks = [
        graph_manager.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=char,
        )
        for char in characters
    ]
    results = await asyncio.gather(*tasks)
    return results
```

## 🛡️ 事务管理

### 自动重试

系统使用 tenacity 实现自动重试：

- 最多重试 3 次
- 指数退避等待（1-10秒）
- 针对 `ServiceUnavailable`, `TransientError`, `SessionExpired`

### 事务统计

```python
stats = graph_manager.get_transaction_stats()
# {
#     "total_transactions": 1000,
#     "successful_transactions": 998,
#     "failed_transactions": 2,
#     "retries": 5
# }
```

## 🔒 数据一致性

### MERGE 操作

`merge_story_element()` 使用 Cypher 的 MERGE 语句：

- **ON CREATE**: 节点不存在时创建
- **ON MATCH**: 节点存在时更新指定字段
- **version**: 自动版本号追踪
- **timestamp**: 记录创建和更新时间

### 版本控制

```python
result = await graph_manager.merge_story_element(
    element_type=NodeType.CHARACTER,
    element_data=character,
    version=2,  # 更新到版本2
)
# result["version"] == 2
```

## 📚 最佳实践

1. **使用原子性操作**: 始终使用 `merge_story_element()` 而不是直接执行 Cypher
2. **合理设置版本号**: 每次重要更新时递增版本号
3. **利用关系**: 图的强大之处在于关系，充分利用 SOCIAL_BOND 和 INFLUENCES
4. **索引优化**: 确保常用查询字段有索引
5. **批量处理**: 大量操作时使用并发提高效率
6. **错误处理**: 始终使用 try-except 处理异常
7. **资源清理**: 使用完毕后调用 `close()` 释放连接

## 🐛 故障排查

### 连接失败

```python
# 检查连接
is_connected = await graph_manager.verify_connectivity()
if not is_connected:
    logger.error("Neo4j 连接失败")
```

### 查询超时

```python
# 增加超时时间
graph_manager = GraphDBManager(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your_password",
    max_transaction_retry_time=60,  # 增加到60秒
)
```

### 性能问题

```python
# 检查事务统计
stats = graph_manager.get_transaction_stats()
if stats["failed_transactions"] > 0:
    logger.warning(f"失败事务: {stats['failed_transactions']}")
```

## 📖 更多示例

完整示例请参考：
- `/examples/graph_example.py` - 详细使用示例
- `/utils/graph_manager.py` - API 文档字符串

## 🔗 相关资源

- [Neo4j 官方文档](https://neo4j.com/docs/)
- [Cypher 查询语言](https://neo4j.com/docs/cypher-manual/)
- [Python 驱动文档](https://neo4j.com/docs/python-manual/)

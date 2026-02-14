# 图数据库集成到 juben 项目

## 📋 集成步骤

### 1. 在 main.py 中注册图数据库路由

```python
# main.py
from fastapi import FastAPI
from apis.graph import router as graph_router

app = FastAPI()

# 注册图数据库路由
app.include_router(graph_router)

@app.on_event("startup")
async def startup_event():
    """启动时初始化图数据库（可选）"""
    try:
        from utils.graph_manager import get_graph_manager
        from config.graph_config import graph_settings

        # 预热连接池
        await get_graph_manager(
            uri=graph_settings.NEO4J_URI,
            username=graph_settings.NEO4J_USERNAME,
            password=graph_settings.NEO4J_PASSWORD,
            database=graph_settings.NEO4J_DATABASE,
        )
        logger.info("图数据库预热完成")
    except Exception as e:
        logger.warning(f"图数据库预热失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理图数据库连接"""
    try:
        from utils.graph_manager import close_graph_manager
        await close_graph_manager()
        logger.info("图数据库连接已关闭")
    except Exception as e:
        logger.warning(f"关闭图数据库连接失败: {e}")
```

### 2. 在 Agent 中使用图数据库

```python
# agents/your_agent.py
from utils.graph_manager import (
    get_graph_manager,
    CharacterData,
    NodeType,
)

class YourAgent:
    async def save_character_to_graph(self, character_data: dict):
        """保存角色到图数据库"""
        graph_manager = await get_graph_manager()

        character = CharacterData(
            character_id=character_data["id"],
            name=character_data["name"],
            story_id=self.session_id,
            # ... 其他属性
        )

        result = await graph_manager.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=character,
        )

        return result
```

### 3. 配置环境变量

在 `.env` 文件中添加：

```env
# Neo4j 图数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# 连接池配置（可选）
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_MAX_CONNECTION_LIFETIME=3600
NEO4J_CONNECTION_ACQUISITION_TIMEOUT=60
NEO4J_MAX_TRANSACTION_RETRY_TIME=30

# 查询配置（可选）
NEO4J_QUERY_TIMEOUT=30
NEO4J_MAX_RESULTS=1000

# 缓存配置（可选）
NEO4J_ENABLE_CACHE=true
NEO4J_CACHE_TTL=300
```

### 4. 启动服务

```bash
# 方式1: 直接启动
python main.py

# 方式2: 使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 测试集成

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/graph/health

# 创建角色
curl -X POST http://localhost:8000/graph/nodes/character \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "test_char_001",
    "name": "测试角色",
    "story_id": "test_story",
    "persona": ["勇敢", "智慧"],
    "arc": 50.0
  }'

# 获取角色网络
curl -X POST http://localhost:8000/graph/network/character \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "test_char_001",
    "depth": 2,
    "include_hidden": false
  }'
```

### 测试脚本

创建 `tests/test_graph_integration.py`:

```python
import pytest
from utils.graph_manager import (
    get_graph_manager,
    CharacterData,
    PlotNodeData,
    NodeType,
    CharacterStatus,
)

@pytest.mark.asyncio
async def test_graph_connection():
    """测试图数据库连接"""
    graph_manager = await get_graph_manager()
    is_connected = await graph_manager.verify_connectivity()
    assert is_connected is True

@pytest.mark.asyncio
async def test_create_character():
    """测试创建角色"""
    graph_manager = await get_graph_manager()

    character = CharacterData(
        character_id="test_char",
        name="测试角色",
        story_id="test_story",
        status=CharacterStatus.ALIVE,
    )

    result = await graph_manager.merge_story_element(
        element_type=NodeType.CHARACTER,
        element_data=character,
    )

    assert result["success"] is True
    assert result["element_id"] == "test_char"

@pytest.mark.asyncio
async def test_character_network():
    """测试角色网络"""
    graph_manager = await get_graph_manager()

    # 先创建两个角色和关系
    # ... 创建代码 ...

    network = await graph_manager.get_character_network(
        character_id="test_char",
        depth=1,
    )

    assert network["success"] is True
    assert "social_network" in network
```

运行测试：

```bash
pytest tests/test_graph_integration.py -v
```

## 📊 监控和维护

### 日志监控

```python
import logging

logger = logging.getLogger("graph_db")

# 在关键操作处添加日志
logger.info(f"创建角色: {character_id}")
logger.error(f"图数据库操作失败: {e}")
logger.warning(f"连接池使用率: {usage}%")
```

### 性能监控

```python
# 定期检查事务统计
async def monitor_graph_performance():
    from utils.graph_manager import get_graph_manager

    graph_manager = await get_graph_manager()
    stats = graph_manager.get_transaction_stats()

    print(f"总事务: {stats['total_transactions']}")
    print(f"成功率: {stats['successful_transactions'] / stats['total_transactions'] * 100:.2f}%")
    print(f"重试次数: {stats['retries']}")
```

### 数据备份

```bash
# 使用 Neo4j 的备份工具
neo4j-admin backup --from=/neo4j/data --to=/backups/neo4j
```

## 🔧 故障排查

### 常见问题

#### 1. 连接失败

```
ServiceUnavailable: Unable to connect to bolt://localhost:7687
```

**解决方案:**
- 检查 Neo4j 是否运行: `docker ps | grep neo4j`
- 检查端口是否开放: `telnet localhost 7687`
- 验证连接配置

#### 2. 认证失败

```
Unauthorized: The client is unauthorized
```

**解决方案:**
- 确认用户名密码正确
- 重置 Neo4j 密码: `docker exec neo4j neo4j-admin set-initial-password`
- 检查 .env 文件配置

#### 3. 查询超时

```
TransientError: Transaction timed out
```

**解决方案:**
- 增加超时配置
- 优化查询语句
- 检查索引是否创建

#### 4. 内存不足

```
OutOfMemoryError: Java heap space
```

**解决方案:**
- 增加 Neo4j 内存配置
- 限制返回结果数量
- 使用分页查询

## 📚 更多资源

- API 文档: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474
- 使用指南: [GRAPH_DATABASE_GUIDE.md](./GRAPH_DATABASE_GUIDE.md)
- 完整示例: [../examples/graph_example.py](../examples/graph_example.py)

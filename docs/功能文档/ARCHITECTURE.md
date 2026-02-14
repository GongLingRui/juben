# Juben 项目架构设计文档

> 版本: v1.0
> 更新日期: 2026-02-03
> 作者: Juben Team

---

## 目录

1. [系统概述](#1-系统概述)
2. [架构设计原则](#2-架构设计原则)
3. [技术架构](#3-技术架构)
4. [核心组件设计](#4-核心组件设计)
5. [数据流设计](#5-数据流设计)
6. [部署架构](#6-部署架构)
7. [安全架构](#7-安全架构)
8. [扩展性设计](#8-扩展性设计)

---

## 1. 系统概述

### 1.1 系统定位

Juben是一个**专业的竖屏短剧策划助手系统**，基于Agent架构模式，提供从创意到策划的完整短剧创作服务。

### 1.2 核心价值

- **情绪价值驱动**: 基于爆款引擎理论，深度理解观众情绪需求
- **智能创作辅助**: AI驱动的剧本策划、创作、评估全流程
- **专业工具链**: 30+专业Agent，覆盖短剧创作的各个环节
- **高性能架构**: 异步处理、连接池管理、多级缓存

### 1.3 技术栈概览

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| Web框架 | FastAPI | 高性能异步Web框架 |
| 数据验证 | Pydantic v2 | 类型安全的数据验证 |
| LLM提供商 | 智谱AI/OpenRouter/OpenAI | 多模型支持 |
| 关系型数据库 | PostgreSQL (PostgreSQL) | 会话管理、数据持久化 |
| 缓存 | Redis | 会话缓存、连接池 |
| 向量数据库 | Milvus | 知识库RAG检索 |
| 容器化 | Docker + Docker Compose | 容器化部署 |
| 监控 | Prometheus + Grafana | 指标监控和可视化 |
| 认证 | JWT | 基于令牌的认证 |

---

## 2. 架构设计原则

### 2.1 设计理念

```
分层清晰 + 模块化 + 可扩展 + 高性能
```

### 2.2 核心原则

1. **单一职责原则**: 每个Agent专注于特定领域
2. **开放封闭原则**: 对扩展开放，对修改封闭
3. **依赖倒置原则**: 依赖抽象而非具体实现
4. **接口隔离原则**: 细粒度接口设计
5. **迪米特法则**: 最少知识原则

### 2.3 架构风格

- **分层架构**: API层 → Agent层 → 工具层 → 数据层
- **事件驱动**: 流式事件处理
- **异步优先**: 全面采用asyncio
- **微服务就绪**: 模块化设计便于拆分

---

## 3. 技术架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              客户端层 (Clients)                              │
│  Web App / Mobile App / CLI Tool / Third-party Integration                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API网关层 (API Gateway)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 认证中间件    │  │ 限流中间件    │  │ 日志中间件    │  │ 错误处理     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              业务服务层 (Services)                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  核心API服务       │  │  增强API服务       │  │  Agent输出服务           │  │
│  │  (Core API)      │  │  (Enhanced API)  │  │  (Agent Outputs)        │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent层 (30+ Agents)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        JubenOrchestrator                              │    │
│  │                        (任务编排与协调)                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │ Concierge  │ │ Planner   │ │ Creator   │ │ Evaluator │ │ Analyzer  │    │
│  │ (接待员)   │ │ (策划)    │ │ (创作)    │ │ (评估)    │ │ (分析)    │    │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              工具层 (38+ Utils)                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ LLM客户端   │ │ 搜索客户端   │ │ 知识库客户端 │ │ 连接池管理器 │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ 存储管理器   │ │ 性能监控器   │ │ 错误处理器   │ │ Notes管理器  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层 (Data Layer)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ PostgreSQL    │ │ Redis       │ │ Milvus      │ │ File System │           │
│  │ (PostgreSQL)│ │ (Cache)     │ │ (Vector DB) │ │ (Outputs)   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 分层说明

#### 3.2.1 客户端层

支持多种客户端接入方式：
- Web应用 (推荐使用Lovable生成的React前端)
- 移动应用
- CLI工具
- 第三方集成 (通过RESTful API)

#### 3.2.2 API网关层

**中间件栈**:
1. **认证中间件**: JWT令牌验证
2. **限流中间件**: 基于用户/IP的速率限制
3. **日志中间件**: 请求/响应日志记录
4. **错误处理中间件**: 统一异常处理

#### 3.2.3 业务服务层

**核心服务**:
- `Core API`: 基础聊天和策划功能
- `Enhanced API`: 高级分析和创作功能
- `Agent Outputs`: Agent输出管理服务

#### 3.2.4 Agent层

**Agent分类**:
- **编排类**: JubenOrchestrator, JubenConcierge
- **策划类**: ShortDramaPlannerAgent
- **创作类**: ShortDramaCreatorAgent, CharacterProfileAgent
- **评估类**: ShortDramaEvaluationAgent, ScriptEvaluationAgent
- **分析类**: StoryFiveElementsAgent, DramaAnalysisAgent
- **工具类**: WebSearchAgent, KnowledgeAgent, FileReferenceAgent

#### 3.2.5 工具层

**工具模块** (38+):
- LLM客户端: 多提供商支持
- 搜索客户端: 网络搜索能力
- 知识库客户端: RAG检索
- 连接池管理: 高性能连接复用
- 存储管理: 多数据库抽象
- 性能监控: 实时性能指标
- 错误处理: 统一错误管理
- Notes管理: 用户上下文管理

#### 3.2.6 数据层

**存储架构** (三层存储):
1. **内存层**: 热点数据缓存
2. **Redis层**: 会话状态、连接池
3. **PostgreSQL层**: 数据持久化
4. **Milvus层**: 向量检索
5. **文件系统**: Agent输出存储

---

## 4. 核心组件设计

### 4.1 BaseJubenAgent (基础Agent类)

**职责**: 提供所有Agent的通用基础功能

**核心功能**:
```python
class BaseJubenAgent(ABC):
    # 1. LLM调用
    async def _call_llm(messages, **kwargs) -> str
    async def _stream_llm(messages, **kwargs) -> AsyncGenerator

    # 2. 搜索能力
    async def _search_web(query, count) -> Dict
    async def _search_knowledge_base(query, collection) -> Dict

    # 3. 数据存储
    async def save_chat_message(...) -> str
    async def get_chat_messages(...) -> List
    async def save_context_state(...) -> bool
    async def save_note(...) -> str

    # 4. 流式事件
    async def emit_juben_event(event_type, data, metadata) -> Dict

    # 5. 停止管理
    async def check_stop_status(...) -> bool
    async def request_stop(...) -> bool

    # 6. 性能优化
    def enable_performance_mode()
    def enable_debug_mode()
```

**设计亮点**:
- Agent级别的temperature配置
- 连接池管理集成
- 停止状态检查优化
- 多模态内容处理

### 4.2 JubenOrchestrator (编排器)

**职责**: 任务分解、Agent协调、工作流管理

**核心功能**:
```python
class JubenOrchestrator(BaseJubenAgent):
    # 1. Agent as Tool机制
    async def call_agent_as_tool(agent_name, request_data, ...) -> Dict

    # 2. ReAct模式支持
    async def _run_react_mode(request_data, context) -> AsyncGenerator

    # 3. 工作流编排
    async def _orchestrate_workflow(workflow_name, steps, context) -> AsyncGenerator

    # 4. 智能Agent选择
    async def _select_agent_for_task(task_type, context) -> str
```

**ReAct模式**:
```
Thought → Action → Observation → Thought → ... → Final Answer
```

**Agent工具池** (8个核心工具):
1. 网络搜索 (WebSearchAgent)
2. 知识库检索 (KnowledgeAgent)
3. 文件引用 (FileReferenceAgent)
4. 短剧策划 (ShortDramaPlannerAgent)
5. 短剧创作 (ShortDramaCreatorAgent)
6. 短剧评估 (ShortDramaEvaluationAgent)
7. 故事分析 (StoryFiveElementsAgent)
8. 剧集分析 (SeriesAnalysisAgent)

### 4.3 连接池管理器

**职责**: 管理数据库和外部服务的连接池

**架构**:
```python
class ConnectionPoolManager:
    # Redis连接池
    - high_priority_pool (orchestrator/concierge)
    - normal_pool (其他agents)

    # PostgreSQL连接池
    - normal_client (普通查询)
    - service_client (绕过RLS)

    # 连接池操作
    async def get_redis_client(pool_type) -> Redis
    async def get_db_client(client_type) -> Client
    async def health_check() -> Dict
    async def get_connection_stats() -> Dict
```

**优化特性**:
- 连接池预热
- 动态连接数调整
- 健康检查机制
- 连接池监控指标

### 4.4 性能监控器

**职责**: 实时监控Agent和系统性能

**监控指标**:
```python
class PerformanceMonitor:
    # Agent性能
    - 调用次数
    - 平均响应时间
    - 错误率
    - P50/P95/P99延迟

    # 系统性能
    - LLM响应时间
    - 数据库查询时间
    - 缓存命中率
    - 连接池使用率
```

---

## 5. 数据流设计

### 5.1 请求处理流程

```
用户请求
    │
    ▼
┌──────────────┐
│  认证中间件   │ ──→ 验证JWT令牌
└──────────────┘
    │
    ▼
┌──────────────┐
│  意图识别     │ ──→ Concierge分析意图
└──────────────┘
    │
    ▼
┌──────────────┐
│  任务编排     │ ──→ Orchestrator分解任务
└──────────────┘
    │
    ├──→ Agent1 (处理子任务1)
    ├──→ Agent2 (处理子任务2)
    └──→ Agent3 (处理子任务3)
    │
    ▼
┌──────────────┐
│  结果整合     │ ──→ 聚合Agent输出
└──────────────┘
    │
    ▼
┌──────────────┐
│  输出存储     │ ──→ 保存到数据库/文件
└──────────────┘
    │
    ▼
流式响应返回用户
```

### 5.2 Notes系统数据流

```
用户输入
    │
    ▼
┌──────────────┐
│ 消息队列管理  │ ──→ 添加到用户消息队列
└──────────────┘
    │
    ▼
┌──────────────┐
│ Agent处理    │ ──→ 生成Notes (自动/手动选择)
└──────────────┘
    │
    ▼
┌──────────────┐
│ Notes存储    │ ──→ 保存到PostgreSQL
└──────────────┘
    │
    ▼
┌──────────────┐
│ 引用解析     │ ──→ 支持@note1引用
└──────────────┘
```

### 5.3 流式事件流

```
Agent执行
    │
    ├─── emit_juben_event("thought", "思考内容...")
    ├─── emit_juben_event("tool_call", "调用搜索工具...")
    ├─── emit_juben_event("tool_result", "搜索结果...")
    └─── emit_juben_event("final_answer", "最终答案...")
    │
    ▼
SSE流式返回前端
    │
    ▼
前端实时渲染
```

---

## 6. 部署架构

### 6.1 Docker Compose部署

**服务清单**:
```yaml
services:
  juben-api:        # 主API服务
  redis:            # 缓存服务
  milvus:           # 向量数据库
  etcd:             # Milvus依赖
  minio:            # Milvus存储
  nginx:            # 反向代理
  prometheus:       # 监控
  grafana:          # 可视化
```

### 6.2 网络架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (80/443)                       │
│  SSL终止 / 反向代理 / 静态资源 / 负载均衡                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ juben-api    │  │ redis        │  │ milvus       │      │
│  │ :8000        │  │ :6379        │  │ :19530       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ prometheus   │  │ grafana      │  │ nginx        │      │
│  │ :9090        │  │ :3000        │  │ :80/443      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      External Services                       │
│  PostgreSQL (云托管)                                           │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 生产部署建议

**推荐配置**:
- CPU: 4核心+
- 内存: 8GB+
- 存储: 50GB SSD
- 网络: 100Mbps+

**高可用部署** (未来):
- Kubernetes集群
- 服务网格 (Istio)
- 消息队列 (RabbitMQ/Kafka)
- 分布式追踪 (Jaeger)

---

## 7. 安全架构

### 7.1 认证流程

```
用户登录
    │
    ▼
POST /auth/login
    │
    ▼
验证用户名密码
    │
    ▼
生成JWT令牌
    │
    ├── Access Token (30分钟)
    └── Refresh Token (7天)
    │
    ▼
返回令牌给客户端
```

### 7.2 API鉴权

**保护机制**:
1. JWT令牌验证
2. 令牌黑名单 (登出)
3. 令牌自动刷新
4. 权限检查

**权限模型**:
```python
# 用户权限
permissions = [
    "chat:write",      # 发送消息
    "script:read",     # 读取剧本
    "script:write",    # 创建/编辑剧本
    "admin:manage"     # 管理员权限
]
```

### 7.3 安全措施

| 安全措施 | 实现方式 |
|----------|----------|
| API鉴权 | JWT令牌 |
| 速率限制 | Redis计数器 |
| 输入验证 | Pydantic模型 |
| 密码加密 | bcrypt |
| SQL注入防护 | 参数化查询 |
| XSS防护 | 输入转义 |
| CSRF防护 | SameSite Cookie |
| 日志脱敏 | 敏感信息过滤 |

---

## 8. 扩展性设计

### 8.1 水平扩展

**API服务扩展**:
```bash
# 启动多个API实例
docker-compose up --scale juben-api=3
```

**数据库扩展**:
- Redis集群 (Redis Cluster)
- PostgreSQL读写分离
- Milvus分布式部署

### 8.2 垂直扩展

**资源配置**:
```yaml
juben-api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

### 8.3 微服务拆分路径

**第一阶段: 模块化**
```
juben/
├── services/
│   ├── planner-service/    # 策划服务
│   ├── creator-service/    # 创作服务
│   ├── evaluator-service/  # 评估服务
│   └── shared/             # 共享模块
```

**第二阶段: 服务拆分**
```
每个服务独立部署:
- 独立数据库
- 独立缓存
- 独立监控
```

**第三阶段: 微服务化**
```
- API Gateway
- Service Mesh (Istio)
- 消息队列
- 配置中心
- 服务发现
```

### 8.4 插件化扩展

**Agent插件**:
```python
# 自定义Agent
class CustomAgent(BaseJubenAgent):
    async def process_request(self, request_data, context):
        # 自定义逻辑
        yield {"event_type": "custom", "data": "..."}

# 注册插件
AgentRegistry.register("custom_agent", CustomAgent)
```

**工具插件**:
```python
# 自定义工具
@tool_registry.register("custom_tool")
async def custom_tool(input: str) -> str:
    # 工具逻辑
    return "result"
```

---

## 附录

### A. 关键术语表

| 术语 | 说明 |
|------|------|
| Agent | 具有特定功能的AI智能体 |
| Orchestrator | 任务编排和协调的Agent |
| Concierge | 接待员Agent，负责意图识别 |
| Notes | 用户上下文中的关键信息片段 |
| ReAct | Reasoning + Acting模式 |
| RAG | Retrieval Augmented Generation |

### B. 相关文档

- [API使用指南](./API_GUIDE.md)
- [Agent开发指南](./AGENT_DEVELOPMENT.md)
- [部署运维手册](./DEPLOYMENT.md)
- [故障排除指南](./TROUBLESHOOTING.md)

### C. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-02-03 | 初始版本 |

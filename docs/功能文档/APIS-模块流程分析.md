# APIs模块流程分析

## 功能概述

APIs模块是系统的API网关层，负责接收前端HTTP请求，路由到相应的Agent处理，并将Agent的流式响应转换为SSE格式返回给前端。该模块包含核心API路由、Agent专用API路由、百度搜索API、工具API和项目管理API等子模块。

## 入口方法

```
main.py:main()
apis/core/api_routes.py:router (FastAPI Router)
apis/agents/api_routes_agents.py:router
apis/baidu/api_routes_baidu.py:router
apis/tools/api_routes_tools.py:router
apis/projects/api_routes_projects.py:router
```

## 方法调用树

```
FastAPI应用启动 (main.py)
├─ 创建FastAPI应用实例
├─ 添加CORS中间件
├─ 注册路由
│  ├─ core_router (/juben/*) - 核心API路由
│  ├─ agents_router (/agents/*) - Agent专用路由
│  ├─ baidu_router (/baidu/*) - 百度搜索API
│  ├─ tools_router (/tools/*) - 工具API
│  └─ projects_router (/projects/*) - 项目管理API
├─ 挂载静态文件服务 (frontend/dist)
└─ 启动Uvicorn服务器

核心API路由 (apis/core/api_routes.py)
├─ Agent管理
│  ├─ GET /juben/agents/list - 获取Agent列表
│  ├─ GET /juben/agents/{agent_id} - 获取Agent详情
│  ├─ GET /juben/agents/categories - 获取Agent分类
│  └─ GET /juben/agents/search - 搜索Agent
├─ 聊天接口
│  ├─ POST /juben/chat - 策划助手聊天 (SSE流式)
│  ├─ POST /juben/creator/chat - 创作助手聊天 (SSE流式)
│  ├─ POST /juben/evaluation/chat - 评估助手聊天 (SSE流式)
│  ├─ POST /juben/websearch/chat - 网络搜索聊天 (SSE流式)
│  ├─ POST /juben/knowledge/chat - 知识库查询聊天 (SSE流式)
│  └─ POST /juben/file-reference/chat - 文件引用解析 (SSE流式)
├─ 分析接口
│  ├─ POST /juben/story-analysis/analyze - 故事五元素分析 (SSE流式)
│  ├─ POST /juben/series-analysis/analyze - 已播剧集分析 (SSE流式)
│  ├─ POST /juben/drama/analysis - 剧本深度分析 (SSE流式)
│  └─ POST /juben/story-type/analyze - 故事类型分析 (SSE流式)
├─ 工作流接口
│  ├─ POST /juben/plot-points-workflow/execute - 情节点工作流 (SSE流式)
│  └─ POST /juben/drama-workflow/execute - 剧本创作工作流 (SSE流式)
├─ 故事处理接口
│  ├─ POST /juben/story/summary - 故事大纲生成 (SSE流式)
│  ├─ POST /juben/major-plot-points/chat - 大情节点分析 (SSE流式)
│  └─ POST /juben/plot-points/detailed - 详细情节点生成 (SSE流式)
├─ 人物处理接口
│  ├─ POST /juben/character/profile - 人物小传生成 (SSE流式)
│  └─ POST /juben/character/relationship - 人物关系分析 (SSE流式)
├─ 评估接口
│  ├─ POST /juben/script/evaluation - 剧本评估 (SSE流式)
│  ├─ POST /juben/ip/evaluation - IP价值评估 (SSE流式)
│  ├─ POST /juben/story/evaluation - 故事质量评估 (SSE流式)
│  ├─ POST /juben/outline/evaluation - 大纲评估 (SSE流式)
│  └─ POST /juben/novel/screening - 小说筛选评估 (SSE流式)
├─ 工具接口
│  ├─ POST /juben/text/split - 文本分割 (SSE流式)
│  ├─ POST /juben/text/truncate - 文本截断 (SSE流式)
│  ├─ POST /juben/mind-map/generate - 思维导图生成 (SSE流式)
│  ├─ POST /juben/output/format - 输出格式化 (SSE流式)
│  ├─ POST /juben/document/generate - 文档生成 (SSE流式)
│  ├─ POST /juben/score/analyze - 评分分析 (SSE流式)
│  ├─ POST /juben/text/evaluate - 文本处理评估 (SSE流式)
│  └─ POST /juben/result/analyze - 结果分析评估 (SSE流式)
├─ 剧集处理接口
│  ├─ POST /juben/series/info - 剧集信息提取 (SSE流式)
│  └─ POST /juben/series/name - 剧名提取 (SSE流式)
├─ 系统接口
│  ├─ GET /juben/health - 健康检查
│  ├─ GET /juben/config - 获取系统配置
│  ├─ GET /juben/models - 获取可用模型列表
│  ├─ GET /juben/models/recommend - 获取推荐模型
│  ├─ GET /juben/models/types - 按类型获取模型
│  ├─ POST /juben/intent/analyze - 意图分析
│  ├─ GET /juben/knowledge/collections - 获取知识库集合
│  └─ POST /juben/knowledge/search - 知识库搜索
└─ Agent信息接口
   └─ GET /juben/{agent_id}/info - 获取Agent信息 (各Agent专用)

SSE流式响应处理
├─ generate_stream_response() - 生成流式响应
│  └─ agent.process_request() -> Agent处理
│     └─ 转换为SSE格式: "data: {json}\\n\\n"
├─ generate_file_reference_stream_response() - 文件引用流式响应
├─ generate_story_analysis_stream_response() - 故事分析流式响应
└─ generate_series_analysis_stream_response() - 剧集分析流式响应
```

## 详细业务流程

### 1. API请求处理流程

**1.1 聊天接口处理流程** (`POST /juben/chat`)
```
1. 接收ChatRequest请求
   {
     input: str,              # 用户输入
     user_id: str,            # 用户ID
     session_id: str,         # 会话ID
     model: str,              # 模型名称(可选)
     model_provider: str,     # 模型提供商(可选)
     enable_web_search: bool, # 是否启用网络搜索
     enable_knowledge_base: bool # 是否启用知识库
   }

2. 构建request_data
   - 提取input、enable_web_search、enable_knowledge_base

3. 构建context
   - user_id: 用户ID
   - session_id: 会话ID(默认基于hash生成)
   - model_provider: 模型提供商(从配置读取)
   - model: 模型名称

4. 获取Agent实例
   - get_planner_agent() -> ShortDramaPlannerAgent单例

5. 返回StreamingResponse
   - media_type: text/plain
   - headers: Cache-Control, Connection, Content-Type
   - 生成器: generate_stream_response()

6. 流式生成响应
   a. 调用agent.process_request(request_data, context)
   b. 接收Agent的event事件
   c. 转换为SSE格式: "data: {json}\\n\\n"
   d. yield格式化后的数据

7. 异常处理
   - 捕获异常
   - 返回错误事件
```

**1.2 流式响应格式**
```
事件类型 (event_type):
- system: 系统消息(开始处理、步骤提示等)
- llm_chunk: LLM生成的内容块
- error: 错误信息
- billing: Token计费信息
- done: 完成标识

数据格式:
data: {"event": "message", "data": {"content": "...", "metadata": {}, "timestamp": "..."}}
```

### 2. Agent列表管理流程

**2.1 获取Agent列表** (`GET /juben/agents/list`)
```
1. 接收category参数(可选)
2. 从AGENTS_LIST_CONFIG获取所有Agent配置
3. 如果指定category，过滤出对应分类的Agent
4. 统计各分类Agent数量
5. 返回响应:
   {
     success: true,
     agents: [...],        # Agent列表
     total: 40,            # 总数
     category_counts: {}   # 各分类统计
   }
```

**2.2 获取Agent详情** (`GET /juben/agents/{agent_id}`)
```
1. 从AGENTS_LIST_CONFIG查找指定agent_id
2. 如果不存在，返回404
3. 返回Agent完整配置信息
```

### 3. 模型管理流程

**3.1 获取可用模型列表** (`GET /juben/models`)
```
1. 接收provider参数(默认zhipu)
2. 调用list_available_models(provider)
3. 获取各场景推荐模型:
   - default: 默认模型
   - reasoning: 推理模型
   - vision: 视觉模型
   - image_gen: 图像生成模型
   - video_gen: 视频生成模型
   - latest: 最新模型
4. 返回模型配置信息
```

**3.2 获取推荐模型** (`GET /juben/models/recommend`)
```
1. 接收purpose参数(default/reasoning/vision等)
2. 调用get_model_for_purpose(purpose)
3. 获取模型配置
4. 返回推荐模型信息:
   {
     name: "glm-4-flash",
     display_name: "智谱清言Flash",
     description: "...",
     max_tokens: 128000,
     thinking_enabled: false
   }
```

### 4. Agent调用流程

**4.1 核心三步流程**
```
步骤1: Agent实例获取
- 使用全局单例模式
- 延迟初始化(首次使用时创建)
- 函数命名: get_xxx_agent()

步骤2: 请求数据构建
- 提取ChatRequest中的字段
- 构建request_data字典
- 构建context字典(含user_id、session_id等)

步骤3: 流式响应生成
- 创建async生成器函数
- 调用agent.process_request()
- 逐个yield事件(转换为SSE格式)
- 异常处理和错误响应
```

**4.2 典型Agent调用示例**
```python
# 1. 定义全局Agent实例
_agent_xxx = None

# 2. 定义获取函数
def get_xxx_agent():
    global _agent_xxx
    if _agent_xxx is None:
        from agents.xxx_agent import XxxAgent
        _agent_xxx = XxxAgent()
    return _agent_xxx

# 3. 定义API端点
@router.post("/xxx/operation")
async def xxx_operation(request: ChatRequest):
    agent = get_xxx_agent()

    async def event_generator():
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id
        }
        request_data = {"input": request.input}

        async for event in agent.process_request(request_data, context):
            event_data = json.dumps(event, ensure_ascii=False)
            yield f"data: {event_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
```

### 5. 工作流执行流程

**5.1 情节点工作流执行** (`POST /juben/plot-points-workflow/execute`)
```
1. 获取工作流编排器实例
   - get_workflow_orchestrator() -> PlotPointsWorkflowOrchestrator

2. 构建request_data
   {
     input: str,
     chunk_size: int (默认10000),
     length_size: int (默认50000),
     format: str (默认"markdown")
   }

3. 构建context
   {
     user_id: str,
     session_id: str
   }

4. 执行工作流
   - orchestrator.execute_workflow(request_data, context)
   - 流式返回工作流事件

5. 事件类型:
   - workflow_start: 工作流开始
   - workflow_step: 步骤通知
   - workflow_progress: 进度通知
   - workflow_result: 最终结果
   - workflow_complete: 工作流完成
   - workflow_error: 工作流错误
```

### 6. 知识库接口流程

**6.1 获取知识库集合** (`GET /juben/knowledge/collections`)
```
1. 获取知识库Agent实例
2. 调用agent.get_available_collections()
3. 返回集合列表:
   [
     {
       name: "script_segments",
       display_name: "剧本桥段库",
       description: "包含各种经典剧本桥段和情节模板"
     },
     {
       name: "drama_highlights",
       display_name: "短剧高能情节库",
       description: "包含短剧中的高能情节和爆点设计"
     }
   ]
```

**6.2 知识库搜索** (`POST /juben/knowledge/search`)
```
1. 提取query和collection参数
2. 调用知识库Agent的knowledge_client.search()
3. 返回搜索结果
```

## 关键业务规则

### SSE流式响应规则
- **格式规范**: 严格遵循SSE格式 `data: {json}\\n\\n`
- **事件类型**: system/llm_chunk/error/billing/done
- **编码要求**: ensure_ascii=False,支持中文
- **缓存控制**: Cache-Control: no-cache
- **连接保持**: Connection: keep-alive

### Agent单例规则
- **全局单例**: 每个Agent类型使用全局单例模式
- **延迟初始化**: 首次调用时初始化,避免启动时加载所有Agent
- **线程安全**: Python GIL保证单例创建的线程安全

### 请求验证规则
- **必需参数**: input为必需参数
- **默认值设置**: session_id、user_id等有默认值
- **参数校验**: 使用Pydantic进行参数校验

### 错误处理规则
- **HTTP异常**: 使用HTTPException返回错误
- **日志记录**: 所有错误记录到日志
- **用户友好**: 生产环境不返回详细错误信息

## 数据流转

### 请求流程
```
Frontend -> FastAPI -> API路由 -> Agent -> LLM/外部服务
   <--------- SSE流式响应 -------------
```

### ChatRequest模型
```python
class ChatRequest(BaseModel):
    input: str                           # 用户输入
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = None
    model: Optional[str] = None          # 模型名称
    model_provider: Optional[str] = None
    enable_web_search: Optional[bool] = True
    enable_knowledge_base: Optional[bool] = True
```

### Agent配置
```python
AGENTS_LIST_CONFIG = [
    {
        "id": "short_drama_planner",
        "name": "ShortDramaPlannerAgent",
        "display_name": "短剧策划助手",
        "description": "专业的短剧策划和创作建议助手",
        "category": "planning",
        "icon": "📋",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/chat",
        "features": [...],
        "capabilities": [...],
        "status": "active"
    },
    ...
]
```

## 扩展点/分支逻辑

### Agent分类
- **planning**: 策划类Agent
- **creation**: 创作类Agent
- **evaluation**: 评估类Agent
- **analysis**: 分析类Agent
- **workflow**: 工作流Agent
- **character**: 人物类Agent
- **story**: 故事类Agent
- **utility**: 工具类Agent

### 响应格式分支
- **流式响应**: 使用StreamingResponse,返回SSE格式
- **JSON响应**: 使用JSONResponse,返回结构化数据

### Agent状态
- **active**: 活跃状态,正常使用
- **beta**: 测试状态,功能可能不完善
- **deprecated**: 已弃用,不推荐使用

## 外部依赖

### FastAPI框架
- 路由管理
- 请求验证
- 响应序列化
- 中间件支持

### Uvicorn服务器
- ASGI服务器
- 热重载支持
- 日志集成

### Agents模块
- 提供所有业务逻辑处理
- 流式事件生成

## 注意事项

### 性能优化
1. **Agent单例**: 避免重复创建Agent实例
2. **异步处理**: 所有Agent调用使用async/await
3. **流式响应**: 使用SSE流式返回,提升用户体验

### 安全考虑
1. **CORS配置**: 正确配置CORS,允许前端访问
2. **输入验证**: 使用Pydantic验证所有输入
3. **错误隔离**: 不暴露敏感错误信息

### 可维护性
1. **路由分组**: 按功能模块分组路由
2. **命名规范**: 统一的命名规范
3. **文档注释**: 完整的API文档注释

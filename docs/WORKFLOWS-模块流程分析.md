# Workflows模块流程分析

## 功能概述

Workflows模块负责复杂业务流程的编排和协调，通过工作流编排器(Orchestrator)将多个Agent组合成完整的业务流程。该模块实现了Agent as Tool机制，支持Agent间的模块化调用和上下文隔离。

## 入口方法

```
workflows/plot_points_workflow.py:PlotPointsWorkflowOrchestrator.execute_workflow()
```

## 方法调用树

```
PlotPointsWorkflowOrchestrator (情节点工作流编排器)
├─ __init__()
│  ├─ 初始化工作流Agent
│  ├─ 初始化子Agent注册表(延迟加载)
│  ├─ 初始化工作流状态
│  └─ 配置工作流参数
├─ execute_workflow(input_data, context)
│  ├─ 生成workflow_id
│  ├─ 步骤1: _step_input_validation() - 输入验证
│  ├─ 步骤2: _step_text_preprocessing() - 文本预处理
│  │  ├─ TextTruncator.truncate_text() - 文本截断
│  │  └─ TextSplitter.split_text() - 文本分割
│  ├─ 步骤3: _step_batch_coordination() - 批处理协调
│  ├─ 步骤4: _step_agent_coordination() - Agent协调
│  │  ├─ 并发控制(Semaphore)
│  │  ├─ 超时控制(asyncio.wait_for)
│  │  ├─ _call_story_summary_agent() - 故事大纲
│  │  ├─ _call_major_plot_points_agent() - 大情节点
│  │  ├─ _call_mind_map_agent() - 思维导图
│  │  └─ _call_detailed_plot_points_agent() - 详细情节点
│  ├─ 步骤5: _step_result_integration() - 结果整合
│  │  └─ OutputFormatterAgent.process_request() - 格式化输出
│  └─ 计算处理时间
└─ get_workflow_info()
```

## 详细业务流程

### 1. 工作流执行主流程

```
1. 工作流初始化
   - 生成唯一workflow_id (UUID)
   - 记录开始时间
   - 初始化工作流状态

2. 步骤1: 输入验证
   - 验证必需参数(input)
   - 设置配置参数(chunk_size, length_size, format)
   - 发送验证通过事件

3. 步骤2: 文本预处理
   - 调用TextTruncator截断超长文本
   - 调用TextSplitter分割文本为chunks
   - 存储处理后的chunks到workflow_state

4. 步骤3: 批处理协调
   - 配置BatchProcessor
   - 设置并行限制参数

5. 步骤4: Agent协调执行
   - 使用Semaphore限制并发数量(默认4个)
   - 为每个Agent调用设置超时(默认300秒)
   - 并行调用四个Agent:
     a. StorySummaryGeneratorAgent - 故事大纲生成
     b. MajorPlotPointsAgent - 大情节点提取
     c. MindMapAgent - 思维导图生成
     d. DetailedPlotPointsAgent - 详细情节点展开
   - 收集所有Agent结果

6. 步骤5: 结果整合
   - 调用OutputFormatterAgent格式化输出
   - 整合所有Agent结果
   - 构建最终结果结构
   - 添加元数据(处理时间、chunk数量等)

7. 工作流完成
   - 计算处理时间
   - 记录结束时间
   - 发送完成事件
```

### 2. Agent调用流程

**2.1 故事大纲Agent调用**
```
1. 检查sub_agents注册表
2. 如果未加载,延迟加载StorySummaryGeneratorAgent
3. 调用agent.process_request()
4. 传入拼接的chunks作为input
5. 收集type="content"的事件
6. 拼接所有内容块
7. 返回结果或错误信息
```

**2.2 大情节点Agent调用**
```
1. 检查sub_agents注册表
2. 如果未加载,延迟加载MajorPlotPointsAgent
3. 调用agent.process_request()
4. 传入拼接的chunks作为input
5. 收集type="content"的事件
6. 拼接所有内容块
7. 返回结果或错误信息
```

**2.3 思维导图Agent调用**
```
1. 检查sub_agents注册表
2. 如果未加载,延迟加载MindMapAgent
3. 调用agent.process_request()
4. 传入拼接的chunks作为input
5. 收集type="mind_map_generated"的事件
6. 提取pic和jump_link字段
7. 返回结果或错误信息
```

**2.4 详细情节点Agent调用**
```
1. 检查sub_agents注册表
2. 如果未加载,延迟加载DetailedPlotPointsAgent
3. 获取大情节点结果(agent_1)
4. 调用agent.process_request()
5. 传入大情节点作为input
6. 收集type="content"的事件
7. 拼接所有内容块
8. 返回结果或错误信息
```

### 3. 并发控制流程

**3.1 信号量控制**
```
1. 创建Semaphore实例(limit=4)
2. 每个Agent调用前acquire信号量
3. 执行Agent调用
4. 完成后release信号量
5. 最多4个Agent同时执行
```

**3.2 超时控制**
```
1. 使用asyncio.wait_for包装Agent调用
2. 设置timeout=300秒
3. 超时后捕获TimeoutError
4. 返回超时错误信息
5. 不中断其他Agent执行
```

**3.3 异常处理**
```
1. 使用asyncio.gather的return_exceptions=True
2. 捕获所有异常,不中断整体流程
3. 区分Exception和普通错误结果
4. 返回统一的错误事件格式
```

## 关键业务规则

### Agent延迟加载规则
- **按需加载**: Agent仅在首次使用时加载
- **注册表管理**: 使用sub_agents字典管理已加载Agent
- **线程安全**: 使用asyncio.Lock保护加载过程

### 并发执行规则
- **并发限制**: 使用Semaphore限制并发数量
- **超时控制**: 每个Agent调用设置独立超时
- **异常隔离**: 单个Agent失败不影响其他Agent

### 结果整合规则
- **顺序固定**: Agent结果按固定顺序存储(agent_0, agent_1, ...)
- **依赖关系**: 详细情节点依赖大情节点结果
- **格式化输出**: 使用OutputFormatterAgent统一格式

### 工作流状态规则
- **状态追踪**: 记录每个步骤的当前状态
- **时间记录**: 记录开始时间和结束时间
- **结果存储**: 存储所有中间结果和最终结果

## 数据流转

### 输入数据
```python
input_data = {
    input: str,              # 输入文本
    chunk_size: int,         # 文本块大小(默认10000)
    length_size: int,        # 最大长度(默认50000)
    format: str              # 输出格式(默认markdown)
}

context = {
    user_id: str,
    session_id: str
}
```

### 中间数据
```python
workflow_state = {
    workflow_id: str,
    start_time: datetime,
    end_time: datetime,
    current_step: str,
    processed_chunks: [str],  # 分割后的文本块
    agent_results: {          # Agent执行结果
        agent_0: {...},       # 故事大纲
        agent_1: {...},       # 大情节点
        agent_2: {...},       # 思维导图
        agent_3: {...}        # 详细情节点
    },
    final_result: {...}
}
```

### 输出数据
```python
final_result = {
    story_summary: str,       # 故事大纲
    major_plot_points: str,   # 大情节点
    mind_map: {               # 思维导图
        pic: str,             # 图片URL
        jump_link: str        # 编辑链接
    },
    detailed_plot_points: str,# 详细情节点
    formatted_output: str,    # 格式化输出
    metadata: {
        processing_time: str,
        chunks_processed: int,
        agents_used: [str],
        workflow_id: str
    }
}
```

## 扩展点/分支逻辑

### 配置分支
- **chunk_size**: 控制文本分割大小
- **length_size**: 控制文本截断长度
- **agent_concurrency_limit**: 控制Agent并发数量
- **agent_call_timeout**: 控制Agent调用超时

### 输出格式分支
- **markdown**: Markdown格式输出
- **json**: JSON格式输出
- **html**: HTML格式输出

### 错误处理分支
- **验证错误**: 输入参数验证失败
- **处理错误**: 文本预处理失败
- **Agent错误**: Agent调用失败(超时、异常)
- **整合错误**: 结果整合失败

## 外部依赖

### Agents模块
- PlotPointsWorkflowAgent: 主工作流Agent
- StorySummaryGeneratorAgent: 故事大纲生成
- MajorPlotPointsAgent: 大情节点提取
- MindMapAgent: 思维导图生成
- DetailedPlotPointsAgent: 详细情节点展开
- OutputFormatterAgent: 输出格式化

### 工具类
- TextTruncator: 文本截断工具
- TextSplitter: 文本分割工具

## 注意事项

### 性能优化
1. **并发执行**: 四个Agent并行执行,提升效率
2. **延迟加载**: Agent按需加载,减少启动时间
3. **超时控制**: 避免单个Agent阻塞整个流程

### 容错处理
1. **异常隔离**: 单个Agent失败不影响其他Agent
2. **超时保护**: 每个Agent有独立超时控制
3. **降级处理**: 失败时返回错误信息而非中断流程

### 可扩展性
1. **Agent注册表**: 可动态添加新的Agent
2. **配置灵活**: 支持运行时配置参数
3. **步骤可扩展**: 可添加新的处理步骤

## 系统交互图

```plantuml
@startuml
participant API
participant Orchestrator
participant Agent1
participant Agent2
participant Agent3
participant Agent4

API -> Orchestrator: execute_workflow(input_data, context)
activate Orchestrator

Orchestrator -> Orchestrator: _step_input_validation()
Orchestrator -> Orchestrator: _step_text_preprocessing()
Orchestrator -> Orchestrator: _step_batch_coordination()

Orchestrator -> Agent1: _call_story_summary_agent()
activate Agent1
Agent1 --> Orchestrator: 故事大纲
deactivate Agent1

par 并行执行
    Orchestrator -> Agent2: _call_major_plot_points_agent()
    activate Agent2
    Agent2 --> Orchestrator: 大情节点
    deactivate Agent2
and
    Orchestrator -> Agent3: _call_mind_map_agent()
    activate Agent3
    Agent3 --> Orchestrator: 思维导图
    deactivate Agent3
end

Orchestrator -> Agent4: _call_detailed_plot_points_agent(依赖大情节点)
activate Agent4
Agent4 --> Orchestrator: 详细情节点
deactivate Agent4

Orchestrator -> Orchestrator: _step_result_integration()
Orchestrator --> API: final_result
deactivate Orchestrator
@enduml
```

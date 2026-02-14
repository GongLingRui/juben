# Juben Agent 开发指南

> 版本: v1.0
> 更新日期: 2026-02-03
> 作者: Juben Team

---

## 目录

1. [Agent概述](#1-agent概述)
2. [快速开始](#2-快速开始)
3. [核心概念](#3-核心概念)
4. [Agent开发](#4-agent开发)
5. [高级特性](#5-高级特性)
6. [最佳实践](#6-最佳实践)
7. [插件开发](#7-插件开发)

---

## 1. Agent概述

### 1.1 什么是Agent

Agent是Juben系统中的基本执行单元，每个Agent专注于特定的短剧创作任务。

**Agent类型**:
- **编排类**: Orchestrator, Concierge
- **策划类**: ShortDramaPlannerAgent
- **创作类**: ShortDramaCreatorAgent, CharacterProfileAgent
- **评估类**: ShortDramaEvaluationAgent, ScriptEvaluationAgent
- **分析类**: StoryFiveElementsAgent, DramaAnalysisAgent
- **工具类**: WebSearchAgent, KnowledgeAgent

### 1.2 Agent生命周期

```
初始化 → 接收请求 → 处理请求 → 发送事件 → 保存结果 → 清理
```

---

## 2. 快速开始

### 2.1 创建第一个Agent

```python
from agents.base_juben_agent import BaseJubenAgent
from typing import Dict, Any, AsyncGenerator

class MyCustomAgent(BaseJubenAgent):
    """自定义Agent示例"""

    def __init__(self):
        super().__init__(
            agent_name="my_custom_agent",
            model_provider="zhipu"
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理请求的主方法"""

        # 1. 发送思考事件
        yield {
            "event_type": "thought",
            "data": "正在分析用户需求...",
            "metadata": {}
        }

        # 2. 处理业务逻辑
        user_input = request_data.get("input", "")
        result = await self._process_input(user_input)

        # 3. 发送最终答案
        yield {
            "event_type": "final_answer",
            "data": result,
            "metadata": {}
        }

    async def _process_input(self, input_text: str) -> str:
        """处理输入文本"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": input_text}
        ]

        response = await self._call_llm(messages)
        return response
```

### 2.2 注册Agent

```python
# 在 agents/__init__.py 中注册
from .my_custom_agent import MyCustomAgent

__all__ = [
    # ...
    "MyCustomAgent"
]
```

### 2.3 使用Agent

```python
# 初始化Agent
agent = MyCustomAgent()

# 处理请求
async def main():
    request_data = {
        "input": "测试输入",
        "user_id": "user_123",
        "session_id": "session_456"
    }

    async for event in agent.process_request(request_data):
        print(f"Event: {event['event_type']}, Data: {event['data']}")

# 运行
import asyncio
asyncio.run(main())
```

---

## 3. 核心概念

### 3.1 BaseJubenAgent

**基础功能**:
```python
class BaseJubenAgent(ABC):
    # LLM调用
    async def _call_llm(messages, **kwargs) -> str
    async def _stream_llm(messages, **kwargs) -> AsyncGenerator[str]

    # 搜索能力
    async def _search_web(query, count) -> Dict
    async def _search_knowledge_base(query, collection) -> Dict

    # 数据存储
    async def save_chat_message(...) -> str
    async def get_chat_messages(...) -> List
    async def save_context_state(...) -> bool
    async def save_note(...) -> str

    # 流式事件
    async def emit_juben_event(event_type, data, metadata) -> Dict

    # 停止管理
    async def check_stop_status(...) -> bool
    async def request_stop(...) -> bool
```

### 3.2 系统提示词

**加载方式** (按优先级):

1. **Python模块** (推荐):
```python
# prompts/my_agent_prompts.py
MY_AGENT_PROMPTS = {
    "my_agent": """
你是专业的短剧策划助手...
"""
}
```

2. **TXT文件**:
```python
# prompts/my_agent_system.txt
你是专业的短剧策划助手...
```

3. **默认提示词**:
```python
self.system_prompt = f"你是{self.agent_name}，专业的竖屏短剧策划助手。"
```

### 3.3 Agent配置

**Temperature配置**:
```python
def get_agent_temperature(self) -> float:
    """
    根据agent类型返回temperature

    - orchestrator: 0.5 (需要创造性但保持逻辑)
    - concierge: 0.4 (稳定理解和回应)
    - knowledge: 0.3 (更准确客观)
    - 创作类: 0.6 (需要更多创造性)
    - 评估类: 0.2 (需要更客观准确)
    """
    if self.agent_name == "juben_orchestrator":
        return 0.5
    elif 'knowledge' in self.agent_name.lower():
        return 0.3
    elif self.agent_name in ["short_drama_creator_agent", "character_profile_agent"]:
        return 0.6
    else:
        return 0.4
```

**Thinking Budget配置**:
```python
def get_thinking_budget(self) -> int:
    """
    创作类agent和hitpoint agent使用512，其他agent使用128
    """
    high_budget_agents = {
        'short_drama_creator_agent',
        'story_outline_evaluation_agent',
        'character_profile_agent',
        'plot_points_workflow_agent',
        'juben_orchestrator',
    }

    if self.agent_name in high_budget_agents:
        return 500
    else:
        return 128
```

---

## 4. Agent开发

### 4.1 Agent模板

```python
"""
Agent模板
复制此模板创建新Agent
"""
from agents.base_juben_agent import BaseJubenAgent
from typing import Dict, Any, AsyncGenerator

class TemplateAgent(BaseJubenAgent):
    """
    Agent描述

    功能: 简要描述Agent功能
    输入: 期望的输入格式
    输出: 返回的数据格式
    """

    def __init__(self):
        """初始化Agent"""
        super().__init__(
            agent_name="template_agent",
            model_provider="zhipu"
        )

        # 自定义配置
        self.custom_config = {}

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理请求的主方法

        Args:
            request_data: 请求数据
            context: 上下文信息

        Yields:
            Dict: 流式事件
        """
        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"

        # 设置会话信息
        self.set_current_session(user_id, session_id)

        # 初始化Token累加器
        await self.initialize_token_accumulator(user_id, session_id)

        try:
            # 1. 发送思考事件
            yield await self.emit_juben_event(
                "thought",
                "开始处理请求..."
            )

            # 2. 处理业务逻辑
            result = await self._process_business_logic(request_data, context)

            # 3. 发送最终答案
            yield await self.emit_juben_event(
                "final_answer",
                result
            )

            # 4. 保存输出
            await self.auto_save_output(result, user_id, session_id)

        except Exception as e:
            self.logger.error(f"处理请求失败: {e}")
            yield await self.emit_juben_event(
                "error",
                f"处理失败: {str(e)}"
            )
        finally:
            # 清理会话信息
            self.clear_current_session()

    async def _process_business_logic(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """处理业务逻辑"""

        # 构建提示词
        user_prompt = self._build_user_prompt(request_data, context)

        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 调用LLM
        response = await self._call_llm(messages)

        return response

    def _build_user_prompt(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> str:
        """构建用户提示词"""

        input_text = request_data.get("input", "")
        prompt = f"用户输入: {input_text}\n"

        # 添加上下文
        if context:
            if context.get("search_results"):
                prompt += f"\n搜索结果: {context['search_results']}\n"
            if context.get("knowledge_results"):
                prompt += f"\n知识库结果: {context['knowledge_results']}\n"

        return prompt
```

### 4.2 Agent开发流程

```
1. 继承BaseJubenAgent
2. 实现process_request方法
3. 配置系统提示词
4. 测试Agent
5. 注册Agent
6. 添加API路由 (可选)
```

### 4.3 完整示例

```python
"""
剧本对比Agent
对比两个剧本的差异
"""
from agents.base_juben_agent import BaseJubenAgent
from typing import Dict, Any, AsyncGenerator
import json

class ScriptComparisonAgent(BaseJubenAgent):
    """剧本对比Agent"""

    def __init__(self):
        super().__init__(
            agent_name="script_comparison_agent",
            model_provider="zhipu"
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理对比请求"""

        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"

        self.set_current_session(user_id, session_id)

        # 获取两个剧本
        script1 = request_data.get("script1", "")
        script2 = request_data.get("script2", "")

        if not script1 or not script2:
            yield await self.emit_juben_event(
                "error",
                "请提供两个剧本进行对比"
            )
            return

        # 发送思考事件
        yield await self.emit_juben_event("thought", "正在分析剧本1...")

        # 分析剧本1
        analysis1 = await self._analyze_script(script1, "剧本1")

        # 检查停止状态
        if await self.check_stop_status(user_id, session_id):
            return

        yield await self.emit_juben_event("thought", "正在分析剧本2...")

        # 分析剧本2
        analysis2 = await self._analyze_script(script2, "剧本2")

        yield await self.emit_juben_event("thought", "正在生成对比报告...")

        # 生成对比报告
        comparison = await self._generate_comparison(analysis1, analysis2)

        # 创建Note
        await self.create_note(
            user_id=user_id,
            session_id=session_id,
            action="script_comparison",
            name=f"comparison_{self.get_next_action_id(user_id, session_id, 'comparison')}",
            context=comparison,
            title="剧本对比报告",
            select=0
        )

        # 发送最终答案
        yield await self.emit_juben_event("final_answer", comparison)

        self.clear_current_session()

    async def _analyze_script(self, script: str, script_name: str) -> Dict[str, Any]:
        """分析单个剧本"""

        prompt = f"""
请分析以下{script_name}，从以下几个方面进行评估：

1. 故事情节 (20分)
2. 人物塑造 (20分)
3. 对话质量 (20分)
4. 节奏控制 (20分)
5. 商业价值 (20分)

剧本内容：
{script}

请以JSON格式返回分析结果。
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self._call_llm(messages)

        # 尝试解析JSON
        try:
            return json.loads(response)
        except:
            return {"raw_analysis": response}

    async def _generate_comparison(
        self,
        analysis1: Dict[str, Any],
        analysis2: Dict[str, Any]
    ) -> str:
        """生成对比报告"""

        prompt = f"""
请根据以下两个剧本的分析结果，生成一份详细的对比报告：

剧本1分析：
{json.dumps(analysis1, ensure_ascii=False, indent=2)}

剧本2分析：
{json.dumps(analysis2, ensure_ascii=False, indent=2)}

对比报告应包括：
1. 各维度得分对比
2. 优缺点分析
3. 改进建议
4. 综合推荐
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages)
```

---

## 5. 高级特性

### 5.1 Agent as Tool

**在Orchestrator中调用其他Agent**:

```python
class OrchestratorAgent(BaseJubenAgent):

    async def _call_sub_agent(
        self,
        agent_name: str,
        request_data: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """调用子Agent作为工具"""

        # 获取Agent实例
        from agents.agent_registry import AgentRegistry
        agent = AgentRegistry.get_agent(agent_name)

        # 调用Agent
        result = {}
        async for event in agent.process_request(request_data):
            if event["event_type"] == "final_answer":
                result = event["data"]

        return result

    async def process_request(self, request_data, context):
        """使用Agent as Tool"""

        # 调用策划Agent
        plan_result = await self._call_sub_agent(
            "short_drama_planner_agent",
            {"input": "策划一个短剧"},
            context["user_id"],
            context["session_id"]
        )

        # 使用策划结果进行下一步
        # ...
```

### 5.2 流式处理

```python
async def process_request(self, request_data, context):
    """流式处理示例"""

    # 流式LLM调用
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": request_data["input"]}
    ]

    full_response = ""

    async for chunk in self._stream_llm(messages):
        full_response += chunk

        # 发送流式事件
        yield await self.emit_juben_event(
            "message",
            chunk
        )

    # 发送完成事件
    yield await self.emit_juben_event(
        "final_answer",
        full_response
    )
```

### 5.3 工具调用

```python
async def process_request(self, request_data, context):
    """使用工具的示例"""

    user_input = request_data["input"]

    # 判断是否需要搜索
    if self._needs_search(user_input):
        # 发送工具调用事件
        yield await self.emit_juben_event(
            "tool_call",
            "正在搜索相关信息...",
            metadata={"tool": "web_search"}
        )

        # 调用搜索工具
        search_results = await self._search_web(
            query=user_input,
            count=5
        )

        # 发送工具结果事件
        yield await self.emit_juben_event(
            "tool_result",
            f"找到{len(search_results)}条相关信息",
            metadata={"count": len(search_results)}
        )

    # 使用搜索结果生成回答
    # ...
```

### 5.4 Notes管理

```python
async def process_request(self, request_data, context):
    """Notes管理示例"""

    user_id = context["user_id"]
    session_id = context["session_id"]

    # 获取用户的Notes
    notes = await self.get_notes(user_id, session_id)

    # 构建包含Notes的上下文
    notes_context = await self.build_notes_context(user_id, session_id)

    # 解析引用
    resolved_input = await self.resolve_note_references(
        request_data["input"],
        user_id,
        session_id
    )

    # 创建新Note
    await self.create_note(
        user_id=user_id,
        session_id=session_id,
        action="my_action",
        name=f"note_{self.get_next_action_id(user_id, session_id, 'my_action')}",
        context="重要内容",
        title="标题",
        select=0  # 等待用户选择
    )
```

---

## 6. 最佳实践

### 6.1 错误处理

```python
async def process_request(self, request_data, context):
    """完善的错误处理"""

    try:
        # 业务逻辑
        result = await self._process_logic(request_data)

        yield await self.emit_juben_event("final_answer", result)

    except ValueError as e:
        # 输入验证错误
        yield await self.emit_juben_event(
            "error",
            f"输入参数错误: {str(e)}"
        )

    except ConnectionError as e:
        # 网络连接错误
        self.logger.error(f"网络错误: {e}")
        yield await self.emit_juben_event(
            "error",
            "网络连接失败，请稍后重试"
        )

    except Exception as e:
        # 未知错误
        self.logger.error(f"未知错误: {e}", exc_info=True)
        yield await self.emit_juben_event(
            "error",
            f"处理失败: {str(e)}"
        )
```

### 6.2 性能优化

```python
class OptimizedAgent(BaseJubenAgent):
    """性能优化示例"""

    async def process_request(self, request_data, context):
        """性能优化的请求处理"""

        # 1. 使用连接池
        redis_client = await self._get_redis_client()

        # 2. 检查缓存
        cache_key = f"agent:{self.agent_name}:{hash(str(request_data))}"
        cached_result = await redis_client.get(cache_key)

        if cached_result:
            yield await self.emit_juben_event("final_answer", cached_result)
            return

        # 3. 处理请求
        result = await self._process_with_cache_check(request_data, context)

        # 4. 缓存结果
        await redis_client.set(cache_key, result, ex=3600)

        yield await self.emit_juben_event("final_answer", result)
```

### 6.3 停止管理

```python
async def process_request(self, request_data, context):
    """支持停止的长时间任务"""

    user_id = context["user_id"]
    session_id = context["session_id"]

    # 步骤1
    await self.check_and_raise_if_stopped(user_id, session_id, "步骤1")
    result1 = await self._step1(request_data)

    # 步骤2
    await self.check_and_raise_if_stopped(user_id, session_id, "步骤2")
    result2 = await self._step2(result1)

    # 步骤3
    await self.check_and_raise_if_stopped(user_id, session_id, "步骤3")
    result3 = await self._step3(result2)

    yield await self.emit_juben_event("final_answer", result3)
```

### 6.4 日志记录

```python
class WellLoggedAgent(BaseJubenAgent):
    """完善的日志记录"""

    async def process_request(self, request_data, context):
        """详细日志记录"""

        user_id = context.get("user_id", "unknown")
        session_id = context.get("session_id", "unknown")

        # 记录请求开始
        self.logger.info(f"[{user_id}/{session_id}] 开始处理请求")

        # 使用性能监控
        with PerformanceContext(
            self.performance_monitor,
            self.agent_name,
            "process_request",
            {"user_id": user_id, "session_id": session_id}
        ) as perf_context:

            try:
                # 业务逻辑
                result = await self._process_logic(request_data)

                # 记录成功
                perf_context.success = True
                self.logger.info(f"[{user_id}/{session_id}] 请求处理成功")

                yield await self.emit_juben_event("final_answer", result)

            except Exception as e:
                # 记录错误
                perf_context.success = False
                perf_context.error_message = str(e)
                self.logger.error(
                    f"[{user_id}/{session_id}] 请求处理失败",
                    exc_info=True
                )
                raise
```

---

## 7. 插件开发

### 7.1 Agent插件

```python
# 创建插件文件: plugins/my_plugin.py

from agents.base_juben_agent import BaseJubenAgent
from typing import Dict, Any, AsyncGenerator

class MyPluginAgent(BaseJubenAgent):
    """插件Agent"""

    def __init__(self):
        super().__init__(
            agent_name="my_plugin_agent",
            model_provider="zhipu"
        )

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理请求"""
        yield await self.emit_juben_event("final_answer", "插件响应")

# 插件元数据
PLUGIN_METADATA = {
    "name": "my_plugin",
    "version": "1.0.0",
    "description": "我的插件",
    "author": "Your Name",
    "agent_class": MyPluginAgent
}
```

### 7.2 注册插件

```python
# 在主程序中注册插件

def load_plugin(plugin_path: str):
    """加载插件"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("plugin", plugin_path)
    plugin_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_module)

    metadata = plugin_module.PLUGIN_METADATA
    agent_class = metadata["agent_class"]

    # 注册Agent
    from agents.agent_registry import AgentRegistry
    AgentRegistry.register_agent(
        metadata["name"],
        agent_class
    )

    return metadata

# 使用
load_plugin("plugins/my_plugin.py")
```

### 7.3 工具插件

```python
# 创建工具插件

from utils.tool_registry import tool

@tool(name="custom_calculator")
async def calculate_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    自定义计算工具

    Args:
        data: 输入数据

    Returns:
        Dict: 计算结果
    """
    result = {
        "metric1": data["value1"] * 2,
        "metric2": data["value2"] + 10
    }
    return result

# 在Agent中使用工具
class AgentWithTool(BaseJubenAgent):

    async def process_request(self, request_data, context):

        # 调用工具
        from utils.tool_registry import tool_registry
        result = await tool_registry.call_tool("custom_calculator", {
            "value1": 5,
            "value2": 10
        })

        yield await self.emit_juben_event("final_answer", str(result))
```

---

## 附录

### A. Agent开发检查清单

- [ ] 继承BaseJubenAgent
- [ ] 实现process_request方法
- [ ] 配置系统提示词
- [ ] 实现错误处理
- [ ] 添加停止检查
- [ ] 实现日志记录
- [ ] 添加性能监控
- [ ] 编写单元测试
- [ ] 更新API路由
- [ ] 更新文档

### B. 相关文档

- [架构设计文档](./ARCHITECTURE.md)
- [API使用指南](./API_GUIDE.md)
- [部署运维手册](./DEPLOYMENT.md)

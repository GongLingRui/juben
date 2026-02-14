# Agent统一输出格式规范

本文档定义了所有40+个Agent必须遵循的统一输出格式规范。

## 📋 目录

- [输出格式标准](#输出格式标准)
- [使用方法](#使用方法)
- [代码示例](#代码示例)
- [最佳实践](#最佳实践)
- [迁移指南](#迁移指南)

---

## 🎯 输出格式标准

### 标准输出结构

所有Agent的输出必须遵循以下结构：

```json
{
  "code": 200,
  "success": true,
  "message": "操作成功",
  "data": {
    // Agent特定的数据内容
  },
  "error": null,
  "metadata": {
    "agent_name": "agent_name",
    "model_provider": "zhipu",
    "timestamp": "2025-01-15T10:30:00",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `code` | int | ✅ | HTTP状态码: 200成功, 400客户端错误, 500服务端错误 |
| `success` | bool | ✅ | 操作是否成功 |
| `message` | str | ✅ | 用户友好的提示消息 |
| `data` | any | ❌ | 主要数据内容（成功时必需） |
| `error` | str | ❌ | 错误详情（失败时必需） |
| `metadata` | object | ✅ | 元数据，包含agent_name, model_provider, timestamp, trace_id |

### 状态码规范

| 代码 | 含义 | 使用场景 |
|------|------|---------|
| 200 | 成功 | 操作正常完成 |
| 400 | 客户端错误 | 参数错误、格式错误等 |
| 404 | 未找到 | 资源不存在 |
| 500 | 服务端错误 | 内部错误、LLM调用失败等 |
| 503 | 服务不可用 | 外部服务超时等 |
| 504 | 网关超时 | 请求超时 |

---

## 🛠️ 使用方法

### 1. 基础方法

所有方法已在 `BaseJubenAgent` 中实现，自动可用：

```python
# 主方法：format_output()
output = self.format_output(
    success=True,
    data={"result": "..."},
    message="操作成功",
    metadata={"key": "value"},
    code=200
)

# 快捷方法：format_success()
output = self.format_success(
    data={"result": "..."},
    message="操作成功"
)

# 快捷方法：format_error()
output = self.format_error(
    error="具体错误信息",
    message="操作失败",
    code=500
)

# 流式事件：format_stream_event()
event = self.format_stream_event(
    event_type="progress",
    data={"percent": 50},
    message="处理中..."
)

# JSON转换：to_json()
json_str = self.to_json(output)
```

### 2. 输出验证

```python
# 验证输出格式
is_valid = await self.validate_output_format(output)
```

### 3. 批量处理

```python
# 批量结果格式化
output = self.format_batch_results(
    results=[result1, result2, ...],
    total=10,
    successful=8,
    failed=2
)
```

---

## 📝 代码示例

### 示例1: 简单Agent输出

```python
class SimpleAgent(BaseJubenAgent):
    async def process_request(self, request_data, context=None):
        try:
            # 执行业务逻辑
            result = await self._do_something(request_data)

            # 返回统一格式
            return self.format_success(
                data={"output": result},
                message="处理成功"
            )

        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            return self.format_error(
                error=str(e),
                message="处理失败，请重试"
            )
```

### 示例2: 流式Agent输出

```python
class StreamingAgent(BaseJubenAgent):
    async def process_request(self, request_data, context=None):
        try:
            # 发送开始事件
            yield self.format_stream_event(
                event_type="start",
                message="开始处理"
            )

            # 发送进度事件
            yield self.format_stream_event(
                event_type="progress",
                data={"step": 1, "total": 3},
                message="步骤1/3"
            )

            # 处理逻辑
            result = await self._process(request_data)

            # 发送完成事件
            yield self.format_stream_event(
                event_type="complete",
                data=result,
                message="处理完成"
            )

        except Exception as e:
            yield self.format_stream_event(
                event_type="error",
                data={"error": str(e)},
                message="处理失败"
            )
```

### 示例3: 剧本生成Agent

```python
class ScriptGeneratorAgent(BaseJubenAgent):
    async def process_request(self, request_data, context=None):
        user_id = request_data.get("user_id", "unknown")
        session_id = request_data.get("session_id", "unknown")

        try:
            # 获取剧本要求
            plot_type = request_data.get("plot_type")
            characters = request_data.get("characters", [])

            # 生成剧本
            script = await self._generate_script(plot_type, characters)

            # 添加剧本记忆
            for char in characters:
                await self.update_character(
                    user_id, session_id,
                    character_name=char["name"],
                    description=char.get("description")
                )

            # 返回结果
            return self.format_success(
                data={
                    "script": script,
                    "script_metadata": {
                        "plot_type": plot_type,
                        "character_count": len(characters),
                        "scene_count": len(script.get("scenes", []))
                    }
                },
                message=f"剧本生成成功，共{len(script.get('scenes', []))}场",
                metadata={
                    "plot_type": plot_type,
                    "word_count": len(str(script))
                }
            )

        except ValueError as e:
            return self.format_error(
                error=str(e),
                message="参数错误",
                code=400
            )
        except Exception as e:
            return self.format_error(
                error=str(e),
                message="剧本生成失败",
                code=500
            )
```

### 示例4: 评估Agent

```python
class EvaluationAgent(BaseJubenAgent):
    async def process_request(self, request_data, context=None):
        try:
            # 获取待评估内容
            content = request_data.get("content")

            # 执行评估
            scores = await self._evaluate_content(content)

            # 计算总分
            total_score = sum(scores.values()) / len(scores)

            # 判断评级
            if total_score >= 90:
                grade = "优秀"
            elif total_score >= 75:
                grade = "良好"
            elif total_score >= 60:
                grade = "及格"
            else:
                grade = "不及格"

            return self.format_success(
                data={
                    "scores": scores,
                    "total_score": round(total_score, 2),
                    "grade": grade,
                    "recommendation": self._get_recommendation(grade)
                },
                message=f"评估完成，评级: {grade}"
            )

        except Exception as e:
            return self.format_error(
                error=str(e),
                message="评估失败"
            )
```

### 示例5: 工作流Agent

```python
class WorkflowAgent(BaseJubenAgent):
    async def process_request(self, request_data, context=None):
        results = []
        successful = 0
        failed = 0

        try:
            # 获取任务列表
            tasks = request_data.get("tasks", [])
            total = len(tasks)

            # 逐个处理
            for task in tasks:
                try:
                    result = await self._process_task(task)
                    results.append({
                        "task_id": task["id"],
                        "success": True,
                        "result": result
                    })
                    successful += 1
                except Exception as e:
                    results.append({
                        "task_id": task["id"],
                        "success": False,
                        "error": str(e)
                    })
                    failed += 1

            # 返回批量结果
            return self.format_batch_results(
                results=results,
                total=total,
                successful=successful,
                failed=failed,
                message=f"工作流处理完成: {successful}/{total}"
            )

        except Exception as e:
            return self.format_error(
                error=str(e),
                message="工作流执行失败"
            )
```

---

## 🎯 最佳实践

### 1. 始终使用统一方法

```python
# ✅ 正确
return self.format_success(data=result, message="成功")

# ❌ 错误
return {"result": result, "status": "ok"}
```

### 2. 提供清晰的message

```python
# ✅ 正确
return self.format_success(
    data=script,
    message="剧本生成成功，共10场戏，包含5个角色"
)

# ❌ 错误
return self.format_success(
    data=script,
    message="成功"  # 太模糊
)
```

### 3. 使用适当的HTTP状态码

```python
# ✅ 正确
if missing_param:
    return self.format_error(
        error="缺少必需参数: plot_type",
        message="参数不完整",
        code=400  # 客户端错误
    )

if llm_timeout:
    return self.format_error(
        error="LLM服务超时",
        message="服务暂时不可用",
        code=504  # 网关超时
    )
```

### 4. 添加有价值的metadata

```python
# ✅ 正确
return self.format_success(
    data=script,
    metadata={
        "word_count": len(script),
        "genre": "悬疑",
        "target_audience": "18-35岁",
        "estimated_duration": "15分钟"
    }
)

# ❌ 错误
return self.format_success(
    data=script,
    metadata={"debug": "some debug info"}  # 无用信息
)
```

### 5. 流式事件遵循类型规范

```python
# 推荐的事件类型
EVENT_TYPES = [
    "start",       # 开始处理
    "thinking",    # 思考过程
    "progress",    # 进度更新
    "step",        # 步骤完成
    "result",      # 最终结果
    "complete",    # 处理完成
    "error",       # 错误发生
    "warning"      # 警告信息
]
```

---

## 🔄 迁移指南

### 如何将现有Agent迁移到新格式

**步骤1: 识别当前输出格式**

```python
# 旧代码
async def process_request(self, request_data, context=None):
    result = await self._generate(request_data)
    return {
        "status": "success",
        "data": result
    }
```

**步骤2: 替换为统一格式**

```python
# 新代码
async def process_request(self, request_data, context=None):
    try:
        result = await self._generate(request_data)
        return self.format_success(
            data=result,
            message="生成完成"
        )
    except Exception as e:
        return self.format_error(
            error=str(e),
            message="生成失败"
        )
```

**步骤3: 添加验证（可选）**

```python
async def process_request(self, request_data, context=None):
    try:
        result = await self._generate(request_data)
        output = self.format_success(data=result, message="完成")

        # 验证格式
        is_valid = await self.validate_output_format(output)
        if not is_valid:
            self.logger.warning("输出格式验证失败")

        return output
    except Exception as e:
        return self.format_error(error=str(e))
```

---

## 📊 常见场景模板

### 场景1: 数据检索

```python
async def process_request(self, request_data, context=None):
    query = request_data.get("query")
    results = await self._search(query)

    return self.format_success(
        data={
            "results": results,
            "count": len(results)
        },
        message=f"找到{len(results)}条结果"
    )
```

### 场景2: 内容创建

```python
async def process_request(self, request_data, context=None):
    content_type = request_data.get("type")
    content = await self._create_content(request_data)

    return self.format_success(
        data={
            "content": content,
            "content_id": content["id"],
            "preview": content["text"][:200]
        },
        message=f"{content_type}创建成功",
        metadata={
            "content_type": content_type,
            "length": len(content.get("text", ""))
        }
    )
```

### 场景3: 批量操作

```python
async def process_request(self, request_data, context=None):
    items = request_data.get("items", [])
    results = []
    successful = 0
    failed = 0

    for item in items:
        try:
            result = await self._process_item(item)
            results.append({"id": item["id"], "success": True, "result": result})
            successful += 1
        except Exception as e:
            results.append({"id": item["id"], "success": False, "error": str(e)})
            failed += 1

    return self.format_batch_results(
        results=results,
        total=len(items),
        successful=successful,
        failed=failed
    )
```

---

## ✅ 检查清单

使用此清单确保Agent符合输出格式规范：

- [ ] 所有返回值使用 `format_success()` 或 `format_error()`
- [ ] 所有事件使用 `format_stream_event()`
- [ ] 成功响应包含有意义的 `data`
- [ ] 失败响应包含明确的 `error`
- [ ] `message` 字段对用户友好
- [ ] 使用正确的HTTP状态码
- [ ] `metadata` 包含有价值的信息
- [ ] 复杂操作有适当的进度反馈

---

## 🔧 工具函数

### 合并多个Agent输出

```python
def merge_agent_outputs(outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    合并多个Agent的输出

    Args:
        outputs: Agent输出列表

    Returns:
        合并后的统一格式输出
    """
    total = len(outputs)
    successful = sum(1 for o in outputs if o.get("success", False))
    failed = total - successful

    # 提取所有data
    all_data = [o.get("data") for o in outputs if o.get("success")]

    return {
        "code": 200 if failed == 0 else 207,  # 207 Multi-Status
        "success": failed == 0,
        "message": f"批量完成: {successful}/{total}",
        "data": {
            "results": all_data,
            "summary": {
                "total": total,
                "successful": successful,
                "failed": failed
            }
        },
        "metadata": {
            "merged": True,
            "source_agents": [o.get("metadata", {}).get("agent_name") for o in outputs]
        }
    }
```

### 提取Agent输出数据

```python
def extract_agent_data(output: Dict[str, Any]) -> Any:
    """
    从Agent输出中提取数据

    Args:
        output: Agent输出

    Returns:
        提取的数据，失败返回None
    """
    if output.get("success") and "data" in output:
        return output["data"]
    return None
```

---

## 📚 相关文档

- [BaseJubenAgent文档](./BASE_AGENT.md)
- [上下文管理指南](./CONTEXT_MANAGEMENT.md)
- [Agent开发规范](./AGENT_DEVELOPMENT.md)

# Agent输出保存机制说明

## 概述

本项目实现了智能的Agent输出自动保存机制，确保所有重要Agent的输出结果都被保存到数据库，同时避免保存工具类Agent的中间结果。

---

## 存储架构

### 三层存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                      内存 (Memory)                           │
│              快速访问，临时存储                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      Redis                                  │
│            缓存层，存储会话和最近的事件                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL (PostgreSQL)                      │
│           持久化存储，保存所有重要数据和事件                  │
└─────────────────────────────────────────────────────────────┘
```

### 数据库表结构

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `stream_events` | 流式事件 | event_type, agent_source, event_data |
| `chat_messages` | 聊天消息 | message_type, content, agent_name |
| `context_state` | 上下文状态 | context_data, context_type, is_active |
| `notes` | 笔记 | action, name, context, metadata |

---

## 自动保存机制

### 工作原理

1. **流式事件捕获**
   - Agent通过 `emit_juben_event()` 发送事件
   - 事件自动保存到 `stream_events` 表

2. **最终结果识别**
   - 系统检测到 `complete`/`result`/`final_output` 等事件类型
   - 自动触发最终结果保存

3. **智能保存决策**
   - 工具类Agent不保存（避免垃圾数据）
   - 核心Agent自动保存

### 触发条件

以下事件类型会触发自动保存：
- `complete`
- `result`
- `final_output`
- `analysis_complete`
- `generation_complete`
- `evaluation_complete`
- `planning_complete`

---

## Agent分类

### 核心Agent（自动保存）

这些Agent的输出会被自动保存到数据库和文件系统：

| Agent类型 | 示例 | 保存位置 |
|----------|------|---------|
| 策划类 | `short_drama_planner_agent` | `drama_planning/` |
| 创作类 | `short_drama_creator_agent` | `drama_creation/` |
| 评估类 | `short_drama_evaluation_agent` | `drama_evaluation/` |
| 分析类 | `story_five_elements_agent` | `story_analysis/` |
| 角色类 | `character_profile_generator_agent` | `character_development/` |
| 情节类 | `plot_points_analyzer_agent` | `plot_development/` |

### 工具类Agent（不保存）

这些Agent的输出不会被保存（作为中间结果）：

| Agent | 用途 |
|-------|------|
| `file_reference_agent` | 文件引用解析 |
| `websearch_agent` | 网络搜索 |
| `knowledge_agent` | 知识库查询 |
| `text_splitter_agent` | 文本分割 |
| `text_truncator_agent` | 文本截断 |

---

## 手动保存

如果需要在特定时刻手动保存输出，可以使用 `auto_save_output` 方法：

```python
# 在Agent的process_request方法中
async def process_request(self, request_data, context=None):
    # ... 处理逻辑 ...

    # 手动保存输出
    await self.auto_save_output(
        output_content=result,
        user_id=user_id,
        session_id=session_id,
        file_type="json",
        metadata={"custom": "metadata"}
    )

    yield result
```

**注意**：手动保存的Agent不会被自动保存机制重复处理。

---

## 配置选项

### 启用/禁用自动保存

在 `BaseJubenAgent` 的 `__init__` 方法中：

```python
self._stream_storage_enabled = True  # 启用流式存储
```

### 修改工具类Agent列表

编辑 `BaseJubenAgent._should_auto_save()` 方法中的 `utility_agents` 列表。

---

## 文件系统存储

输出同时保存到文件系统：

```
juben_outputs/
├── drama_planning/          # 策划输出
│   ├── raw_outputs/         # 原始输出
│   ├── processed_outputs/   # 处理后输出
│   └── metadata/            # 元数据
├── drama_creation/          # 创作输出
├── drama_evaluation/        # 评估输出
└── ...
```

---

## 查询已保存的输出

### 通过API查询

```python
# 获取Agent的输出列表
outputs = await agent.get_agent_outputs(
    output_tag="drama_planning",
    user_id=user_id,
    session_id=session_id,
    limit=10
)

# 获取特定输出内容
content = await agent.get_output_content(
    file_id=file_id,
    output_tag="drama_planning"
)
```

### 直接查询数据库

```sql
-- 查询流式事件
SELECT * FROM stream_events
WHERE user_id = 'user123'
  AND session_id = 'session456'
  AND agent_source = 'short_drama_planner_agent'
ORDER BY created_at DESC;

-- 查询聊天消息
SELECT * FROM chat_messages
WHERE user_id = 'user123'
  AND session_id = 'session456'
ORDER BY created_at DESC;
```

---

## 故障排除

### 输出没有被保存

**可能原因**：
1. Agent没有使用 `emit_juben_event()` 发送最终结果
2. 事件类型不在触发列表中
3. Agent被识别为工具类Agent
4. 存储管理器未正确初始化

**解决方案**：
```python
# 1. 确保发送正确的事件类型
yield await self.emit_juben_event(
    "complete",  # 或 "result", "final_output" 等
    result_data,
    metadata
)

# 2. 检查Agent名称
self.logger.info(f"Agent名称: {self.agent_name}")

# 3. 检查是否被识别为工具类
should_save = self._should_auto_save()
self.logger.info(f"是否应该保存: {should_save}")
```

### 重复保存问题

如果Agent同时使用了手动保存和自动保存，可能会保存两次。解决方法：

1. **移除手动保存**：依赖自动保存机制
2. **修改事件类型**：使用不在触发列表中的事件类型
3. **覆盖判断方法**：在子类中重写 `_should_auto_save()` 返回 `False`

---

## 最佳实践

1. **使用统一的事件类型**
   - 最终结果：`complete`、`result`
   - 进度更新：`progress`、`step`
   - 错误：`error`

2. **包含有意义的元数据**
   ```python
   yield await self.emit_juben_event(
       "complete",
       result_data,
       {
           "scene_count": 10,
           "character_count": 5,
           "word_count": 5000
       }
   )
   ```

3. **避免保存敏感信息**
   - 自动保存会持久化所有发送的数据
   - 确保不包含敏感个人信息

---

## 监控和维护

### 检查存储状态

```python
# 检查Agent的输出
outputs = await agent.get_agent_outputs(
    output_tag="drama_planning",
    limit=50
)

print(f"总输出数: {len(outputs)}")
for output in outputs:
    print(f"- {output['file_id']}: {output['created_at']}")
```

### 清理旧数据

```sql
-- 删除30天前的流式事件
DELETE FROM stream_events
WHERE created_at < NOW() - INTERVAL '30 days';

-- 删除30天前的聊天消息
DELETE FROM chat_messages
WHERE created_at < NOW() - INTERVAL '30 days';
```

---

## 更新日志

- **2025-01-XX**: 实现自动保存机制
  - 修复 `_store_stream_event_async` 方法
  - 添加 `_auto_save_final_result` 方法
  - 添加 `_should_auto_save` 智能判断

---

## 相关文档

- [存储管理器文档](../utils/storage_manager.py)
- [Agent输出存储文档](../utils/agent_output_storage.py)
- [BaseJubenAgent文档](../agents/base_juben_agent.py)

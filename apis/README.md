# APIs 模块结构

本目录包含了所有的 API 路由和相关的数据模式定义，按照功能模块进行了清晰的分类组织。

## 目录结构

```
apis/
├── __init__.py                    # 主模块入口，导出所有路由和数据模式
├── router_registry.py             # 路由注册器，统一管理所有路由
├── core/                          # 核心 API 模块
│   ├── __init__.py
│   ├── api_routes.py             # 主要的 API 路由
│   └── schemas.py                # 数据模式定义
├── drama_analysis/                # 戏剧分析 API 模块
│   ├── __init__.py
│   └── api_routes_drama_analysis.py
├── novel_screening/               # 小说初筛 API 模块
│   ├── __init__.py
│   └── api_routes_novel_screening.py
├── agent_outputs/                 # 智能体输出 API 模块
│   ├── __init__.py
│   └── api_routes_agent_outputs.py
└── enhanced/                      # 增强功能 API 模块
    ├── __init__.py
    └── api_routes_enhanced.py
```

## 模块说明

### 核心模块 (core)
- **api_routes.py**: 包含主要的 API 路由，提供竖屏短剧策划助手的核心功能
- **schemas.py**: 定义所有 API 请求和响应的数据模式

### 戏剧分析模块 (drama_analysis)
- **api_routes_drama_analysis.py**: 提供戏剧分析相关的 API 接口

### 小说初筛模块 (novel_screening)
- **api_routes_novel_screening.py**: 提供小说初筛评估相关的 API 接口

### 智能体输出模块 (agent_outputs)
- **api_routes_agent_outputs.py**: 提供智能体输出存储和管理相关的 API 接口

### 增强功能模块 (enhanced)
- **api_routes_enhanced.py**: 提供增强版功能的 API 接口

## 使用方法

### 导入路由

```python
# 导入所有路由
from apis import (
    core_router,
    drama_analysis_router,
    novel_screening_router,
    agent_outputs_router,
    enhanced_router
)

# 或者使用路由注册器
from apis.router_registry import api_router
```

### 注册路由

```python
from fastapi import FastAPI
from apis.router_registry import api_router

app = FastAPI()
app.include_router(api_router)
```

### 使用数据模式

```python
from apis.core.schemas import (
    ChatRequest,
    ChatResponse,
    BaseResponse,
    ErrorResponse
)
```

## 开发指南

1. **添加新的 API 路由**: 在对应的功能模块目录下创建新的路由文件
2. **定义数据模式**: 在 `core/schemas.py` 中添加新的数据模式
3. **更新路由注册**: 在 `router_registry.py` 中注册新的路由
4. **更新模块导出**: 在对应的 `__init__.py` 文件中导出新的组件

## 注意事项

- 所有路由都使用统一的异常处理和数据验证
- 数据模式定义遵循 Pydantic 规范
- 路由按照功能模块进行分组，便于维护和扩展
- 支持异步处理和流式响应

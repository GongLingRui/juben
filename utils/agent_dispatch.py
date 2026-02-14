"""
统一的Agent调用入口

为所有API路由提供一致的上下文增强注入能力，避免在各处重复判断。
"""
import asyncio
from typing import Any, Dict, Optional, AsyncGenerator
from utils.output_constraints import get_output_constraint_template


async def build_agent_generator(
    agent: Any,
    request_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    构建Agent请求生成器

    - 自动启用增强上下文（如果agent支持）
    - 基于请求数据选择RAG/智能选择开关
    """
    enable_rag = bool(
        request_data.get("enable_knowledge_base")
        or request_data.get("enable_rag")
        or request_data.get("enable_auto_rag")
    )
    enable_smart_select = bool(request_data.get("enable_smart_select"))

    if "output_constraint_template" not in request_data:
        request_data["output_constraint_template"] = get_output_constraint_template()

    # 检查agent是否有process_request_with_enhanced_context方法
    if hasattr(agent, "process_request_with_enhanced_context"):
        result = agent.process_request_with_enhanced_context(
            request_data,
            context,
            enable_rag=enable_rag,
            enable_smart_select=enable_smart_select,
            context_sources=request_data.get("context_sources"),
        )
    else:
        result = agent.process_request(request_data, context)

    # 如果返回的是协程，需要先await
    if asyncio.iscoroutine(result):
        result = await result

    # 处理不同类型的返回值
    if isinstance(result, dict):
        # 返回的是字典，作为单个事件yield
        yield result
    elif isinstance(result, AsyncGenerator):
        # 返回的是异步生成器，迭代并yield每个事件
        async for event in result:
            yield event
    else:
        # 其他类型，尝试作为生成器处理
        try:
            async for event in result:
                yield event
        except TypeError:
            # 如果无法迭代，作为单个事件yield
            yield result

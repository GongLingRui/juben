"""
Meta 优化器 Agent
专门负责优化其他 Agent 的 System Prompt

功能：
1. 分析差评案例，找出问题根源
2. 学习用户修改后的正确范文
3. 生成优化后的 Prompt 版本
4. 提供优化建议和变更日志

代码作者：Claude
创建时间：2026年2月7日
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent


@dataclass
class PromptOptimizationResult:
    """Prompt 优化结果"""
    original_prompt: str
    optimized_prompt: str
    agent_name: str
    version: str

    # 分析结果
    problems_identified: List[str]
    improvement_suggestions: List[str]
    optimization_reasoning: str

    # 示例
    negative_examples_used: int
    positive_examples_used: int

    # 元数据
    timestamp: str
    confidence: float


class MetaOptimizerAgent(BaseJubenAgent):
    """
    Meta 优化器 Agent

    System Prompt: "你是一个 Prompt 工程师专家，专门优化 AI Agent 的 System Prompt。"

    功能：
    1. 分析 Agent 的差评案例，找出 Prompt 的问题
    2. 学习用户修改后的正确输出
    3. 生成优化后的 Prompt 版本
    4. 保持 Prompt 的核心逻辑，只改进表达方式
    """

    def __init__(self):
        super().__init__(
            agent_name="meta_optimizer",
            model_provider="zhipu"
        )

        # 覆盖系统提示词
        self.system_prompt = """你是一个专业的 Prompt 工程师专家，专门优化 AI Agent 的 System Prompt。

## 你的专长

1. **Prompt 分析**：深入理解现有 Prompt 的意图、结构和问题
2. **问题诊断**：从用户反馈中识别 Prompt 的不足之处
3. **优化策略**：应用最佳实践改进 Prompt 的效果
4. **版本管理**：保持优化过程的可追溯性

## 优化原则

1. **保持核心逻辑**：不要改变 Prompt 的主要功能和目标
2. **明确指令**：使用清晰、具体、无歧义的语言
3. **结构化**：合理使用分段、标题和列表
4. **示例驱动**：添加恰当的示例来引导输出
5. **约束明确**：清楚地说明输出格式和要求

## 常见问题及解决方案

| 问题 | 解决方案 |
|------|----------|
| 输出过于生硬 | 添加语气要求，使用更自然的表达方式 |
| 逻辑不通 | 强化逻辑流程要求，添加检查点 |
| 格式混乱 | 明确输出格式模板 |
| 细节不足 | 强调细节描写的重要性 |
| 风格不一致 | 添加风格一致性要求 |

## 优化流程

1. 分析原始 Prompt 的结构和意图
2. 研究差评案例，找出共同问题
3. 研究好评案例，总结成功模式
4. 应用优化策略，生成新版本
5. 编写详细的变更说明

请始终以专业、客观、建设性的态度进行 Prompt 优化。"""

        self.logger.info("Meta 优化器 Agent 初始化完成")

    async def optimize_prompt(
        self,
        agent_name: str,
        current_prompt: str,
        negative_cases: List[Dict[str, Any]],
        positive_cases: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> PromptOptimizationResult:
        """
        优化 Prompt

        Args:
            agent_name: Agent 名称
            current_prompt: 当前 System Prompt
            negative_cases: 差评案例列表 [{"user_input": "...", "ai_output": "...", "feedback": "..."}]
            positive_cases: 好评案例/用户修改后的正确范文
            context: 额外上下文

        Returns:
            PromptOptimizationResult: 优化结果
        """
        try:
            self.logger.info(f"🔧 开始优化 Prompt (agent: {agent_name})")

            # 构建优化请求
            optimization_request = self._build_optimization_request(
                agent_name, current_prompt, negative_cases, positive_cases, context
            )

            # 调用 LLM 进行优化
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": optimization_request}
            ]

            optimized_response = await self._call_llm(messages)

            # 解析响应
            result = self._parse_optimization_response(
                agent_name, current_prompt, optimized_response,
                len(negative_cases), len(positive_cases)
            )

            self.logger.info(f"✅ Prompt 优化完成 (agent: {agent_name}, version: {result.version})")
            return result

        except Exception as e:
            self.logger.error(f"Prompt 优化失败: {e}")
            # 返回原始结果
            return PromptOptimizationResult(
                original_prompt=current_prompt,
                optimized_prompt=current_prompt,
                agent_name=agent_name,
                version="v1.0.0-failed",
                problems_identified=[],
                improvement_suggestions=[],
                optimization_reasoning=f"优化失败: {str(e)}",
                negative_examples_used=len(negative_cases),
                positive_examples_used=len(positive_cases),
                timestamp=datetime.now().isoformat(),
                confidence=0.0
            )

    def _build_optimization_request(
        self,
        agent_name: str,
        current_prompt: str,
        negative_cases: List[Dict[str, Any]],
        positive_cases: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建优化请求"""
        request = f"""# Prompt 优化请求

## 目标 Agent
- Agent 名称: {agent_name}
- 优化目标: 根据用户反馈优化 System Prompt

## 当前 System Prompt
```
{current_prompt}
```

## 差评案例分析（{len(negative_cases)} 个案例）
"""

        # 添加差评案例
        for i, case in enumerate(negative_cases[:5], 1):
            request += f"""
### 案例 {i}
**用户输入**: {case.get('user_input', '')[:200]}

**AI 输出**: {case.get('ai_output', '')[:300]}

**用户反馈**: {case.get('feedback', '')[:200]}

**问题点**: {case.get('problem', '待分析')}
"""

        request += f"""

## 好评案例/正确范文（{len(positive_cases)} 个案例）
"""

        # 添加好评案例
        for i, case in enumerate(positive_cases[:5], 1):
            request += f"""
### 案例 {i}
**用户输入**: {case.get('user_input', '')[:200]}

**理想输出**: {case.get('ai_output', '')[:300]}

**成功原因**: {case.get('success_reason', '待分析')}
"""

        if context:
            request += f"""

## 额外上下文
{str(context)[:500]}
"""

        request += """

## 输出要求

请以 JSON 格式返回优化结果：

```json
{
  "problems_identified": ["问题1", "问题2", "问题3"],
  "improvement_suggestions": ["建议1", "建议2"],
  "optimization_reasoning": "详细的优化思路说明...",
  "optimized_prompt": "优化后的完整 System Prompt..."
}
```

**注意**：
1. optimized_prompt 必须是完整的、可直接使用的 System Prompt
2. 保持原 Prompt 的核心功能和结构
3. 针对识别出的问题进行有针对性的改进
4. 优化后的 Prompt 应该更加清晰、具体、有效
"""

        return request

    def _parse_optimization_response(
        self,
        agent_name: str,
        original_prompt: str,
        response: str,
        negative_count: int,
        positive_count: int
    ) -> PromptOptimizationResult:
        """解析优化响应"""
        try:
            import json
            import re

            # 提取 JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response

            data = json.loads(json_str)

            # 生成新版本号
            version = self._generate_next_version()

            return PromptOptimizationResult(
                original_prompt=original_prompt,
                optimized_prompt=data.get('optimized_prompt', original_prompt),
                agent_name=agent_name,
                version=version,
                problems_identified=data.get('problems_identified', []),
                improvement_suggestions=data.get('improvement_suggestions', []),
                optimization_reasoning=data.get('optimization_reasoning', ''),
                negative_examples_used=negative_count,
                positive_examples_used=positive_count,
                timestamp=datetime.now().isoformat(),
                confidence=0.8
            )

        except Exception as e:
            self.logger.warning(f"解析优化响应失败: {e}，使用原始响应")
            # 返回基本结果
            return PromptOptimizationResult(
                original_prompt=original_prompt,
                optimized_prompt=response if len(response) < 5000 else original_prompt,
                agent_name=agent_name,
                version=self._generate_next_version(),
                problems_identified=["解析响应失败，可能需要人工审核"],
                improvement_suggestions=[],
                optimization_reasoning=response[:500],
                negative_examples_used=negative_count,
                positive_examples_used=positive_count,
                timestamp=datetime.now().isoformat(),
                confidence=0.3
            )

    def _generate_next_version(self) -> str:
        """生成下一个版本号"""
        import time
        return f"v1.{int(time.time() % 1000)}"

    async def analyze_feedback(
        self,
        feedbacks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析反馈数据

        Args:
            feedbacks: 反馈列表

        Returns:
            Dict: 分析结果
        """
        try:
            # 构建分析请求
            analysis_request = f"""# 反馈分析请求

请分析以下 {len(feedbacks)} 条用户反馈数据，总结主要问题和改进方向。

## 反馈数据
"""
            for i, fb in enumerate(feedbacks[:10], 1):
                analysis_request += f"""
### 反馈 {i}
- 用户评分: {fb.get('user_rating', 'N/A')}
- AI 输出: {fb.get('ai_output', '')[:200]}...
- 用户修改: {fb.get('user_edit_text', '无')[:200]}...
- 问题类型: {fb.get('problem_type', '未知')}
"""

            analysis_request += """

## 输出要求

请以 JSON 格式返回分析结果：

```json
{
  "common_problems": ["问题1", "问题2"],
  "problem_categories": ["类别1", "类别2"],
  "improvement_priority": "优先级最高的改进方向",
  "recommended_changes": ["建议修改1", "建议修改2"]
}
```
"""

            messages = [
                {"role": "system", "content": "你是专业的 AI 产品分析专家，擅长从用户反馈中提炼问题和改进方向。"},
                {"role": "user", "content": analysis_request}
            ]

            response = await self._call_llm(messages)

            # 解析 JSON 响应
            import json
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            try:
                return json.loads(json_str)
            except:
                return {
                    "common_problems": ["无法自动解析，需要人工分析"],
                    "analysis_raw": response[:1000]
                }

        except Exception as e:
            self.logger.error(f"分析反馈失败: {e}")
            return {}

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理优化请求（兼容基类接口）

        Args:
            request_data: 请求数据
                - action: "optimize" 或 "analyze"
                - agent_name: Agent 名称
                - current_prompt: 当前 Prompt（优化时需要）
                - negative_cases: 差评案例
                - positive_cases: 好评案例
            context: 上下文

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            action = request_data.get("action", "optimize")
            agent_name = request_data.get("agent_name", "unknown")

            yield await self._emit_event("system", f"🔧 Meta 优化器启动 (action: {action}, agent: {agent_name})")

            if action == "optimize":
                # 执行优化
                result = await self.optimize_prompt(
                    agent_name=agent_name,
                    current_prompt=request_data.get("current_prompt", ""),
                    negative_cases=request_data.get("negative_cases", []),
                    positive_cases=request_data.get("positive_cases", []),
                    context=context
                )

                yield await self._emit_event("content", f"""# Prompt 优化完成

## 优化版本
**版本**: {result.version}
**置信度**: {result.confidence:.2f}

## 识别的问题
{chr(10).join(f'- {p}' for p in result.problems_identified)}

## 改进建议
{chr(10).join(f'- {s}' for s in result.improvement_suggestions)}

## 优化思路
{result.optimization_reasoning}

## 优化后的 Prompt
```
{result.optimized_prompt}
```
""")

                yield await self._emit_event("metadata", f'{{"version": "{result.version}", "confidence": {result.confidence}}}')

            elif action == "analyze":
                # 执行分析
                feedbacks = request_data.get("feedbacks", [])
                analysis = await self.analyze_feedback(feedbacks)

                yield await self._emit_event("content", f"""# 反馈分析完成

## 常见问题
{chr(10).join(f'- {p}' for p in analysis.get("common_problems", []))}

## 问题类别
{chr(10).join(f'- {c}' for c in analysis.get("problem_categories", []))}

## 改进优先级
**{analysis.get("improvement_priority", "未知")}**

## 推荐修改
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(analysis.get("recommended_changes", [])))}
""")

            yield await self._emit_event("system", "✅ Meta 优化器处理完成")

        except Exception as e:
            self.logger.error(f"处理请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")

    async def _emit_event(self, event_type: str, content: str) -> Dict[str, Any]:
        """构建事件"""
        return {
            "type": event_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }


# ==================== 全局实例 ====================

_meta_optimizer_agent: Optional[MetaOptimizerAgent] = None


def get_meta_optimizer_agent() -> MetaOptimizerAgent:
    """获取 Meta 优化器单例"""
    global _meta_optimizer_agent
    if _meta_optimizer_agent is None:
        _meta_optimizer_agent = MetaOptimizerAgent()
    return _meta_optimizer_agent

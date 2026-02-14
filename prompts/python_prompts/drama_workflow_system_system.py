"""
drama_workflow_system 系统提示词
自动从txt文件转换生成
"""

DRAMA_WORKFLOW_SYSTEM_SYSTEM_PROMPT = """你是一个专业的情节点戏剧功能分析工作流编排器，负责协调整个分析流程。

## 工作流步骤
1. 文本预处理：截断和分割长文本
2. 并行分析：对文本片段进行情节点分析
3. 结果整合：合并和优化分析结果
4. 报告生成：生成最终的综合分析报告

## 编排原则
- 确保每个步骤的输入输出正确传递
- 管理智能体间的上下文隔离
- 优化并行处理性能
- 保证分析结果的完整性和准确性

## 工作流目标
通过模块化的智能体协作，实现对长文本的情节点和戏剧功能分析，提供专业的编剧视角洞察。"""

# 结构化提示词配置
DRAMA_WORKFLOW_SYSTEM_PROMPT_CONFIG = {
    "agent_name": "drama_workflow_system",
    "role": "",
    "profile": {},
    "background": """""",
    "goals": [],
    "constraints": [],
    "skills": [],
    "workflows": [],
    "output_format": """""",
    "definitions": {},
    "version": "2.0",
    "created_by": "prompt_converter",
    "source_file": "drama_workflow_system_system.txt"
}

def get_drama_workflow_system_system_prompt() -> str:
    """获取drama_workflow_system系统提示词"""
    return DRAMA_WORKFLOW_SYSTEM_SYSTEM_PROMPT

def get_drama_workflow_system_prompt_config() -> dict:
    """获取drama_workflow_system提示词配置"""
    return DRAMA_WORKFLOW_SYSTEM_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "DRAMA_WORKFLOW_SYSTEM_SYSTEM_PROMPT",
    "DRAMA_WORKFLOW_SYSTEM_PROMPT_CONFIG",
    "get_drama_workflow_system_system_prompt",
    "get_drama_workflow_system_prompt_config"
]

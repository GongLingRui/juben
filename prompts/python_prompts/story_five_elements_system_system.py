"""
story_five_elements_system 系统提示词
自动从txt文件转换生成
"""

STORY_FIVE_ELEMENTS_SYSTEM_SYSTEM_PROMPT = """你是故事五元素分析智能体，专门用于分析故事的五個核心元素。

## 核心功能
1. **文本处理**: 截断和分割长文本，确保分析质量
2. **批处理机制**: 高效处理大量文本片段
3. **五个专业分析维度**:
   - 题材类型与创意提炼
   - 故事梗概生成
   - 人物小传生成
   - 人物关系分析
   - 大情节点分析
4. **思维导图生成**: 可视化展示情节点结构
5. **Agent as Tool机制**: 调用专业子智能体进行深度分析

## 分析流程
1. 接收用户输入（文本或文件）
2. 文本截断和分割处理
3. 批处理生成初步总结
4. 整合分析结果
5. 调用五个子智能体进行专业分析
6. 生成思维导图
7. 整理并输出最终结果

## 输出格式
最终输出包含六个部分：
- 题材类型与创意提炼
- 故事梗概
- 人物小传
- 人物关系
- 大情节点
- 思维导图

## 技术特点
- 支持Agent as Tool机制，子智能体间相互调用
- 上下文隔离，避免污染
- 流式输出，实时反馈处理进度
- 模块化设计，易于扩展和维护

请始终保持专业、准确、高效的分析能力。"""

# 结构化提示词配置
STORY_FIVE_ELEMENTS_SYSTEM_PROMPT_CONFIG = {
    "agent_name": "story_five_elements_system",
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
    "source_file": "story_five_elements_system_system.txt"
}

def get_story_five_elements_system_system_prompt() -> str:
    """获取story_five_elements_system系统提示词"""
    return STORY_FIVE_ELEMENTS_SYSTEM_SYSTEM_PROMPT

def get_story_five_elements_system_prompt_config() -> dict:
    """获取story_five_elements_system提示词配置"""
    return STORY_FIVE_ELEMENTS_SYSTEM_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "STORY_FIVE_ELEMENTS_SYSTEM_SYSTEM_PROMPT",
    "STORY_FIVE_ELEMENTS_SYSTEM_PROMPT_CONFIG",
    "get_story_five_elements_system_system_prompt",
    "get_story_five_elements_system_prompt_config"
]

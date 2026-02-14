"""
result_integrator_system 系统提示词
自动从txt文件转换生成
"""

RESULT_INTEGRATOR_SYSTEM_SYSTEM_PROMPT = """你是一个专业的结果整合工具，负责将多个情节点分析结果整合成综合报告。

## 整合原则
1. 去重：移除重复或相似的情节点
2. 分类：按照戏剧功能对情节点进行分类
3. 排序：按照在故事中的出现顺序排列
4. 总结：提供整体的戏剧结构分析

## 输出格式
- 保持原有的【情节点】和【戏剧功能】格式
- 在开头提供整体分析总结
- 在结尾提供戏剧结构评价

## 整合要求
- 确保每个情节点都是独特的
- 保持分析的深度和专业性
- 提供清晰的戏剧结构洞察"""

# 结构化提示词配置
RESULT_INTEGRATOR_SYSTEM_PROMPT_CONFIG = {
    "agent_name": "result_integrator_system",
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
    "source_file": "result_integrator_system_system.txt"
}

def get_result_integrator_system_system_prompt() -> str:
    """获取result_integrator_system系统提示词"""
    return RESULT_INTEGRATOR_SYSTEM_SYSTEM_PROMPT

def get_result_integrator_system_prompt_config() -> dict:
    """获取result_integrator_system提示词配置"""
    return RESULT_INTEGRATOR_SYSTEM_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "RESULT_INTEGRATOR_SYSTEM_SYSTEM_PROMPT",
    "RESULT_INTEGRATOR_SYSTEM_PROMPT_CONFIG",
    "get_result_integrator_system_system_prompt",
    "get_result_integrator_system_prompt_config"
]

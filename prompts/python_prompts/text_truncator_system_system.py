"""
text_truncator_system 系统提示词
自动从txt文件转换生成
"""

TEXT_TRUNCATOR_SYSTEM_SYSTEM_PROMPT = """你是一个专业的文本截断工具。

## 功能说明
接收文件路径或字符串以及最大长度，返回截断后的文本内容。

## 处理原则
1. 尽量在句号处断开，保持语义完整性
2. 避免在单词或句子中间截断
3. 保持文本的原始格式和结构
4. 如果文本长度小于最大长度，直接返回原文本

## 输出格式
返回截断后的文本内容，保持原有格式。"""

# 结构化提示词配置
TEXT_TRUNCATOR_SYSTEM_PROMPT_CONFIG = {
    "agent_name": "text_truncator_system",
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
    "source_file": "text_truncator_system_system.txt"
}

def get_text_truncator_system_system_prompt() -> str:
    """获取text_truncator_system系统提示词"""
    return TEXT_TRUNCATOR_SYSTEM_SYSTEM_PROMPT

def get_text_truncator_system_prompt_config() -> dict:
    """获取text_truncator_system提示词配置"""
    return TEXT_TRUNCATOR_SYSTEM_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "TEXT_TRUNCATOR_SYSTEM_SYSTEM_PROMPT",
    "TEXT_TRUNCATOR_SYSTEM_PROMPT_CONFIG",
    "get_text_truncator_system_system_prompt",
    "get_text_truncator_system_prompt_config"
]

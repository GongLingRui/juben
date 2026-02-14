"""
text_splitter_system 系统提示词
自动从txt文件转换生成
"""

TEXT_SPLITTER_SYSTEM_SYSTEM_PROMPT = """你是一个专业的文本分割工具。

## 功能说明
将文本分割成指定大小的块，便于后续处理。

## 分割原则
1. 尽量在句号处断开，保持语义完整性
2. 避免在单词或句子中间截断
3. 保持文本的原始格式和结构
4. 确保每个块的大小不超过指定限制

## 输出格式
返回分割后的文本片段数组。"""

# 结构化提示词配置
TEXT_SPLITTER_SYSTEM_PROMPT_CONFIG = {
    "agent_name": "text_splitter_system",
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
    "source_file": "text_splitter_system_system.txt"
}

def get_text_splitter_system_system_prompt() -> str:
    """获取text_splitter_system系统提示词"""
    return TEXT_SPLITTER_SYSTEM_SYSTEM_PROMPT

def get_text_splitter_system_prompt_config() -> dict:
    """获取text_splitter_system提示词配置"""
    return TEXT_SPLITTER_SYSTEM_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "TEXT_SPLITTER_SYSTEM_SYSTEM_PROMPT",
    "TEXT_SPLITTER_SYSTEM_PROMPT_CONFIG",
    "get_text_splitter_system_system_prompt",
    "get_text_splitter_system_prompt_config"
]

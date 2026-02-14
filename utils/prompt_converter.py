"""
系统提示词转换工具
将txt格式的系统提示词转换为python文件格式
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List
import logging

class PromptConverter:
    """系统提示词转换器"""
    
    def __init__(self, prompts_dir: str = None):
        """
        初始化转换器
        
        Args:
            prompts_dir: 提示词目录路径
        """
        self.logger = logging.getLogger(__name__)
        
        if prompts_dir is None:
            # 默认使用项目中的prompts目录
            current_dir = Path(__file__).parent.parent
            prompts_dir = current_dir / "prompts"
        
        self.prompts_dir = Path(prompts_dir)
        self.output_dir = self.prompts_dir / "python_prompts"
        
        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"提示词转换器初始化完成，输入目录: {self.prompts_dir}")
        self.logger.info(f"输出目录: {self.output_dir}")
    
    def convert_all_txt_to_python(self) -> Dict[str, bool]:
        """
        转换所有txt提示词文件为python文件
        
        Returns:
            Dict[str, bool]: 转换结果，键为文件名，值为是否成功
        """
        results = {}
        
        # 查找所有txt文件
        txt_files = list(self.prompts_dir.glob("*.txt"))
        
        if not txt_files:
            self.logger.warning("未找到任何txt提示词文件")
            return results
        
        self.logger.info(f"找到{len(txt_files)}个txt提示词文件")
        
        for txt_file in txt_files:
            try:
                success = self.convert_txt_to_python(txt_file)
                results[txt_file.name] = success
                if success:
                    self.logger.info(f"✅ 转换成功: {txt_file.name}")
                else:
                    self.logger.error(f"❌ 转换失败: {txt_file.name}")
            except Exception as e:
                self.logger.error(f"❌ 转换异常 {txt_file.name}: {e}")
                results[txt_file.name] = False
        
        return results
    
    def convert_txt_to_python(self, txt_file: Path) -> bool:
        """
        将单个txt文件转换为python文件
        
        Args:
            txt_file: txt文件路径
            
        Returns:
            bool: 转换是否成功
        """
        try:
            # 读取txt文件内容
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 生成python文件名
            python_filename = txt_file.stem + "_system.py"
            python_file = self.output_dir / python_filename
            
            # 解析提示词内容
            parsed_prompt = self._parse_prompt_content(content, txt_file.stem)
            
            # 生成python代码
            python_code = self._generate_python_code(parsed_prompt, txt_file.stem)
            
            # 写入python文件
            with open(python_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            
            self.logger.info(f"生成python文件: {python_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"转换文件失败 {txt_file}: {e}")
            return False
    
    def _parse_prompt_content(self, content: str, agent_name: str) -> Dict[str, Any]:
        """
        解析提示词内容，提取结构化信息
        
        Args:
            content: 提示词内容
            agent_name: Agent名称
            
        Returns:
            Dict[str, Any]: 解析后的结构化信息
        """
        parsed = {
            "agent_name": agent_name,
            "role": "",
            "profile": {},
            "background": "",
            "goals": [],
            "constraints": [],
            "skills": [],
            "workflows": [],
            "output_format": "",
            "definitions": {},
            "full_content": content
        }
        
        # 提取角色信息
        role_match = re.search(r'## Role:\s*(.+)', content)
        if role_match:
            parsed["role"] = role_match.group(1).strip()
        
        # 提取Profile信息
        profile_section = self._extract_section(content, "## Profile:")
        if profile_section:
            parsed["profile"] = self._parse_profile_section(profile_section)
        
        # 提取Background信息
        background_section = self._extract_section(content, "## Background:")
        if background_section:
            parsed["background"] = background_section.strip()
        
        # 提取Goals信息
        goals_section = self._extract_section(content, "## Goals:")
        if goals_section:
            parsed["goals"] = self._parse_list_section(goals_section)
        
        # 提取Constraints信息
        constraints_section = self._extract_section(content, "## Constrains?:")
        if constraints_section:
            parsed["constraints"] = self._parse_list_section(constraints_section)
        
        # 提取Skills信息
        skills_section = self._extract_section(content, "## Skills:")
        if skills_section:
            parsed["skills"] = self._parse_list_section(skills_section)
        
        # 提取Workflows信息
        workflows_section = self._extract_section(content, "## Workflows?:")
        if workflows_section:
            parsed["workflows"] = self._parse_list_section(workflows_section)
        
        # 提取OutputFormat信息
        output_format_section = self._extract_section(content, "## OutputFormat:")
        if output_format_section:
            parsed["output_format"] = output_format_section.strip()
        
        # 提取Definitions信息
        definitions = self._extract_definitions(content)
        parsed["definitions"] = definitions
        
        return parsed
    
    def _extract_section(self, content: str, section_header: str) -> str:
        """提取指定章节的内容"""
        pattern = rf'{re.escape(section_header)}\s*\n(.*?)(?=\n## |\n【|$)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _extract_definitions(self, content: str) -> Dict[str, str]:
        """提取定义信息"""
        definitions = {}
        
        # 查找所有Definition模式
        definition_pattern = r'## Definition(\d*):\s*\n(.*?)(?=\n## |$)'
        matches = re.finditer(definition_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            key = f"definition{match.group(1) if match.group(1) else ''}"
            value = match.group(2).strip()
            definitions[key] = value
        
        return definitions
    
    def _parse_profile_section(self, profile_content: str) -> Dict[str, str]:
        """解析Profile章节"""
        profile = {}
        lines = profile_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                # 解析键值对
                parts = line[2:].split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    profile[key] = value
        
        return profile
    
    def _parse_list_section(self, section_content: str) -> List[str]:
        """解析列表章节"""
        items = []
        lines = section_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                items.append(line[2:].strip())
            elif line and not line.startswith('#'):
                items.append(line)
        
        return items
    
    def _generate_python_code(self, parsed_prompt: Dict[str, Any], agent_name: str) -> str:
        """生成python代码"""
        
        # 生成变量名
        var_name = f"{agent_name.upper()}_SYSTEM_PROMPT"
        
        # 构建系统提示词内容
        system_prompt_content = self._build_system_prompt_string(parsed_prompt)
        
        python_code = f'''"""
{parsed_prompt["role"] or agent_name} 系统提示词
自动从txt文件转换生成
"""

{var_name} = """{system_prompt_content}"""

# 结构化提示词配置
{agent_name.upper()}_PROMPT_CONFIG = {{
    "agent_name": "{parsed_prompt["agent_name"]}",
    "role": "{parsed_prompt["role"]}",
    "profile": {self._format_dict(parsed_prompt["profile"])},
    "background": """{parsed_prompt["background"]}""",
    "goals": {self._format_list(parsed_prompt["goals"])},
    "constraints": {self._format_list(parsed_prompt["constraints"])},
    "skills": {self._format_list(parsed_prompt["skills"])},
    "workflows": {self._format_list(parsed_prompt["workflows"])},
    "output_format": """{parsed_prompt["output_format"]}""",
    "definitions": {self._format_dict(parsed_prompt["definitions"])},
    "version": "2.0",
    "created_by": "prompt_converter",
    "source_file": "{agent_name}_system.txt"
}}

def get_{agent_name}_system_prompt() -> str:
    """获取{agent_name}系统提示词"""
    return {var_name}

def get_{agent_name}_prompt_config() -> dict:
    """获取{agent_name}提示词配置"""
    return {agent_name.upper()}_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "{var_name}",
    "{agent_name.upper()}_PROMPT_CONFIG",
    "get_{agent_name}_system_prompt",
    "get_{agent_name}_prompt_config"
]
'''
        
        return python_code
    
    def _build_system_prompt_string(self, parsed_prompt: Dict[str, Any]) -> str:
        """构建系统提示词字符串"""
        content = parsed_prompt["full_content"]
        
        # 转义三重引号
        content = content.replace('"""', '\\"""')
        
        return content
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """格式化字典为python代码"""
        if not data:
            return "{}"
        
        formatted_items = []
        for key, value in data.items():
            escaped_value = str(value).replace('"', '\\"').replace('\n', '\\n')
            formatted_items.append(f'    "{key}": "{escaped_value}"')
        
        return "{\n" + ",\n".join(formatted_items) + "\n}"
    
    def _format_list(self, data: List[str]) -> str:
        """格式化列表为python代码"""
        if not data:
            return "[]"
        
        formatted_items = []
        for item in data:
            escaped_item = str(item).replace('"', '\\"').replace('\n', '\\n')
            formatted_items.append(f'    "{escaped_item}"')
        
        return "[\n" + ",\n".join(formatted_items) + "\n]"
    
    def create_prompts_index(self) -> bool:
        """创建提示词索引文件"""
        try:
            index_file = self.output_dir / "__init__.py"
            
            # 查找所有生成的python文件
            python_files = list(self.output_dir.glob("*_system.py"))
            
            index_content = '''"""
系统提示词模块索引
自动生成的文件，包含所有转换后的系统提示词
"""

'''
            
            # 为每个文件添加导入
            for py_file in python_files:
                module_name = py_file.stem
                index_content += f"from .{module_name} import *\n"
            
            index_content += f'''
# 所有可用的系统提示词
AVAILABLE_PROMPTS = {[f.stem for f in python_files]}

def get_all_prompts():
    """获取所有可用的提示词模块"""
    return AVAILABLE_PROMPTS

__all__ = ["get_all_prompts", "AVAILABLE_PROMPTS"] + AVAILABLE_PROMPTS
'''
            
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            self.logger.info(f"创建提示词索引文件: {index_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建索引文件失败: {e}")
            return False


def main():
    """主函数"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建转换器
    converter = PromptConverter()
    
    # 执行转换
    logger.info("开始转换系统提示词文件...")
    results = converter.convert_all_txt_to_python()

    # 显示结果
    logger.info("转换结果:")
    success_count = 0
    for filename, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        logger.info(f"  {filename}: {status}")
        if success:
            success_count += 1

    logger.info(f"总计: {success_count}/{len(results)} 个文件转换成功")

    # 创建索引文件
    if success_count > 0:
        logger.info("创建提示词索引文件...")
        index_success = converter.create_prompts_index()
        if index_success:
            logger.info("✅ 索引文件创建成功")
        else:
            logger.error("❌ 索引文件创建失败")
    
    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

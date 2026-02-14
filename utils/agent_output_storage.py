"""
Agent输出内容存储管理器
支持按标签分类保存各个agent的输出内容到文件系统

标签分类：
- 短剧策划 (drama_planning)
- 短剧创作 (drama_creation) 
- 短剧评估 (drama_evaluation)
- 小说初筛评估 (novel_screening)
- 故事分析 (story_analysis)
- 角色开发 (character_development)
- 情节开发 (plot_development)
- 剧集分析 (series_analysis)
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import uuid
import hashlib

from .logger import JubenLogger
from .agent_naming import canonical_agent_id
from .storage_manager import get_storage


class AgentOutputStorage:
    """Agent输出内容存储管理器"""
    
    def __init__(self, base_storage_path: str = "juben_outputs"):
        """初始化存储管理器"""
        self.logger = JubenLogger("agent_output_storage")
        self.base_storage_path = Path(base_storage_path)
        self.storage_manager = get_storage()
        
        # 标签分类配置
        self.output_tags = {
            "drama_planning": {
                "name": "短剧策划",
                "description": "短剧策划相关的输出内容",
                "agents": ["juben_orchestrator", "juben_concierge", "short_drama_planner_agent", "short_drama_planner"]
            },
            "drama_creation": {
                "name": "短剧创作", 
                "description": "短剧创作相关的输出内容",
                "agents": ["short_drama_creator_agent", "short_drama_creator", "story_outline_evaluation_agent", "character_profile_agent"]
            },
            "drama_evaluation": {
                "name": "短剧评估",
                "description": "短剧评估相关的输出内容", 
                "agents": ["short_drama_evaluation_agent", "short_drama_evaluation", "script_evaluation_agent", "drama_analysis_agent"]
            },
            "novel_screening": {
                "name": "小说初筛评估",
                "description": "小说初筛评估相关的输出内容",
                "agents": ["novel_screening_evaluation_agent", "ip_evaluation_agent", "ip_evaluation"]
            },
            "story_analysis": {
                "name": "故事分析",
                "description": "故事分析相关的输出内容",
                "agents": ["story_five_elements_agent", "story_five_elements", "story_outline_evaluation_agent", "story_evaluation_agent"]
            },
            "character_development": {
                "name": "角色开发",
                "description": "角色开发相关的输出内容",
                "agents": ["character_profile_agent", "character_relationship_agent", "character_profile_generator_agent"]
            },
            "plot_development": {
                "name": "情节开发", 
                "description": "情节开发相关的输出内容",
                "agents": ["plot_points_agent", "major_plot_points_agent", "detailed_plot_points_agent", "plot_points_workflow"]
            },
            "series_analysis": {
                "name": "剧集分析",
                "description": "剧集分析相关的输出内容",
                "agents": ["series_analysis_agent", "series_info_agent", "series_name_extractor_agent"]
            }
        }
        
        # 文件类型配置
        self.file_types = {
            "json": {"extension": ".json", "content_type": "application/json"},
            "markdown": {"extension": ".md", "content_type": "text/markdown"},
            "text": {"extension": ".txt", "content_type": "text/plain"},
            "html": {"extension": ".html", "content_type": "text/html"},
            "xml": {"extension": ".xml", "content_type": "application/xml"}
        }
        
        # 初始化存储目录
        self._init_storage_directories()
        
        self.logger.info("📁 Agent输出存储管理器初始化完成")
        self.logger.info(f"📂 基础存储路径: {self.base_storage_path}")
        self.logger.info(f"🏷️ 支持的标签: {list(self.output_tags.keys())}")
    
    def _init_storage_directories(self):
        """初始化存储目录结构"""
        try:
            # 创建基础目录
            self.base_storage_path.mkdir(parents=True, exist_ok=True)
            
            # 为每个标签创建目录
            for tag in self.output_tags.keys():
                tag_dir = self.base_storage_path / tag
                tag_dir.mkdir(parents=True, exist_ok=True)
                
                # 创建子目录
                subdirs = ["raw_outputs", "processed_outputs", "metadata", "exports"]
                for subdir in subdirs:
                    (tag_dir / subdir).mkdir(exist_ok=True)
            
            # 创建通用目录
            common_dirs = ["temp", "backup", "logs", "exports"]
            for dir_name in common_dirs:
                (self.base_storage_path / dir_name).mkdir(exist_ok=True)
            
            self.logger.info("📁 存储目录结构初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化存储目录失败: {e}")
            raise
    
    async def save_agent_output(
        self,
        agent_name: str,
        output_content: Union[str, Dict[str, Any]],
        output_tag: str,
        user_id: str,
        session_id: str,
        file_type: str = "json",
        metadata: Optional[Dict[str, Any]] = None,
        auto_export: bool = True
    ) -> Dict[str, Any]:
        """
        保存Agent输出内容
        
        Args:
            agent_name: Agent名称
            output_content: 输出内容
            output_tag: 输出标签
            user_id: 用户ID
            session_id: 会话ID
            file_type: 文件类型
            metadata: 元数据
            auto_export: 是否自动导出
            
        Returns:
            Dict: 保存结果信息
        """
        try:
            # 验证标签
            if output_tag not in self.output_tags:
                raise ValueError(f"不支持的输出标签: {output_tag}")
            
            # 验证文件类型
            if file_type not in self.file_types:
                raise ValueError(f"不支持的文件类型: {file_type}")
            
            # 生成文件信息
            file_info = self._generate_file_info(
                agent_name, output_tag, user_id, session_id, file_type
            )
            
            # 处理输出内容
            processed_content = self._process_output_content(output_content, file_type)
            
            # 保存到文件系统
            file_path = await self._save_to_filesystem(
                file_info, processed_content, output_tag, file_type
            )
            
            # 保存元数据
            metadata_info = await self._save_metadata(
                file_info, metadata, output_tag, user_id, session_id
            )
            
            # 保存到数据库
            db_record = await self._save_to_database(
                file_info, output_tag, user_id, session_id, file_path, metadata_info
            )
            
            # 自动导出
            export_info = None
            if auto_export:
                export_info = await self._auto_export_output(
                    file_info, output_tag, file_type, user_id, session_id
                )
            
            result = {
                "success": True,
                "file_info": file_info,
                "file_path": str(file_path),
                "metadata_info": metadata_info,
                "db_record": db_record,
                "export_info": export_info,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"💾 保存Agent输出成功: {agent_name} -> {output_tag}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 保存Agent输出失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_file_info(
        self, 
        agent_name: str, 
        output_tag: str, 
        user_id: str, 
        session_id: str, 
        file_type: str
    ) -> Dict[str, Any]:
        """生成文件信息"""
        timestamp = datetime.now()
        file_id = str(uuid.uuid4())
        
        # 生成文件名
        safe_agent_name = self._sanitize_filename(agent_name)
        safe_user_id = self._sanitize_filename(user_id)
        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        filename = f"{safe_agent_name}_{safe_user_id}_{date_str}_{file_id[:8]}"
        filename += self.file_types[file_type]["extension"]
        
        return {
            "file_id": file_id,
            "filename": filename,
            "agent_name": agent_name,
            "output_tag": output_tag,
            "user_id": user_id,
            "session_id": session_id,
            "file_type": file_type,
            "timestamp": timestamp.isoformat(),
            "date_str": date_str
        }
    
    def _process_output_content(
        self, 
        content: Union[str, Dict[str, Any]], 
        file_type: str
    ) -> str:
        """处理输出内容"""
        if file_type == "json":
            if isinstance(content, dict):
                return json.dumps(content, ensure_ascii=False, indent=2)
            else:
                try:
                    # 尝试解析为JSON
                    parsed = json.loads(content)
                    return json.dumps(parsed, ensure_ascii=False, indent=2)
                except:
                    return content
        elif file_type == "markdown":
            if isinstance(content, dict):
                return self._dict_to_markdown(content)
            else:
                return str(content)
        else:
            return str(content)
    
    def _dict_to_markdown(self, data: Dict[str, Any], level: int = 0) -> str:
        """将字典转换为Markdown格式"""
        markdown = ""
        indent = "  " * level
        
        for key, value in data.items():
            if isinstance(value, dict):
                markdown += f"{indent}## {key}\n\n"
                markdown += self._dict_to_markdown(value, level + 1)
            elif isinstance(value, list):
                markdown += f"{indent}### {key}\n\n"
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        markdown += f"{indent}{i+1}. "
                        markdown += self._dict_to_markdown(item, level + 1)
                    else:
                        markdown += f"{indent}{i+1}. {item}\n"
                markdown += "\n"
            else:
                markdown += f"{indent}**{key}**: {value}\n\n"
        
        return markdown
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不安全字符"""
        import re
        # 移除或替换不安全字符
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_filename = re.sub(r'\s+', '_', safe_filename)
        return safe_filename[:50]  # 限制长度
    
    async def _save_to_filesystem(
        self, 
        file_info: Dict[str, Any], 
        content: str, 
        output_tag: str, 
        file_type: str
    ) -> Path:
        """保存到文件系统"""
        try:
            # 确定存储路径
            tag_dir = self.base_storage_path / output_tag / "raw_outputs"
            file_path = tag_dir / file_info["filename"]
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"📁 文件保存成功: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"❌ 保存到文件系统失败: {e}")
            raise
    
    async def _save_metadata(
        self, 
        file_info: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]], 
        output_tag: str, 
        user_id: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """保存元数据"""
        try:
            metadata_info = {
                "file_id": file_info["file_id"],
                "agent_name": file_info["agent_name"],
                "output_tag": output_tag,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": file_info["timestamp"],
                "file_type": file_info["file_type"],
                "custom_metadata": metadata or {},
                "tag_info": self.output_tags[output_tag]
            }
            
            # 保存元数据到文件
            metadata_dir = self.base_storage_path / output_tag / "metadata"
            metadata_file = metadata_dir / f"{file_info['file_id']}.json"
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_info, f, ensure_ascii=False, indent=2)
            
            return metadata_info
            
        except Exception as e:
            self.logger.error(f"❌ 保存元数据失败: {e}")
            return {}
    
    async def _save_to_database(
        self, 
        file_info: Dict[str, Any], 
        output_tag: str, 
        user_id: str, 
        session_id: str, 
        file_path: Path, 
        metadata_info: Dict[str, Any]
    ) -> Optional[str]:
        """保存到数据库"""
        try:
            # 构建数据库记录
            db_record = {
                "file_id": file_info["file_id"],
                "agent_name": file_info["agent_name"],
                "output_tag": output_tag,
                "user_id": user_id,
                "session_id": session_id,
                "file_path": str(file_path),
                "file_type": file_info["file_type"],
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "metadata": metadata_info,
                "created_at": file_info["timestamp"]
            }
            
            # 保存到数据库（这里需要根据实际的数据库实现调整）
            # 假设使用存储管理器的save_stream_event方法
            event_id = await self.storage_manager.save_stream_event(
                user_id=user_id,
                session_id=session_id,
                event_type="agent_output_saved",
                content_type=file_info["file_type"],
                agent_source=file_info["agent_name"],
                event_data=db_record,
                event_metadata={
                    "output_tag": output_tag,
                    "file_id": file_info["file_id"],
                    "file_path": str(file_path)
                }
            )
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"❌ 保存到数据库失败: {e}")
            return None
    
    async def _auto_export_output(
        self, 
        file_info: Dict[str, Any], 
        output_tag: str, 
        file_type: str, 
        user_id: str, 
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """自动导出输出"""
        try:
            # 根据文件类型选择导出格式
            export_formats = []
            
            if file_type == "json":
                export_formats = ["markdown", "html"]
            elif file_type == "markdown":
                export_formats = ["html", "pdf"]
            elif file_type == "text":
                export_formats = ["markdown", "html"]
            
            export_results = []
            for export_format in export_formats:
                try:
                    export_result = await self._export_to_format(
                        file_info, output_tag, export_format, user_id, session_id
                    )
                    if export_result:
                        export_results.append(export_result)
                except Exception as e:
                    self.logger.warning(f"⚠️ 导出格式 {export_format} 失败: {e}")
            
            return {
                "export_formats": export_formats,
                "export_results": export_results,
                "success": len(export_results) > 0
            }
            
        except Exception as e:
            self.logger.error(f"❌ 自动导出失败: {e}")
            return None
    
    async def _export_to_format(
        self, 
        file_info: Dict[str, Any], 
        output_tag: str, 
        export_format: str, 
        user_id: str, 
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """导出到指定格式"""
        try:
            # 读取原始文件
            raw_file_path = self.base_storage_path / output_tag / "raw_outputs" / file_info["filename"]
            if not raw_file_path.exists():
                return None
            
            with open(raw_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据导出格式处理内容
            if export_format == "markdown":
                if file_info["file_type"] == "json":
                    # JSON转Markdown
                    data = json.loads(content)
                    processed_content = self._dict_to_markdown(data)
                else:
                    processed_content = content
            elif export_format == "html":
                if file_info["file_type"] == "json":
                    # JSON转HTML
                    data = json.loads(content)
                    processed_content = self._dict_to_html(data)
                elif file_info["file_type"] == "markdown":
                    # Markdown转HTML
                    processed_content = self._markdown_to_html(content)
                else:
                    processed_content = f"<pre>{content}</pre>"
            else:
                processed_content = content
            
            # 保存导出文件
            export_dir = self.base_storage_path / output_tag / "exports"
            export_filename = file_info["filename"].replace(
                self.file_types[file_info["file_type"]]["extension"],
                self.file_types.get(export_format, {"extension": f".{export_format}"})["extension"]
            )
            export_path = export_dir / export_filename
            
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            return {
                "export_format": export_format,
                "export_path": str(export_path),
                "file_size": export_path.stat().st_size
            }
            
        except Exception as e:
            self.logger.error(f"❌ 导出到 {export_format} 失败: {e}")
            return None
    
    def _dict_to_html(self, data: Dict[str, Any], level: int = 0) -> str:
        """将字典转换为HTML格式"""
        html = "<div class='agent-output'>\n"
        html += self._dict_to_html_recursive(data, level)
        html += "</div>\n"
        return html
    
    def _dict_to_html_recursive(self, data: Dict[str, Any], level: int = 0) -> str:
        """递归转换字典为HTML"""
        html = ""
        indent = "  " * level
        
        for key, value in data.items():
            if isinstance(value, dict):
                html += f"{indent}<div class='section'>\n"
                html += f"{indent}  <h{min(level+2, 6)}>{key}</h{min(level+2, 6)}>\n"
                html += self._dict_to_html_recursive(value, level + 1)
                html += f"{indent}</div>\n"
            elif isinstance(value, list):
                html += f"{indent}<div class='list-section'>\n"
                html += f"{indent}  <h{min(level+2, 6)}>{key}</h{min(level+2, 6)}>\n"
                html += f"{indent}  <ul>\n"
                for item in value:
                    if isinstance(item, dict):
                        html += f"{indent}    <li>\n"
                        html += self._dict_to_html_recursive(item, level + 2)
                        html += f"{indent}    </li>\n"
                    else:
                        html += f"{indent}    <li>{item}</li>\n"
                html += f"{indent}  </ul>\n"
                html += f"{indent}</div>\n"
            else:
                html += f"{indent}<div class='field'>\n"
                html += f"{indent}  <strong>{key}:</strong> {value}\n"
                html += f"{indent}</div>\n"
        
        return html
    
    def _markdown_to_html(self, markdown: str) -> str:
        """简单的Markdown转HTML"""
        # 这里可以实现更复杂的Markdown解析
        # 目前使用简单的文本替换
        html = markdown
        html = html.replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
        html = html.replace('\n**', '\n<strong>').replace('**', '</strong>')
        html = html.replace('\n*', '\n<em>').replace('*', '</em>')
        html = html.replace('\n', '<br>\n')
        return f"<div class='markdown-content'>{html}</div>"
    
    async def get_agent_outputs(
        self, 
        output_tag: str, 
        user_id: Optional[str] = None, 
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取Agent输出列表"""
        try:
            outputs = []
            tag_dir = self.base_storage_path / output_tag / "raw_outputs"
            
            if not tag_dir.exists():
                return outputs
            
            # 遍历文件
            for file_path in tag_dir.iterdir():
                if file_path.is_file():
                    # 读取元数据
                    metadata_file = self.base_storage_path / output_tag / "metadata" / f"{file_path.stem}.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # 应用过滤条件
                        if user_id and metadata.get("user_id") != user_id:
                            continue
                        if session_id and metadata.get("session_id") != session_id:
                            continue
                        if agent_name and metadata.get("agent_name") != agent_name:
                            continue
                        
                        # 添加文件信息
                        metadata["file_path"] = str(file_path)
                        metadata["file_size"] = file_path.stat().st_size
                        metadata["file_exists"] = file_path.exists()
                        
                        outputs.append(metadata)
            
            # 按时间排序
            outputs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return outputs[:limit]
            
        except Exception as e:
            self.logger.error(f"❌ 获取Agent输出失败: {e}")
            return []
    
    async def get_output_content(
        self, 
        file_id: str, 
        output_tag: str
    ) -> Optional[Dict[str, Any]]:
        """获取输出内容"""
        try:
            # 读取元数据
            metadata_file = self.base_storage_path / output_tag / "metadata" / f"{file_id}.json"
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 读取文件内容
            file_path = self.base_storage_path / output_tag / "raw_outputs" / metadata["filename"]
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "metadata": metadata,
                "content": content,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取输出内容失败: {e}")
            return None
    
    async def cleanup_old_outputs(self, days: int = 30) -> Dict[str, Any]:
        """清理旧输出文件"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_files = []
            cleaned_size = 0
            
            for output_tag in self.output_tags.keys():
                tag_dir = self.base_storage_path / output_tag
                
                # 清理原始输出
                raw_dir = tag_dir / "raw_outputs"
                if raw_dir.exists():
                    for file_path in raw_dir.iterdir():
                        if file_path.is_file():
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_time < cutoff_date:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                cleaned_files.append(str(file_path))
                                cleaned_size += file_size
                
                # 清理元数据
                metadata_dir = tag_dir / "metadata"
                if metadata_dir.exists():
                    for file_path in metadata_dir.iterdir():
                        if file_path.is_file():
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_time < cutoff_date:
                                file_path.unlink()
            
            result = {
                "success": True,
                "cleaned_files": len(cleaned_files),
                "cleaned_size": cleaned_size,
                "cutoff_date": cutoff_date.isoformat()
            }
            
            self.logger.info(f"🧹 清理完成: {len(cleaned_files)} 个文件, {cleaned_size} 字节")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 清理旧文件失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            stats = {
                "total_tags": len(self.output_tags),
                "tag_stats": {},
                "total_size": 0,
                "total_files": 0
            }
            
            for output_tag in self.output_tags.keys():
                tag_dir = self.base_storage_path / output_tag
                tag_stats = {
                    "raw_outputs": 0,
                    "metadata": 0,
                    "exports": 0,
                    "size": 0
                }
                
                # 统计原始输出
                raw_dir = tag_dir / "raw_outputs"
                if raw_dir.exists():
                    for file_path in raw_dir.iterdir():
                        if file_path.is_file():
                            tag_stats["raw_outputs"] += 1
                            tag_stats["size"] += file_path.stat().st_size
                
                # 统计元数据
                metadata_dir = tag_dir / "metadata"
                if metadata_dir.exists():
                    for file_path in metadata_dir.iterdir():
                        if file_path.is_file():
                            tag_stats["metadata"] += 1
                
                # 统计导出文件
                exports_dir = tag_dir / "exports"
                if exports_dir.exists():
                    for file_path in exports_dir.iterdir():
                        if file_path.is_file():
                            tag_stats["exports"] += 1
                
                stats["tag_stats"][output_tag] = tag_stats
                stats["total_size"] += tag_stats["size"]
                stats["total_files"] += tag_stats["raw_outputs"]

            return stats

        except Exception as e:
            self.logger.error(f"❌ 获取存储统计失败: {e}")
            return {"error": str(e)}


# 全局存储管理器实例（延迟初始化）
agent_output_storage = None


def get_agent_output_storage() -> AgentOutputStorage:
    """获取Agent输出存储管理器实例（延迟初始化）"""
    global agent_output_storage
    if agent_output_storage is None:
        agent_output_storage = AgentOutputStorage()
    return agent_output_storage

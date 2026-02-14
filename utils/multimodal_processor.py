"""
Juben多模态处理器
 ，提供多模态文件处理功能
"""
import asyncio
import os
import mimetypes
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import base64
import hashlib
from datetime import datetime

try:
    from .logger import JubenLogger
    from .storage_manager import get_storage
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from utils.logger import JubenLogger
    from utils.storage_manager import get_storage


class JubenMultimodalProcessor:
    """
    Juben多模态处理器
    
    核心功能：
    1. 文件类型检测和验证
    2. 图像文件处理和分析
    3. 文档文件解析和提取
    4. 音频/视频文件处理
    5. 文件元数据提取
    6. 多模态内容融合
    """
    
    def __init__(self):
        self.logger = JubenLogger("MultimodalProcessor")
        self.storage = get_storage()
        
        # 支持的文件类型
        self.supported_types = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            'document': ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf'],
            'audio': ['.mp3', '.wav', '.m4a', '.aac', '.ogg'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz']
        }
        
        # 文件大小限制（字节）
        self.size_limits = {
            'image': 10 * 1024 * 1024,  # 10MB
            'document': 50 * 1024 * 1024,  # 50MB
            'audio': 100 * 1024 * 1024,  # 100MB
            'video': 500 * 1024 * 1024,  # 500MB
            'archive': 100 * 1024 * 1024,  # 100MB
        }
        
        self.logger.info("多模态处理器初始化完成")
    
    def is_enabled(self) -> bool:
        """检查多模态处理是否可用"""
        return True  # 基础功能总是可用
    
    async def should_use_multimodal_processing(self, user_id: str, session_id: str, instruction: str) -> bool:
        """
        判断是否需要多模态处理
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            instruction: 用户指令
            
        Returns:
            bool: 是否需要多模态处理
        """
        try:
            # 检查指令中是否包含文件相关关键词
            multimodal_keywords = [
                '文件', '图片', '图像', '照片', '文档', 'PDF', '音频', '视频',
                '上传', '分析', '识别', '提取', '处理', '查看', '显示'
            ]
            
            instruction_lower = instruction.lower()
            has_multimodal_keywords = any(keyword in instruction_lower for keyword in multimodal_keywords)
            
            # 检查是否有文件上传
            has_files = await self._check_uploaded_files(user_id, session_id)
            
            result = has_multimodal_keywords or has_files
            self.logger.debug(f"多模态处理判断: {result} (关键词: {has_multimodal_keywords}, 文件: {has_files})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 多模态处理判断失败: {e}")
            return False
    
    async def _check_uploaded_files(self, user_id: str, session_id: str) -> bool:
        """检查是否有上传的文件"""
        try:
            # 这里可以检查文件存储中是否有相关文件
            # 暂时返回False
            return False
        except Exception as e:
            self.logger.error(f"❌ 检查上传文件失败: {e}")
            return False
    
    async def process_multimodal_files(self, user_id: str, session_id: str, 
                                     instruction: str, agent_name: str = "multimodal") -> List[Dict[str, Any]]:
        """
        处理多模态文件
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            instruction: 处理指令
            agent_name: Agent名称
            
        Returns:
            List[Dict]: 处理结果列表
        """
        try:
            self.logger.info(f"开始多模态文件处理: user_id={user_id}, session_id={session_id}")
            
            # 获取文件列表
            files = await self._get_files_for_processing(user_id, session_id)
            if not files:
                self.logger.info("没有找到需要处理的文件")
                return []
            
            results = []
            for file_info in files:
                try:
                    result = await self._process_single_file(file_info, instruction, agent_name)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"❌ 处理文件失败: {file_info.get('filename', 'unknown')}, {e}")
                    continue
            
            self.logger.info(f"✅ 多模态文件处理完成: {len(results)}个文件")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 多模态文件处理失败: {e}")
            return []
    
    async def _get_files_for_processing(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """获取需要处理的文件列表"""
        try:
            # 这里应该从文件存储中获取文件列表
            # 暂时返回空列表
            return []
        except Exception as e:
            self.logger.error(f"❌ 获取文件列表失败: {e}")
            return []
    
    async def _process_single_file(self, file_info: Dict[str, Any], instruction: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """处理单个文件"""
        try:
            file_path = file_info.get('file_path')
            filename = file_info.get('filename', 'unknown')
            file_type = file_info.get('file_type', 'unknown')
            
            if not os.path.exists(file_path):
                self.logger.warning(f"文件不存在: {file_path}")
                return None
            
            # 验证文件类型和大小
            if not self._validate_file(file_path, file_type):
                return None
            
            # 根据文件类型选择处理方式
            if file_type == 'image':
                analysis = await self._analyze_image(file_path, instruction)
            elif file_type == 'document':
                analysis = await self._analyze_document(file_path, instruction)
            elif file_type in ['audio', 'video']:
                analysis = await self._analyze_media(file_path, instruction)
            else:
                analysis = f"文件类型 {file_type} 暂不支持详细分析"
            
            result = {
                "ref_name": f"file_{filename}_{hash(file_path)}",
                "file_info": file_info,
                "file_type": file_type,
                "analysis": analysis,
                "processed_by": agent_name,
                "processed_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ 文件处理完成: {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 处理单个文件失败: {e}")
            return None
    
    def _validate_file(self, file_path: str, file_type: str) -> bool:
        """验证文件"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            size_limit = self.size_limits.get(file_type, 10 * 1024 * 1024)  # 默认10MB
            if file_size > size_limit:
                self.logger.warning(f"文件过大: {file_size} > {size_limit}")
                return False
            
            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower()
            supported_exts = self.supported_types.get(file_type, [])
            if file_ext not in supported_exts:
                self.logger.warning(f"不支持的文件扩展名: {file_ext}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 文件验证失败: {e}")
            return False
    
    async def _analyze_image(self, file_path: str, instruction: str) -> str:
        """分析图像文件"""
        try:
            # 获取图像基本信息
            file_size = os.path.getsize(file_path)
            filename = Path(file_path).name
            
            # 这里可以集成图像分析API
            # 暂时返回基本信息
            analysis = f"""
图像文件分析结果：
- 文件名: {filename}
- 文件大小: {file_size} 字节
- 文件类型: 图像文件
- 处理指令: {instruction}

注意: 图像分析功能需要集成相应的AI服务，当前仅提供基本信息。
"""
            return analysis.strip()
            
        except Exception as e:
            self.logger.error(f"❌ 图像分析失败: {e}")
            return f"图像分析失败: {str(e)}"
    
    async def _analyze_document(self, file_path: str, instruction: str) -> str:
        """分析文档文件"""
        try:
            # 获取文档基本信息
            file_size = os.path.getsize(file_path)
            filename = Path(file_path).name
            file_ext = Path(file_path).suffix.lower()
            
            # 根据文件类型进行不同的处理
            if file_ext == '.txt':
                content = await self._extract_text_content(file_path)
            elif file_ext == '.md':
                content = await self._extract_markdown_content(file_path)
            else:
                content = f"文档类型 {file_ext} 的内容提取功能待实现"
            
            analysis = f"""
文档文件分析结果：
- 文件名: {filename}
- 文件大小: {file_size} 字节
- 文件类型: {file_ext} 文档
- 处理指令: {instruction}

文档内容摘要:
{content[:500]}{'...' if len(content) > 500 else ''}
"""
            return analysis.strip()
            
        except Exception as e:
            self.logger.error(f"❌ 文档分析失败: {e}")
            return f"文档分析失败: {str(e)}"
    
    async def _analyze_media(self, file_path: str, instruction: str) -> str:
        """分析音频/视频文件"""
        try:
            file_size = os.path.getsize(file_path)
            filename = Path(file_path).name
            file_ext = Path(file_path).suffix.lower()
            
            media_type = "音频" if file_ext in self.supported_types['audio'] else "视频"
            
            analysis = f"""
{media_type}文件分析结果：
- 文件名: {filename}
- 文件大小: {file_size} 字节
- 文件类型: {media_type}文件
- 处理指令: {instruction}

注意: {media_type}分析功能需要集成相应的AI服务，当前仅提供基本信息。
"""
            return analysis.strip()
            
        except Exception as e:
            self.logger.error(f"❌ 媒体分析失败: {e}")
            return f"媒体分析失败: {str(e)}"
    
    async def _extract_text_content(self, file_path: str) -> str:
        """提取文本内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception:
                return "无法读取文件内容"
        except Exception as e:
            return f"读取文件失败: {str(e)}"
    
    async def _extract_markdown_content(self, file_path: str) -> str:
        """提取Markdown内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取Markdown文件失败: {str(e)}"
    
    def get_file_type(self, file_path: str) -> str:
        """获取文件类型"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            for file_type, extensions in self.supported_types.items():
                if file_ext in extensions:
                    return file_type
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def get_supported_extensions(self, file_type: str = None) -> List[str]:
        """获取支持的文件扩展名"""
        if file_type:
            return self.supported_types.get(file_type, [])
        else:
            all_extensions = []
            for extensions in self.supported_types.values():
                all_extensions.extend(extensions)
            return all_extensions


# 全局实例
_multimodal_processor = None

def get_multimodal_processor() -> JubenMultimodalProcessor:
    """获取多模态处理器实例"""
    global _multimodal_processor
    if _multimodal_processor is None:
        _multimodal_processor = JubenMultimodalProcessor()
    return _multimodal_processor
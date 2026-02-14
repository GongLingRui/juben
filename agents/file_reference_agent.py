"""
竖屏短剧策划助手 - 文件引用智能体
 架构的文件引用机制设计
支持@文件名引用和自然语言文件引用解析

业务处理逻辑：
1. 输入处理：接收包含文件引用的文本，支持多种引用格式
2. 引用解析：解析@文件名引用和自然语言文件引用
3. 文件识别：识别引用的文件类型和内容
4. 内容提取：提取文件内容并进行结构化处理
5. 格式支持：支持多种文件格式（PDF、Word、图片、txt等）
6. 内容验证：验证文件内容的完整性和准确性
7. 结构化输出：将文件内容转换为结构化数据
8. 集成服务：与主策划流程无缝集成
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
import re
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
import uuid

from .base_juben_agent import BaseJubenAgent


class FileReferenceAgent(BaseJubenAgent):
    """
    竖屏短剧策划助手文件引用智能体
    
    核心功能：
    1. 解析@文件名引用（如@file1, @image1等）
    2. 解析自然语言文件引用（如"第一个文件"、"最新上传的图片"等）
    3. 文件内容提取和结构化输出
    4. 支持多种文件格式（PDF、Word、图片、txt等）
    5. 与策划Agent集成，提供文件引用服务
    
    设计理念：
    - 专门处理文件引用解析
    - 支持自然语言和@符号引用
    - 提供结构化的文件内容输出
    - 与主策划流程无缝集成
    """
    
    def __init__(self):
        super().__init__("file_reference", model_provider="zhipu")
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 文件类型映射
        self.file_type_mapping = {
            "file": "文档",
            "image": "图片", 
            "document": "文档",
            "pdf": "PDF文档",
            "word": "Word文档",
            "excel": "Excel表格",
            "txt": "文本文件",
            "audio": "音频文件",
            "video": "视频文件"
        }
        
        # 自然语言引用模式
        self.natural_reference_patterns = {
            r"第([一二三四五六七八九十\d]+)个文件": "ordinal_file",
            r"最新上传的(.+)": "latest_upload",
            r"刚才上传的(.+)": "recent_upload", 
            r"那个(.+)文件": "that_file",
            r"我的(.+)文件": "my_file",
            r"(.+)文件": "type_file"
        }
        
        # 序号词汇映射
        self.ordinal_mapping = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
            "6": 6, "7": 7, "8": 8, "9": 9, "10": 10
        }
        
        self.logger.info("文件引用智能体初始化完成")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理文件引用解析请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            user_input = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            self.logger.info(f"开始处理文件引用解析请求: {user_input}")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始处理事件
            yield await self._emit_event("system", "📁 开始解析文件引用...")
            
            # 1. 检测文件引用
            yield await self._emit_event("system", "🔍 正在检测文件引用...")
            file_references = await self._detect_file_references(user_input)
            
            if not file_references:
                yield await self._emit_event("system", "⚠️ 未检测到文件引用")
                return
            
            yield await self._emit_event("system", f"✅ 检测到 {len(file_references)} 个文件引用")
            
            # 2. 解析文件引用
            yield await self._emit_event("system", "📋 正在解析文件引用...")
            resolved_references = []
            
            for i, ref in enumerate(file_references, 1):
                yield await self._emit_event("system", f"🔍 解析第 {i}/{len(file_references)} 个引用...")
                
                resolved_ref = await self._resolve_file_reference(ref, user_id, session_id, context)
                if resolved_ref:
                    resolved_references.append(resolved_ref)
                    yield await self._emit_event("system", f"✅ 引用解析成功: {resolved_ref.get('reference_name', 'unknown')}")
                else:
                    yield await self._emit_event("system", f"❌ 引用解析失败: {ref}")
            
            # 3. 生成文件引用报告
            yield await self._emit_event("system", "📝 正在生成文件引用报告...")
            
            async for chunk in self._generate_file_reference_report(resolved_references, user_input, user_id, session_id):
                yield chunk
            
            # 4. 获取Token计费摘要
            billing_summary = await self.get_token_billing_summary()
            if billing_summary:
                yield await self._emit_event("billing", f"📊 Token消耗: {billing_summary['total_tokens']} tokens, 积分扣减: {billing_summary['deducted_points']} 积分")
            
            # 5. 发送完成事件
            yield await self._emit_event("system", "📁 文件引用解析完成！")
            
        except Exception as e:
            self.logger.error(f"处理文件引用请求失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")
    
    async def _detect_file_references(self, text: str) -> List[str]:
        """检测文本中的文件引用"""
        references = []
        
        # 1. 检测@符号引用
        at_ref_pattern = r'@(file\d+|image\d+|document\d+|pdf\d+|excel\d+|audio\d+|video\d+)'
        at_matches = re.findall(at_ref_pattern, text, re.IGNORECASE)
        references.extend([f"@{match}" for match in at_matches])
        
        # 2. 检测自然语言引用
        for pattern, ref_type in self.natural_reference_patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                references.append({
                    "type": ref_type,
                    "match": match,
                    "original": f"第{match}个文件" if ref_type == "ordinal_file" else match
                })
        
        # 3. 检测文件类型引用
        file_type_pattern = r'([图片|图像|照片|文档|PDF|Word|Excel|文本|音频|视频]+文件)'
        type_matches = re.findall(file_type_pattern, text)
        for match in type_matches:
            references.append({
                "type": "type_file",
                "match": match,
                "original": match
            })
        
        return references
    
    async def _resolve_file_reference(self, reference: str, user_id: str, session_id: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析单个文件引用"""
        try:
            if isinstance(reference, str) and reference.startswith("@"):
                # 处理@符号引用
                return await self._resolve_at_reference(reference, user_id, session_id, context)
            elif isinstance(reference, dict):
                # 处理自然语言引用
                return await self._resolve_natural_reference(reference, user_id, session_id, context)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"解析文件引用失败: {e}")
            return None
    
    async def _resolve_at_reference(self, at_ref: str, user_id: str, session_id: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析@符号引用"""
        try:
            # 提取引用名称（去掉@符号）
            ref_name = at_ref[1:]  # 去掉@符号
            
            # 从引用名称推断文件类型和序号
            file_type = "file"
            file_index = 1
            
            for type_name in self.file_type_mapping.keys():
                if ref_name.startswith(type_name):
                    file_type = type_name
                    # 提取序号
                    index_str = ref_name[len(type_name):]
                    if index_str.isdigit():
                        file_index = int(index_str)
                    break
            
            # 模拟文件信息（实际实现中应该从文件存储系统获取）
            mock_file_info = await self._get_mock_file_info(user_id, session_id, file_type, file_index)
            
            return {
                "reference_type": "at_reference",
                "reference_name": at_ref,
                "file_type": file_type,
                "file_index": file_index,
                "file_info": mock_file_info,
                "resolved_content": mock_file_info.get("content", "")
            }
            
        except Exception as e:
            self.logger.error(f"解析@引用失败: {e}")
            return None
    
    async def _resolve_natural_reference(self, natural_ref: Dict[str, Any], user_id: str, session_id: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析自然语言引用"""
        try:
            ref_type = natural_ref.get("type", "")
            match = natural_ref.get("match", "")
            original = natural_ref.get("original", "")
            
            file_type = "file"
            file_index = 1
            
            if ref_type == "ordinal_file":
                # 处理序号引用
                file_index = self.ordinal_mapping.get(match, 1)
            elif ref_type in ["latest_upload", "recent_upload"]:
                # 处理最新上传引用
                file_index = 1  # 假设最新的是第一个
            elif ref_type == "type_file":
                # 处理文件类型引用
                for type_name, chinese_name in self.file_type_mapping.items():
                    if chinese_name in match or type_name in match.lower():
                        file_type = type_name
                        break
            
            # 模拟文件信息
            mock_file_info = await self._get_mock_file_info(user_id, session_id, file_type, file_index)
            
            return {
                "reference_type": "natural_reference",
                "reference_name": original,
                "file_type": file_type,
                "file_index": file_index,
                "file_info": mock_file_info,
                "resolved_content": mock_file_info.get("content", "")
            }
            
        except Exception as e:
            self.logger.error(f"解析自然语言引用失败: {e}")
            return None
    
    async def _get_mock_file_info(self, user_id: str, session_id: str, file_type: str, file_index: int) -> Dict[str, Any]:
        """获取模拟文件信息（实际实现中应该从真实的文件存储系统获取）"""
        # 这里是模拟数据，实际实现中应该：
        # 1. 从数据库或文件存储系统查询用户文件
        # 2. 根据文件类型和索引获取具体文件
        # 3. 提取文件内容
        
        mock_files = {
            "file": {
                1: {
                    "filename": "短剧策划方案.docx",
                    "content": "这是一个关于战神归来题材的短剧策划方案，包含人物设定、情节大纲和商业化建议。",
                    "file_size": "2.5MB",
                    "upload_time": "2024-12-20 10:30:00"
                },
                2: {
                    "filename": "市场调研报告.pdf", 
                    "content": "最新的竖屏短剧市场调研报告，包含用户偏好分析和竞品对比。",
                    "file_size": "1.8MB",
                    "upload_time": "2024-12-20 09:15:00"
                }
            },
            "image": {
                1: {
                    "filename": "角色设定图.jpg",
                    "content": "主角形象设计图，包含服装、表情和场景设定。",
                    "file_size": "3.2MB", 
                    "upload_time": "2024-12-20 11:00:00"
                }
            },
            "pdf": {
                1: {
                    "filename": "剧本大纲.pdf",
                    "content": "详细的剧本大纲，包含三幕式结构和关键情节设计。",
                    "file_size": "4.1MB",
                    "upload_time": "2024-12-20 08:45:00"
                }
            }
        }
        
        # 获取对应类型和索引的文件信息
        file_info = mock_files.get(file_type, {}).get(file_index, {
            "filename": f"未知{self.file_type_mapping.get(file_type, '文件')}{file_index}",
            "content": f"这是第{file_index}个{self.file_type_mapping.get(file_type, '文件')}的内容。",
            "file_size": "未知大小",
            "upload_time": "未知时间"
        })
        
        return file_info
    
    async def _generate_file_reference_report(self, resolved_references: List[Dict[str, Any]], original_input: str, user_id: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """生成文件引用报告"""
        try:
            # 构建报告提示词
            report_prompt = f"""
请根据以下文件引用解析结果，生成一个详细的文件引用报告：

原始用户输入: {original_input}

解析的文件引用:
{json.dumps(resolved_references, ensure_ascii=False, indent=2)}

请生成一个专业的文件引用报告，包括：
1. 引用摘要
2. 文件内容概览
3. 关键信息提取
4. 应用建议

要求：
- 内容专业、准确
- 突出与竖屏短剧策划相关的信息
- 结构清晰、易于理解
- 提供具体的应用建议
"""
            
            # 调用LLM生成报告
            messages = [
                {"role": "system", "content": "你是竖屏短剧策划助手的文件引用分析专家，专门负责分析文件引用并生成专业的引用报告。"},
                {"role": "user", "content": report_prompt}
            ]
            
            # 流式输出报告
            async for chunk in self._stream_llm(messages, user_id=user_id, session_id=session_id):
                yield await self._emit_event("llm_chunk", chunk)
                
        except Exception as e:
            self.logger.error(f"生成文件引用报告失败: {e}")
            yield await self._emit_event("error", f"生成报告失败: {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "file_reference",
            "description": "竖屏短剧策划助手文件引用智能体，专门处理文件引用解析和内容提取",
            "capabilities": [
                "解析@文件名引用",
                "解析自然语言文件引用",
                "文件内容提取和结构化输出",
                "支持多种文件格式",
                "与策划流程无缝集成"
            ],
            "supported_reference_types": [
                "@file1, @image1等@符号引用",
                "第一个文件、最新上传等自然语言引用",
                "文件类型引用（图片文件、PDF文档等）"
            ],
            "file_type_mapping": self.file_type_mapping
        })
        return base_info

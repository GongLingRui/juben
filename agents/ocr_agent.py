"""
OCR 识别 Agent
支持用户上传文件进行 OCR 识别和保存

功能：
1. 接收用户上传的图片/PDF 文件
2. 调用 PaddleOCR 进行文本识别
3. 支持多种输出格式（纯文本、Markdown、JSON）
4. 保存识别结果到文件
5. 返回结构化的识别结果

代码作者：Claude
创建时间：2026年2月7日
"""
import os
import io
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
import json
import base64
from enum import Enum

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent

from utils.paddleocr_service import (
    get_paddleocr_service,
    PaddleOCRService,
    OCRMode,
    OCRResult,
    is_paddleocr_available
)
from utils.artifact_manager import (
    get_artifact_manager,
    ArtifactType,
    AgentSource
)


class OutputFormat(Enum):
    """输出格式"""
    TEXT = "text"              # 纯文本
    MARKDOWN = "markdown"      # Markdown 格式
    JSON = "json"              # JSON 格式
    STRUCTURED = "structured"  # 结构化数据


@dataclass
class FileUploadResult:
    """文件上传结果"""
    success: bool
    filename: str
    file_path: str
    file_size: int
    file_type: str
    ocr_result: Optional[OCRResult] = None
    error: Optional[str] = None
    saved_paths: Dict[str, str] = field(default_factory=dict)  # 保存的文件路径


class OCRAgent(BaseJubenAgent):
    """
    OCR 识别 Agent

    负责：
    1. 处理用户上传的文件
    2. 调用 PaddleOCR 服务进行识别
    3. 格式化输出结果
    4. 保存识别结果
    """

    def __init__(self):
        super().__init__("ocr_agent", model_provider="local")

        # 覆盖系统提示词
        self.system_prompt = """你是专业的 OCR 识别助手，使用 PaddleOCR-VL 模型进行文字识别。

你的能力包括：
1. 文本检测和识别（支持中英文混合）
2. 版面分析和结构化输出
3. 表格识别
4. 公式识别

输出格式说明：
- text: 纯文本格式，按阅读顺序拼接所有识别的文本
- markdown: Markdown 格式，包含标题、表格、公式等
- json: JSON 格式，包含完整的结构化数据
- structured: 结构化数据，便于程序处理

你可以处理的文件类型：
- 图片：JPG, JPEG, PNG, BMP, TIFF
- 文档：PDF（需要额外处理）

请始终提供准确、完整的识别结果。"""

        # OCR 服务
        self.ocr_service: Optional[PaddleOCRService] = None

        # 文件存储目录
        self.upload_dir = Path("uploads/ocr")
        self.output_dir = Path("outputs/ocr")

        # 创建目录
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("OCR Agent 初始化完成")

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理 OCR 请求

        Args:
            request_data: 请求数据
                - file: 上传的文件（可选）
                - file_path: 文件路径（可选）
                - file_base64: Base64 编码的文件（可选）
                - output_format: 输出格式 (text/markdown/json/structured)
                - use_structure: 是否使用结构化识别（默认 false）
                - save_result: 是否保存结果（默认 true）
            context: 上下文信息

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 检查 OCR 可用性
            if not is_paddleocr_available():
                yield await self._emit_event(
                    "error",
                    "PaddleOCR 未安装。请联系管理员安装。"
                )
                return

            # 初始化 OCR 服务
            if self.ocr_service is None:
                self.ocr_service = get_paddleocr_service(use_gpu=True, gpu_id=0, lang="ch")

            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"

            yield await self._emit_event("system", "📁 准备处理 OCR 请求...")

            # 获取文件
            file_source = await self._get_file_source(request_data)
            if file_source is None:
                yield await self._emit_event(
                    "error",
                    "未找到有效的文件。请上传文件或提供文件路径。"
                )
                return

            # 获取配置
            output_format = OutputFormat(request_data.get("output_format", "text"))
            use_structure = request_data.get("use_structure", False)
            save_result = request_data.get("save_result", True)

            # 执行 OCR
            yield await self._emit_event("system", "🔍 正在进行 OCR 识别...")

            ocr_mode = OCRMode.STRUCTURE if use_structure else OCRMode.TEXT_ONLY

            # 在线程池中执行 OCR（避免阻塞）
            loop = asyncio.get_event_loop()
            if ocr_mode == OCRMode.STRUCTURE:
                ocr_result = await loop.run_in_executor(
                    None,
                    self.ocr_service.recognize_structure,
                    file_source
                )
            else:
                ocr_result = await loop.run_in_executor(
                    None,
                    self.ocr_service.recognize_text,
                    file_source
                )

            # 检查识别结果
            if not ocr_result.success:
                yield await self._emit_event(
                    "error",
                    f"OCR 识别失败: {ocr_result.metadata.get('error', '未知错误')}"
                )
                return

            # 格式化输出
            yield await self._emit_event("system", "📝 正在格式化输出...")

            formatted_output = await self._format_output(ocr_result, output_format)

            # 保存结果
            saved_paths = {}
            if save_result:
                yield await self._emit_event("system", "💾 正在保存结果...")
                saved_paths = await self._save_result(
                    ocr_result,
                    formatted_output,
                    output_format,
                    user_id,
                    session_id
                )

            # 返回结果
            yield await self._emit_event(
                "content",
                f"## OCR 识别完成\n\n"
                f"- **识别时间**: {ocr_result.processing_time:.2f}秒\n"
                f"- **文本框数量**: {len(ocr_result.text_boxes)}\n"
                f"- **表格数量**: {len(ocr_result.tables)}\n"
                f"- **公式数量**: {len(ocr_result.formulas)}\n\n"
                f"---\n\n"
                f"{formatted_output}"
            )

            # 添加元数据
            yield await self._emit_event(
                "metadata",
                json.dumps({
                    "processing_time": ocr_result.processing_time,
                    "text_box_count": len(ocr_result.text_boxes),
                    "table_count": len(ocr_result.tables),
                    "formula_count": len(ocr_result.formulas),
                    "saved_paths": saved_paths,
                    "output_format": output_format.value
                }, ensure_ascii=False)
            )

            yield await self._emit_event("system", "✅ OCR 处理完成！")

        except Exception as e:
            self.logger.error(f"OCR 处理失败: {e}")
            yield await self._emit_event("error", f"处理失败: {str(e)}")

    async def _get_file_source(self, request_data: Dict[str, Any]) -> Optional[Union[str, bytes]]:
        """获取文件源"""
        # 1. 检查直接上传的文件
        if "file" in request_data:
            file_obj = request_data["file"]
            if hasattr(file_obj, "read"):
                return file_obj.read()
            return file_obj

        # 2. 检查文件路径
        if "file_path" in request_data:
            file_path = request_data["file_path"]
            if os.path.exists(file_path):
                return file_path

        # 3. 检查 Base64 编码
        if "file_base64" in request_data:
            base64_data = request_data["file_base64"]
            try:
                return base64.b64decode(base64_data)
            except Exception as e:
                self.logger.error(f"Base64 解码失败: {e}")

        return None

    async def _format_output(self, ocr_result: OCRResult, output_format: OutputFormat) -> str:
        """格式化输出"""
        if output_format == OutputFormat.TEXT:
            return ocr_result.text

        elif output_format == OutputFormat.MARKDOWN:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.ocr_service.export_to_markdown,
                ocr_result
            )

        elif output_format == OutputFormat.JSON:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.ocr_service.export_to_json,
                ocr_result
            )

        elif output_format == OutputFormat.STRUCTURED:
            return json.dumps({
                "text": ocr_result.text,
                "text_boxes": [box.to_dict() for box in ocr_result.text_boxes],
                "layout": ocr_result.layout,
                "tables": ocr_result.tables,
                "formulas": ocr_result.formulas,
                "metadata": ocr_result.metadata
            }, ensure_ascii=False, indent=2)

        return ocr_result.text

    async def _save_result(
        self,
        ocr_result: OCRResult,
        formatted_output: str,
        output_format: OutputFormat,
        user_id: str,
        session_id: str
    ) -> Dict[str, str]:
        """保存识别结果到 Artifact 文件系统"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"ocr_{session_id}_{timestamp}"

        saved_paths = {}
        artifact_manager = get_artifact_manager()

        try:
            # 确定文件类型
            ext_map = {
                OutputFormat.TEXT: "txt",
                OutputFormat.MARKDOWN: "md",
                OutputFormat.JSON: "json",
                OutputFormat.STRUCTURED: "json"
            }
            ext = ext_map.get(output_format, "txt")

            # 保存原始 JSON 数据（用于记录）
            json_filename = f"{base_filename}_raw.json"
            artifact_id_json = artifact_manager.save_artifact(
                content=json.dumps(ocr_result.to_dict(), ensure_ascii=False, indent=2),
                filename=json_filename,
                file_type=ArtifactType.JSON,
                agent_source=AgentSource.OCR_AGENT,
                user_id=user_id,
                session_id=session_id,
                project_id=f"{user_id}_ocr",
                description="OCR 识别原始数据（JSON格式）",
                tags=["ocr", "raw", "json"],
                metadata={
                    "processing_time": ocr_result.processing_time,
                    "text_box_count": len(ocr_result.text_boxes),
                    "table_count": len(ocr_result.tables),
                    "formula_count": len(ocr_result.formulas),
                    "output_format": "raw"
                }
            )
            saved_paths["json"] = artifact_id_json

            # 保存格式化输出文件
            output_filename = f"{base_filename}.{ext}"
            artifact_id_output = artifact_manager.save_artifact(
                content=formatted_output,
                filename=output_filename,
                file_type=ArtifactType.OCR_RESULT,
                agent_source=AgentSource.OCR_AGENT,
                user_id=user_id,
                session_id=session_id,
                project_id=f"{user_id}_ocr",
                description=f"OCR 识别结果 ({output_format.value} 格式)",
                tags=["ocr", output_format.value],
                parent_id=artifact_id_json,  # 关联到原始 JSON
                metadata={
                    "processing_time": ocr_result.processing_time,
                    "text_box_count": len(ocr_result.text_boxes),
                    "table_count": len(ocr_result.tables),
                    "formula_count": len(ocr_result.formulas),
                    "output_format": output_format.value
                }
            )
            saved_paths["output"] = artifact_id_output

            # 更新父级关联
            artifact_manager.metadata[artifact_id_json].children_ids.append(artifact_id_output)
            artifact_manager._save_metadata()

            self.logger.info(f"✅ OCR 结果已保存到 Artifact 系统: {saved_paths}")

        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")

        return saved_paths

    async def batch_process(
        self,
        file_paths: List[str],
        output_format: OutputFormat = OutputFormat.TEXT
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        批量处理文件

        Args:
            file_paths: 文件路径列表
            output_format: 输出格式

        Yields:
            Dict[str, Any]: 每个文件的处理结果
        """
        if not is_paddleocr_available():
            yield {
                "success": False,
                "error": "PaddleOCR 未安装"
            }
            return

        if self.ocr_service is None:
            self.ocr_service = get_paddleocr_service(use_gpu=True, gpu_id=0, lang="ch")

        total = len(file_paths)
        for i, file_path in enumerate(file_paths, 1):
            try:
                yield {
                    "type": "progress",
                    "message": f"正在处理 {i}/{total}: {os.path.basename(file_path)}"
                }

                result = self.ocr_service.recognize_text(file_path)

                yield {
                    "type": "result",
                    "file_path": file_path,
                    "success": result.success,
                    "text": result.text if result.success else None,
                    "error": result.metadata.get("error") if not result.success else None,
                    "processing_time": result.processing_time
                }

            except Exception as e:
                self.logger.error(f"处理文件失败 {file_path}: {e}")
                yield {
                    "type": "result",
                    "file_path": file_path,
                    "success": False,
                    "error": str(e)
                }

    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return ["jpg", "jpeg", "png", "bmp", "tiff", "pdf"]

    def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "agent_type": "ocr",
            "description": "OCR 文字识别助手，使用 PaddleOCR-VL 模型",
            "capabilities": [
                "文本检测和识别（中英文混合）",
                "版面分析和结构化输出",
                "表格识别",
                "公式识别",
                "批量文件处理"
            ],
            "supported_formats": self.get_supported_formats(),
            "output_formats": ["text", "markdown", "json", "structured"],
            "requires_gpu": True,
            "gpu_memory": "8GB+ recommended",
            "model": "PaddleOCR-VL"
        })
        return base_info


# ==================== 全局实例 ====================

_ocr_agent: Optional[OCRAgent] = None


def get_ocr_agent() -> OCRAgent:
    """获取 OCR Agent 单例"""
    global _ocr_agent
    if _ocr_agent is None:
        _ocr_agent = OCRAgent()
    return _ocr_agent


# 便捷函数
async def recognize_file(
    file_path: str,
    output_format: str = "text",
    use_structure: bool = False
) -> Dict[str, Any]:
    """
    识别文件（便捷函数）

    Args:
        file_path: 文件路径
        output_format: 输出格式
        use_structure: 是否使用结构化识别

    Returns:
        Dict: 识别结果
    """
    agent = get_ocr_agent()

    request_data = {
        "file_path": file_path,
        "output_format": output_format,
        "use_structure": use_structure,
        "save_result": True
    }

    context = {
        "user_id": "api",
        "session_id": f"batch_{datetime.now().timestamp()}"
    }

    results = []
    async for event in agent.process_request(request_data, context):
        results.append(event)

    return {
        "success": True,
        "results": results
    }


async def recognize_batch(
    file_paths: List[str],
    output_format: str = "text"
) -> List[Dict[str, Any]]:
    """
    批量识别文件（便捷函数）

    Args:
        file_paths: 文件路径列表
        output_format: 输出格式

    Returns:
        List[Dict]: 识别结果列表
    """
    agent = get_ocr_agent()

    results = []
    async for event in agent.batch_process(file_paths, OutputFormat(output_format)):
        results.append(event)

    return results

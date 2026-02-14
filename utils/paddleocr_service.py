"""
PaddleOCR-VL 服务封装
支持本地 GPU 加速的 OCR 识别
适用于 RTX 5070 8GB 显存

功能：
1. 文本检测和识别（中英文混合）
2. 表格识别
3. 版面分析
4. 文档结构化输出

依赖安装：
pip install paddlepaddle-gpu paddleocr paddlepaddle
pip install pillow opencv-python-headless python-multipart
pip install transformers torch torchvision

代码作者：Claude
创建时间：2026年2月7日
"""
import os
import io
import base64
import hashlib
import json
from typing import Dict, List, Any, Optional, Union, BinaryIO
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# numpy 用于类型注解，需要始终导入
import numpy as np

try:
    from paddleocr import PaddleOCR, PPStructure
    import cv2
    from PIL import Image
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR 未安装，请运行: pip install paddleocr paddlepaddle-gpu")


class OCRMode(Enum):
    """OCR 模式"""
    TEXT_ONLY = "text_only"           # 仅文本识别
    STRUCTURE = "structure"           # 版面分析+结构化
    TABLE = "table"                  # 表格识别
    FORMULA = "formula"              # 公式识别


class ImageFormat(Enum):
    """支持的图片格式"""
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    BMP = "bmp"
    TIFF = "tiff"
    PDF = "pdf"


@dataclass
class OCRTextBox:
    """OCR 文本框"""
    text: str                        # 识别的文本
    box: List[List[int]]             # 边界坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    confidence: float                # 置信度 0-1
    position: tuple                  # (x, y) 中心点位置

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "box": self.box,
            "confidence": self.confidence,
            "position": self.position
        }


@dataclass
class OCRResult:
    """OCR 识别结果"""
    success: bool                    # 是否成功
    text: str                        # 完整文本（按阅读顺序拼接）
    text_boxes: List[OCRTextBox]     # 所有文本框
    layout: List[Dict[str, Any]]     # 版面分析结果（结构化模式）
    tables: List[Dict[str, Any]]     # 表格数据（结构化模式）
    formulas: List[str]              # 公式数据（结构化模式）
    metadata: Dict[str, Any]         # 元数据
    processing_time: float           # 处理耗时（秒）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "text": self.text,
            "text_boxes": [box.to_dict() for box in self.text_boxes],
            "layout": self.layout,
            "tables": self.tables,
            "formulas": self.formulas,
            "metadata": self.metadata,
            "processing_time": self.processing_time
        }


class PaddleOCRService:
    """
    PaddleOCR-VL 服务类

    特性：
    1. GPU 加速支持（适用于 RTX 5070 8GB）
    2. 多语言识别（中英文混合）
    3. 版面分析和结构化输出
    4. 表格识别
    5. 公式识别
    """

    def __init__(
        self,
        use_gpu: bool = True,
        gpu_id: int = 0,
        lang: str = "ch",  # ch=中英文混合
        show_log: bool = False,
        det_model_dir: Optional[str] = None,
        rec_model_dir: Optional[str] = None,
        cls_model_dir: Optional[str] = None,
        use_angle_cls: bool = True,
        max_batch_size: int = 10
    ):
        """
        初始化 PaddleOCR 服务

        Args:
            use_gpu: 是否使用 GPU
            gpu_id: GPU 设备 ID
            lang: 语言 ('ch'=中英文, 'en'=英文, 'japanese'=日语等)
            show_log: 是否显示日志
            det_model_dir: 检测模型路径
            rec_model_dir: 识别模型路径
            cls_model_dir: 方向分类器路径
            use_angle_cls: 是否使用方向分类器
            max_batch_size: 最大批处理大小
        """
        if not PADDLEOCR_AVAILABLE:
            raise RuntimeError(
                "PaddleOCR 未安装。请运行: pip install paddleocr paddlepaddle-gpu"
            )

        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.lang = lang
        self.show_log = show_log
        self.max_batch_size = max_batch_size

        # 初始化基础 OCR 模型
        self.ocr_model = None
        self.structure_model = None

        self.logger = logging.getLogger(__name__)
        self._initialize_models()

        # 存储识别历史（用于缓存）
        self._result_cache: Dict[str, OCRResult] = {}

    def _initialize_models(self):
        """初始化 OCR 模型"""
        try:
            # 初始化文本检测+识别模型
            self.ocr_model = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id,
                show_log=self.show_log,
                det_model_dir=None,  # 使用默认模型（自动下载）
                rec_model_dir=None,
                cls_model_dir=None,
            )

            # 初始化版面分析模型
            self.structure_model = PPStructure(
                show_log=self.show_log,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id,
                image_orientation=True,
                layout=True,
                table=True,
                ocr=True,
            )

            self.logger.info(f"PaddleOCR 服务初始化成功 (GPU: {self.use_gpu}, lang: {self.lang})")

        except Exception as e:
            self.logger.error(f"PaddleOCR 初始化失败: {e}")
            raise

    def _load_image(self, image_source: Union[str, bytes, BinaryIO, np.ndarray]) -> np.ndarray:
        """
        加载图片

        Args:
            image_source: 图片源（文件路径、字节流、或 numpy 数组）

        Returns:
            np.ndarray: 图片数组
        """
        if isinstance(image_source, np.ndarray):
            return image_source

        if isinstance(image_source, bytes):
            image_source = io.BytesIO(image_source)

        if hasattr(image_source, 'read'):
            # 文件对象或 BytesIO
            image_bytes = image_source.read()
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        # 文件路径
        if isinstance(image_source, str):
            if not os.path.exists(image_source):
                raise FileNotFoundError(f"图片文件不存在: {image_source}")
            return cv2.imread(image_source)

        raise ValueError(f"不支持的图片源类型: {type(image_source)}")

    def _generate_cache_key(self, image_source: Union[str, bytes]) -> str:
        """生成缓存键"""
        if isinstance(image_source, str):
            return f"file_{image_source}_{os.path.getmtime(image_source)}"
        elif isinstance(image_source, bytes):
            return f"bytes_{hashlib.md5(image_source).hexdigest()}"
        return f"unknown_{datetime.now().timestamp()}"

    def recognize_text(
        self,
        image_source: Union[str, bytes, BinaryIO, np.ndarray],
        use_cache: bool = True
    ) -> OCRResult:
        """
        文本识别（基础模式）

        Args:
            image_source: 图片源
            use_cache: 是否使用缓存

        Returns:
            OCRResult: 识别结果
        """
        start_time = datetime.now()

        try:
            # 检查缓存
            cache_key = self._generate_cache_key(image_source) if use_cache else None
            if cache_key and cache_key in self._result_cache:
                self.logger.info(f"从缓存返回结果: {cache_key}")
                return self._result_cache[cache_key]

            # 加载图片
            image = self._load_image(image_source)

            # 执行 OCR
            result = self.ocr_model.ocr(image, cls=True)

            # 解析结果
            text_boxes = []
            full_text_parts = []

            if result and result[0]:
                for line in result[0]:
                    box = line[0]  # 边界坐标
                    text_info = line[1]  # (文本, 置信度)
                    text = text_info[0]
                    confidence = float(text_info[1])

                    # 计算中心点
                    x = int(sum([p[0] for p in box]) / 4)
                    y = int(sum([p[1] for p in box]) / 4)

                    text_box = OCRTextBox(
                        text=text,
                        box=[[int(p[0]), int(p[1])] for p in box],
                        confidence=confidence,
                        position=(x, y)
                    )
                    text_boxes.append(text_box)
                    full_text_parts.append(text)

            # 按位置排序文本（从上到下，从左到右）
            text_boxes.sort(key=lambda b: (b.position[1], b.position[0]))
            full_text = "\n".join([box.text for box in text_boxes])

            processing_time = (datetime.now() - start_time).total_seconds()

            ocr_result = OCRResult(
                success=True,
                text=full_text,
                text_boxes=text_boxes,
                layout=[],
                tables=[],
                formulas=[],
                metadata={
                    "mode": "text_only",
                    "image_shape": image.shape if hasattr(image, 'shape') else None,
                    "box_count": len(text_boxes),
                    "timestamp": datetime.now().isoformat()
                },
                processing_time=processing_time
            )

            # 缓存结果
            if cache_key:
                self._result_cache[cache_key] = ocr_result

            return ocr_result

        except Exception as e:
            self.logger.error(f"文本识别失败: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return OCRResult(
                success=False,
                text="",
                text_boxes=[],
                layout=[],
                tables=[],
                formulas=[],
                metadata={"error": str(e)},
                processing_time=processing_time
            )

    def recognize_structure(
        self,
        image_source: Union[str, bytes, BinaryIO, np.ndarray]
    ) -> OCRResult:
        """
        结构化识别（版面分析）

        Args:
            image_source: 图片源

        Returns:
            OCRResult: 识别结果（包含版面信息）
        """
        start_time = datetime.now()

        try:
            # 加载图片
            image = self._load_image(image_source)

            # 执行版面分析
            result = self.structure_model(image)

            # 解析结果
            layout = []
            tables = []
            formulas = []
            text_boxes = []
            full_text_parts = []

            for item in result:
                item_type = item.get('type', '')
                item_data = item.get('res', {})
                item_box = item.get('bbox', [])

                if item_type == 'text':
                    # 文本区域
                    for line in item_data:
                        if isinstance(line, dict):
                            text = line.get('text', '')
                            confidence = line.get('score', 0.0)
                            box = line.get('bbox', [])

                            if text:
                                text_boxes.append(OCRTextBox(
                                    text=text,
                                    box=[[int(p), int(q)] for p, q in zip(box[0::2], box[1::2])],
                                    confidence=confidence,
                                    position=(int(box[0]), int(box[1]))
                                ))
                                full_text_parts.append(text)

                elif item_type == 'table':
                    # 表格区域
                    html_table = item_data.get('html', '')
                    tables.append({
                        "bbox": item_box,
                        "html": html_table,
                        "type": "table"
                    })

                elif item_type == 'figure':
                    # 图片区域
                    layout.append({
                        "type": "figure",
                        "bbox": item_box
                    })

                elif item_type == 'formula':
                    # 公式区域
                    formula_text = item_data.get('text', '')
                    formulas.append(formula_text)
                    layout.append({
                        "type": "formula",
                        "bbox": item_box,
                        "content": formula_text
                    })

            full_text = "\n".join(full_text_parts)

            processing_time = (datetime.now() - start_time).total_seconds()

            return OCRResult(
                success=True,
                text=full_text,
                text_boxes=text_boxes,
                layout=layout,
                tables=tables,
                formulas=formulas,
                metadata={
                    "mode": "structure",
                    "image_shape": image.shape if hasattr(image, 'shape') else None,
                    "layout_count": len(layout),
                    "table_count": len(tables),
                    "formula_count": len(formulas),
                    "timestamp": datetime.now().isoformat()
                },
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.error(f"结构化识别失败: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return OCRResult(
                success=False,
                text="",
                text_boxes=[],
                layout=[],
                tables=[],
                formulas=[],
                metadata={"error": str(e)},
                processing_time=processing_time
            )

    def recognize_batch(
        self,
        image_sources: List[Union[str, bytes, BinaryIO, np.ndarray]],
        mode: OCRMode = OCRMode.TEXT_ONLY
    ) -> List[OCRResult]:
        """
        批量识别

        Args:
            image_sources: 图片源列表
            mode: 识别模式

        Returns:
            List[OCRResult]: 识别结果列表
        """
        results = []

        # 分批处理
        for i in range(0, len(image_sources), self.max_batch_size):
            batch = image_sources[i:i + self.max_batch_size]

            if mode == OCRMode.STRUCTURE:
                batch_results = [self.recognize_structure(img) for img in batch]
            else:
                batch_results = [self.recognize_text(img) for img in batch]

            results.extend(batch_results)

        return results

    def export_to_markdown(self, result: OCRResult) -> str:
        """
        导出为 Markdown 格式

        Args:
            result: OCR 结果

        Returns:
            str: Markdown 文本
        """
        md_lines = []

        # 添加标题
        md_lines.append(f"# OCR 识别结果\n")
        md_lines.append(f"**识别时间**: {result.metadata.get('timestamp', 'N/A')}\n")
        md_lines.append(f"**处理耗时**: {result.processing_time:.2f}秒\n")
        md_lines.append(f"**文本框数量**: {len(result.text_boxes)}\n\n")
        md_lines.append("---\n\n")

        # 添加文本
        if result.text:
            md_lines.append("## 识别文本\n\n")
            md_lines.append(result.text)
            md_lines.append("\n\n")

        # 添加表格
        if result.tables:
            md_lines.append("## 表格\n\n")
            for i, table in enumerate(result.tables):
                md_lines.append(f"### 表格 {i + 1}\n\n")
                md_lines.append(table.get('html', ''))
                md_lines.append("\n\n")

        # 添加公式
        if result.formulas:
            md_lines.append("## 公式\n\n")
            for i, formula in enumerate(result.formulas):
                md_lines.append(f"### 公式 {i + 1}\n\n")
                md_lines.append(f"$$\n{formula}\n$$\n\n")

        return "".join(md_lines)

    def export_to_json(self, result: OCRResult) -> str:
        """导出为 JSON 格式"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    def clear_cache(self):
        """清除缓存"""
        self._result_cache.clear()
        self.logger.info("OCR 结果缓存已清除")


# ==================== 全局单例 ====================

_paddleocr_service: Optional[PaddleOCRService] = None


def get_paddleocr_service(
    use_gpu: bool = True,
    gpu_id: int = 0,
    lang: str = "ch"
) -> PaddleOCRService:
    """
    获取 PaddleOCR 服务单例

    Args:
        use_gpu: 是否使用 GPU
        gpu_id: GPU 设备 ID
        lang: 语言设置

    Returns:
        PaddleOCRService: OCR 服务实例
    """
    global _paddleocr_service

    if _paddleocr_service is None:
        _paddleocr_service = PaddleOCRService(
            use_gpu=use_gpu,
            gpu_id=gpu_id,
            lang=lang
        )

    return _paddleocr_service


def is_paddleocr_available() -> bool:
    """检查 PaddleOCR 是否可用"""
    return PADDLEOCR_AVAILABLE

"""
OCR API 路由
提供文件上传和 OCR 识别的接口

端点：
- POST /juben/ocr/upload        # 上传文件进行 OCR
- POST /juben/ocr/batch         # 批量 OCR
- GET  /juben/ocr/status        # 查询 OCR 状态
- GET  /juben/ocr/result/{id}   # 获取识别结果
- GET  /juben/ocr/download/{id} # 下载识别结果

代码作者：Claude
创建时间：2026年2月7日
"""
import os
import io
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field
import logging

from agents.ocr_agent import get_ocr_agent, OutputFormat, is_paddleocr_available
from utils.agent_dispatch import build_agent_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["OCR 识别"])


# ==================== 请求/响应模型 ====================

class OCRRequest(BaseModel):
    """OCR 请求"""
    output_format: str = Field(default="text", description="输出格式: text/markdown/json/structured")
    use_structure: bool = Field(default=False, description="是否使用结构化识别")
    save_result: bool = Field(default=True, description="是否保存结果")


class OCRBatchRequest(BaseModel):
    """批量 OCR 请求"""
    file_paths: List[str] = Field(..., description="文件路径列表")
    output_format: str = Field(default="text", description="输出格式")


class OCRStatusResponse(BaseModel):
    """OCR 状态响应"""
    available: bool
    gpu_enabled: bool
    supported_formats: List[str]
    output_formats: List[str]


class OCRResultResponse(BaseModel):
    """OCR 结果响应"""
    task_id: str
    status: str
    success: bool
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    saved_paths: Optional[Dict[str, str]] = None


# ==================== 内存存储 ====================

# 任务状态存储（生产环境应使用 Redis）
task_store: Dict[str, Dict[str, Any]] = {}


# ==================== API 端点 ====================

@router.get("/status")
async def get_ocr_status() -> OCRStatusResponse:
    """
    获取 OCR 服务状态

    返回 OCR 可用性、GPU 支持等信息
    """
    try:
        available = is_paddleocr_available()

        return OCRStatusResponse(
            available=available,
            gpu_enabled=available,  # 如果可用则默认启用 GPU
            supported_formats=["jpg", "jpeg", "png", "bmp", "tiff", "pdf"],
            output_formats=["text", "markdown", "json", "structured"]
        )
    except Exception as e:
        logger.error(f"获取 OCR 状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_and_recognize(
    file: UploadFile = File(..., description="上传的图片文件"),
    output_format: str = Form(default="text", description="输出格式"),
    use_structure: bool = Form(default=False, description="是否使用结构化识别"),
    save_result: bool = Form(default=True, description="是否保存结果")
):
    """
    上传文件并进行 OCR 识别

    Args:
        file: 上传的图片文件
        output_format: 输出格式
        use_structure: 是否使用结构化识别
        save_result: 是否保存结果

    Returns:
        StreamingResponse: 流式 OCR 结果
    """
    if not is_paddleocr_available():
        raise HTTPException(
            status_code=503,
            detail="OCR 服务不可用，请先安装 PaddleOCR"
        )

    # 生成任务 ID
    task_id = str(uuid.uuid4())

    try:
        # 读取文件内容
        file_content = await file.read()

        # 获取 Agent
        agent = get_ocr_agent()

        # 构建请求数据
        request_data = {
            "file": file_content,
            "filename": file.filename,
            "output_format": output_format,
            "use_structure": use_structure,
            "save_result": save_result
        }

        # 构建上下文
        context = {
            "user_id": "api",
            "session_id": task_id
        }

        # 初始化任务状态
        task_store[task_id] = {
            "task_id": task_id,
            "status": "processing",
            "filename": file.filename,
            "created_at": datetime.now().isoformat(),
            "result": None
        }

        async def event_stream():
            """生成 SSE 事件流"""
            try:
                async for event in build_agent_generator(agent, request_data, context):
                    # 处理不同类型的事件
                    event_type = event.get("event_type", "message")
                    event_data = event.get("data", "")
                    event_metadata = event.get("metadata", {})

                    # 发送 SSE 事件
                    sse_data = {
                        "event": event_type,
                        "data": {
                            "content": event_data,
                            "metadata": event_metadata,
                            "timestamp": event.get("timestamp", datetime.now().isoformat())
                        }
                    }

                    yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"

                    # 更新任务状态
                    if event_type == "content":
                        task_store[task_id]["status"] = "completed"
                        task_store[task_id]["result"] = {
                            "text": event_data,
                            "metadata": event_metadata
                        }
                    elif event_type == "error":
                        task_store[task_id]["status"] = "failed"
                        task_store[task_id]["error"] = event_data

                # 发送完成事件
                complete_event = {
                    "event": "complete",
                    "data": {
                        "task_id": task_id,
                        "status": task_store[task_id]["status"]
                    }
                }
                yield f"data: {json.dumps(complete_event, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"OCR 处理失败: {e}")
                task_store[task_id]["status"] = "failed"
                task_store[task_id]["error"] = str(e)

                error_event = {
                    "event": "error",
                    "data": {
                        "error": str(e),
                        "task_id": task_id
                    }
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Task-ID": task_id
            }
        )

    except Exception as e:
        logger.error(f"文件上传处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_recognize(request: OCRBatchRequest):
    """
    批量 OCR 识别

    Args:
        request: 批量 OCR 请求

    Returns:
        StreamingResponse: 流式批量处理结果
    """
    if not is_paddleocr_available():
        raise HTTPException(
            status_code=503,
            detail="OCR 服务不可用"
        )

    try:
        agent = get_ocr_agent()

        async def event_stream():
            """生成批量处理事件流"""
            try:
                total = len(request.file_paths)
                completed = 0

                async for event in agent.batch_process(
                    request.file_paths,
                    OutputFormat(request.output_format)
                ):
                    event_type = event.get("type")
                    sse_data = {
                        "event": event_type,
                        "data": event
                    }
                    yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"

                    if event_type == "result":
                        completed += 1
                        progress = {
                            "event": "progress",
                            "data": {
                                "completed": completed,
                                "total": total,
                                "percentage": int(completed / total * 100)
                            }
                        }
                        yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

                # 发送完成事件
                complete_event = {
                    "event": "batch_complete",
                    "data": {
                        "total": total,
                        "completed": completed
                    }
                }
                yield f"data: {json.dumps(complete_event, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"批量处理失败: {e}")
                error_event = {
                    "event": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:
        logger.error(f"批量 OCR 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{task_id}")
async def get_ocr_result(task_id: str) -> OCRResultResponse:
    """
    获取 OCR 识别结果

    Args:
        task_id: 任务 ID

    Returns:
        OCRResultResponse: 识别结果
    """
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_store[task_id]

    return OCRResultResponse(
        task_id=task_id,
        status=task["status"],
        success=task["status"] == "completed",
        text=task.get("result", {}).get("text"),
        metadata=task.get("result", {}).get("metadata"),
        error=task.get("error"),
        saved_paths=task.get("saved_paths")
    )


@router.get("/download/{task_id}")
async def download_ocr_result(
    task_id: str,
    format: str = "txt"
):
    """
    下载 OCR 识别结果

    Args:
        task_id: 任务 ID
        format: 文件格式 (txt/md/json)

    Returns:
        FileResponse: 结果文件
    """
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = task_store[task_id]

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    saved_paths = task.get("saved_paths", {})

    # 查找对应格式的文件
    file_path = None
    media_type = "text/plain"

    if format == "json" and "json" in saved_paths:
        file_path = saved_paths["json"]
        media_type = "application/json"
    elif format in saved_paths:
        file_path = saved_paths[format]
        if format == "md":
            media_type = "text/markdown"
    else:
        # 尝试从输出目录查找
        output_dir = Path("outputs/ocr")
        potential_files = list(output_dir.glob(f"*{task_id}*.{format}"))
        if potential_files:
            file_path = str(potential_files[0])

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path)
    )


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务记录

    Args:
        task_id: 任务 ID
    """
    if task_id in task_store:
        del task_store[task_id]
        return {"success": True, "message": "任务已删除"}

    raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/tasks")
async def list_tasks(limit: int = 50) -> Dict[str, Any]:
    """
    列出所有任务

    Args:
        limit: 返回数量限制

    Returns:
        Dict: 任务列表
    """
    tasks = list(task_store.values())
    tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "success": True,
        "data": tasks[:limit],
        "total": len(tasks)
    }

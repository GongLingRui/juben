"""
工作流相关 API 路由
处理多步骤工作流的执行和管理
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from utils.logger import get_logger
from utils.error_handler import handle_error

logger = get_logger("WorkflowAPI")

# 创建路由器
router = APIRouter(prefix="/workflows", tags=["Workflows"])


class WorkflowStartRequest(BaseModel):
    """启动工作流请求"""
    workflow_type: str = Field(..., description="工作流类型")
    input_data: Dict[str, Any] = Field(default_factory=dict)
    user_id: str
    session_id: str
    options: Optional[Dict[str, Any]] = None


class WorkflowStepRequest(BaseModel):
    """工作流步骤请求"""
    workflow_id: str
    step_index: int
    input_data: Optional[Dict[str, Any]] = None


@router.post("/start")
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks
):
    """
    启动工作流

    Args:
        request: 工作流启动请求
        background_tasks: 后台任务

    Returns:
        工作流执行结果
    """
    try:
        logger.info(f"启动工作流: type={request.workflow_type}, user_id={request.user_id}")

        # 获取工作流管理器
        from agents.workflow_manager import WorkflowManager
        workflow_manager = WorkflowManager()

        # 检查工作流是否支持
        supported = workflow_manager.get_supported_workflows()
        if request.workflow_type not in supported:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的工作流类型: {request.workflow_type}"
            )

        # 获取工作流定义
        workflow_def = workflow_manager.get_workflow_definition(request.workflow_type)
        if not workflow_def:
            raise HTTPException(
                status_code=404,
                detail=f"工作流定义未找到: {request.workflow_type}"
            )

        # 执行工作流
        result = await workflow_manager.execute_workflow(
            workflow_type=request.workflow_type,
            input_data=request.input_data,
            user_id=request.user_id,
            session_id=request.session_id,
            options=request.options or {}
        )

        return {
            "success": True,
            "workflow_id": result.get("workflow_id"),
            "status": result.get("status"),
            "result": result.get("result")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动工作流失败: {str(e)}")
        error_result = await handle_error(e, "workflow_start", {
            "workflow_type": request.workflow_type,
            "user_id": request.user_id
        })
        raise HTTPException(status_code=500, detail=error_result.get("message", "启动工作流失败"))


@router.post("/execute-step")
async def execute_workflow_step(request: WorkflowStepRequest):
    """
    执行工作流的单个步骤

    Args:
        request: 步骤执行请求

    Returns:
        步骤执行结果
    """
    try:
        logger.info(f"执行工作流步骤: workflow_id={request.workflow_id}, step={request.step_index}")

        # 获取工作流管理器
        from agents.workflow_manager import WorkflowManager
        workflow_manager = WorkflowManager()

        # 执行步骤
        result = await workflow_manager.execute_step(
            workflow_id=request.workflow_id,
            step_index=request.step_index,
            input_data=request.input_data or {}
        )

        return {
            "success": True,
            "step_index": request.step_index,
            "result": result
        }

    except Exception as e:
        logger.error(f"执行工作流步骤失败: {str(e)}")
        raise HTTPException(status_code=500, detail="执行步骤失败")


@router.get("/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    获取工作流执行状态

    Args:
        workflow_id: 工作流 ID

    Returns:
        工作流状态
    """
    try:
        # 从存储获取工作流状态
        from utils.storage_manager import get_storage
        storage = get_storage()

        status = await storage.get_workflow_status(workflow_id)

        if not status:
            raise HTTPException(status_code=404, detail="工作流不存在")

        return {
            "success": True,
            "workflow": status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取工作流状态失败")


@router.get("/list")
async def list_workflows():
    """
    获取支持的工作流列表

    Returns:
        工作流列表
    """
    try:
        from agents.workflow_manager import WorkflowManager
        workflow_manager = WorkflowManager()

        workflows = workflow_manager.get_supported_workflows()

        workflow_details = []
        for wf_type in workflows:
            definition = workflow_manager.get_workflow_definition(wf_type)
            if definition:
                workflow_details.append({
                    "type": wf_type,
                    "name": definition.get("name"),
                    "description": definition.get("description"),
                    "steps": definition.get("steps", []),
                    "estimated_time": definition.get("estimated_time")
                })

        return {
            "success": True,
            "workflows": workflow_details
        }

    except Exception as e:
        logger.error(f"获取工作流列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取工作流列表失败")


@router.delete("/{workflow_id}")
async def cancel_workflow(workflow_id: str):
    """
    取消正在执行的工作流

    Args:
        workflow_id: 工作流 ID

    Returns:
        取消结果
    """
    try:
        from agents.workflow_manager import WorkflowManager
        workflow_manager = WorkflowManager()

        cancelled = await workflow_manager.cancel_workflow(workflow_id)

        logger.info(f"取消工作流: workflow_id={workflow_id}, success={cancelled}")

        return {
            "success": cancelled,
            "message": "工作流已取消" if cancelled else "工作流不存在或已完成"
        }

    except Exception as e:
        logger.error(f"取消工作流失败: {str(e)}")
        raise HTTPException(status_code=500, detail="取消工作流失败")


# 导出
__all__ = ["router"]

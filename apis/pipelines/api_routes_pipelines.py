"""
创作管线 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from utils.pipeline_manager import get_pipeline_manager

router = APIRouter(prefix="/juben/pipelines", tags=["创作管线"])


class PipelineRunRequest(BaseModel):
    template_id: str = Field(..., description="模板ID")
    user_input: str = Field(..., description="用户输入")
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    project_id: Optional[str] = Field(None, description="项目ID")


@router.get("/templates")
async def list_templates():
    manager = get_pipeline_manager()
    return {"success": True, "data": manager.list_templates()}


@router.post("/run")
async def run_pipeline(request: PipelineRunRequest):
    manager = get_pipeline_manager()
    try:
        result = await manager.run_pipeline(
            template_id=request.template_id,
            user_input=request.user_input,
            user_id=request.user_id,
            session_id=request.session_id,
            project_id=request.project_id
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs")
async def list_runs(project_id: Optional[str] = Query(None)):
    manager = get_pipeline_manager()
    return {"success": True, "data": manager.list_runs(project_id)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    manager = get_pipeline_manager()
    run = manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    return {"success": True, "data": run}

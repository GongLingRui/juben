"""
项目API路由
提供项目的CRUD操作API端点
"""

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import Optional, List, Dict, Any
import asyncio
import uuid
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse

from apis.core.schemas import (
    BaseResponse,
    Project,
    ProjectFile,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectFileCreateRequest,
    ProjectFileUpdateRequest,
    ProjectExportRequest,
    ProjectSearchRequest,
    ProjectDuplicateRequest,
    ProjectTemplateRequest,
    ProjectFromTemplateRequest,
    ProjectRestoreRequest,
    ProjectMember,
    ProjectMemberUpdateRequest,
    ProjectStatus,
    FileType
)

from utils.project_manager import get_project_manager
from utils.rag_indexer import get_rag_indexer

logger = logging.getLogger(__name__)

REINDEX_TASKS: Dict[str, Dict[str, Any]] = {}
REINDEX_TASKS_FILE = Path("logs/reindex_tasks.json")
REINDEX_WS: Dict[str, List[WebSocket]] = {}
MAX_TASK_RECORDS = int(os.getenv("REINDEX_TASKS_MAX_RECORDS", "200"))


def _load_tasks() -> None:
    try:
        if REINDEX_TASKS_FILE.exists():
            loaded = json.loads(REINDEX_TASKS_FILE.read_text(encoding="utf-8"))
            for task_id, task in loaded.items():
                if task.get("status") == "running":
                    task["status"] = "failed"
                    task["error"] = "服务重启，任务中断"
                    task["finished_at"] = datetime.now().isoformat()
            REINDEX_TASKS.update(loaded)
    except Exception as e:
        logger.warning(f"加载索引任务失败: {e}")


def _save_tasks() -> None:
    try:
        # 清理旧任务记录（保留运行中的 + 最近完成的）
        running = {k: v for k, v in REINDEX_TASKS.items() if v.get("status") == "running"}
        finished = [v for v in REINDEX_TASKS.values() if v.get("status") != "running"]
        finished.sort(key=lambda t: t.get("finished_at") or t.get("started_at") or "", reverse=True)
        trimmed = finished[:MAX_TASK_RECORDS]
        REINDEX_TASKS.clear()
        REINDEX_TASKS.update({t["task_id"]: t for t in trimmed})
        REINDEX_TASKS.update(running)

        REINDEX_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        REINDEX_TASKS_FILE.write_text(json.dumps(REINDEX_TASKS, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"保存索引任务失败: {e}")


def _update_task(task_id: str, **kwargs) -> None:
    if task_id not in REINDEX_TASKS:
        return
    REINDEX_TASKS[task_id].update(kwargs)
    _save_tasks()
    # 推送进度
    if task_id in REINDEX_WS:
        message = json.dumps(REINDEX_TASKS[task_id], ensure_ascii=False)
        disconnected = []
        for ws in REINDEX_WS[task_id]:
            try:
                asyncio.create_task(ws.send_text(message))
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in REINDEX_WS.get(task_id, []):
                REINDEX_WS[task_id].remove(ws)


def _start_reindex_task(coro, task_type: str, project_id: Optional[str] = None, task_id: Optional[str] = None) -> str:
    task_id = task_id or str(uuid.uuid4())
    REINDEX_TASKS[task_id] = {
        "task_id": task_id,
        "type": task_type,
        "project_id": project_id,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "total_files": 0,
        "processed_files": 0,
        "progress": 0.0,
        "result": None,
        "error": None
    }
    _save_tasks()

    async def runner():
        try:
            result = await coro
            total = REINDEX_TASKS.get(task_id, {}).get("total_files", 0)
            processed = REINDEX_TASKS.get(task_id, {}).get("processed_files", total)
            _update_task(
                task_id,
                status="completed",
                result=result,
                processed_files=processed,
                progress=100.0
            )
        except Exception as e:
            _update_task(task_id, status="failed", error=str(e))
        finally:
            _update_task(task_id, finished_at=datetime.now().isoformat())

    asyncio.create_task(runner())
    return task_id


_load_tasks()


async def _index_project_file(file_data: Dict[str, Any]) -> None:
    try:
        indexer = get_rag_indexer()
        await indexer.index_project_file(
            project_id=file_data.get("project_id", ""),
            file_id=file_data.get("id", ""),
            filename=file_data.get("filename", ""),
            content=file_data.get("content", ""),
            file_type=file_data.get("file_type"),
            agent_source=file_data.get("agent_source"),
            tags=file_data.get("tags", [])
        )
    except Exception as e:
        logger.warning(f"项目文件索引失败: {e}")


async def _remove_project_file_index(project_id: str, file_id: str) -> None:
    try:
        indexer = get_rag_indexer()
        await indexer.delete_project_file_chunks(project_id, file_id)
    except Exception as e:
        logger.warning(f"删除项目文件索引失败: {e}")


async def _reindex_project_files(project_id: str, task_id: Optional[str] = None) -> int:
    manager = get_project_manager()
    files = await manager.get_project_files(project_id)
    if task_id:
        _update_task(task_id, total_files=len(files), processed_files=0, progress=0.0)
    count = 0
    for file in files:
        try:
            await _index_project_file(file.dict())
            count += 1
            if task_id:
                processed = REINDEX_TASKS.get(task_id, {}).get("processed_files", 0) + 1
                total = REINDEX_TASKS.get(task_id, {}).get("total_files", len(files))
                progress = round(processed / total * 100, 2) if total else 100.0
                _update_task(task_id, processed_files=processed, progress=progress)
        except Exception as e:
            logger.warning(f"项目文件重建索引失败: {e}")
    return count


async def _reindex_all_projects(user_id: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, int]:
    manager = get_project_manager()
    projects = await manager.list_projects(user_id=user_id, status=None, page=1, page_size=100000)
    files_by_project = []
    total_files = 0
    for project in projects:
        project_files = await manager.get_project_files(project.id)
        total_files += len(project_files)
        for file in project_files:
            files_by_project.append((project.id, file))
    if task_id:
        _update_task(task_id, total_files=total_files, processed_files=0, progress=0.0)
    total_files = 0
    processed = 0
    for project_id, file in files_by_project:
        try:
            await _index_project_file(file.dict())
            total_files += 1
        except Exception as e:
            logger.warning(f"项目文件重建索引失败: {e}")
        processed += 1
        if task_id:
            progress = round(processed / (len(files_by_project) or 1) * 100, 2)
            _update_task(task_id, processed_files=processed, progress=progress)
    return {
        "projects": len(projects),
        "files": total_files
    }

router = APIRouter(prefix="/juben/projects", tags=["projects"])


# ==================== 项目CRUD ====================

@router.post("", response_model=BaseResponse)
async def create_project(request: ProjectCreateRequest, user_id: str = Query(default="default_user")):
    """
    创建新项目

    Args:
        request: 项目创建请求
        user_id: 用户ID

    Returns:
        BaseResponse: 包含创建的项目信息
    """
    try:
        manager = get_project_manager()
        project = await manager.create_project(
            name=request.name,
            user_id=user_id,
            description=request.description,
            tags=request.tags,
            metadata=request.metadata
        )

        return BaseResponse(
            success=True,
            message="项目创建成功",
            data=project.dict()
        )

    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    user_id: str = Query(default="default_user"),
    status: ProjectStatus = Query(default=ProjectStatus.ACTIVE),
    tags: Optional[List[str]] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """
    获取项目列表

    Args:
        user_id: 用户ID
        status: 项目状态过滤
        tags: 标签过滤
        page: 页码
        page_size: 每页数量

    Returns:
        ProjectListResponse: 项目列表响应
    """
    try:
        manager = get_project_manager()
        projects = await manager.list_projects(
            user_id=user_id,
            status=status,
            tags=tags,
            page=page,
            page_size=page_size
        )

        # 获取总数
        all_projects = await manager.list_projects(
            user_id=user_id,
            status=status,
            tags=tags
        )

        return ProjectListResponse(
            success=True,
            message="获取项目列表成功",
            projects=[p.dict() for p in projects],
            total=len(all_projects),
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str):
    """
    获取项目详情

    Args:
        project_id: 项目ID

    Returns:
        ProjectDetailResponse: 项目详情响应
    """
    try:
        manager = get_project_manager()
        project = await manager.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        files = await manager.get_project_files(project_id)

        return ProjectDetailResponse(
            success=True,
            message="获取项目详情成功",
            project=project.dict(),
            files=[f.dict() for f in files]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_project_members(project: Project) -> List[Dict[str, Any]]:
    members = project.metadata.get("members", []) if project.metadata else []
    if isinstance(members, list):
        return members
    return []


@router.get("/{project_id}/members", response_model=BaseResponse)
async def list_project_members(project_id: str):
    manager = get_project_manager()
    project = await manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return BaseResponse(success=True, message="OK", data=_get_project_members(project))


@router.post("/{project_id}/members", response_model=BaseResponse)
async def add_project_member(project_id: str, member: ProjectMember):
    manager = get_project_manager()
    project = await manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    members = _get_project_members(project)
    if any(m.get("user_id") == member.user_id for m in members):
        raise HTTPException(status_code=400, detail="成员已存在")
    members.append(member.dict())
    await manager.update_project(project_id, metadata={"members": members})
    return BaseResponse(success=True, message="OK", data=members)


@router.put("/{project_id}/members/{member_user_id}", response_model=BaseResponse)
async def update_project_member(project_id: str, member_user_id: str, updates: ProjectMemberUpdateRequest):
    manager = get_project_manager()
    project = await manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    members = _get_project_members(project)
    updated = False
    for item in members:
        if item.get("user_id") == member_user_id:
            if updates.role is not None:
                item["role"] = updates.role
            if updates.display_name is not None:
                item["display_name"] = updates.display_name
            updated = True
            break
    if not updated:
        raise HTTPException(status_code=404, detail="成员不存在")
    await manager.update_project(project_id, metadata={"members": members})
    return BaseResponse(success=True, message="OK", data=members)


@router.delete("/{project_id}/members/{member_user_id}", response_model=BaseResponse)
async def remove_project_member(project_id: str, member_user_id: str):
    manager = get_project_manager()
    project = await manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    members = _get_project_members(project)
    new_members = [m for m in members if m.get("user_id") != member_user_id]
    if len(new_members) == len(members):
        raise HTTPException(status_code=404, detail="成员不存在")
    await manager.update_project(project_id, metadata={"members": new_members})
    return BaseResponse(success=True, message="OK", data=new_members)


@router.put("/{project_id}", response_model=BaseResponse)
async def update_project(project_id: str, request: ProjectUpdateRequest):
    """
    更新项目信息

    Args:
        project_id: 项目ID
        request: 更新请求

    Returns:
        BaseResponse: 更新结果
    """
    try:
        manager = get_project_manager()
        project = await manager.update_project(
            project_id=project_id,
            name=request.name,
            description=request.description,
            status=request.status,
            tags=request.tags,
            metadata=request.metadata
        )

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        return BaseResponse(
            success=True,
            message="项目更新成功",
            data=project.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}", response_model=BaseResponse)
async def delete_project(
    project_id: str,
    permanent: bool = Query(default=False)
):
    """
    删除项目

    Args:
        project_id: 项目ID
        permanent: 是否永久删除

    Returns:
        BaseResponse: 删除结果
    """
    try:
        manager = get_project_manager()
        success = await manager.delete_project(project_id, permanent=permanent)

        if not success:
            raise HTTPException(status_code=404, detail="项目不存在")

        return BaseResponse(
            success=True,
            message=f"项目已{'永久' if permanent else '软'}删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 项目文件管理 ====================

@router.get("/{project_id}/files", response_model=BaseResponse)
async def get_project_files(
    project_id: str,
    file_type: Optional[FileType] = None
):
    """
    获取项目文件列表

    Args:
        project_id: 项目ID
        file_type: 文件类型过滤

    Returns:
        BaseResponse: 文件列表响应
    """
    try:
        manager = get_project_manager()
        files = await manager.get_project_files(project_id, file_type)

        return BaseResponse(
            success=True,
            message="获取文件列表成功",
            data=[f.dict() for f in files]
        )

    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/files/latest", response_model=BaseResponse)
async def get_latest_project_file(
    project_id: str,
    file_type: Optional[FileType] = None
):
    """
    获取项目最新文件
    """
    try:
        manager = get_project_manager()
        files = await manager.get_project_files(project_id, file_type)
        if not files:
            return BaseResponse(success=True, message="无文件", data=None)
        latest = sorted(files, key=lambda f: f.updated_at, reverse=True)[0]
        return BaseResponse(success=True, message="OK", data=latest.dict())
    except Exception as e:
        logger.error(f"获取最新文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/files/{file_id}", response_model=BaseResponse)
async def get_project_file(project_id: str, file_id: str):
    """
    获取单个文件

    Args:
        project_id: 项目ID
        file_id: 文件ID

    Returns:
        BaseResponse: 文件内容响应
    """
    try:
        manager = get_project_manager()
        file = await manager.get_file(project_id, file_id)

        if not file:
            raise HTTPException(status_code=404, detail="文件不存在")

        return BaseResponse(
            success=True,
            message="获取文件成功",
            data=file.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/files", response_model=BaseResponse)
async def create_project_file(
    project_id: str,
    request: ProjectFileCreateRequest
):
    """
    添加文件到项目

    Args:
        project_id: 项目ID
        request: 文件创建请求

    Returns:
        BaseResponse: 创建结果
    """
    try:
        manager = get_project_manager()
        file = await manager.add_file_to_project(
            project_id=project_id,
            filename=request.filename,
            file_type=request.file_type,
            content=request.content,
            agent_source=request.agent_source,
            tags=request.tags
        )

        if not file:
            raise HTTPException(status_code=404, detail="项目不存在")

        asyncio.create_task(_index_project_file(file.dict()))

        return BaseResponse(
            success=True,
            message="文件创建成功",
            data=file.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/files/{file_id}", response_model=BaseResponse)
async def update_project_file(
    project_id: str,
    file_id: str,
    request: ProjectFileUpdateRequest
):
    """
    更新项目文件

    Args:
        project_id: 项目ID
        file_id: 文件ID
        request: 更新请求

    Returns:
        BaseResponse: 更新结果
    """
    try:
        manager = get_project_manager()
        file = await manager.update_file(
            project_id=project_id,
            file_id=file_id,
            filename=request.filename,
            content=request.content,
            tags=request.tags
        )

        if not file:
            raise HTTPException(status_code=404, detail="文件不存在")

        if request.content is not None:
            asyncio.create_task(_index_project_file(file.dict()))

        return BaseResponse(
            success=True,
            message="文件更新成功",
            data=file.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/files/{file_id}", response_model=BaseResponse)
async def delete_project_file(project_id: str, file_id: str):
    """
    删除项目文件

    Args:
        project_id: 项目ID
        file_id: 文件ID

    Returns:
        BaseResponse: 删除结果
    """
    try:
        manager = get_project_manager()
        success = await manager.delete_file(project_id, file_id)

        if not success:
            raise HTTPException(status_code=404, detail="文件不存在")

        asyncio.create_task(_remove_project_file_index(project_id, file_id))

        return BaseResponse(
            success=True,
            message="文件删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/files/reindex", response_model=BaseResponse)
async def reindex_project_files(project_id: str):
    """
    重建单个项目所有文件的向量索引
    """
    try:
        task_id = str(uuid.uuid4())
        task_id = _start_reindex_task(
            _reindex_project_files(project_id, task_id=task_id),
            task_type="project_reindex",
            project_id=project_id,
            task_id=task_id
        )
        return BaseResponse(
            success=True,
            message="已开始重建项目文件索引",
            data={"project_id": project_id, "task_id": task_id}
        )
    except Exception as e:
        logger.error(f"重建项目索引失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex-all", response_model=BaseResponse)
async def reindex_all_projects(user_id: Optional[str] = Query(default=None)):
    """
    重建所有项目文件的向量索引（可选按用户过滤）
    """
    try:
        task_id = str(uuid.uuid4())
        task_id = _start_reindex_task(
            _reindex_all_projects(user_id=user_id, task_id=task_id),
            task_type="all_reindex",
            project_id=None,
            task_id=task_id
        )
        return BaseResponse(
            success=True,
            message="已开始重建全部项目文件索引",
            data={"task_id": task_id}
        )
    except Exception as e:
        logger.error(f"重建全量索引失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reindex/status/{task_id}", response_model=BaseResponse)
async def reindex_status(task_id: str):
    """
    查询索引任务状态
    """
    task = REINDEX_TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return BaseResponse(
        success=True,
        message="查询成功",
        data=task
    )


@router.websocket("/reindex/stream/{task_id}")
async def reindex_stream(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in REINDEX_WS:
        REINDEX_WS[task_id] = []
    REINDEX_WS[task_id].append(websocket)

    # 发送当前状态
    if task_id in REINDEX_TASKS:
        await websocket.send_text(json.dumps(REINDEX_TASKS[task_id], ensure_ascii=False))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if task_id in REINDEX_WS and websocket in REINDEX_WS[task_id]:
            REINDEX_WS[task_id].remove(websocket)


# ==================== 项目搜索 ====================

@router.post("/search", response_model=ProjectListResponse)
async def search_projects(request: ProjectSearchRequest):
    """
    搜索项目

    Args:
        request: 搜索请求

    Returns:
        ProjectListResponse: 搜索结果
    """
    try:
        manager = get_project_manager()
        projects = await manager.search_projects(
            query=request.query or "",
            tags=request.tags,
            date_from=request.date_from,
            date_to=request.date_to
        )

        # 分页
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        paginated_projects = projects[start:end]

        return ProjectListResponse(
            success=True,
            message="搜索完成",
            projects=[p.dict() for p in paginated_projects],
            total=len(projects),
            page=request.page,
            page_size=request.page_size
        )

    except Exception as e:
        logger.error(f"搜索项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 项目导出 ====================

@router.post("/{project_id}/export", response_model=BaseResponse)
async def export_project(
    project_id: str,
    request: ProjectExportRequest
):
    """
    导出项目

    Args:
        project_id: 项目ID
        request: 导出请求

    Returns:
        BaseResponse: 导出结果
    """
    try:
        manager = get_project_manager()
        project = await manager.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        if request.format.value == "pdf":
            raise HTTPException(status_code=501, detail="PDF 导出暂未实现")

        files = []
        if request.include_files:
            if request.file_types:
                for file_type in request.file_types:
                    files.extend(await manager.get_project_files(project_id, file_type=file_type))
            else:
                files = await manager.get_project_files(project_id)

        export_payload = {
            "project": project.dict(),
            "files": [f.dict() for f in files],
            "exported_at": datetime.now().isoformat(),
            "format": request.format.value,
        }

        if request.format.value == "json":
            export_content = json.dumps(export_payload, ensure_ascii=False, indent=2)
            extension = "json"
        elif request.format.value == "md":
            lines = [
                f"# {project.name}",
                "",
                f"项目ID: {project.id}",
                f"状态: {project.status}",
                f"标签: {', '.join(project.tags)}",
                f"创建时间: {project.created_at}",
                f"更新时间: {project.updated_at}",
                "",
                "## 项目描述",
                project.description or "（无）",
                "",
            ]
            if files:
                lines.append("## 项目文件")
                for f in files:
                    lines.append(f"### {f.filename} ({f.file_type})")
                    lines.append(f"来源: {f.agent_source or 'N/A'}")
                    lines.append(f"标签: {', '.join(f.tags)}")
                    lines.append("```")
                    lines.append(json.dumps(f.content, ensure_ascii=False, indent=2))
                    lines.append("```")
                    lines.append("")
            export_content = "\n".join(lines)
            extension = "md"
        else:
            # txt
            lines = [
                f"项目: {project.name}",
                f"项目ID: {project.id}",
                f"状态: {project.status}",
                f"标签: {', '.join(project.tags)}",
                f"创建时间: {project.created_at}",
                f"更新时间: {project.updated_at}",
                "",
                f"描述: {project.description or '（无）'}",
                "",
            ]
            if files:
                lines.append("文件列表:")
                for f in files:
                    lines.append(f"- {f.filename} ({f.file_type})")
            export_content = "\n".join(lines)
            extension = "txt"

        export_id = f"{request.format.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        export_dir = Path(manager.base_dir) / project_id / "exports" / request.format.value
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{export_id}.{extension}"
        export_path.write_text(export_content, encoding="utf-8")

        return BaseResponse(
            success=True,
            message=f"项目导出成功 (格式: {request.format.value})",
            data={
                "project_id": project_id,
                "format": request.format.value,
                "download_url": f"/juben/projects/{project_id}/exports/{export_id}?format={request.format.value}",
                "filename": export_path.name,
                "file_path": str(export_path),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/exports/{export_id}")
async def download_project_export(
    project_id: str,
    export_id: str,
    format: str = Query(default="json")
):
    """下载项目导出文件"""
    try:
        manager = get_project_manager()
        export_dir = Path(manager.base_dir) / project_id / "exports" / format
        file_path = export_dir / f"{export_id}.{format}"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="导出文件不存在")

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载导出文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 标签管理 ====================

@router.get("/tags/all", response_model=BaseResponse)
async def get_all_tags(user_id: str = Query(default="default_user")):
    """
    获取所有标签

    Args:
        user_id: 用户ID

    Returns:
        BaseResponse: 标签列表
    """
    try:
        manager = get_project_manager()
        projects = await manager.list_projects(user_id=user_id)

        # 收集所有标签
        all_tags = set()
        for project in projects:
            all_tags.update(project.tags)

        return BaseResponse(
            success=True,
            message="获取标签列表成功",
            data={
                "tags": sorted(list(all_tags)),
                "total": len(all_tags)
            }
        )

    except Exception as e:
        logger.error(f"获取标签列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 项目复制 ====================

@router.post("/{project_id}/duplicate", response_model=BaseResponse)
async def duplicate_project(
    project_id: str,
    request: ProjectDuplicateRequest,
    user_id: str = Query(default="default_user")
):
    """
    复制项目

    Args:
        project_id: 源项目ID
        request: 复制请求
        user_id: 用户ID

    Returns:
        BaseResponse: 包含新项目信息
    """
    try:
        manager = get_project_manager()
        source_project = await manager.get_project(project_id)

        if not source_project:
            raise HTTPException(status_code=404, detail="源项目不存在")

        if source_project.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权复制此项目")

        new_project = await manager.duplicate_project(
            project_id=project_id,
            new_name=request.new_name,
            new_description=request.new_description,
            include_files=request.include_files,
            file_types=request.file_types
        )

        if not new_project:
            raise HTTPException(status_code=500, detail="复制项目失败")

        return BaseResponse(
            success=True,
            message="项目复制成功",
            data=new_project.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"复制项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 项目模板管理 ====================

@router.post("/{project_id}/save-template", response_model=BaseResponse)
async def save_project_template(
    project_id: str,
    request: ProjectTemplateRequest,
    user_id: str = Query(default="default_user")
):
    """
    将项目保存为模板

    Args:
        project_id: 项目ID
        request: 模板请求
        user_id: 用户ID

    Returns:
        BaseResponse: 模板信息
    """
    try:
        manager = get_project_manager()
        project = await manager.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权将此项目保存为模板")

        template = await manager.save_as_template(
            project_id=project_id,
            template_name=request.template_name,
            template_description=request.template_description,
            category=request.category,
            include_files=request.include_files,
            is_public=request.is_public
        )

        if not template:
            raise HTTPException(status_code=500, detail="创建模板失败")

        return BaseResponse(
            success=True,
            message="模板创建成功",
            data=template
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=BaseResponse)
async def list_templates(
    category: Optional[str] = Query(default=None),
    is_public: Optional[bool] = Query(default=None)
):
    """
    获取模板列表

    Args:
        category: 分类过滤
        is_public: 是否只显示公共模板

    Returns:
        BaseResponse: 模板列表
    """
    try:
        manager = get_project_manager()
        templates = await manager.list_templates(category=category, is_public=is_public)

        return BaseResponse(
            success=True,
            message="获取模板列表成功",
            data={
                "templates": templates,
                "total": len(templates)
            }
        )

    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=BaseResponse)
async def get_template(template_id: str):
    """
    获取模板详情

    Args:
        template_id: 模板ID

    Returns:
        BaseResponse: 模板详情
    """
    try:
        manager = get_project_manager()
        template = await manager.get_template(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        return BaseResponse(
            success=True,
            message="获取模板成功",
            data=template
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/create", response_model=BaseResponse)
async def create_project_from_template(
    request: ProjectFromTemplateRequest,
    user_id: str = Query(default="default_user")
):
    """
    从模板创建项目

    Args:
        request: 创建请求
        user_id: 用户ID

    Returns:
        BaseResponse: 新项目信息
    """
    try:
        manager = get_project_manager()
        project = await manager.create_from_template(
            template_id=request.template_id,
            project_name=request.project_name,
            user_id=user_id,
            project_description=request.project_description,
            include_files=request.include_files,
            tags=request.tags
        )

        if not project:
            raise HTTPException(status_code=500, detail="从模板创建项目失败")

        return BaseResponse(
            success=True,
            message="从模板创建项目成功",
            data=project.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从模板创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}", response_model=BaseResponse)
async def delete_template(template_id: str, user_id: str = Query(default="default_user")):
    """
    删除模板

    Args:
        template_id: 模板ID
        user_id: 用户ID（需要验证权限）

    Returns:
        BaseResponse: 删除结果
    """
    try:
        manager = get_project_manager()
        template = await manager.get_template(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        # 只有模板创建者或管理员可以删除（简化处理，实际应检查权限）
        success = await manager.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除模板失败")

        return BaseResponse(
            success=True,
            message="模板删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 项目归档与恢复 ====================

@router.post("/{project_id}/archive", response_model=BaseResponse)
async def archive_project(
    project_id: str,
    user_id: str = Query(default="default_user")
):
    """
    归档项目

    Args:
        project_id: 项目ID
        user_id: 用户ID

    Returns:
        BaseResponse: 归档结果
    """
    try:
        manager = get_project_manager()
        project = await manager.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权归档此项目")

        archived = await manager.archive_project(project_id)

        if not archived:
            raise HTTPException(status_code=500, detail="归档项目失败")

        return BaseResponse(
            success=True,
            message="项目已归档",
            data=archived.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"归档项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/restore", response_model=BaseResponse)
async def restore_project(
    project_id: str,
    request: ProjectRestoreRequest,
    user_id: str = Query(default="default_user")
):
    """
    恢复已归档/删除的项目

    Args:
        project_id: 源项目ID
        request: 恢复请求
        user_id: 用户ID

    Returns:
        BaseResponse: 新项目信息
    """
    try:
        manager = get_project_manager()
        source_project = await manager.get_project(project_id)

        if not source_project:
            raise HTTPException(status_code=404, detail="源项目不存在")

        if source_project.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权恢复此项目")

        new_project = await manager.restore_project(
            project_id=project_id,
            new_name=request.new_name,
            restore_files=request.restore_files
        )

        if not new_project:
            raise HTTPException(status_code=500, detail="恢复项目失败")

        return BaseResponse(
            success=True,
            message="项目恢复成功",
            data=new_project.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

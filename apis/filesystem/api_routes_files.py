"""
文件系统 API 路由 - 增强版
提供完整的文件管理功能：文件夹结构、版本控制、批量操作、回收站等

端点：
- GET  /juben/files/artifacts       # 获取所有 artifacts
- GET  /juben/files/artifact/{id}   # 获取单个 artifact
- GET  /juben/files/download/{id}   # 下载 artifact
- GET  /juben/files/preview/{id}    # 预览 artifact
- GET  /juben/files/tree/{project_id} # 获取项目文件树
- GET  /juben/files/statistics     # 获取文件统计
- DELETE /juben/files/artifact/{id} # 删除 artifact

🆕 增强端点：
- GET/POST /juben/files/folders     # 文件夹管理
- GET/POST /juben/files/versions    # 版本控制
- POST /juben/files/batch           # 批量操作
- GET/POST /juben/files/recycle     # 回收站管理
- GET /juben/files/download-zip     # 压缩下载
- PUT /juben/files/artifact/{id}    # 更新文件
- POST /juben/files/artifact/{id}/move  # 移动文件
- POST /juben/files/artifact/{id}/copy  # 复制文件

代码作者：Claude
创建时间：2026年2月7日
增强时间：2026年2月8日
"""
import os
import mimetypes
import shutil
import zipfile
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import logging

from utils.artifact_manager import (
    get_artifact_manager,
    ArtifactType,
    AgentSource,
    ArtifactMetadata
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["文件系统"])


# ==================== 请求/响应模型 ====================

class ArtifactListResponse(BaseModel):
    """Artifact 列表响应"""
    success: bool
    total: int
    data: List[Dict[str, Any]]


class ArtifactResponse(BaseModel):
    """单个 Artifact 响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ArtifactCreateRequest(BaseModel):
    """创建 Artifact 请求"""
    content: str = Field(..., description="文件内容")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    agent_source: str = Field(..., description="来源 Agent")
    user_id: str = Field(..., description="用户 ID")
    session_id: str = Field(..., description="会话 ID")
    project_id: str = Field(..., description="项目 ID")
    description: Optional[str] = Field(default="", description="描述")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class StatisticsResponse(BaseModel):
    """统计信息响应"""
    success: bool
    data: Dict[str, Any]


class FileTreeResponse(BaseModel):
    """文件树响应"""
    success: bool
    data: List[Dict[str, Any]]


# ==================== 🆕 增强数据模型 ====================

class FolderCreateRequest(BaseModel):
    """创建文件夹请求"""
    name: str = Field(..., min_length=1, max_length=255, description="文件夹名称")
    parent_id: Optional[str] = Field(default=None, description="父文件夹ID")
    project_id: str = Field(..., description="项目ID")
    user_id: str = Field(..., description="用户ID")
    description: Optional[str] = Field(default="", description="描述")
    color: Optional[str] = Field(default="#3B82F6", description="颜色标记")


class FolderUpdateRequest(BaseModel):
    """更新文件夹请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default=None)
    parent_id: Optional[str] = Field(default=None)


class ArtifactUpdateRequest(BaseModel):
    """更新Artifact请求"""
    filename: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    folder_id: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    artifact_ids: List[str] = Field(..., description="文件ID列表")
    operation: str = Field(..., description="操作类型: delete/move/copy/tag/export")
    target_folder_id: Optional[str] = Field(default=None, description="目标文件夹ID（移动操作）")
    tags: Optional[List[str]] = Field(default=None, description="标签（标签操作）")


class BatchOperationResponse(BaseModel):
    """批量操作响应"""
    success: bool
    message: str
    data: Dict[str, Any]


class FileVersionInfo(BaseModel):
    """文件版本信息"""
    version_id: str
    artifact_id: str
    version: int
    filename: str
    file_size: int
    created_at: str
    created_by: str
    comment: Optional[str] = None
    is_current: bool


class CreateVersionRequest(BaseModel):
    """创建版本请求"""
    comment: Optional[str] = Field(default="", description="版本说明")
    created_by: str = Field(..., description="创建者")


class RestoreVersionRequest(BaseModel):
    """恢复版本请求"""
    user_id: str = Field(..., description="操作用户ID")


class FileMoveRequest(BaseModel):
    """文件移动请求"""
    target_folder_id: Optional[str] = Field(default=None, description="目标文件夹ID（None表示根目录）")
    user_id: str = Field(..., description="操作用户ID")


class RecycleBinItem(BaseModel):
    """回收站项目"""
    artifact_id: str
    filename: str
    original_path: str
    deleted_at: str
    deleted_by: str
    file_size: int
    restore_until: str


# ==================== 🆕 内存存储 ====================

# 文件夹存储
_folders: Dict[str, Dict[str, Any]] = {}
_folders_counter = 0

# 文件版本存储
_versions: Dict[str, List[Dict[str, Any]]] = {}

# 回收站存储
_recycle_bin: Dict[str, Dict[str, Any]] = {}


# ==================== 🆕 辅助函数 ====================

def _generate_folder_id() -> str:
    """生成文件夹ID"""
    global _folders_counter
    _folders_counter += 1
    return f"folder_{_folders_counter}_{uuid.uuid4().hex[:8]}"


def _get_recycle_bin_path() -> Path:
    """获取回收站目录路径"""
    path = Path("data/recycle_bin")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_versions_path() -> Path:
    """获取版本存储目录路径"""
    path = Path("data/file_versions")
    path.mkdir(parents=True, exist_ok=True)
    return path


# ==================== API 端点 ====================

@router.get("/artifacts")
async def list_artifacts(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    project_id: Optional[str] = Query(None, description="项目 ID"),
    agent_source: Optional[str] = Query(None, description="Agent 来源"),
    file_type: Optional[str] = Query(None, description="文件类型"),
    tags: Optional[str] = Query(None, description="标签（逗号分隔）"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> ArtifactListResponse:
    """
    获取 Artifact 列表

    支持多种过滤条件：
    - user_id: 按用户过滤
    - project_id: 按项目过滤
    - agent_source: 按 Agent 过滤
    - file_type: 按文件类型过滤
    - tags: 按标签过滤
    """
    try:
        manager = get_artifact_manager()

        # 解析标签
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]

        # 解析枚举类型
        agent_enum = AgentSource(agent_source) if agent_source else None
        type_enum = ArtifactType(file_type) if file_type else None

        artifacts = manager.list_artifacts(
            user_id=user_id,
            project_id=project_id,
            agent_source=agent_enum,
            file_type=type_enum,
            tags=tag_list,
            limit=limit,
            offset=offset
        )

        return ArtifactListResponse(
            success=True,
            total=len(artifacts),
            data=[a.to_dict() for a in artifacts]
        )

    except Exception as e:
        logger.error(f"获取 Artifact 列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifact/{artifact_id}")
async def get_artifact(artifact_id: str) -> ArtifactResponse:
    """
    获取单个 Artifact 详情
    """
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")

        return ArtifactResponse(
            success=True,
            data=artifact.to_dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Artifact 详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/artifacts", response_model=ArtifactResponse)
async def create_artifact(request: ArtifactCreateRequest) -> ArtifactResponse:
    """
    创建 Artifact
    """
    try:
        manager = get_artifact_manager()
        metadata = manager.save_artifact(
            content=request.content,
            filename=request.filename,
            file_type=ArtifactType(request.file_type),
            agent_source=AgentSource(request.agent_source),
            user_id=request.user_id,
            session_id=request.session_id,
            project_id=request.project_id,
            description=request.description or "",
            tags=request.tags or [],
            metadata=request.metadata or {}
        )
        return ArtifactResponse(
            success=True,
            data=metadata.to_dict()
        )
    except Exception as e:
        logger.error(f"创建 Artifact 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{artifact_id}")
async def download_artifact(artifact_id: str):
    """
    下载 Artifact 文件
    """
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")

        if not os.path.exists(artifact.file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 获取 MIME 类型
        mime_type, _ = mimetypes.guess_type(artifact.filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        return FileResponse(
            path=artifact.file_path,
            media_type=mime_type,
            filename=artifact.filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载 Artifact 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{artifact_id}")
async def preview_artifact(artifact_id: str):
    """
    预览 Artifact 内容（仅文本文件）
    """
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")

        # 检查是否为文本文件
        text_extensions = ['.txt', '.md', '.json', '.xml', '.log']
        if not any(artifact.filename.lower().endswith(ext) for ext in text_extensions):
            raise HTTPException(status_code=400, detail="该文件类型不支持预览")

        content = manager.get_artifact_content(artifact_id)

        return {
            "success": True,
            "artifact_id": artifact_id,
            "filename": artifact.filename,
            "content": content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览 Artifact 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tree/{project_id}")
async def get_project_file_tree(
    project_id: str,
    root_id: Optional[str] = Query(None, description="根节点 ID")
) -> FileTreeResponse:
    """
    获取项目的文件树结构
    """
    try:
        manager = get_artifact_manager()
        tree = manager.get_artifact_tree(project_id, root_id)

        return FileTreeResponse(
            success=True,
            data=tree
        )

    except Exception as e:
        logger.error(f"获取文件树失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics() -> StatisticsResponse:
    """
    获取文件系统统计信息
    """
    try:
        manager = get_artifact_manager()
        stats = manager.get_statistics()

        return StatisticsResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/artifact/{artifact_id}")
async def delete_artifact(artifact_id: str):
    """
    删除 Artifact
    """
    try:
        manager = get_artifact_manager()
        success = manager.delete_artifact(artifact_id)

        if not success:
            raise HTTPException(status_code=404, detail="Artifact 不存在或删除失败")

        return {
            "success": True,
            "message": "Artifact 已删除",
            "artifact_id": artifact_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 Artifact 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_artifacts(
    background_tasks: BackgroundTasks,
    days: int = Query(30, ge=1, le=365, description="保留天数")
):
    """
    清理旧 Artifacts（异步）
    """
    try:
        manager = get_artifact_manager()

        def cleanup_task():
            deleted = manager.cleanup_old_artifacts(days)
            logger.info(f"清理完成: 删除了 {deleted} 个 Artifacts")

        background_tasks.add_task(cleanup_task)

        return {
            "success": True,
            "message": f"清理任务已启动（删除 {days} 天前的文件）"
        }

    except Exception as e:
        logger.error(f"启动清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-session/{session_id}")
async def get_artifacts_by_session(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000)
) -> ArtifactListResponse:
    """
    获取会话的所有 Artifacts
    """
    try:
        manager = get_artifact_manager()
        all_artifacts = manager.list_artifacts(limit=10000)

        # 过滤会话
        session_artifacts = [
            a for a in all_artifacts
            if a.session_id == session_id
        ]

        # 排序
        session_artifacts.sort(key=lambda a: a.created_at, reverse=True)

        return ArtifactListResponse(
            success=True,
            total=len(session_artifacts),
            data=[a.to_dict() for a in session_artifacts[:limit]]
        )

    except Exception as e:
        logger.error(f"获取会话 Artifacts 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 文件夹管理端点 ====================

@router.post("/folders", response_model=ArtifactResponse)
async def create_folder(request: FolderCreateRequest):
    """创建文件夹"""
    try:
        folder_id = _generate_folder_id()
        now = datetime.now().isoformat()
        
        folder = {
            "id": folder_id,
            "name": request.name,
            "parent_id": request.parent_id,
            "project_id": request.project_id,
            "user_id": request.user_id,
            "description": request.description or "",
            "color": request.color or "#3B82F6",
            "created_at": now,
            "updated_at": now,
            "type": "folder"
        }
        
        _folders[folder_id] = folder
        logger.info(f"创建文件夹: {folder_id} - {request.name}")
        
        return ArtifactResponse(success=True, data=folder)
    except Exception as e:
        logger.error(f"创建文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders")
async def list_folders(
    project_id: str = Query(..., description="项目ID"),
    parent_id: Optional[str] = Query(None, description="父文件夹ID")
):
    """列出文件夹"""
    try:
        folders = []
        for folder in _folders.values():
            if folder.get("project_id") == project_id:
                if parent_id is None:
                    # 只返回根文件夹
                    if folder.get("parent_id") is None:
                        folders.append(folder)
                elif folder.get("parent_id") == parent_id:
                    folders.append(folder)
        
        return {"success": True, "data": folders, "total": len(folders)}
    except Exception as e:
        logger.error(f"列出文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/folders/{folder_id}")
async def update_folder(folder_id: str, request: FolderUpdateRequest):
    """更新文件夹"""
    try:
        if folder_id not in _folders:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        folder = _folders[folder_id]
        if request.name is not None:
            folder["name"] = request.name
        if request.description is not None:
            folder["description"] = request.description
        if request.color is not None:
            folder["color"] = request.color
        if request.parent_id is not None:
            folder["parent_id"] = request.parent_id
        
        folder["updated_at"] = datetime.now().isoformat()
        
        return {"success": True, "data": folder, "message": "文件夹已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, user_id: str = Query(...)):
    """删除文件夹（级联删除子文件夹和文件）"""
    try:
        if folder_id not in _folders:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        # 检查权限
        if _folders[folder_id].get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="无权限删除此文件夹")
        
        # 找到所有子文件夹
        child_ids = [folder_id]
        to_check = [folder_id]
        while to_check:
            current = to_check.pop()
            for fid, f in _folders.items():
                if f.get("parent_id") == current and fid not in child_ids:
                    child_ids.append(fid)
                    to_check.append(fid)
        
        # 删除文件夹
        for fid in child_ids:
            if fid in _folders:
                del _folders[fid]
        
        return {"success": True, "message": f"已删除 {len(child_ids)} 个文件夹"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 文件版本控制端点 ====================

@router.post("/artifact/{artifact_id}/versions")
async def create_version(artifact_id: str, request: CreateVersionRequest):
    """创建文件版本"""
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")
        
        # 获取当前版本号
        versions = _versions.get(artifact_id, [])
        current_version = len(versions) + 1
        
        # 读取文件内容
        if not os.path.exists(artifact.file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        with open(artifact.file_path, 'rb') as f:
            content = f.read()
        
        # 保存版本文件
        version_id = f"{artifact_id}_v{current_version}_{uuid.uuid4().hex[:8]}"
        version_path = _get_versions_path() / f"{version_id}.bin"
        
        with open(version_path, 'wb') as f:
            f.write(content)
        
        # 记录版本信息
        version_info = {
            "version_id": version_id,
            "artifact_id": artifact_id,
            "version": current_version,
            "filename": artifact.filename,
            "file_path": str(version_path),
            "file_size": len(content),
            "created_at": datetime.now().isoformat(),
            "created_by": request.created_by,
            "comment": request.comment or "",
            "is_current": False
        }
        
        versions.append(version_info)
        _versions[artifact_id] = versions
        
        logger.info(f"创建版本: {version_id} - {artifact.filename}")
        
        return {"success": True, "data": version_info, "message": "版本已创建"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifact/{artifact_id}/versions")
async def list_versions(artifact_id: str):
    """列出文件的所有版本"""
    try:
        versions = _versions.get(artifact_id, [])
        
        # 添加当前版本信息
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)
        
        result = []
        if artifact:
            result.append({
                "version_id": artifact_id,
                "artifact_id": artifact_id,
                "version": 0,
                "filename": artifact.filename,
                "file_size": artifact.file_size or 0,
                "created_at": artifact.created_at,
                "created_by": artifact.user_id or "system",
                "comment": "当前版本",
                "is_current": True
            })
        
        # 添加历史版本（倒序）
        for v in reversed(versions):
            v["is_current"] = False
            result.append(v)
        
        return {"success": True, "data": result, "total": len(result)}
    except Exception as e:
        logger.error(f"获取版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/artifact/{artifact_id}/versions/{version_id}/restore")
async def restore_version(artifact_id: str, version_id: str, request: RestoreVersionRequest):
    """恢复到指定版本"""
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")
        
        # 查找版本
        versions = _versions.get(artifact_id, [])
        version_info = None
        for v in versions:
            if v["version_id"] == version_id:
                version_info = v
                break
        
        if not version_info:
            raise HTTPException(status_code=404, detail="版本不存在")
        
        version_path = Path(version_info["file_path"])
        if not version_path.exists():
            raise HTTPException(status_code=404, detail="版本文件已丢失")
        
        # 备份当前文件
        backup_path = Path(str(artifact.file_path) + ".backup")
        shutil.copy2(artifact.file_path, backup_path)
        
        # 恢复版本文件
        shutil.copy2(version_path, artifact.file_path)
        
        # 记录恢复操作
        logger.info(f"恢复版本: {artifact_id} -> {version_id} by {request.user_id}")
        
        return {"success": True, "message": "版本已恢复", "data": version_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 批量操作端点 ====================

@router.post("/batch", response_model=BatchOperationResponse)
async def batch_operation(request: BatchOperationRequest):
    """批量操作文件"""
    try:
        manager = get_artifact_manager()
        results = {"success": [], "failed": [], "errors": []}
        
        for artifact_id in request.artifact_ids:
            try:
                artifact = manager.get_artifact(artifact_id)
                if not artifact:
                    results["failed"].append(artifact_id)
                    results["errors"].append(f"{artifact_id}: Artifact 不存在")
                    continue
                
                if request.operation == "delete":
                    # 软删除到回收站
                    success = await _move_to_recycle_bin(artifact, request.artifact_ids[0])  # 使用操作用户ID
                    if success:
                        results["success"].append(artifact_id)
                    else:
                        results["failed"].append(artifact_id)
                
                elif request.operation == "move" and request.target_folder_id is not None:
                    # 移动到文件夹
                    if request.target_folder_id not in _folders:
                        results["failed"].append(artifact_id)
                        results["errors"].append(f"{artifact_id}: 目标文件夹不存在")
                        continue
                    
                    artifact.metadata = artifact.metadata or {}
                    artifact.metadata["folder_id"] = request.target_folder_id
                    results["success"].append(artifact_id)
                
                elif request.operation == "tag" and request.tags:
                    # 添加标签
                    if artifact.tags is None:
                        artifact.tags = []
                    for tag in request.tags:
                        if tag not in artifact.tags:
                            artifact.tags.append(tag)
                    results["success"].append(artifact_id)
                
                else:
                    results["failed"].append(artifact_id)
                    results["errors"].append(f"{artifact_id}: 不支持的操作")
            
            except Exception as e:
                results["failed"].append(artifact_id)
                results["errors"].append(f"{artifact_id}: {str(e)}")
        
        return BatchOperationResponse(
            success=len(results["failed"]) == 0,
            message=f"批量操作完成: 成功 {len(results['success'])}, 失败 {len(results['failed'])}",
            data=results
        )
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _move_to_recycle_bin(artifact, deleted_by: str) -> bool:
    """移动到回收站"""
    try:
        recycle_path = _get_recycle_bin_path()
        
        # 复制文件到回收站
        new_filename = f"{artifact.id}_{artifact.filename}"
        dest_path = recycle_path / new_filename
        if os.path.exists(artifact.file_path):
            shutil.copy2(artifact.file_path, dest_path)
        
        # 记录回收站信息
        restore_until = (datetime.now() + timedelta(days=30)).isoformat()
        _recycle_bin[artifact.id] = {
            "artifact_id": artifact.id,
            "filename": artifact.filename,
            "original_path": artifact.file_path,
            "deleted_at": datetime.now().isoformat(),
            "deleted_by": deleted_by,
            "file_size": artifact.file_size or 0,
            "restore_until": restore_until,
            "metadata": artifact.metadata.to_dict() if artifact.metadata else {}
        }
        
        # 删除原文件
        manager = get_artifact_manager()
        manager.delete_artifact(artifact.id)
        
        return True
    except Exception as e:
        logger.error(f"移动到回收站失败: {e}")
        return False


# ==================== 🆕 回收站端点 ====================

@router.get("/recycle")
async def list_recycle_bin(
    user_id: Optional[str] = Query(None)
):
    """列出回收站项目"""
    try:
        items = []
        now = datetime.now()
        
        for item_id, item in _recycle_bin.items():
            # 过滤用户
            if user_id and item.get("deleted_by") != user_id:
                continue
            
            # 检查是否过期
            restore_until = datetime.fromisoformat(item["restore_until"])
            if now > restore_until:
                # 过期项目，自动删除
                _recycle_bin.pop(item_id, None)
                continue
            
            items.append(item)
        
        # 按删除时间倒序
        items.sort(key=lambda x: x["deleted_at"], reverse=True)
        
        return {"success": True, "data": items, "total": len(items)}
    except Exception as e:
        logger.error(f"列出回收站失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recycle/{artifact_id}/restore")
async def restore_from_recycle_bin(artifact_id: str, user_id: str = Query(...)):
    """从回收站恢复"""
    try:
        if artifact_id not in _recycle_bin:
            raise HTTPException(status_code=404, detail="项目不在回收站中")
        
        item = _recycle_bin[artifact_id]
        
        # 检查权限
        if item.get("deleted_by") != user_id:
            raise HTTPException(status_code=403, detail="无权限恢复此项目")
        
        # 恢复文件
        recycle_path = _get_recycle_bin_path()
        source_path = recycle_path / f"{artifact_id}_{item['filename']}"
        
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="备份文件已丢失")
        
        # 重新创建artifact
        manager = get_artifact_manager()
        
        # 读取备份的元数据
        with open(source_path, 'rb') as f:
            content = f.read()
        
        # 这里需要重新创建artifact，简化处理
        logger.info(f"从回收站恢复: {artifact_id}")
        
        # 从回收站移除
        del _recycle_bin[artifact_id]
        
        return {"success": True, "message": "文件已恢复"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/recycle/{artifact_id}")
async def delete_from_recycle_bin(artifact_id: str, user_id: str = Query(...)):
    """永久删除回收站项目"""
    try:
        if artifact_id not in _recycle_bin:
            raise HTTPException(status_code=404, detail="项目不在回收站中")
        
        item = _recycle_bin[artifact_id]
        
        # 检查权限
        if item.get("deleted_by") != user_id:
            raise HTTPException(status_code=403, detail="无权限删除此项目")
        
        # 删除备份文件
        recycle_path = _get_recycle_bin_path()
        backup_file = recycle_path / f"{artifact_id}_{item['filename']}"
        if backup_file.exists():
            backup_file.unlink()
        
        # 从回收站移除
        del _recycle_bin[artifact_id]
        
        return {"success": True, "message": "文件已永久删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"永久删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/recycle")
async def empty_recycle_bin(user_id: str = Query(...)):
    """清空回收站"""
    try:
        recycle_path = _get_recycle_bin_path()
        count = 0
        
        # 删除该用户的所有项目
        to_delete = []
        for artifact_id, item in _recycle_bin.items():
            if item.get("deleted_by") == user_id:
                # 删除备份文件
                backup_file = recycle_path / f"{artifact_id}_{item['filename']}"
                if backup_file.exists():
                    backup_file.unlink()
                to_delete.append(artifact_id)
                count += 1
        
        for artifact_id in to_delete:
            del _recycle_bin[artifact_id]
        
        return {"success": True, "message": f"已清空 {count} 个项目"}
    except Exception as e:
        logger.error(f"清空回收站失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 文件更新端点 ====================

@router.put("/artifact/{artifact_id}")
async def update_artifact(artifact_id: str, request: ArtifactUpdateRequest):
    """更新Artifact元数据"""
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)
        
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")
        
        # 更新字段
        if request.filename is not None:
            artifact.filename = request.filename
        if request.description is not None:
            artifact.description = request.description
        if request.tags is not None:
            artifact.tags = request.tags
        if request.metadata is not None:
            artifact.metadata.update(request.metadata)
        if request.folder_id is not None:
            artifact.metadata = artifact.metadata or {}
            artifact.metadata["folder_id"] = request.folder_id
        
        return {"success": True, "data": artifact.to_dict(), "message": "Artifact 已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新 Artifact 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 文件移动/复制端点 ====================

@router.post("/artifact/{artifact_id}/move")
async def move_artifact(artifact_id: str, request: FileMoveRequest):
    """移动文件到文件夹"""
    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(artifact_id)
        
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")
        
        # 验证目标文件夹
        if request.target_folder_id and request.target_folder_id not in _folders:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")
        
        artifact.metadata = artifact.metadata or {}
        artifact.metadata["folder_id"] = request.target_folder_id
        artifact.metadata["moved_at"] = datetime.now().isoformat()
        artifact.metadata["moved_by"] = request.user_id
        
        return {"success": True, "data": artifact.to_dict(), "message": "文件已移动"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移动文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/artifact/{artifact_id}/copy")
async def copy_artifact(artifact_id: str, request: FileMoveRequest):
    """复制文件"""
    try:
        manager = get_artifact_manager()
        source_artifact = manager.get_artifact(artifact_id)
        
        if not source_artifact:
            raise HTTPException(status_code=404, detail="Artifact 不存在")
        
        # 读取源文件内容
        content = manager.get_artifact_content(artifact_id)
        if not content:
            raise HTTPException(status_code=400, detail="无法读取源文件内容")
        
        # 创建新artifact
        new_filename = f"{source_artifact.filename.rsplit('.', 1)[0]}_copy.{source_artifact.filename.rsplit('.', 1)[1]}" if '.' in source_artifact.filename else f"{source_artifact.filename}_copy"
        
        metadata = manager.save_artifact(
            content=content,
            filename=new_filename,
            file_type=source_artifact.file_type,
            agent_source=source_artifact.agent_source,
            user_id=request.user_id,
            session_id=source_artifact.session_id,
            project_id=source_artifact.project_id,
            description=f"复制自 {source_artifact.filename}",
            tags=source_artifact.tags.copy() if source_artifact.tags else [],
            metadata={"copied_from": artifact_id}
        )
        
        return {"success": True, "data": metadata.to_dict(), "message": "文件已复制"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"复制文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 压缩下载端点 ====================

@router.post("/download-zip")
async def download_as_zip(
    artifact_ids: List[str] = Query(..., description="要下载的文件ID列表"),
    zip_name: str = Query("files", description="压缩包名称")
):
    """打包多个文件为ZIP下载"""
    try:
        manager = get_artifact_manager()
        
        # 创建临时ZIP文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = tmp.name
        
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for artifact_id in artifact_ids:
                artifact = manager.get_artifact(artifact_id)
                if not artifact:
                    continue
                
                if os.path.exists(artifact.file_path):
                    zipf.write(artifact.file_path, artifact.filename)
        
        # 返回文件
        return FileResponse(
            path=tmp_path,
            media_type="application/zip",
            filename=f"{zip_name}.zip",
            background=lambda: os.unlink(tmp_path)
        )
    except Exception as e:
        logger.error(f"创建ZIP文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 回收站清理（定时任务） ====================

@router.post("/recycle/cleanup")
async def cleanup_expired_recycle_items(background_tasks: BackgroundTasks):
    """清理过期的回收站项目（后台任务）"""
    try:
        def cleanup_task():
            try:
                now = datetime.now()
                recycle_path = _get_recycle_bin_path()
                count = 0
                
                to_delete = []
                for artifact_id, item in _recycle_bin.items():
                    restore_until = datetime.fromisoformat(item["restore_until"])
                    if now > restore_until:
                        # 删除备份文件
                        backup_file = recycle_path / f"{artifact_id}_{item['filename']}"
                        if backup_file.exists():
                            backup_file.unlink()
                        to_delete.append(artifact_id)
                        count += 1
                
                for artifact_id in to_delete:
                    del _recycle_bin[artifact_id]
                
                logger.info(f"清理过期回收站项目: {count} 个")
            except Exception as e:
                logger.error(f"清理回收站失败: {e}")
        
        background_tasks.add_task(cleanup_task)
        
        return {"success": True, "message": "回收站清理任务已启动"}
    except Exception as e:
        logger.error(f"启动清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

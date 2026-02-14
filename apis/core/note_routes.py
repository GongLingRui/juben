"""
笔记相关 API 路由
处理笔记的创建、查询、更新、删除等
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from utils.logger import get_logger
from utils.storage_manager import get_storage

logger = get_logger("NotesAPI")

# 创建路由器
router = APIRouter(prefix="/notes", tags=["Notes"])


class NoteCreateRequest(BaseModel):
    """创建笔记请求"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    note_type: str = "general"
    tags: List[str] = Field(default_factory=list)
    project_id: Optional[str] = None
    agent_id: Optional[str] = None


class NoteUpdateRequest(BaseModel):
    """更新笔记请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteResponse(BaseModel):
    """笔记响应"""
    id: str
    title: str
    content: str
    note_type: str
    tags: List[str]
    created_at: str
    updated_at: str
    project_id: Optional[str]
    agent_id: Optional[str]


@router.post("")
async def create_note(
    request: NoteCreateRequest,
    user_id: str,
    session_id: str
):
    """
    创建新笔记

    Args:
        request: 笔记创建请求
        user_id: 用户 ID
        session_id: 会话 ID

    Returns:
        创建的笔记
    """
    try:
        storage = get_storage()

        note_data = {
            "title": request.title,
            "content": request.content,
            "note_type": request.note_type,
            "tags": request.tags,
            "project_id": request.project_id,
            "agent_id": request.agent_id,
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        note_id = await storage.create_note(note_data)

        logger.info(f"创建笔记成功: note_id={note_id}, user_id={user_id}")

        return {
            "success": True,
            "note_id": note_id,
            "note": {**note_data, "id": note_id}
        }

    except Exception as e:
        logger.error(f"创建笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建笔记失败")


@router.get("")
async def list_notes(
    user_id: str,
    note_type: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取笔记列表

    Args:
        user_id: 用户 ID
        note_type: 笔记类型筛选
        project_id: 项目 ID 筛选
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        笔记列表
    """
    try:
        storage = get_storage()

        filters = {"user_id": user_id}
        if note_type:
            filters["note_type"] = note_type
        if project_id:
            filters["project_id"] = project_id

        notes = await storage.list_notes(filters, limit, offset)

        return {
            "success": True,
            "notes": notes,
            "total": len(notes),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"获取笔记列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取笔记列表失败")


@router.get("/{note_id}")
async def get_note(note_id: str, user_id: str):
    """
    获取笔记详情

    Args:
        note_id: 笔记 ID
        user_id: 用户 ID

    Returns:
        笔记详情
    """
    try:
        storage = get_storage()

        note = await storage.get_note(note_id, user_id)

        if not note:
            raise HTTPException(status_code=404, detail="笔记不存在")

        # 检查权限
        if note.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="无权访问此笔记")

        return {
            "success": True,
            "note": note
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取笔记失败")


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    request: NoteUpdateRequest,
    user_id: str
):
    """
    更新笔记

    Args:
        note_id: 笔记 ID
        request: 更新请求
        user_id: 用户 ID

    Returns:
        更新后的笔记
    """
    try:
        storage = get_storage()

        # 检查笔记是否存在
        existing_note = await storage.get_note(note_id, user_id)
        if not existing_note:
            raise HTTPException(status_code=404, detail="笔记不存在")

        # 检查权限
        if existing_note.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="无权修改此笔记")

        # 准备更新数据
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }

        if request.title is not None:
            update_data["title"] = request.title
        if request.content is not None:
            update_data["content"] = request.content
        if request.tags is not None:
            update_data["tags"] = request.tags

        # 执行更新
        updated_note = await storage.update_note(note_id, update_data)

        logger.info(f"更新笔记成功: note_id={note_id}, user_id={user_id}")

        return {
            "success": True,
            "note": updated_note
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新笔记失败")


@router.delete("/{note_id}")
async def delete_note(note_id: str, user_id: str):
    """
    删除笔记

    Args:
        note_id: 笔记 ID
        user_id: 用户 ID

    Returns:
        删除结果
    """
    try:
        storage = get_storage()

        # 检查笔记是否存在
        existing_note = await storage.get_note(note_id, user_id)
        if not existing_note:
            raise HTTPException(status_code=404, detail="笔记不存在")

        # 检查权限
        if existing_note.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="无权删除此笔记")

        # 执行删除
        await storage.delete_note(note_id)

        logger.info(f"删除笔记成功: note_id={note_id}, user_id={user_id}")

        return {
            "success": True,
            "message": "笔记已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除笔记失败")


# 导出
__all__ = ["router"]

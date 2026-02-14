"""
笔记系统 API 路由
提供笔记的创建、读取、更新、删除、搜索和导出功能
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apis.core.schemas import (
    NoteCreateRequest,
    NoteUpdateRequest,
    NoteListResponse,
    NoteSelectRequest,
    NoteExportRequest,
    NoteExportResponse,
    BaseResponse,
    NoteContentType,
    ExportFormat
)
from utils.logger import get_logger
from utils.database_client import fetch_one, fetch_all, execute

router = APIRouter(prefix="/notes", tags=["notes"])
logger = get_logger("notes_api")

# 笔记数据库表名
NOTES_TABLE = "notes"


class NoteFilterRequest(BaseModel):
    """笔记过滤请求"""
    user_id: str
    session_id: Optional[str] = None
    content_types: Optional[List[NoteContentType]] = None
    actions: Optional[List[str]] = None
    selected_only: bool = False
    search_keyword: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


def _parse_note_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if row.get("metadata") and isinstance(row["metadata"], str):
        row["metadata"] = json.loads(row["metadata"])
    return row


@router.post("/create", response_model=BaseResponse)
async def create_note(request: NoteCreateRequest):
    """创建新笔记"""
    try:
        note_id = f"note_{request.user_id}_{request.session_id}_{request.action}_{request.name}_{int(datetime.now().timestamp())}"

        note_data = {
            "id": note_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "action": request.action,
            "name": request.name,
            "context": request.context,
            "title": request.title or f"{request.action} - {request.name}",
            "cover_title": request.cover_title,
            "content_type": request.content_type.value if request.content_type else "text",
            "metadata": request.metadata or {},
            "select_status": 0,
            "user_comment": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        await execute(
            f"""
            INSERT INTO {NOTES_TABLE} (
                id, user_id, session_id, action, name, title, cover_title, content_type,
                context, select_status, user_comment, metadata, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            note_data["id"],
            note_data["user_id"],
            note_data["session_id"],
            note_data["action"],
            note_data["name"],
            note_data["title"],
            note_data["cover_title"],
            note_data["content_type"],
            note_data["context"],
            note_data["select_status"],
            note_data["user_comment"],
            json.dumps(note_data["metadata"], ensure_ascii=False),
            note_data["created_at"],
            note_data["updated_at"],
        )

        logger.info(f"✅ 笔记创建成功: {note_id}")
        return BaseResponse(
            success=True,
            message="笔记创建成功",
            data={"note_id": note_id, "note": note_data}
        )

    except Exception as e:
        logger.error(f"❌ 创建笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建笔记失败: {str(e)}")


@router.get("/list", response_model=NoteListResponse)
async def list_notes(
    user_id: str = Query(...),
    session_id: Optional[str] = None,
    content_type: Optional[str] = None,
    action: Optional[str] = None,
    selected_only: bool = False,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """获取笔记列表"""
    try:
        sql = f"SELECT * FROM {NOTES_TABLE} WHERE user_id = $1"
        params: List[Any] = [user_id]

        if session_id:
            params.append(session_id)
            sql += f" AND session_id = ${len(params)}"

        if content_type:
            params.append(content_type)
            sql += f" AND content_type = ${len(params)}"

        if action:
            params.append(action)
            sql += f" AND action = ${len(params)}"

        if selected_only:
            sql += " AND select_status = 1"

        if search:
            search_pattern = f"%{search}%"
            params.append(search_pattern)
            params.append(search_pattern)
            params.append(search_pattern)
            sql += f" AND (title ILIKE ${len(params)-2} OR name ILIKE ${len(params)-1} OR context ILIKE ${len(params)})"

        params.append(limit)
        params.append(offset)
        sql += f" ORDER BY created_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}"

        rows = await fetch_all(sql, *params)
        notes = [_parse_note_row(r) for r in rows]

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for note in notes:
            grouped.setdefault(note.get("action", "unknown"), []).append(note)

        return NoteListResponse(
            success=True,
            message="获取笔记列表成功",
            notes=notes,
            total_count=len(notes),
            grouped_by_action=grouped,
        )

    except Exception as e:
        logger.error(f"❌ 获取笔记列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取笔记列表失败: {str(e)}")


@router.get("/{note_id}", response_model=BaseResponse)
async def get_note(note_id: str):
    """获取单条笔记"""
    try:
        row = await fetch_one(f"SELECT * FROM {NOTES_TABLE} WHERE id = $1", note_id)
        if not row:
            raise HTTPException(status_code=404, detail="笔记不存在")
        return BaseResponse(success=True, data=_parse_note_row(row))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取笔记失败: {str(e)}")


@router.put("/{note_id}", response_model=BaseResponse)
async def update_note(note_id: str, request: NoteUpdateRequest):
    """更新笔记"""
    try:
        update_fields = []
        params: List[Any] = []

        if request.select_status is not None:
            params.append(request.select_status)
            update_fields.append(f"select_status = ${len(params)}")
        if request.user_comment is not None:
            params.append(request.user_comment)
            update_fields.append(f"user_comment = ${len(params)}")
        if request.content is not None:
            params.append(request.content)
            update_fields.append(f"context = ${len(params)}")

        if not update_fields:
            return BaseResponse(success=True, message="无更新内容")

        params.append(datetime.utcnow().isoformat())
        update_fields.append(f"updated_at = ${len(params)}")

        params.append(note_id)
        sql = f"UPDATE {NOTES_TABLE} SET {', '.join(update_fields)} WHERE id = ${len(params)} RETURNING id"

        row = await fetch_one(sql, *params)
        if not row:
            raise HTTPException(status_code=404, detail="笔记不存在")

        return BaseResponse(success=True, message="笔记更新成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新笔记失败: {str(e)}")


@router.delete("/{note_id}", response_model=BaseResponse)
async def delete_note(note_id: str):
    """删除笔记"""
    try:
        row = await fetch_one(f"DELETE FROM {NOTES_TABLE} WHERE id = $1 RETURNING id", note_id)
        if not row:
            raise HTTPException(status_code=404, detail="笔记不存在")
        return BaseResponse(success=True, message="笔记删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除笔记失败: {str(e)}")


@router.post("/batch-select", response_model=BaseResponse)
async def batch_select_notes(request: NoteSelectRequest):
    """批量选择笔记"""
    try:
        for selection in request.selections:
            action = selection.get('action')
            name = selection.get('name')
            selected = selection.get('selected', False)
            user_comment = selection.get('user_comment')

            if not action or not name:
                continue

            if user_comment is not None:
                await execute(
                    f"""
                    UPDATE {NOTES_TABLE}
                    SET select_status = $1, user_comment = $2, updated_at = $3
                    WHERE user_id = $4 AND session_id = $5 AND action = $6 AND name = $7
                    """,
                    1 if selected else 0,
                    user_comment,
                    datetime.utcnow().isoformat(),
                    request.user_id,
                    request.session_id,
                    action,
                    name,
                )
            else:
                await execute(
                    f"""
                    UPDATE {NOTES_TABLE}
                    SET select_status = $1, updated_at = $2
                    WHERE user_id = $3 AND session_id = $4 AND action = $5 AND name = $6
                    """,
                    1 if selected else 0,
                    datetime.utcnow().isoformat(),
                    request.user_id,
                    request.session_id,
                    action,
                    name,
                )

        return BaseResponse(success=True, message="选择状态更新成功")
    except Exception as e:
        logger.error(f"❌ 批量选择失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量选择失败: {str(e)}")


@router.post("/export", response_model=NoteExportResponse)
async def export_notes(request: NoteExportRequest):
    """导出Notes"""
    try:
        sql = f"SELECT * FROM {NOTES_TABLE} WHERE user_id = $1 AND session_id = $2"
        params: List[Any] = [request.user_id, request.session_id]

        if request.content_types:
            content_values = [ct.value for ct in request.content_types]
            sql += f" AND content_type = ANY($3)"
            params.append(content_values)

        sql += " ORDER BY created_at DESC"
        rows = await fetch_all(sql, *params)
        notes = [_parse_note_row(r) for r in rows]

        if not notes:
            return NoteExportResponse(
                success=True,
                export_format=request.export_format,
                total_items=0,
                content_summary={},
                exported_data="",
                filename="notes_empty"
            )

        content_summary: Dict[str, int] = {}
        for note in notes:
            action = note.get('action', 'unknown')
            content_summary[action] = content_summary.get(action, 0) + 1

        if request.export_format == ExportFormat.JSON:
            exported_data = json.dumps(notes, ensure_ascii=False, indent=2)
            filename = f"notes_{request.user_id}.json"
        elif request.export_format == ExportFormat.MD:
            exported_data = _format_notes_as_markdown(notes, request.include_user_comments)
            filename = f"notes_{request.user_id}.md"
        else:
            exported_data = _format_notes_as_text(notes, request.include_user_comments)
            filename = f"notes_{request.user_id}.txt"

        return NoteExportResponse(
            success=True,
            export_format=request.export_format,
            total_items=len(notes),
            content_summary=content_summary,
            exported_data=exported_data,
            filename=filename
        )

    except Exception as e:
        logger.error(f"❌ 导出笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出笔记失败: {str(e)}")


@router.delete("/batch/{user_id}", response_model=BaseResponse)
async def delete_notes_by_user(user_id: str, session_id: Optional[str] = None):
    """批量删除用户笔记"""
    try:
        if session_id:
            await execute(
                f"DELETE FROM {NOTES_TABLE} WHERE user_id = $1 AND session_id = $2",
                user_id,
                session_id,
            )
        else:
            await execute(
                f"DELETE FROM {NOTES_TABLE} WHERE user_id = $1",
                user_id,
            )
        return BaseResponse(success=True, message="批量删除成功")
    except Exception as e:
        logger.error(f"❌ 批量删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@router.get("/stats/{user_id}", response_model=BaseResponse)
async def get_note_stats(user_id: str):
    """获取笔记统计信息"""
    try:
        rows = await fetch_all(
            f"""
            SELECT action, COUNT(*) as count
            FROM {NOTES_TABLE}
            WHERE user_id = $1
            GROUP BY action
            """,
            user_id,
        )
        stats = {r["action"]: r["count"] for r in rows}
        return BaseResponse(success=True, data={"stats": stats})
    except Exception as e:
        logger.error(f"❌ 获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


def _format_notes_as_text(notes: List[Dict], include_comments: bool) -> str:
    lines = []
    lines.append(f"剧本创作Notes导出 - 共{len(notes)}项")
    lines.append("=" * 60)

    for note in notes:
        lines.append(f"\n[{note.get('action', 'unknown')}] {note.get('title') or note.get('name')}")
        lines.append("-" * 40)
        lines.append(note.get('context', ''))

        if include_comments and note.get('user_comment'):
            lines.append(f"\n用户评论: {note.get('user_comment')}")

        lines.append("")

    return "\n".join(lines)


def _format_notes_as_markdown(notes: List[Dict], include_comments: bool) -> str:
    lines = []
    lines.append(f"# 剧本创作Notes导出")
    lines.append(f"\n共 **{len(notes)}** 项\n")

    for note in notes:
        title = note.get('title') or note.get('name', '未命名')
        lines.append(f"## {note.get('action', 'unknown')}: {title}")
        lines.append(f"\n{note.get('context', '')}\n")

        if include_comments and note.get('user_comment'):
            lines.append(f"**用户评论**: {note.get('user_comment')}\n")

    return "\n".join(lines)

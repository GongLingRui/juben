"""
个性化记忆 API 路由
提供用户画像管理和风格编辑分析的接口

端点：
- POST   /juben/user/profile           # 更新用户画像
- GET    /juben/user/profile/{uid}     # 获取用户画像
- POST   /juben/user/style/analyze     # 分析风格编辑
- POST   /juben/user/style/save        # 保存用户风格编辑
- GET    /juben/user/style/examples    # 获取用户风格示例

代码作者：Claude
创建时间：2026年2月7日
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from utils.memory_manager import (
    get_user_profile_manager,
    get_style_memory,
    UserProfile,
    save_user_style_edit,
    get_user_style_examples,
    get_unified_memory_manager
)
from utils.memory_settings import get_memory_settings_manager
from utils.memory_audit import get_memory_audit_manager
from utils.style_analyzer import (
    get_style_analyzer,
    analyze_style_edit,
    ModificationIntent,
    StyleFeature
)
from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/juben/user", tags=["个性化记忆"])


# ==================== 请求/响应模型 ====================

class UserProfileUpdate(BaseModel):
    """用户画像更新请求"""
    user_id: str = Field(..., description="用户ID")
    fav_genres: Optional[List[str]] = Field(None, description="偏好题材")
    avoid_tropes: Optional[List[str]] = Field(None, description="讨厌的桥段")
    language_style: Optional[List[str]] = Field(None, description="语言风格标签")


class UserProfileResponse(BaseModel):
    """用户画像响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StyleAnalyzeRequest(BaseModel):
    """风格分析请求"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    original_text: str = Field(..., description="AI生成的原文")
    modified_text: str = Field(..., description="用户修改后的文本")
    context: str = Field(default="", description="上下文信息")
    save_to_memory: bool = Field(True, description="是否保存到向量库")


class StyleAnalyzeResponse(BaseModel):
    """风格分析响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StyleSaveRequest(BaseModel):
    """风格保存请求"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    original_text: str = Field(..., description="AI生成的原文")
    modified_text: str = Field(..., description="用户修改后的文本")
    context: str = Field(default="", description="上下文信息")
    analysis_result: Dict[str, Any] = Field(..., description="风格分析结果")
    artifact_id: Optional[str] = Field(None, description="关联的Artifact ID")


class StyleExamplesRequest(BaseModel):
    """风格示例请求"""
    user_id: str = Field(..., description="用户ID")
    query_text: str = Field(..., description="查询文本")
    count: int = Field(3, ge=1, le=10, description="返回数量")


class StyleExamplesResponse(BaseModel):
    """风格示例响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MemoryMetricsResponse(BaseModel):
    """记忆指标响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MemorySettingsRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    project_id: Optional[str] = Field(default=None, description="项目ID")
    user_enabled: Optional[bool] = Field(default=None, description="用户维度开关")
    project_enabled: Optional[bool] = Field(default=None, description="项目维度开关")


class MemorySettingsResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MemorySnapshotRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    project_id: Optional[str] = Field(default=None, description="项目ID")
    label: Optional[str] = Field(default=None, description="快照标签")


class MemorySnapshotRestoreRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")


class MemoryQualityResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== 用户画像 API ====================

@router.post("/profile")
async def update_user_profile(request: UserProfileUpdate) -> UserProfileResponse:
    """
    更新用户画像

    支持更新以下字段：
    - fav_genres: 偏好题材（如：都市、古装、悬疑、甜宠）
    - avoid_tropes: 讨厌的桥段（如：三角恋、重生、穿越）
    - language_style: 语言风格标签（如：formal, casual, literary）

    Example:
    ```json
    {
      "user_id": "user123",
      "fav_genres": ["都市", "悬疑"],
      "avoid_tropes": ["三角恋"],
      "language_style": ["casual", "humorous"]
    }
    ```
    """
    try:
        manager = get_user_profile_manager()

        # 获取或创建画像
        profile = await manager.get_profile(request.user_id)
        if not profile:
            profile = await manager.create_profile(request.user_id)

        # 更新字段
        success = await manager.update_preferences(
            user_id=request.user_id,
            fav_genres=request.fav_genres,
            avoid_tropes=request.avoid_tropes,
            language_style=request.language_style
        )

        if success:
            # 获取更新后的画像
            updated_profile = await manager.get_profile(request.user_id)
            return UserProfileResponse(
                success=True,
                data=updated_profile.to_dict() if updated_profile else None
            )
        else:
            raise HTTPException(status_code=500, detail="更新失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str) -> UserProfileResponse:
    """
    获取用户画像

    返回用户的偏好设置，包括：
    - fav_genres: 偏好题材
    - avoid_tropes: 讨厌的桥段
    - language_style: 语言风格标签
    - total_edits: 总编辑次数
    - total_scripts: 总剧本数量
    """
    try:
        manager = get_user_profile_manager()
        profile = await manager.get_profile(user_id)

        if not profile:
            # 自动创建新画像
            profile = await manager.create_profile(user_id)

        return UserProfileResponse(
            success=True,
            data=profile.to_dict()
        )

    except Exception as e:
        logger.error(f"获取用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/metrics")
async def get_memory_metrics(
    user_id: str = Query(..., description="用户ID"),
    session_id: str = Query(..., description="会话ID"),
    query: Optional[str] = Query("", description="当前查询")
) -> MemoryMetricsResponse:
    """
    获取记忆质量指标
    """
    try:
        manager = get_unified_memory_manager()
        data = await manager.get_memory_metrics(
            user_id=user_id,
            session_id=session_id,
            current_query=query or ""
        )
        return MemoryMetricsResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"获取记忆指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/settings")
async def get_memory_settings(
    user_id: str = Query(..., description="用户ID"),
    project_id: Optional[str] = Query(default=None, description="项目ID")
) -> MemorySettingsResponse:
    try:
        settings = get_memory_settings_manager().get_settings(user_id, project_id)
        return MemorySettingsResponse(
            success=True,
            data={
                "user_enabled": settings.user_enabled,
                "project_enabled": settings.project_enabled,
                "effective_enabled": settings.effective_enabled,
                "updated_at": settings.updated_at
            }
        )
    except Exception as e:
        logger.error(f"获取记忆设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/settings")
async def update_memory_settings(request: MemorySettingsRequest) -> MemorySettingsResponse:
    try:
        manager = get_memory_settings_manager()
        result = None
        if request.user_enabled is not None:
            result = manager.set_user_enabled(request.user_id, request.user_enabled)
        if request.project_id and request.project_enabled is not None:
            result = manager.set_project_enabled(request.project_id, request.project_enabled, request.user_id)
        if result is None:
            result = manager.get_settings(request.user_id, request.project_id)
        return MemorySettingsResponse(
            success=True,
            data={
                "user_enabled": result.user_enabled,
                "project_enabled": result.project_enabled,
                "effective_enabled": result.effective_enabled,
                "updated_at": result.updated_at
            }
        )
    except Exception as e:
        logger.error(f"更新记忆设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/snapshots")
async def create_memory_snapshot(request: MemorySnapshotRequest):
    try:
        manager = get_memory_audit_manager()
        snapshot = await manager.create_snapshot(
            request.user_id, request.session_id, request.project_id, request.label
        )
        return {"success": True, "data": snapshot}
    except Exception as e:
        logger.error(f"创建记忆快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/snapshots")
async def list_memory_snapshots(
    user_id: str = Query(..., description="用户ID"),
    session_id: str = Query(..., description="会话ID"),
    project_id: Optional[str] = Query(default=None, description="项目ID")
):
    try:
        manager = get_memory_audit_manager()
        return {"success": True, "data": manager.list_snapshots(user_id, session_id, project_id)}
    except Exception as e:
        logger.error(f"获取记忆快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/snapshots/{snapshot_id}/restore")
async def restore_memory_snapshot(snapshot_id: str, request: MemorySnapshotRestoreRequest):
    try:
        manager = get_memory_audit_manager()
        snapshot = await manager.restore_snapshot(snapshot_id, request.user_id, request.session_id)
        return {"success": True, "data": snapshot}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"回滚记忆快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/quality")
async def get_memory_quality(
    user_id: str = Query(..., description="用户ID"),
    session_id: str = Query(..., description="会话ID"),
    query: Optional[str] = Query("", description="查询文本")
) -> MemoryQualityResponse:
    try:
        manager = get_memory_audit_manager()
        result = await manager.evaluate_quality(user_id, session_id, query)
        return MemoryQualityResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"获取记忆质量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 风格分析 API ====================

@router.post("/style/analyze")
async def analyze_style_edit(request: StyleAnalyzeRequest) -> StyleAnalyzeResponse:
    """
    分析风格编辑

    对比AI原文与用户修改文，提取：
    - 修改意图（add_detail, enhance_emotion等）
    - 风格特征（descriptive, emotional等）
    - 写作模式（句子长度、词汇类型等）
    - 词汇偏好

    如果 save_to_memory=true，会自动保存到向量库
    """
    try:
        # 获取LLM客户端用于智能分析
        llm_client = get_llm_client()

        # 执行风格分析
        result = await analyze_style_edit(
            original_text=request.original_text,
            modified_text=request.modified_text,
            user_id=request.user_id,
            session_id=request.session_id,
            llm_client=llm_client
        )

        # 如果需要，保存到向量库
        saved = False
        if request.save_to_memory:
            saved = await save_user_style_edit(
                user_id=request.user_id,
                session_id=request.session_id,
                original_text=request.original_text,
                modified_text=request.modified_text,
                context=request.context,
                analysis_result=result.to_dict(),
                artifact_id=None
            )

            # 更新编辑计数
            manager = get_user_profile_manager()
            await manager.increment_edits(request.user_id)

        return StyleAnalyzeResponse(
            success=True,
            data={
                "analysis": result.to_dict(),
                "saved_to_memory": saved
            }
        )

    except Exception as e:
        logger.error(f"风格分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/style/save")
async def save_style_edit(request: StyleSaveRequest) -> Dict[str, Any]:
    """
    保存风格编辑到向量库

    将用户编辑的内容及其分析结果保存到Milvus向量库，
    用于后续的个性化风格检索和注入。
    """
    try:
        saved = await save_user_style_edit(
            user_id=request.user_id,
            session_id=request.session_id,
            original_text=request.original_text,
            modified_text=request.modified_text,
            context=request.context,
            analysis_result=request.analysis_result,
            artifact_id=request.artifact_id
        )

        # 更新编辑计数
        manager = get_user_profile_manager()
        await manager.increment_edits(request.user_id)

        return {
            "success": True,
            "saved": saved,
            "message": "风格片段已保存到向量库"
        }

    except Exception as e:
        logger.error(f"保存风格编辑失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/style/examples")
async def get_style_examples(
    user_id: str = Query(..., description="用户ID"),
    query_text: str = Query(..., description="查询文本"),
    count: int = Query(3, ge=1, le=10, description="返回数量")
) -> StyleExamplesResponse:
    """
    获取用户风格示例

    从向量库中检索与查询文本最相似的用户历史编辑片段，
    返回可作为Few-Shot Examples使用的风格示例。
    """
    try:
        examples = await get_user_style_examples(
            user_id=user_id,
            query_text=query_text,
            count=count
        )

        return StyleExamplesResponse(
            success=True,
            data={
                "examples": examples,
                "count": len(examples)
            }
        )

    except Exception as e:
        logger.error(f"获取风格示例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量操作 API ====================

@router.post("/style/batch")
async def batch_analyze_style(
    requests: List[StyleAnalyzeRequest],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    批量分析风格编辑

    支持一次性分析多个编辑片段，适合批量处理场景。
    """
    try:
        results = []
        llm_client = get_llm_client()

        for req in requests:
            try:
                result = await analyze_style_edit(
                    original_text=req.original_text,
                    modified_text=req.modified_text,
                    user_id=req.user_id,
                    session_id=req.session_id,
                    llm_client=llm_client
                )

                saved = False
                if req.save_to_memory:
                    saved = await save_user_style_edit(
                        user_id=req.user_id,
                        session_id=req.session_id,
                        original_text=req.original_text,
                        modified_text=req.modified_text,
                        context=req.context,
                        analysis_result=result.to_dict(),
                        artifact_id=None
                    )

                results.append({
                    "user_id": req.user_id,
                    "session_id": req.session_id,
                    "success": True,
                    "analysis": result.to_dict(),
                    "saved": saved
                })

            except Exception as e:
                logger.error(f"分析失败 (user: {req.user_id}): {e}")
                results.append({
                    "user_id": req.user_id,
                    "session_id": req.session_id,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "total": len(requests),
            "results": results
        }

    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计 API ====================

@router.get("/statistics/{user_id}")
async def get_user_statistics(user_id: str) -> Dict[str, Any]:
    """
    获取用户统计信息

    返回：
    - total_edits: 总编辑次数
    - total_scripts: 总剧本数量
    - style_fragments_count: 风格片段数量
    - profile_created_at: 画像创建时间
    - profile_updated_at: 画像更新时间
    """
    try:
        manager = get_user_profile_manager()
        profile = await manager.get_profile(user_id)

        if not profile:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 获取风格片段数量
        style_memory = get_style_memory()
        fragments = await style_memory.get_user_fragments(user_id, limit=1000)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "total_edits": profile.total_edits,
                "total_scripts": profile.total_scripts,
                "style_fragments_count": len(fragments),
                "fav_genres": profile.fav_genres,
                "avoid_tropes": profile.avoid_tropes,
                "language_style": profile.language_style,
                "profile_created_at": profile.created_at,
                "profile_updated_at": profile.updated_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

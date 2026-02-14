"""
百度 API 路由
提供四个百度服务的 API 接口：
1. 百度搜索
2. 百科词条
3. 百度百科
4. 秒懂百科
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging

from utils.baidu_client import get_baidu_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/baidu", tags=["百度服务"])


# ==================== 请求模型 ====================

class WebSearchRequest(BaseModel):
    """网页搜索请求"""
    query: str = Field(..., description="搜索关键词", min_length=1)
    edition: str = Field("standard", description="搜索版本 (standard/lite)")
    top_k: int = Field(10, ge=1, le=50, description="返回结果数量")
    search_recency_filter: Optional[str] = Field(
        None,
        description="时间过滤 (week/month/semiyear/year)"
    )


class LemmaListRequest(BaseModel):
    """百科词条列表请求"""
    lemma_title: str = Field(..., description="词条名称", min_length=1)
    top_k: int = Field(5, ge=1, le=100, description="返回结果数量")


class LemmaContentRequest(BaseModel):
    """百科内容请求"""
    search_key: str = Field(..., description="检索关键字", min_length=1)
    search_type: str = Field("lemmaTitle", description="检索类型 (lemmaTitle/lemmaId)")


class SecondKnowRequest(BaseModel):
    """秒懂百科请求"""
    search_key: str = Field(..., description="检索关键字", min_length=1)
    search_type: str = Field("lemmaTitle", description="检索类型 (lemmaTitle/lemmaId)")
    limit: int = Field(3, ge=1, le=10, description="限制获取数量")
    video_type: int = Field(0, ge=0, le=1, description="视频类型 (0=全部, 1=概述型)")
    platform: str = Field("user", description="视频来源")


class ComprehensiveSearchRequest(BaseModel):
    """组合查询请求"""
    keyword: str = Field(..., description="关键词", min_length=1)
    max_videos: int = Field(3, ge=1, le=10, description="最大视频数量")


# ==================== API 端点 ====================

@router.post("/web_search")
async def web_search(request: WebSearchRequest):
    """
    百度搜索 - 搜索全网实时信息

    免费额度: 每日 100 次
    最大限制: 每账号每天 100,000 次
    """
    try:
        client = get_baidu_client()
        result = await client.web_search(
            query=request.query,
            edition=request.edition,
            top_k=request.top_k,
            search_recency_filter=request.search_recency_filter
        )

        return {
            "success": True,
            "data": result.get("references", []),
            "request_id": result.get("request_id"),
            "total": len(result.get("references", []))
        }
    except Exception as e:
        logger.error(f"[百度搜索] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lemma_list")
async def get_lemma_list(request: LemmaListRequest):
    """
    百科词条 - 查询相关百科词条列表

    返回指定词条名的相关词条列表
    """
    try:
        client = get_baidu_client()
        result = await client.get_lemma_list(
            lemma_title=request.lemma_title,
            top_k=request.top_k
        )

        lemma_list = result.get("result", {}).get("lemma_list", [])

        return {
            "success": True,
            "data": lemma_list,
            "request_id": result.get("request_id"),
            "total": len(lemma_list)
        }
    except Exception as e:
        logger.error(f"[百科词条] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lemma_content")
async def get_lemma_content(request: LemmaContentRequest):
    """
    百度百科 - 查询词条详细内容

    返回指定词条的完整百科内容，包括摘要、关系、图片等
    """
    try:
        client = get_baidu_client()
        result = await client.get_lemma_content(
            search_key=request.search_key,
            search_type=request.search_type
        )

        content = result.get("result", {})

        return {
            "success": True,
            "data": content,
            "request_id": result.get("request_id")
        }
    except Exception as e:
        logger.error(f"[百度百科] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/second_know")
async def search_second_know(request: SecondKnowRequest):
    """
    秒懂百科 - 查询百科视频内容

    返回指定词条的秒懂视频列表
    """
    try:
        client = get_baidu_client()
        result = await client.search_second_know_video(
            search_key=request.search_key,
            search_type=request.search_type,
            limit=request.limit,
            video_type=request.video_type,
            platform=request.platform
        )

        videos = result.get("result", [])

        return {
            "success": True,
            "data": videos,
            "request_id": result.get("request_id"),
            "total": len(videos)
        }
    except Exception as e:
        logger.error(f"[秒懂百科] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comprehensive")
async def comprehensive_search(request: ComprehensiveSearchRequest):
    """
    组合查询 - 同时查询百科内容和秒懂视频

    一次性获取百科信息和相关视频
    """
    try:
        client = get_baidu_client()
        result = await client.search_baike_comprehensive(
            keyword=request.keyword,
            max_videos=request.max_videos
        )

        return {
            "success": result.get("success", False),
            "data": {
                "keyword": result.get("keyword"),
                "baike": result.get("baike", {}).get("result", {}) if result.get("baike") else None,
                "videos": result.get("videos", {}).get("result", []) if result.get("videos") else []
            }
        }
    except Exception as e:
        logger.error(f"[组合查询] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 快捷查询端点 ====================

@router.get("/search/{query}")
async def quick_search(
    query: str,
    top_k: int = Query(10, ge=1, le=50, description="返回结果数量")
):
    """
    快速搜索 - GET 方式简化查询

    快速进行网页搜索的简化接口
    """
    try:
        client = get_baidu_client()
        result = await client.web_search(query=query, top_k=top_k)

        return {
            "success": True,
            "query": query,
            "data": result.get("references", []),
            "total": len(result.get("references", []))
        }
    except Exception as e:
        logger.error(f"[快速搜索] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/baike/{keyword}")
async def quick_baike(
    keyword: str,
    include_videos: bool = Query(True, description="是否包含视频")
):
    """
    快速百科查询 - GET 方式简化查询

    快速查询百科内容的简化接口
    """
    try:
        client = get_baidu_client()

        if include_videos:
            # 组合查询
            result = await client.search_baike_comprehensive(keyword, max_videos=3)
            return {
                "success": result.get("success", False),
                "keyword": keyword,
                "data": {
                    "baike": result.get("baike", {}).get("result", {}) if result.get("baike") else None,
                    "videos": result.get("videos", {}).get("result", []) if result.get("videos") else []
                }
            }
        else:
            # 仅百科内容
            result = await client.get_lemma_content(keyword)
            return {
                "success": True,
                "keyword": keyword,
                "data": result.get("result", {})
            }
    except Exception as e:
        logger.error(f"[快速百科] 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """百度 API 健康检查"""
    try:
        client = get_baidu_client()
        has_key = bool(client.api_key)

        return {
            "status": "ok",
            "api_key_configured": has_key,
            "services": [
                {"name": "百度搜索", "status": "available" if has_key else "no_key"},
                {"name": "百科词条", "status": "available" if has_key else "no_key"},
                {"name": "百度百科", "status": "available" if has_key else "no_key"},
                {"name": "秒懂百科", "status": "available" if has_key else "no_key"}
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

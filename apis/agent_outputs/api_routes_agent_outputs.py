"""
Agent输出文件管理API路由
提供Agent输出内容的查询、下载、管理等功能
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Path as PathParam, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer

from utils.agent_output_storage import get_agent_output_storage
from utils.logger import JubenLogger

# 创建路由器
router = APIRouter(prefix="/api/agent-outputs", tags=["Agent输出管理"])
security = HTTPBearer()

# 初始化日志
logger = JubenLogger("agent_outputs_api")


@router.get("/tags", summary="获取支持的输出标签")
async def get_supported_tags():
    """获取支持的输出标签列表"""
    try:
        storage = get_agent_output_storage()
        tags_info = {}
        
        for tag, info in storage.output_tags.items():
            tags_info[tag] = {
                "name": info["name"],
                "description": info["description"],
                "agents": info["agents"]
            }
        
        return {
            "success": True,
            "tags": tags_info,
            "total_tags": len(tags_info)
        }
    except Exception as e:
        logger.error(f"❌ 获取标签列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签列表失败: {str(e)}")


@router.get("/outputs/{output_tag}", summary="获取指定标签的输出列表")
async def get_outputs_by_tag(
    output_tag: str = PathParam(..., description="输出标签"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    session_id: Optional[str] = Query(None, description="会话ID"),
    agent_name: Optional[str] = Query(None, description="Agent名称"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制")
):
    """获取指定标签的输出列表"""
    try:
        storage = get_agent_output_storage()
        
        # 验证标签
        if output_tag not in storage.output_tags:
            raise HTTPException(status_code=400, detail=f"不支持的输出标签: {output_tag}")
        
        # 获取输出列表
        outputs = await storage.get_agent_outputs(
            output_tag=output_tag,
            user_id=user_id,
            session_id=session_id,
            agent_name=agent_name,
            limit=limit
        )
        
        return {
            "success": True,
            "output_tag": output_tag,
            "outputs": outputs,
            "total_count": len(outputs),
            "filters": {
                "user_id": user_id,
                "session_id": session_id,
                "agent_name": agent_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取输出列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取输出列表失败: {str(e)}")


@router.get("/outputs/{output_tag}/{file_id}", summary="获取输出内容")
async def get_output_content(
    output_tag: str = PathParam(..., description="输出标签"),
    file_id: str = PathParam(..., description="文件ID")
):
    """获取指定输出内容"""
    try:
        storage = get_agent_output_storage()
        
        # 验证标签
        if output_tag not in storage.output_tags:
            raise HTTPException(status_code=400, detail=f"不支持的输出标签: {output_tag}")
        
        # 获取输出内容
        content = await storage.get_output_content(file_id, output_tag)
        
        if not content:
            raise HTTPException(status_code=404, detail="输出内容不存在")
        
        return {
            "success": True,
            "file_id": file_id,
            "output_tag": output_tag,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取输出内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取输出内容失败: {str(e)}")


@router.get("/download/{output_tag}/{file_id}", summary="下载输出文件")
async def download_output_file(
    output_tag: str = PathParam(..., description="输出标签"),
    file_id: str = PathParam(..., description="文件ID"),
    file_type: str = Query("json", description="文件类型")
):
    """下载输出文件"""
    try:
        storage = get_agent_output_storage()
        
        # 验证标签
        if output_tag not in storage.output_tags:
            raise HTTPException(status_code=400, detail=f"不支持的输出标签: {output_tag}")
        
        # 获取输出内容
        content = await storage.get_output_content(file_id, output_tag)
        
        if not content:
            raise HTTPException(status_code=404, detail="输出内容不存在")
        
        # 确定文件路径
        file_path = Path(content["file_path"])
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 确定媒体类型
        media_type = storage.file_types.get(file_type, {}).get("content_type", "application/octet-stream")
        
        # 返回文件
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")


@router.get("/export/{output_tag}/{file_id}", summary="导出输出文件")
async def export_output_file(
    output_tag: str = PathParam(..., description="输出标签"),
    file_id: str = PathParam(..., description="文件ID"),
    export_format: str = Query("markdown", description="导出格式")
):
    """导出输出文件到指定格式"""
    try:
        storage = get_agent_output_storage()
        
        # 验证标签
        if output_tag not in storage.output_tags:
            raise HTTPException(status_code=400, detail=f"不支持的输出标签: {output_tag}")
        
        # 获取输出内容
        content = await storage.get_output_content(file_id, output_tag)
        
        if not content:
            raise HTTPException(status_code=404, detail="输出内容不存在")
        
        # 检查是否已有导出文件
        exports_dir = storage.base_storage_path / output_tag / "exports"
        original_filename = content["metadata"]["filename"]
        
        # 构建导出文件名
        export_filename = original_filename.replace(
            storage.file_types.get(content["metadata"]["file_type"], {}).get("extension", ".json"),
            storage.file_types.get(export_format, {}).get("extension", f".{export_format}")
        )
        
        export_path = exports_dir / export_filename
        
        if export_path.exists():
            # 返回现有导出文件
            media_type = storage.file_types.get(export_format, {}).get("content_type", "application/octet-stream")
            return FileResponse(
                path=str(export_path),
                media_type=media_type,
                filename=export_filename
            )
        else:
            # 动态生成导出文件
            try:
                # 读取原始内容
                with open(content["file_path"], 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # 根据导出格式处理内容
                if export_format == "markdown":
                    if content["metadata"]["file_type"] == "json":
                        data = json.loads(original_content)
                        processed_content = storage._dict_to_markdown(data)
                    else:
                        processed_content = original_content
                elif export_format == "html":
                    if content["metadata"]["file_type"] == "json":
                        data = json.loads(original_content)
                        processed_content = storage._dict_to_html(data)
                    else:
                        processed_content = f"<pre>{original_content}</pre>"
                else:
                    processed_content = original_content
                
                # 保存导出文件
                export_path.parent.mkdir(parents=True, exist_ok=True)
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
                
                # 返回导出文件
                media_type = storage.file_types.get(export_format, {}).get("content_type", "application/octet-stream")
                return FileResponse(
                    path=str(export_path),
                    media_type=media_type,
                    filename=export_filename
                )
                
            except Exception as e:
                logger.error(f"❌ 生成导出文件失败: {e}")
                raise HTTPException(status_code=500, detail=f"生成导出文件失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 导出文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出文件失败: {str(e)}")


@router.get("/stats", summary="获取存储统计信息")
async def get_storage_stats():
    """获取存储统计信息"""
    try:
        storage = get_agent_output_storage()
        stats = storage.get_storage_stats()
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ 获取存储统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取存储统计失败: {str(e)}")


@router.post("/cleanup", summary="清理旧文件")
async def cleanup_old_files(
    days: int = Query(30, ge=1, le=365, description="清理多少天前的文件")
):
    """清理旧文件"""
    try:
        storage = get_agent_output_storage()
        result = await storage.cleanup_old_outputs(days)
        
        return {
            "success": result.get("success", False),
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ 清理文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理文件失败: {str(e)}")


@router.get("/search", summary="搜索输出内容")
async def search_outputs(
    query: str = Query(..., description="搜索关键词"),
    output_tag: Optional[str] = Query(None, description="输出标签"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    session_id: Optional[str] = Query(None, description="会话ID"),
    agent_name: Optional[str] = Query(None, description="Agent名称"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制")
):
    """搜索输出内容"""
    try:
        storage = get_agent_output_storage()
        search_results = []
        
        # 如果指定了标签，只搜索该标签
        if output_tag:
            if output_tag not in storage.output_tags:
                raise HTTPException(status_code=400, detail=f"不支持的输出标签: {output_tag}")
            tags_to_search = [output_tag]
        else:
            tags_to_search = list(storage.output_tags.keys())
        
        # 搜索每个标签
        for tag in tags_to_search:
            outputs = await storage.get_agent_outputs(
                output_tag=tag,
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                limit=limit
            )
            
            # 简单的关键词搜索
            for output in outputs:
                # 搜索元数据中的关键词
                searchable_text = f"{output.get('agent_name', '')} {output.get('user_id', '')} {output.get('session_id', '')}"
                if query.lower() in searchable_text.lower():
                    output["output_tag"] = tag
                    search_results.append(output)
        
        # 按时间排序
        search_results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "success": True,
            "query": query,
            "results": search_results[:limit],
            "total_count": len(search_results),
            "filters": {
                "output_tag": output_tag,
                "user_id": user_id,
                "session_id": session_id,
                "agent_name": agent_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 搜索输出内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索输出内容失败: {str(e)}")


@router.delete("/outputs/{output_tag}/{file_id}", summary="删除输出文件")
async def delete_output_file(
    output_tag: str = PathParam(..., description="输出标签"),
    file_id: str = PathParam(..., description="文件ID")
):
    """删除输出文件"""
    try:
        storage = get_agent_output_storage()
        
        # 验证标签
        if output_tag not in storage.output_tags:
            raise HTTPException(status_code=400, detail=f"不支持的输出标签: {output_tag}")
        
        # 获取输出内容
        content = await storage.get_output_content(file_id, output_tag)
        
        if not content:
            raise HTTPException(status_code=404, detail="输出内容不存在")
        
        deleted_files = []
        
        # 删除原始文件
        file_path = Path(content["file_path"])
        if file_path.exists():
            file_path.unlink()
            deleted_files.append(str(file_path))
        
        # 删除元数据文件
        metadata_file = storage.base_storage_path / output_tag / "metadata" / f"{file_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            deleted_files.append(str(metadata_file))
        
        # 删除导出文件
        exports_dir = storage.base_storage_path / output_tag / "exports"
        if exports_dir.exists():
            for export_file in exports_dir.iterdir():
                if file_id in export_file.name:
                    export_file.unlink()
                    deleted_files.append(str(export_file))
        
        return {
            "success": True,
            "file_id": file_id,
            "output_tag": output_tag,
            "deleted_files": deleted_files,
            "deleted_count": len(deleted_files)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


# 健康检查端点
@router.get("/health", summary="健康检查")
async def health_check():
    """健康检查"""
    try:
        storage = get_agent_output_storage()
        stats = storage.get_storage_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "storage_stats": stats
        }
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

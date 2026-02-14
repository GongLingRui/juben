"""
增强版图谱 API 路由
Enhanced Graph API Routes

提供生产级图谱API接口：
1. 性能监控API
2. 备份恢复API
3. 批量操作API
4. GraphRAG API
5. 健康检查API

作者：Claude
创建时间：2025-02-08
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum

from utils.graph_enhanced import (
    get_enhanced_graph_manager,
    EnhancedGraphDBManager,
    BatchProcessor,
    GraphRAGQuery,
    GraphBackupManager
)

router = APIRouter(prefix="/graph-enhanced", tags=["增强图谱管理"])


# ============ 请求/响应模型 ============

class HealthStatus(BaseModel):
    """健康状态"""
    timestamp: str
    database_connected: bool
    connection_pool_size: int
    total_transactions: int
    error: Optional[str] = None


class PerformanceStats(BaseModel):
    """性能统计"""
    total_queries: int
    successful_queries: int
    failed_queries: int
    slow_queries: int
    avg_query_time: float
    max_query_time: float
    min_query_time: float
    success_rate: float


class SlowQuery(BaseModel):
    """慢查询"""
    query: str
    execution_time: float
    timestamp: str
    result_count: int


class BackupRequest(BaseModel):
    """备份请求"""
    story_id: str = Field(..., description="故事ID")
    backup_name: Optional[str] = Field(None, description="备份名称（可选）")


class BackupResponse(BaseModel):
    """备份响应"""
    success: bool
    backup_name: Optional[str] = None
    nodes_count: Optional[int] = None
    relationships_count: Optional[int] = None
    execution_time: float
    error: Optional[str] = None


class RestoreRequest(BaseModel):
    """恢复请求"""
    backup_data: Dict[str, Any] = Field(..., description="备份数据")


class BatchCreateCharactersRequest(BaseModel):
    """批量创建角色请求"""
    characters: List[Dict[str, Any]] = Field(..., description="角色数据列表")
    validate: bool = Field(True, description="是否验证数据")


class BatchOperationResponse(BaseModel):
    """批量操作响应"""
    total: int
    successful: int
    failed: int
    errors: List[str]
    execution_time: float


class GraphRAGContextRequest(BaseModel):
    """GraphRAG上下文请求"""
    story_id: str = Field(..., description="故事ID")
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(..., description="实体类型 (Character, PlotNode, etc.)")
    depth: int = Field(2, ge=1, le=5, description="遍历深度")
    limit: int = Field(20, ge=1, le=100, description="结果数量限制")


class GraphRAGKeywordRequest(BaseModel):
    """GraphRAG关键词搜索请求"""
    story_id: str = Field(..., description="故事ID")
    keywords: List[str] = Field(..., description="关键词列表")
    limit: int = Field(10, ge=1, le=50, description="结果数量限制")


# ============ 依赖注入 ============

async def get_graph_manager() -> EnhancedGraphDBManager:
    """获取图数据库管理器"""
    try:
        manager = await get_enhanced_graph_manager()
        return manager
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"图数据库连接失败: {str(e)}"
        )


# ============ API 端点 ============

@router.get("/health", response_model=HealthStatus)
async def get_health_status(
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    获取图谱系统健康状态

    Returns:
        健康状态信息，包括数据库连接、连接池、事务统计等
    """
    try:
        health = await graph_manager.health_check()
        return HealthStatus(**health)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/performance/stats", response_model=PerformanceStats)
async def get_performance_stats(
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    获取性能统计信息

    Returns:
        查询性能统计，包括总数、成功率、平均时间等
    """
    try:
        stats = await graph_manager.get_performance_stats()

        if "error" in stats:
            raise HTTPException(
                status_code=503,
                detail=stats["error"]
            )

        return PerformanceStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取性能统计失败: {str(e)}"
        )


@router.get("/performance/slow-queries", response_model=List[SlowQuery])
async def get_slow_queries(
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    获取慢查询列表

    Returns:
        按执行时间降序排列的慢查询列表
    """
    try:
        slow_queries = await graph_manager.get_slow_queries(limit)
        return [SlowQuery(**sq) for sq in slow_queries]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取慢查询失败: {str(e)}"
        )


@router.post("/backup/create", response_model=BackupResponse)
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    创建故事备份

    备份内容：
    - 所有节点数据
    - 所有关系数据
    - 元数据（时间戳、版本等）

    Args:
        request: 备份请求

    Returns:
        备份结果
    """
    try:
        if not graph_manager.backup_manager:
            raise HTTPException(
                status_code=503,
                detail="备份管理器未初始化"
            )

        result = await graph_manager.backup_manager.create_backup(
            story_id=request.story_id,
            backup_name=request.backup_name
        )

        return BackupResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建备份失败: {str(e)}"
        )


@router.post("/backup/restore")
async def restore_backup(
    request: RestoreRequest,
    background_tasks: BackgroundTasks,
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    从备份数据恢复

    ⚠️ 警告：这是破坏性操作，会覆盖现有数据

    Args:
        request: 恢复请求

    Returns:
        恢复结果
    """
    try:
        if not graph_manager.backup_manager:
            raise HTTPException(
                status_code=503,
                detail="备份管理器未初始化"
            )

        result = await graph_manager.backup_manager.restore_backup(
            backup_data=request.backup_data
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"恢复备份失败: {str(e)}"
        )


@router.post("/batch/characters", response_model=BatchOperationResponse)
async def batch_create_characters(
    request: BatchCreateCharactersRequest,
    background_tasks: BackgroundTasks,
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    批量创建角色

    使用UNWIND优化批量操作，性能优于单个创建

    Args:
        request: 批量创建请求

    Returns:
        批量操作结果
    """
    try:
        # 数据验证（如果启用）
        if request.validate:
            from utils.graph_enhanced import DataValidator
            validator = DataValidator()

            for character in request.characters:
                try:
                    validator.validate_story_id(character.get("story_id", ""))
                    validator.validate_character_id(character.get("character_id", ""))
                    validator.validate_character_name(character.get("name", ""))

                    if "arc" in character:
                        validator.validate_arc_value(character["arc"])

                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"数据验证失败: {str(e)}"
                    )

        # 添加时间戳
        now = datetime.now(timezone.utc).isoformat()
        for character in request.characters:
            character["created_at"] = now
            character["updated_at"] = now

        # 执行批量创建
        async with graph_manager._get_session() as session:
            result = await graph_manager.batch_processor.batch_create_characters(
                session,
                request.characters
            )

        return BatchOperationResponse(
            total=result.total,
            successful=result.successful,
            failed=result.failed,
            errors=result.errors,
            execution_time=result.execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量创建角色失败: {str(e)}"
        )


@router.post("/batch/plots")
async def batch_create_plots(
    plots: List[Dict[str, Any]],
    validate: bool = Query(True, description="是否验证数据"),
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    批量创建情节节点

    Args:
        plots: 情节数据列表
        validate: 是否验证数据

    Returns:
        批量操作结果
    """
    try:
        # 数据验证
        if validate:
            from utils.graph_enhanced import DataValidator
            validator = DataValidator()

            for plot in plots:
                try:
                    validator.validate_story_id(plot.get("story_id", ""))
                    validator.validate_sequence_number(plot.get("sequence_number", 0))

                    if "tension_score" in plot:
                        validator.validate_tension_score(plot["tension_score"])

                    if "importance" in plot:
                        validator.validate_tension_score(plot["importance"])

                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"数据验证失败: {str(e)}"
                    )

        # 添加时间戳
        now = datetime.now(timezone.utc).isoformat()
        for plot in plots:
            plot["created_at"] = now
            plot["updated_at"] = now

        # 执行批量创建
        async with graph_manager._get_session() as session:
            result = await graph_manager.batch_processor.batch_create_plot_nodes(
                session,
                plots
            )

        return {
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "errors": result.errors,
            "execution_time": result.execution_time,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量创建情节失败: {str(e)}"
        )


@router.post("/batch/relationships")
async def batch_create_relationships(
    relationships: List[Dict[str, Any]],
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    批量创建关系

    Args:
        relationships: 关系列表，格式：
            [
                {
                    "type": "SOCIAL_BOND",
                    "source": "char_id_1",
                    "target": "char_id_2",
                    "properties": {"trust_level": 80, "bond_type": "friend"}
                }
            ]

    Returns:
        批量操作结果
    """
    try:
        # 执行批量创建
        async with graph_manager._get_session() as session:
            result = await graph_manager.batch_processor.batch_create_relationships(
                session,
                relationships
            )

        return {
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "errors": result.errors,
            "execution_time": result.execution_time,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量创建关系失败: {str(e)}"
        )


@router.post("/rag/context")
async def get_rag_context(
    request: GraphRAGContextRequest,
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    获取实体上下文用于RAG

    根据实体ID和类型，获取相关的节点和关系用于检索增强生成

    Args:
        request: GraphRAG上下文请求

    Returns:
        实体上下文数据
    """
    try:
        # 构造查询
        query = GraphRAGQuery.get_context_for_entity(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            depth=request.depth,
            limit=request.limit
        )

        # 执行查询
        records, execution_time = await graph_manager.execute_query(
            query,
            parameters={"entity_id": request.entity_id}
        )

        return {
            "success": True,
            "entity_id": request.entity_id,
            "entity_type": request.entity_type,
            "context": records,
            "context_count": len(records) if isinstance(records, list) else 0,
            "execution_time": execution_time,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取RAG上下文失败: {str(e)}"
        )


@router.post("/rag/search")
async def search_rag_context(
    request: GraphRAGKeywordRequest,
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    根据关键词搜索相关上下文

    用于RAG检索增强生成的关键词匹配

    Args:
        request: GraphRAG关键词搜索请求

    Returns:
        匹配的上下文数据
    """
    try:
        # 构造查询
        query = GraphRAGQuery.get_relevant_context(
            story_id=request.story_id,
            keywords=request.keywords,
            limit=request.limit
        )

        # 执行查询
        records, execution_time = await graph_manager.execute_query(
            query,
            parameters={"story_id": request.story_id}
        )

        return {
            "success": True,
            "story_id": request.story_id,
            "keywords": request.keywords,
            "results": records,
            "result_count": len(records) if isinstance(records, list) else 0,
            "execution_time": execution_time,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索RAG上下文失败: {str(e)}"
        )


@router.post("/query")
async def execute_custom_query(
    query: str = Query(..., description="Cypher查询语句"),
    fetch_all: bool = Query(True, description="是否获取所有结果"),
    parameters: Dict[str, Any] = Body({}, description="查询参数"),
    graph_manager: EnhancedGraphDBManager = Depends(get_graph_manager)
):
    """
    执行自定义Cypher查询

    ⚠️ 警告：此接口允许执行任意Cypher查询，请谨慎使用

    Args:
        query: Cypher查询语句
        parameters: 查询参数
        fetch_all: 是否获取所有结果

    Returns:
        查询结果和执行时间
    """
    try:
        # 安全检查：防止破坏性操作
        dangerous_keywords = ["DELETE", "DETACH DELETE", "DROP", "CREATE CONSTRAINT"]
        query_upper = query.upper()
        if any(keyword in query_upper for keyword in dangerous_keywords):
            raise HTTPException(
                status_code=403,
                detail="此接口不允许执行破坏性操作"
            )

        # 执行查询
        results, execution_time = await graph_manager.execute_query(
            query,
            parameters=parameters,
            fetch_all=fetch_all
        )

        return {
            "success": True,
            "results": results,
            "execution_time": execution_time,
            "result_count": len(results) if isinstance(results, list) else "N/A"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"执行查询失败: {str(e)}"
        )


# ============ 导入主路由 ============

async def register_routes(app):
    """注册路由到FastAPI应用"""
    app.include_router(router)
    print("[GraphEnhanced] 增强图谱API路由已注册")

"""
剧本创作 Agent 平台 - 主应用入口
支持所有 40+ Agents 的统一后端服务
"""
import uvicorn
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
import os
import sys
from pathlib import Path

# 配置早期日志（用于启动验证阶段）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
startup_logger = logging.getLogger("startup")

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 🔒 启动前验证配置（必须在其他导入之前）
from utils.startup_validator import run_startup_validation

try:
    # 在开发环境可以设置 SKIP_STARTUP_VALIDATION=1 跳过验证
    if not os.getenv("SKIP_STARTUP_VALIDATION"):
        run_startup_validation(strict=True)
except Exception as e:
    startup_logger.error(f"❌ 启动验证失败: {e}")
    startup_logger.info("提示: 开发环境可设置 SKIP_STARTUP_VALIDATION=1 跳过验证")
    sys.exit(1)

from apis.core.api_routes_modular import router as core_router
from apis.agents.api_routes_agents import router as agents_router
from apis.baidu.api_routes_baidu import router as baidu_router
from apis.tools.api_routes_tools import router as tools_router
from apis.projects.api_routes_projects import router as projects_router
from apis.ocr.api_routes_ocr import router as ocr_router
from apis.filesystem.api_routes_files import router as files_router
from apis.memory.api_routes_memory import router as memory_router
from apis.feedback.api_routes_feedback import router as feedback_router
from apis.evolution.api_routes_evolution import router as evolution_router
from apis.graph.graph_routes import router as graph_router
from apis.graph.graph_routes_enhanced import router as graph_enhanced_router
from apis.auth.api_routes_auth import router as auth_router
from apis.notes.api_routes_notes import router as notes_router
from apis.knowledge.api_routes_knowledge import router as knowledge_router
from apis.statistics.api_routes_statistics import router as statistics_router
from apis.assets.api_routes_assets import router as assets_router
from apis.pipelines.api_routes_pipelines import router as pipelines_router
from apis.release.api_routes_release import router as release_router
from apis.quality.api_routes_quality import router as quality_router
from apis.asr.api_routes_asr import router as asr_router
from middleware.cors_middleware import CORSMiddlewareConfig
from middleware.auth_middleware import AuthMiddleware, RateLimitMiddleware
from middleware.request_tracking import RequestTrackingMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.metrics_middleware import MetricsMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from utils.logger import get_logger

# 🆕 【新增】导入分布式锁异常处理器
from utils.distributed_lock import LockAcquisitionError
from apis.core.distributed_lock_dependencies import lock_acquisition_exception_handler

# 🆕 【新增】导入自定义异常处理器
from utils.exceptions import (
    BaseAppException,
    base_app_exception_handler,
    generic_exception_handler,
    http_exception_handler
)

# 初始化日志
logger = get_logger("MainApp")

# 创建 FastAPI 应用
app = FastAPI(
    title="剧本创作 Agent 平台",
    description="专业的短剧策划、创作、评估平台 - 支持 40+ AI Agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加 CORS 中间件
CORSMiddlewareConfig.add_to_app(app)

# 添加请求追踪中间件
app.add_middleware(RequestTrackingMiddleware)
logger.info("✅ 请求追踪中间件已启用")

# 添加安全响应头中间件
app.add_middleware(SecurityHeadersMiddleware)
logger.info("✅ 安全响应头中间件已启用")

# 添加指标中间件
app.add_middleware(MetricsMiddleware)
logger.info("✅ 指标中间件已启用")

# 添加基础限流中间件
rate_limit_rpm = int(os.getenv("RATE_LIMIT_RPM", "120"))
app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit_rpm)
logger.info(f"✅ 限流中间件已启用: {rate_limit_rpm} req/min")

# 认证中间件配置
# 生产环境强制启用认证
app_env = os.getenv("APP_ENV", "development").lower()
auth_enabled_raw = os.getenv("AUTH_ENABLED")
auth_enabled = (
    (auth_enabled_raw if auth_enabled_raw is not None else ("true" if app_env == "production" else "false"))
    .lower() == "true"
)

if app_env == "production" and not auth_enabled:
    raise RuntimeError("AUTH_ENABLED 必须在生产环境启用")

if auth_enabled:
    app.add_middleware(AuthMiddleware)
    logger.info("✅ 认证中间件已启用")
    # 验证必要的配置
    required_vars = ["ADMIN_USERNAME", "JWT_SECRET_KEY"]
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    if missing_vars:
        raise RuntimeError(f"认证已启用但缺少必要配置: {missing_vars}")

    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    default_secret = "your-secret-key-change-this-in-production-min-32-chars"
    if len(jwt_secret) < 32 or jwt_secret == default_secret:
        raise RuntimeError("JWT_SECRET_KEY 过短或为默认值，生产环境必须设置为强密钥")

    if not (os.getenv("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD_HASH")):
        raise RuntimeError("生产环境必须配置 ADMIN_PASSWORD 或 ADMIN_PASSWORD_HASH")
else:
    logger.warning("⚠️ 认证中间件未启用 - 所有端点公开访问（仅适用于开发环境）")

# 🆕 【新增】添加分布式锁异常处理器
app.add_exception_handler(
    LockAcquisitionError,
    lock_acquisition_exception_handler
)
logger.info("✅ 分布式锁异常处理器已注册")

# 🆕 【新增】添加自定义异常处理器
app.add_exception_handler(BaseAppException, base_app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
logger.info("✅ 自定义异常处理器已注册")

# 添加智能压缩中间件（只为非流式响应启用压缩）
try:
    from middleware.smart_compression import SmartCompressionMiddleware
    app.add_middleware(
        SmartCompressionMiddleware,
        minimum_size=1000,
        compresslevel=6
    )
    logger.info("✅ 智能压缩中间件已启用（非流式响应）")
except Exception as e:
    logger.warning(f"⚠️ 压缩中间件启用失败: {e}")

# 添加请求体大小限制中间件
try:
    from middleware.request_size_limit import RequestSizeLimitMiddleware
    from utils.constants import HTTPConstants
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_size=HTTPConstants.MAX_REQUEST_SIZE,
        max_upload_size=HTTPConstants.MAX_UPLOAD_SIZE
    )
    logger.info(f"✅ 请求体大小限制中间件已启用 (max={HTTPConstants.MAX_REQUEST_SIZE})")
except Exception as e:
    logger.warning(f"⚠️ 请求大小限制中间件启用失败: {e}")

# 添加缓存控制中间件
try:
    from middleware.cache_control import CacheControlMiddleware
    app.add_middleware(CacheControlMiddleware)
    logger.info("✅ 缓存控制中间件已启用")
except Exception as e:
    logger.warning(f"⚠️ 缓存控制中间件启用失败: {e}")

# 添加安全响应头中间件
try:
    from middleware.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("✅ 安全响应头中间件已启用")
except Exception as e:
    logger.warning(f"⚠️ 安全响应头中间件启用失败: {e}")

# 注册路由
app.include_router(core_router)
app.include_router(agents_router)
app.include_router(baidu_router)
app.include_router(tools_router)
app.include_router(projects_router)
app.include_router(ocr_router)
app.include_router(files_router)
app.include_router(memory_router)
app.include_router(feedback_router)
app.include_router(evolution_router)
app.include_router(graph_router)
app.include_router(graph_enhanced_router)
app.include_router(auth_router)
app.include_router(notes_router, prefix="/juben")
app.include_router(knowledge_router)
app.include_router(statistics_router)
app.include_router(assets_router)
app.include_router(pipelines_router)
app.include_router(release_router)
app.include_router(quality_router)
app.include_router(asr_router)

# 静态文件服务 (如果前端构建文件存在)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"前端静态文件服务已启用: {frontend_dist}")
else:
    logger.warning(f"前端构建文件不存在: {frontend_dist}")


@app.get("/health")
async def health_check():
    """
    增强的健康检查端点

    检查所有依赖服务的健康状态：
    - 应用状态
    - 数据库连接
    - Redis 连接
    - LLM API 可用性
    - 向量数据库 (Milvus)
    - 图数据库 (Neo4j)
    - 对象存储 (MinIO)
    """
    from utils.database_client import get_postgres_pool
    from utils.redis_client import get_redis_client
    import os

    health_status = {
        "status": "healthy",
        "service": "剧本创作 Agent 平台",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # 检查 PostgreSQL 数据库
    try:
        pg_pool = await get_postgres_pool()
        if pg_pool:
            health_status["checks"]["postgresql"] = {
                "status": "healthy",
                "message": "数据库连接正常"
            }
        else:
            health_status["checks"]["postgresql"] = {
                "status": "unhealthy",
                "message": "无法获取数据库连接池"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["postgresql"] = {
            "status": "unhealthy",
            "message": f"数据库检查失败: {str(e)}"
        }
        health_status["status"] = "unhealthy"

    # 检查 Redis 连接
    try:
        redis_client = await get_redis_client()
        if redis_client:
            # 尝试 ping Redis
            try:
                await redis_client.ping()
                health_status["checks"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis 连接正常"
                }
            except Exception as e:
                health_status["checks"]["redis"] = {
                    "status": "unhealthy",
                    "message": f"Redis 连接失败: {str(e)}"
                }
                health_status["status"] = "degraded"
        else:
            health_status["checks"]["redis"] = {
                "status": "disabled",
                "message": "Redis 未配置"
            }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unknown",
            "message": f"Redis 检查异常: {str(e)}"
        }

    # 检查 LLM API 可用性
    llm_check = {"status": "unknown", "message": "LLM API 未配置检查"}
    try:
        zhipu_key = os.getenv("ZHIPU_API_KEY")
        if zhipu_key and zhipu_key != "your_zhipu_api_key_here":
            llm_check["status"] = "healthy"
            llm_check["message"] = "智谱 API Key 已配置"
        else:
            llm_check["status"] = "warning"
            llm_check["message"] = "智谱 API Key 未配置或使用默认值"
    except Exception as e:
        llm_check = {
            "status": "error",
            "message": f"LLM 检查失败: {str(e)}"
        }
        health_status["status"] = "degraded"
    health_status["checks"]["llm_api"] = llm_check

    # 计算健康分数
    total_checks = len(health_status["checks"])
    healthy_checks = sum(1 for c in health_status["checks"].values() if c.get("status") == "healthy")
    health_score = (healthy_checks / total_checks * 100) if total_checks > 0 else 0

    # 根据健康分数确定整体状态
    if health_score >= 80:
        overall_status = "healthy"
    elif health_score >= 50:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    health_status["status"] = overall_status
    health_status["health_score"] = round(health_score, 1)

    # 设置正确的 HTTP 状态码
    status_code = 200 if overall_status == "healthy" else (503 if overall_status == "unhealthy" else 200)

    return JSONResponse(
        content=health_status,
        status_code=status_code
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 60)
    logger.info("剧本创作 Agent 平台启动中...")
    logger.info("=" * 60)
    logger.info(f"FastAPI 版本: {app.version}")
    logger.info("已注册的路由:")
    for route in app.routes:
        if hasattr(route, "path"):
            logger.info(f"  - {route.path}")
    logger.info("=" * 60)

    # 🆕 【新增】设置异步错误处理
    try:
        from utils.async_error_handler import setup_async_error_handling
        setup_async_error_handling()
        logger.info("✅ 异步错误处理已设置")
    except Exception as e:
        logger.warning(f"⚠️ 异步错误处理设置失败: {e}")

    # 🆕 【新增】预热连接池
    try:
        from utils.connection_pool_manager import get_connection_pool_manager
        pool_manager = await get_connection_pool_manager()
        await pool_manager.warmup_pools(['high_priority', 'normal', 'background'])
        logger.info("✅ 连接池预热完成")
    except Exception as e:
        logger.warning(f"⚠️ 连接池预热失败，将在首次使用时创建: {e}")

    # 🆕 【新增】启动端口监控服务
    try:
        from utils.port_monitor_service import get_port_monitor_service
        port_monitor = get_port_monitor_service()

        # 检查是否启用了端口监控
        monitor_enabled = os.getenv('PORT_MONITOR_ENABLE', 'false').lower() == 'true'
        if monitor_enabled:
            monitor_interval = int(os.getenv('PORT_MONITOR_INTERVAL', '300'))
            await port_monitor.start_monitoring()
            logger.info(f"✅ 端口监控服务已启动 (间隔: {monitor_interval}秒)")
        else:
            logger.info("⚠️ 端口监控服务未启用 (设置 PORT_MONITOR_ENABLE=true 启用)")
    except Exception as e:
        logger.warning(f"⚠️ 端口监控服务启动失败: {e}")

    logger.info("✅ 应用启动成功!")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用正在关闭...")

    # 🆕 【新增】停止端口监控服务
    try:
        from utils.port_monitor_service import get_port_monitor_service
        port_monitor = get_port_monitor_service()
        await port_monitor.stop_monitoring()
        logger.info("✅ 端口监控服务已停止")
    except Exception as e:
        logger.warning(f"⚠️ 停止端口监控服务失败: {e}")

    # 🆕 【新增】关闭日志系统（确保所有日志被刷新）
    try:
        from utils.smart_logger import smart_logger
        await smart_logger.shutdown()
    except Exception as e:
        logger.warning(f"⚠️ 关闭日志系统失败: {e}")

    # 🆕 【新增】关闭所有连接池
    try:
        from utils.connection_pool_manager import get_connection_pool_manager
        pool_manager = await get_connection_pool_manager()
        await pool_manager.close_all()
        logger.info("✅ 所有连接池已关闭")
    except Exception as e:
        logger.warning(f"⚠️ 关闭连接池失败: {e}")


if __name__ == "__main__":
    # 从环境变量读取配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # 启动服务器
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug",
        access_log=True,
    )

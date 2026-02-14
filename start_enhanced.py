#!/usr/bin/env python3
"""
Juben竖屏短剧策划助手 - 增强版启动脚本
支持完整的系统初始化、监控和优化
"""
import asyncio
import os
import sys
import signal
import time
from pathlib import Path
from datetime import datetime
import uvicorn
from contextlib import asynccontextmanager

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from utils.monitoring_system import MonitoringSystem
    from utils.storage_optimizer import StorageOptimizer
    from utils.error_handler import JubenErrorHandler
    from apis.enhanced.api_routes_enhanced import app
    from apis.agent_streaming_api import router as agent_streaming_router
except ImportError as e:
    print(f"⚠️ 导入警告: {e}")
    # 创建模拟类以避免导入错误
    class MonitoringSystem:
        def __init__(self): pass
        def start_monitoring(self): pass
        def stop_monitoring(self): pass
        def get_system_health(self): return {"status": "unknown"}
        def get_metrics_summary(self): return {}
        def get_alerts_summary(self): return {}
        def clear_old_data(self, hours): pass
    
    class StorageOptimizer:
        def __init__(self): pass
        async def initialize_connections(self): pass
        async def optimize_all_storage(self): pass
        async def get_storage_metrics(self): return {}
    
    class JubenErrorHandler:
        def __init__(self): pass
        def get_error_summary(self): return {}
    
    # 创建模拟FastAPI应用
    from fastapi import FastAPI
    app = FastAPI(title="Juben竖屏短剧策划助手API")
    
    # 创建模拟路由器
    from fastapi import APIRouter
    agent_streaming_router = APIRouter()


class JubenEnhancedServer:
    """Juben增强版服务器"""
    
    def __init__(self):
        """初始化服务器"""
        self.monitoring_system = MonitoringSystem()
        self.storage_optimizer = StorageOptimizer()
        self.error_handler = JubenErrorHandler()
        self.is_running = False
        self.startup_time = None
        
    async def startup(self):
        """启动服务器"""
        try:
            print("🚀 Juben竖屏短剧策划助手启动中...")
            self.startup_time = datetime.now()
            
            # 1. 初始化存储系统
            print("📊 初始化存储系统...")
            await self.storage_optimizer.initialize_connections()
            
            # 2. 优化存储性能
            print("⚡ 优化存储性能...")
            await self.storage_optimizer.optimize_all_storage()
            
            # 3. 启动监控系统
            print("🔍 启动监控系统...")
            self.monitoring_system.start_monitoring()
            
            # 4. 注册智能体流式API路由
            print("🤖 注册智能体流式API...")
            app.include_router(agent_streaming_router)
            
            # 4. 生成启动报告
            await self._generate_startup_report()
            
            self.is_running = True
            print("✅ Juben竖屏短剧策划助手启动完成！")
            print(f"⏰ 启动时间: {self.startup_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🌐 API文档: http://localhost:8000/docs")
            print(f"📊 系统监控: http://localhost:8000/system/info")
            
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """关闭服务器"""
        try:
            print("🛑 Juben竖屏短剧策划助手关闭中...")
            
            # 停止监控系统
            self.monitoring_system.stop_monitoring()
            
            # 生成关闭报告
            await self._generate_shutdown_report()
            
            self.is_running = False
            print("✅ Juben竖屏短剧策划助手关闭完成")
            
        except Exception as e:
            print(f"❌ 关闭失败: {e}")
    
    async def _generate_startup_report(self):
        """生成启动报告"""
        try:
            # 获取存储指标
            storage_metrics = await self.storage_optimizer.get_storage_metrics()
            
            # 获取系统健康状态
            system_health = self.monitoring_system.get_system_health()
            
            report = {
                "startup_time": self.startup_time.isoformat(),
                "status": "started",
                "storage_metrics": storage_metrics,
                "system_health": system_health,
                "version": "1.0.0"
            }
            
            # 保存启动报告
            report_path = project_root / "logs" / "startup_report.json"
            report_path.parent.mkdir(exist_ok=True)
            
            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"📋 启动报告已保存: {report_path}")
            
        except Exception as e:
            print(f"⚠️ 生成启动报告失败: {e}")
    
    async def _generate_shutdown_report(self):
        """生成关闭报告"""
        try:
            shutdown_time = datetime.now()
            uptime = shutdown_time - self.startup_time if self.startup_time else None
            
            # 获取最终指标
            storage_metrics = await self.storage_optimizer.get_storage_metrics()
            system_health = self.monitoring_system.get_system_health()
            
            report = {
                "shutdown_time": shutdown_time.isoformat(),
                "uptime_seconds": uptime.total_seconds() if uptime else 0,
                "status": "shutdown",
                "final_storage_metrics": storage_metrics,
                "final_system_health": system_health
            }
            
            # 保存关闭报告
            report_path = project_root / "logs" / "shutdown_report.json"
            report_path.parent.mkdir(exist_ok=True)
            
            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"📋 关闭报告已保存: {report_path}")
            
        except Exception as e:
            print(f"⚠️ 生成关闭报告失败: {e}")
    
    async def health_check(self):
        """健康检查"""
        try:
            # 检查存储系统
            storage_metrics = await self.storage_optimizer.get_storage_metrics()
            
            # 检查系统健康
            system_health = self.monitoring_system.get_system_health()
            
            # 检查错误率
            error_summary = self.error_handler.get_error_summary()
            
            health_status = {
                "status": "healthy" if system_health["status"] == "healthy" else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0,
                "storage_metrics": storage_metrics,
                "system_health": system_health,
                "error_summary": error_summary
            }
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 全局服务器实例
server = JubenEnhancedServer()


@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动
    await server.startup()
    yield
    # 关闭
    await server.shutdown()


# 设置应用生命周期
app.router.lifespan_context = lifespan


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n🛑 接收到信号 {signum}，正在关闭服务器...")
    asyncio.create_task(server.shutdown())
    sys.exit(0)


def main():
    """主函数"""
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 检查环境变量
    required_env_vars = [
        "ZHIPU_API_KEY",
        "REDIS_HOST",
        "MILVUS_HOST"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
        print("请设置以下环境变量:")
        for var in missing_vars:
            print(f"  export {var}=your_value")
        sys.exit(1)
    
    # 启动服务器
    try:
        print("🌟 欢迎使用Juben竖屏短剧策划助手！")
        print("=" * 50)
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True,
            reload=False,  # 生产环境建议关闭
            workers=1  # 单进程模式，便于调试
        )
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在关闭服务器...")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

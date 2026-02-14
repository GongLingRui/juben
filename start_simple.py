#!/usr/bin/env python3
"""
Juben竖屏短剧策划助手 - 简化版启动脚本
用于测试和调试系统
"""
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
from setup_env import setup_environment
setup_environment()

# 创建简化的FastAPI应用
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 创建应用
app = FastAPI(
    title="Juben竖屏短剧策划助手API",
    description="专业的竖屏短剧策划和创作助手",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Juben竖屏短剧策划助手API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00"
    }

@app.get("/test")
async def test_endpoint():
    """测试端点"""
    return {
        "message": "系统运行正常",
        "environment": {
            "python_version": sys.version,
            "working_directory": str(Path.cwd()),
            "project_root": str(project_root)
        }
    }

def main():
    """主函数"""
    print("🚀 启动Juben竖屏短剧策划助手...")
    print("📊 环境变量已设置")
    print("🌐 API文档: http://localhost:8000/docs")
    print("🔍 健康检查: http://localhost:8000/health")
    print("🧪 测试端点: http://localhost:8000/test")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=True
        )
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在关闭服务器...")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

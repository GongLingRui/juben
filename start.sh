#!/bin/bash

# 剧本创作 Agent 平台 - 启动脚本

set -e

echo "========================================"
echo "  剧本创作 Agent 平台"
echo "  支持 40+ 专业 AI Agents"
echo "========================================"
echo ""

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3，请先安装 Python 3.8+"
    exit 1
fi

# 检查 Node.js 环境
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"
echo "✅ Node.js 版本: $(node --version)"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，配置必要的 API 密钥"
    echo ""
fi

# 安装后端依赖
echo "📦 安装后端依赖..."
pip install -r requirements.txt --quiet
echo "✅ 后端依赖安装完成"
echo ""

# 检查前端
if [ -d "frontend" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install --silent
    cd ..
    echo "✅ 前端依赖安装完成"
    echo ""
fi

# 启动选择
echo "请选择启动方式:"
echo "1) 仅启动后端 (FastAPI)"
echo "2) 仅启动前端 (Vite 开发服务器)"
echo "3) 同时启动前后端"
echo "4) 构建并启动生产版本"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动后端服务..."
        echo "后端地址: http://localhost:8000"
        echo "API 文档: http://localhost:8000/docs"
        echo ""
        python3 main.py
        ;;
    2)
        echo ""
        echo "🚀 启动前端服务..."
        echo "前端地址: http://localhost:5173"
        echo ""
        cd frontend
        npm run dev
        ;;
    3)
        echo ""
        echo "🚀 启动前后端服务..."
        echo "后端地址: http://localhost:8000"
        echo "前端地址: http://localhost:5173"
        echo "API 文档: http://localhost:8000/docs"
        echo ""
        # 后台启动后端
        python3 main.py &
        BACKEND_PID=$!
        echo "✅ 后端已启动 (PID: $BACKEND_PID)"

        # 启动前端
        cd frontend
        npm run dev

        # 前端退出时，也关闭后端
        kill $BACKEND_PID 2>/dev/null || true
        ;;
    4)
        echo ""
        echo "🔨 构建前端..."
        cd frontend
        npm run build
        cd ..
        echo "✅ 前端构建完成"
        echo ""
        echo "🚀 启动生产服务..."
        echo "访问地址: http://localhost:8000"
        echo ""
        python3 main.py
        ;;
    *)
        echo "❌ 无效的选项"
        exit 1
        ;;
esac

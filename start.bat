@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   剧本创作 Agent 平台
echo   支持 40+ 专业 AI Agents
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo ✅ Python 版本:
python --version
echo ✅ Node.js 版本:
node --version
echo.

REM 检查 .env 文件
if not exist ".env" (
    echo 📝 创建 .env 文件...
    copy .env.example .env
    echo ⚠️  请编辑 .env 文件，配置必要的 API 密钥
    echo.
)

REM 安装后端依赖
echo 📦 安装后端依赖...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ❌ 后端依赖安装失败
    pause
    exit /b 1
)
echo ✅ 后端依赖安装完成
echo.

REM 检查前端
if exist "frontend" (
    echo 📦 安装前端依赖...
    cd frontend
    call npm install --silent
    cd ..
    echo ✅ 前端依赖安装完成
    echo.
)

echo 请选择启动方式:
echo 1^) 仅启动后端 ^(FastAPI^)
echo 2^) 仅启动前端 ^(Vite 开发服务器^)
echo 3^) 同时启动前后端
echo 4^) 构建并启动生产版本
echo.

set /p choice=请输入选项 (1-4):

if "%choice%"=="1" goto backend_only
if "%choice%"=="2" goto frontend_only
if "%choice%"=="3" goto both
if "%choice%"=="4" goto production
echo ❌ 无效的选项
pause
exit /b 1

:backend_only
echo.
echo 🚀 启动后端服务...
echo 后端地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.
python main.py
goto end

:frontend_only
echo.
echo 🚀 启动前端服务...
echo 前端地址: http://localhost:5173
echo.
cd frontend
call npm run dev
cd ..
goto end

:both
echo.
echo 🚀 启动前后端服务...
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.

REM 启动后端
start /B python main.py

REM 启动前端
cd frontend
call npm run dev
cd ..

goto end

:production
echo.
echo 🔨 构建前端...
cd frontend
call npm run build
cd ..
if errorlevel 1 (
    echo ❌ 前端构建失败
    pause
    exit /b 1
)
echo ✅ 前端构建完成
echo.
echo 🚀 启动生产服务...
echo 访问地址: http://localhost:8000
echo.
python main.py
goto end

:end
pause

# 剧本创作 Agent 平台 - 开发环境搭建指南

## 方法一：使用 Conda 创建虚拟环境

### 1. 安装 Conda（如果还没有）

**macOS:**
```bash
# 使用 Homebrew 安装
brew install --cask conda
```

**Windows/Linux:**
```bash
# 下载 Miniconda 安装脚本
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# 运行安装脚本
bash Miniconda3-latest-Linux-x86_64.sh

# 重启终端
source ~/.bashrc  # Linux
# 或
重启终端  # Windows
```

### 2. 创建 Conda 虚拟环境

```bash
# 创建 Python 3.10 环境
conda create -n juben python=3.10

# 或指定 Python 3.11
conda create -n juben python=3.11
```

### 3. 激活环境

```bash
# 激活环境
conda activate juben

# 确认环境已激活（终端提示符会变化）
# (juben) user@hostname ~%
```

### 4. 进入项目目录

```bash
# 进入项目目录
cd /Users/gongfan/juben  # macOS
# 或
cd ~/juben  # Linux/Windows
```

### 5. 安装项目依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 或使用 conda 安装（推荐）
conda install -c conda-forge fastapi uvicorn[standard] python-multipart python-jose[cryptography] cryptography
```

### 6. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用 vim、code 等
```

### 7. 启动后端服务

```bash
# 开发模式启动（热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Python 直接启动
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 方法二：使用 Python venv（轻量级方案）

如果你不想安装 Conda，可以使用 Python 内置的 venv：

```bash
# 1. 进入项目目录
cd /Users/gongfan/juben

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 方法三：使用 Docker（推荐用于生产环境）

```bash
# 1. 构建镜像
docker build -t juben-backend .

# 2. 运行容器
docker run -p 8000:8000 -e APP_ENV=production juben-backend

# 或使用 docker-compose（更方便）
docker-compose up -d
```

---

## 快速启动脚本

创建一个便捷的启动脚本 `start_dev.sh`：

```bash
#!/bin/bash

# 剧本创作 Agent 平台 - 开发环境启动脚本

echo "🚀 启动剧本创作 Agent 平台开发环境..."

# 检查 conda 是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ Conda 未安装，请先安装 Conda"
    echo "   访问: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# 激活 conda 环境
echo "📦 激活 conda 环境: juben"
source $(conda info --base)/etc/profile.d/conda.sh && conda activate juben

# 进入项目目录
cd "$(dirname "$0")"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 创建..."
    cp .env.example .env
    echo "   请编辑 .env 文件配置你的 API 密钥"
    echo "   nano .env"
    exit 1
fi

# 安装/更新依赖
echo "📦 安装 Python 依赖..."
pip install -q -r requirements.txt

# 检查依赖安装结果
if [ $? -eq 0 ]; then
    echo "✅ 依赖安装成功"
else
    echo "❌ 依赖安装失败"
    exit 1
fi

# 启动后端服务
echo "🎬 启动后端服务..."
echo "   API 文档: http://localhost:8000/docs"
echo "   健康检查: http://localhost:8000/health"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

使用方法：
```bash
# 1. 保存脚本
cat > start_dev.sh << 'EOF'
#!/bin/bash
# ... 复制上面的脚本内容 ...
EOF

# 2. 添加执行权限
chmod +x start_dev.sh

# 3. 运行
./start_dev.sh
```

---

## 前端开发环境设置

### 安装前端依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖（使用 pnpm）
pnpm install

# 或使用 npm
npm install
```

### 启动前端开发服务器

```bash
# 开发模式（热重载）
pnpm dev

# 或
npm run dev
```

前端将在 `http://localhost:5173` 启动

---

## 环境变量配置说明

### 必需配置的变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ZHIPU_API_KEY` | 智谱AI API密钥 | 从 https://open.bigmodel.cn 获取 |
| `POSTGRES_PASSWORD` | 数据库密码 | 随机强密码 |
| `JWT_SECRET_KEY` | JWT密钥 | 至少32位随机字符串 |
| `ADMIN_PASSWORD` | 管理员密码 | 随机强密码 |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_ENV` | 运行环境 | development |
| `DEBUG` | 调试模式 | false |
| `LOG_LEVEL` | 日志级别 | INFO |
| `REDIS_HOST` | Redis地址 | localhost:6379 |

---

## 常见问题排查

### 问题 1: ModuleNotFoundError: No module named 'xxx'

**解决方案**:
```bash
# 确保环境已激活
conda activate juben

# 重新安装依赖
pip install -r requirements.txt
```

### 问题 2: PostgreSQL 连接失败

**解决方案**:
```bash
# 检查 PostgreSQL 是否运行
brew services list  # macOS
# 或
sudo systemctl status postgresql  # Linux

# 启动 PostgreSQL
brew services start postgresql  # macOS
# 或
sudo systemctl start postgresql  # Linux

# 创建数据库
psql -U postgres -c "CREATE DATABASE juben;"
```

### 问题 3: 端口已被占用

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 终止进程
kill -9 <PID>

# 或使用其他端口
uvicorn main:app --port 8001
```

### 问题 4: CORS 错误

**解决方案**:
在 `.env` 文件中配置：
```bash
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## IDE 配置建议

### VS Code

推荐安装扩展：
- Python
- Pylance
- Python Docstring Generator

### PyCharm

1. 打开项目目录
2. File → Settings → Project → juben
3. 配置 Python 解释器为 conda 环境

---

## 验证安装

安装完成后，访问以下地址验证：

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| Prometheus 指标 | http://localhost:8000/metrics |
| 前端 | http://localhost:5173 |

---

## 生产环境部署注意事项

1. **修改所有默认密码和密钥**
2. **设置 `APP_ENV=production`**
3. **配置 HTTPS/SSL 证书**
4. **配置数据库备份策略**
5. **设置日志级别为 WARNING 或 ERROR**
6. **配置防火墙和安全组**
7. **启用进程管理器（如 supervisor、systemd）**

---

## 项目结构概览

```
juben/
├── main.py                 # FastAPI 应用入口
├── requirements.txt          # Python 依赖
├── .env.example            # 环境变量模板
├── apis/                  # API 路由
├── agents/                # AI Agents
├── utils/                 # 工具函数
├── middleware/             # 中间件
├── frontend/               # React 前端
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
└── migrations/             # 数据库迁移
```

---

## 下一步

1. ✅ 创建 conda 环境
2. ✅ 安装依赖
3. ✅ 配置环境变量
4. ✅ 启动后端
5. ✅ 启动前端（新终端）
6. ✅ 访问 http://localhost:8000/docs 测试 API

祝开发顺利！🎉

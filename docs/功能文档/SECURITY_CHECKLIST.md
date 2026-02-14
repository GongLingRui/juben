# 安全检查清单

在将代码公开到 GitHub 之前，请务必完成以下安全检查：

## ✅ 已完成的安全措施

### 1. Git 配置
- [x] 更新 `.gitignore` 文件，忽略所有敏感文件
- [x] 创建 `frontend/.gitignore` 文件
- [x] 添加环境变量文件到 `.gitignore`

### 2. 环境变量
- [x] 创建 `.env.example` 文件作为模板
- [x] 确保 `.env` 文件不包含真实密钥
- [x] 所有密钥使用占位符（如 `your-api-key-here`）

### 3. 代码检查
- [x] 创建 `scripts/security_check.py` 安全检查脚本
- [x] 创建 `scripts/pre-commit` 提交前钩子
- [x] 所有代码从环境变量读取密钥

## 🔍 提交前检查清单

### 必须检查

- [ ] **运行安全检查脚本**
  ```bash
  python scripts/security_check.py
  ```

- [ ] **验证 .gitignore**
  ```bash
  git status --short
  ```
  确保没有显示 `.env` 文件

- [ ] **检查 .env 文件**
  ```bash
  cat .env
  ```
  确保所有值都是占位符，不包含真实密钥

- [ ] **搜索硬编码密钥**
  ```bash
  grep -r "sk-" --include="*.py" --include="*.js" --exclude-dir=node_modules --exclude-dir=venv
  grep -r "sess-" --include="*.py" --include="*.js" --exclude-dir=node_modules --exclude-dir=venv
  ```

- [ ] **检查配置文件**
  - `config/settings.py` - 只应从环境变量读取
  - `config/config.yaml` - 使用 `${VAR_NAME}` 格式
  - 所有 `.env` 文件都在 `.gitignore` 中

### 推荐检查

- [ ] **启用 pre-commit hooks**
  ```bash
  chmod +x scripts/pre-commit
  ln -s ../../scripts/pre-commit .git/hooks/pre-commit
  ```

- [ ] **审查最近的提交**
  ```bash
  git log --oneline -10
  ```

- [ ] **检查分支中的敏感文件**
  ```bash
  git diff --name-only main | xargs grep -l "password\|secret\|api_key"
  ```

## 🚨 禁止提交的文件类型

以下文件类型和模式绝对不能提交：

### 环境变量文件
- `.env` （任何变体）
- `.env.local`
- `.env.development.local`
- `.env.test.local`
- `.env.production.local`

### 密钥文件
- `*.pem` - 私钥文件
- `*.key` - 密钥文件
- `credentials.json` - 凭证文件
- `secrets.yaml` - 密钥配置

### 数据库文件
- `*.sqlite`
- `*.sqlite3`
- `*.db`

### 日志文件
- `*.log`
- `logs/`

## ✅ 安全编码实践

### 1. 使用环境变量

❌ **错误做法**：
```python
api_key = "sk-abc123xyz789"
```

✅ **正确做法**：
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set")
```

### 2. 配置文件使用变量引用

❌ **错误做法**（config.yaml）：
```yaml
api_key: "sk-abc123xyz789"
```

✅ **正确做法**：
```yaml
api_key: "${OPENAI_API_KEY}"
```

### 3. 使用 .env.example

创建 `.env.example` 作为模板，包含所有必要的环境变量但不包含真实值：

```env
# API Keys
OPENAI_API_KEY=your-openai-api-key-here
ZHIPUAI_API_KEY=your-zhipuai-api-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

## 🔐 密钥管理最佳实践

### 开发环境
1. 创建 `.env` 文件（已在 `.gitignore` 中）
2. 从安全位置复制真实密钥
3. 永不提交 `.env` 文件

### 生产环境
1. 使用环境变量或密钥管理服务（如 AWS Secrets Manager）
2. 使用 CI/CD 平台的密钥管理功能
3. 定期轮换密钥

### 团队协作
1. 共享 `.env.example` 模板
2. 通过安全渠道（如 1Password、LastPass）共享真实密钥
3. 不要通过聊天、邮件等方式传输密钥

## 📋 提交前最后检查

运行以下命令确保没有敏感信息：

```bash
# 1. 检查 git 状态
git status

# 2. 确保没有敏感文件被跟踪
git ls-files | grep -E "\.env$|\.key$|\.pem$"

# 3. 运行安全检查
python scripts/security_check.py

# 4. 检查最近的更改
git diff --cached --name-only

# 5. 提交
git add .
git commit -m "你的提交信息"
```

## 🚨 如果发现已提交的敏感信息

如果发现已经提交了敏感信息：

1. **立即轮换密钥**
   - 登录相应的服务（OpenAI、智谱AI等）
   - 撤销旧密钥
   - 生成新密钥
   - 更新本地配置

2. **从 Git 历史中移除**
   ```bash
   # 使用 git filter-branch（需要谨慎）
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" --prune-empty HEAD

   # 或者使用 BFG Repo-Cleaner（推荐）
   # https://rtyley.github.io/bfg-repo-cleaner/
   ```

3. **强制推送到远程**
   ```bash
   git push origin --force --all
   ```

4. **通知团队成员**
   - 告知他们重新克隆仓库
   - 共享新的密钥获取方式

## 📞 联系方式

如果发现安全问题或需要帮助，请：
- 查看项目文档
- 提交 Issue
- 联系项目负责人

---

**记住：预防胜于治疗！永远不要提交敏感信息到代码仓库。**

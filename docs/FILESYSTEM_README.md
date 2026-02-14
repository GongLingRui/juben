# 文件系统 Artifact 管理文档

## 📁 概述

所有 Agent 的输出文件和 artifacts 现在统一存储在文件系统中，可以通过统一的 API 和前端页面进行浏览、下载和管理。

## 🏗️ 架构

### 文件存储结构

```
artifacts/
├── scripts/           # 剧本文件
├── outlines/          # 故事大纲
├── characters/        # 人物档案
├── plot_points/       # 情节点
├── mind_maps/         # 思维导图
├── ocr_results/       # OCR 识别结果
├── evaluations/       # 评测报告
├── analyses/          # 分析报告
├── workflows/         # 工作流输出
└── others/            # 其他文件
```

### 元数据存储

元数据存储在 `artifacts/.metadata.json`，包含：
- `artifact_id`: 唯一 ID
- `filename`: 文件名
- `file_path`: 完整路径
- `file_type`: 文件类型枚举
- `agent_source`: 来源 Agent
- `user_id`: 用户 ID
- `session_id`: 会话 ID
- `project_id`: 项目 ID
- `file_size`: 文件大小
- `content_hash`: SHA256 哈希
- `created_at/updated_at`: 时间戳
- `tags`: 标签列表
- `description`: 描述
- `parent_id/children_ids`: 父子关系
- `preview`: 内容预览（前200字符）
- `metadata`: 额外元数据

## 🔌 API 端点

### 1. 获取 Artifact 列表
```http
GET /juben/files/artifacts
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户 ID 过滤 |
| `project_id` | string | 项目 ID 过滤 |
| `agent_source` | string | Agent 来源过滤 |
| `file_type` | string | 文件类型过滤 |
| `tags` | string | 标签过滤（逗号分隔） |
| `limit` | int | 返回数量（默认100） |
| `offset` | int | 偏移量（默认0） |

**响应**:
```json
{
  "success": true,
  "total": 50,
  "data": [
    {
      "artifact_id": "art_20260207_120000_abc123",
      "filename": "ocr_session_20260207_120000.txt",
      "file_type": "ocr_result",
      "agent_source": "ocr_agent",
      "user_id": "user123",
      "session_id": "session456",
      "project_id": "user123_ocr",
      "file_size": 2048,
      "created_at": "2026-02-07T12:00:00",
      "tags": ["ocr", "text"],
      "description": "OCR 识别结果"
    }
  ]
}
```

### 2. 获取单个 Artifact
```http
GET /juben/files/artifact/{artifact_id}
```

### 3. 下载 Artifact
```http
GET /juben/files/download/{artifact_id}
```

### 4. 预览 Artifact
```http
GET /juben/files/preview/{artifact_id}
```

### 5. 获取项目文件树
```http
GET /juben/files/tree/{project_id}
```

### 6. 获取统计信息
```http
GET /juben/files/statistics
```

### 7. 删除 Artifact
```http
DELETE /juben/files/artifact/{artifact_id}
```

## 💻 集成到 Agent

### 方式一：使用 Artifact Manager

```python
from utils.artifact_manager import (
    get_artifact_manager,
    ArtifactType,
    AgentSource,
    register_agent_output
)

# 在 Agent 中保存输出
def save_my_agent_output(content: str, filename: str):
    artifact_id = register_agent_output(
        content=content,
        filename=filename,
        file_type=ArtifactType.SCRIPT,
        agent_source=AgentSource.SHORT_DRAMA_CREATOR,
        user_id="user123",
        session_id="session456",
        project_id="my_project",
        description="短剧剧本",
        tags=["剧本", "第一集"]
    )
    return artifact_id
```

### 方式二：直接使用 Manager

```python
from utils.artifact_manager import get_artifact_manager

manager = get_artifact_manager()

# 保存文件
metadata = manager.save_artifact(
    content="文件内容",
    filename="output.txt",
    file_type=ArtifactType.SCRIPT,
    agent_source=AgentSource.SHORT_DRAMA_CREATOR,
    user_id="user123",
    session_id="session456",
    project_id="my_project",
    description="描述",
    tags=["tag1", "tag2"],
    parent_id=None,  # 父 artifact ID（用于关联）
    metadata={"extra": "data"}
)
```

## 🎨 前端集成

### 1. 添加路由

在 `frontend/src/App.tsx` 中添加文件系统页面路由：

```tsx
import FileSystemPage from '@/pages/FileSystemPage';

// 在路由配置中添加
<Route path="/files" element={<FileSystemPage />} />
```

### 2. 在导航菜单中添加链接

```tsx
<Link to="/files" className="flex items-center gap-2">
  <FolderOpen className="w-5 h-5" />
  <span>文件系统</span>
</Link>
```

## 📊 文件类型

| 类型 | 枚举值 | 存储目录 | 图标 |
|------|--------|----------|------|
| 剧本 | `script` | `scripts/` | 📜 |
| 大纲 | `outline` | `outlines/` | 📋 |
| 人物 | `character` | `characters/` | 👤 |
| 情节点 | `plot_points` | `plot_points/` | 📍 |
| 思维导图 | `mind_map` | `mind_maps/` | 🧠 |
| OCR结果 | `ocr_result` | `ocr_results/` | 📷 |
| 评测报告 | `evaluation` | `evaluations/` | 📊 |
| 分析报告 | `analysis` | `analyses/` | 🔍 |
| Markdown | `markdown` | `workflows/` | 📝 |
| JSON | `json` | `workflows/` | 🗂️ |
| 图片 | `image` | `mind_maps/` | 🖼️ |

## 🔧 Agent 来源

| Agent | 枚举值 | 说明 |
|-------|--------|------|
| 短剧创作 | `short_drama_creator` | 短剧剧本生成 |
| 短剧评测 | `short_drama_evaluation` | 短剧质量评测 |
| 故事大纲 | `story_summary_generator` | 故事大纲生成 |
| 人物小传 | `character_profile_generator` | 人物档案生成 |
| 大情节点 | `major_plot_points` | 大情节点生成 |
| 详细情节点 | `detailed_plot_points` | 详细情节点生成 |
| 思维导图 | `mind_map` | 思维导图生成 |
| OCR识别 | `ocr_agent` | OCR 文字识别 |
| 工作流编排 | `workflow_orchestrator` | 工作流编排器 |

## 📝 使用示例

### Python API

```python
# 获取管理器
from utils.artifact_manager import get_artifact_manager
manager = get_artifact_manager()

# 列出所有 artifacts
artifacts = manager.list_artifacts(limit=50)

# 按用户过滤
user_artifacts = manager.list_artifacts(user_id="user123")

# 按项目过滤
project_artifacts = manager.list_artifacts(project_id="my_project")

# 按 Agent 过滤
from utils.artifact_manager import AgentSource
scripts = manager.list_artifacts(agent_source=AgentSource.SHORT_DRAMA_CREATOR)

# 获取文件内容
content = manager.get_artifact_content(artifact_id)

# 获取统计信息
stats = manager.get_statistics()
print(f"总文件数: {stats['total_artifacts']}")
print(f"总大小: {stats['total_size_mb']} MB")

# 获取项目文件树
tree = manager.get_artifact_tree(project_id="my_project")

# 删除旧文件
deleted = manager.cleanup_old_artifacts(days=30)
```

### cURL

```bash
# 获取所有 artifacts
curl http://localhost:8000/juben/files/artifacts

# 获取特定用户的文件
curl "http://localhost:8000/juben/files/artifacts?user_id=user123"

# 获取 OCR 结果
curl "http://localhost:8000/juben/files/artifacts?file_type=ocr_result"

# 下载文件
curl -O http://localhost:8000/juben/files/download/art_20260207_120000_abc123

# 获取统计信息
curl http://localhost:8000/juben/files/statistics

# 删除文件
curl -X DELETE http://localhost:8000/juben/files/artifact/art_20260207_120000_abc123
```

### JavaScript/TypeScript

```typescript
// 获取 artifacts
const response = await fetch('http://localhost:8000/juben/files/artifacts');
const data = await response.json();
console.log(data.data);

// 下载文件
const downloadFile = async (artifactId: string, filename: string) => {
  const response = await fetch(`http://localhost:8000/juben/files/download/${artifactId}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
```

## 🔐 文件关联

Artifact 系统支持文件间的父子关联，例如：

1. OCR 识别：原始 JSON ← 格式化输出
2. 工作流：工作流元数据 ← 各阶段输出
3. 评测：评测报告 ← 被评测内容 ← 评测详情

```python
# 父 artifact ID
parent_id = register_agent_output(raw_content, "raw.json", ...)

# 子 artifact（关联到父）
child_id = register_agent_output(
    formatted_content,
    "output.md",
    parent_id=parent_id  # 关联
)
```

## 📅 定期清理

可以定期清理旧的 artifacts：

```python
# Python 代码
from utils.artifact_manager import get_artifact_manager

manager = get_artifact_manager()

# 清理 30 天前的文件
deleted_count = manager.cleanup_old_artifacts(days=30)

# 或使用 API
# POST /juben/files/cleanup?days=30
```

## 🚀 快速开始

1. **启动服务**：
```bash
python main.py
```

2. **访问文件系统页面**：
```
http://localhost:8000/files
```

3. **查看 API 文档**：
```
http://localhost:8000/docs
```

## 📄 许可

内部项目，仅供团队使用。

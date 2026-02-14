# PaddleOCR-VL 集成文档

基于 PaddleOCR-VL 模型的本地 OCR 识别服务，支持 RTX 5070 8GB 显存。

## 📦 环境准备

### 1. 硬件要求
- **GPU**: NVIDIA RTX 5070 (8GB VRAM) 或更高
- **内存**: 建议 16GB+ RAM
- **存储**: 至少 10GB 可用空间

### 2. 软件依赖

#### Python 环境
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 升级 pip
pip install --upgrade pip
```

#### 安装 PaddlePaddle (GPU 版)
```bash
# CUDA 11.8 版本
pip install paddlepaddle-gpu==2.6.0 -i https://mirror.baidu.com/pypi/simple

# 或 CUDA 12.3 版本
pip install paddlepaddle-gpu==2.6.0 -i https://mirror.baidu.com/pypi/simple
```

#### 安装 PaddleOCR
```bash
pip install paddleocr>=2.7.0
```

#### 其他依赖
```bash
pip install pillow opencv-python-headless python-multipart
pip install fastapi python-multipart uvicorn
```

## 🚀 快速开始

### 1. 启动服务

```bash
# 进入项目目录
cd /path/to/juben

# 启动后端服务
python main.py

# 服务将在 http://localhost:8000 启动
```

### 2. 测试 OCR

访问 http://localhost:8000/docs 查看自动生成的 API 文档。

#### 使用 curl 测试

```bash
# 上传文件进行 OCR
curl -X POST "http://localhost:8000/juben/ocr/upload" \
  -F "file=@test_image.jpg" \
  -F "output_format=text" \
  -F "use_structure=false"
```

#### 使用 Python 测试

```python
import requests

# 上传文件
with open('test_image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/juben/ocr/upload',
        files={'file': f},
        data={
            'output_format': 'markdown',
            'use_structure': 'true'
        },
        stream=True
    )

    # 处理 SSE 响应
    for line in response.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            print(f"Event: {data['event']}, Data: {data['data']}")
```

## 📁 文件结构

```
juben/
├── agents/
│   └── ocr_agent.py              # OCR Agent
├── apis/
│   └── ocr/
│       └── api_routes_ocr.py     # OCR API 路由
├── utils/
│   └── paddleocr_service.py      # PaddleOCR 服务封装
├── frontend/
│   └── src/
│       ├── components/ocr/
│       │   ├── OCRUploader.tsx   # 上传组件
│       │   └── index.ts
│       └── pages/
│           └── OCRPage.tsx       # OCR 页面
├── uploads/ocr/                  # 上传文件存储目录
└── outputs/ocr/                  # OCR 结果输出目录
```

## 🔌 API 端点

### 1. 查询 OCR 状态
```http
GET /juben/ocr/status
```

**响应**:
```json
{
  "available": true,
  "gpu_enabled": true,
  "supported_formats": ["jpg", "jpeg", "png", "bmp", "tiff", "pdf"],
  "output_formats": ["text", "markdown", "json", "structured"]
}
```

### 2. 上传文件进行 OCR
```http
POST /juben/ocr/upload
Content-Type: multipart/form-data
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 上传的图片文件 |
| output_format | string | 否 | 输出格式 (text/markdown/json/structured) |
| use_structure | boolean | 否 | 是否使用结构化识别 |
| save_result | boolean | 否 | 是否保存结果 |

**响应**: SSE 流式事件

### 3. 批量 OCR
```http
POST /juben/ocr/batch
Content-Type: application/json
```

**请求体**:
```json
{
  "file_paths": ["path1.jpg", "path2.png"],
  "output_format": "text"
}
```

### 4. 获取识别结果
```http
GET /juben/ocr/result/{task_id}
```

### 5. 下载识别结果
```http
GET /juben/ocr/download/{task_id}?format=txt
```

## 🎨 输出格式

### 1. 纯文本 (text)
```
识别的文本内容
按阅读顺序拼接
```

### 2. Markdown (markdown)
```markdown
# OCR 识别结果

**识别时间**: 2026-02-07T12:00:00
**处理耗时**: 1.23秒

## 识别文本
...

## 表格
...

## 公式
$$...
$$
```

### 3. JSON (json)
```json
{
  "success": true,
  "text": "完整文本",
  "text_boxes": [
    {
      "text": "文本内容",
      "box": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
      "confidence": 0.98,
      "position": [x, y]
    }
  ],
  "metadata": {...}
}
```

### 4. 结构化数据 (structured)
```json
{
  "text": "完整文本",
  "text_boxes": [...],
  "layout": [...],
  "tables": [...],
  "formulas": [...]
}
```

## 🔧 配置选项

### GPU 配置
```python
from utils.paddleocr_service import get_paddleocr_service

# 使用 GPU 0
ocr_service = get_paddleocr_service(
    use_gpu=True,
    gpu_id=0,
    lang="ch"  # 中英文混合
)

# 使用 GPU 1
ocr_service = get_paddleocr_service(
    use_gpu=True,
    gpu_id=1,
    lang="en"  # 英文
)
```

### 语言支持
| 语言代码 | 说明 |
|---------|------|
| `ch` | 中英文混合（默认） |
| `en` | 英文 |
| `japanese` | 日语 |
| `korean` | 韩语 |
| `french` | 法语 |
| `german` | 德语 |

## 🐛 故障排除

### 1. CUDA 错误
```bash
# 检查 CUDA 版本
nvidia-smi

# 检查 PyTorch CUDA 支持
python -c "import torch; print(torch.cuda.is_available())"
```

### 2. 内存不足
```python
# 减小批处理大小
ocr_service = get_paddleocr_service(max_batch_size=5)

# 或禁用 GPU（使用 CPU）
ocr_service = get_paddleocr_service(use_gpu=False)
```

### 3. 模型下载失败
```bash
# 手动下载模型
wget https://paddleocr.bj.bcebos.com/PP-OCRv3/chinese/ch_PP-OCRv3_det_infer.tar

# 放置到指定目录
mkdir -p ~/.paddleocr/whl/det/ch/
mv ch_PP-OCRv3_det_infer.tar ~/.paddleocr/whl/det/ch/
```

## 📊 性能优化

### RTX 5070 8GB 配置建议
```python
# 最优配置
ocr_service = PaddleOCRService(
    use_gpu=True,
    gpu_id=0,
    lang="ch",
    max_batch_size=10,      # 批处理大小
    use_angle_cls=True,     # 启用方向分类
    show_log=False          # 关闭日志
)
```

### 预期性能
| 分辨率 | 处理时间 | GPU 使用 |
|--------|----------|----------|
| 1920x1080 | ~1.5秒 | ~6GB |
| 1280x720 | ~0.8秒 | ~4GB |
| 800x600 | ~0.5秒 | ~3GB |

## 🔐 安全注意事项

1. **文件大小限制**: 默认最大 20MB
2. **文件类型限制**: 仅支持图片和 PDF
3. **本地处理**: 所有处理在本地完成，数据不上传云端
4. **存储清理**: 定期清理 uploads/ 和 outputs/ 目录

## 📚 参考资料

- [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR 文档](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/doc/doc_ch/quickstart.md)
- [PaddleOCR-VL 模型](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

## 📄 许可

内部项目，仅供团队使用。

# 百度 API 集成文档

本项目集成了四个百度服务 API，提供搜索、百科查询、视频搜索等功能。

## 📋 目录

- [服务概述](#服务概述)
- [免费额度](#免费额度)
- [快速开始](#快速开始)
- [API 接口](#api-接口)
- [前端使用](#前端使用)
- [后端使用](#后端使用)
- [示例代码](#示例代码)

## 🎯 服务概述

本项目集成了以下四个百度 API 服务：

| 服务 | 描述 | 用途 |
|------|------|------|
| **百度搜索** | 搜索全网实时信息 | 获取最新资讯、参考资料 |
| **百科词条** | 查询相关百科词条列表 | 快速找到相关词条 |
| **百度百科** | 查询词条详细内容 | 获取完整的百科信息 |
| **秒懂百科** | 查询百科视频内容 | 获取科普视频资源 |

## 💰 免费额度

### 百度搜索 API
- **每日免费额度**: 100 次
- **最大限制**: 每账号每天 100,000 次（需开通后付费）
- **计费方式**: 默认优先抵扣免费资源

### 百科系列 API
- **百科词条**: 按组件计费
- **百度百科**: 按组件计费
- **秒懂百科**: 按组件计费
- **详细计费**: 请查看 [百度千帆平台计费说明](https://qianfan.baidubce.com/price)

> 💡 **提示**: 免费额度足以支持开发和测试使用。生产环境建议开通后付费。

## 🚀 快速开始

### 1. 配置 API Key

在项目根目录的 `.env` 文件中添加百度 API Key：

```bash
# 百度API配置
BAIDU_API_KEY=your-baidu-api-key-here
```

### 2. 获取 API Key

1. 访问 [百度千帆平台](https://qianfan.baidubce.com/)
2. 注册/登录账号
3. 进入「应用接入」→「API Key 管理」
4. 创建新的 API Key

### 3. 安装依赖

后端已包含所需依赖 (`httpx`)，无需额外安装。

## 📡 API 接口

### 后端 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/baidu/web_search` | POST | 百度搜索 |
| `/baidu/lemma_list` | POST | 百科词条列表 |
| `/baidu/lemma_content` | POST | 百度百科内容 |
| `/baidu/second_know` | POST | 秒懂百科视频 |
| `/baidu/comprehensive` | POST | 组合查询 |
| `/baidu/search/{query}` | GET | 快速搜索 |
| `/baidu/baike/{keyword}` | GET | 快速百科 |
| `/baidu/health` | GET | 健康检查 |

### 请求/响应格式

#### 1. 百度搜索

**请求示例:**
```json
POST /baidu/web_search
{
  "query": "北京旅游景点",
  "edition": "standard",
  "top_k": 10,
  "search_recency_filter": "month"
}
```

**响应示例:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "北京十大旅游景点推荐",
      "url": "https://example.com/beijing",
      "content": "北京作为中国的首都...",
      "date": "2024-01-15",
      "type": "web"
    }
  ],
  "total": 10
}
```

#### 2. 百科词条列表

**请求示例:**
```json
POST /baidu/lemma_list
{
  "lemma_title": "刘德华",
  "top_k": 5
}
```

**响应示例:**
```json
{
  "success": true,
  "data": [
    {
      "lemma_id": 114923,
      "lemma_title": "刘德华",
      "lemma_desc": "华语影视男演员、流行乐歌手...",
      "is_default": 1,
      "url": "https://baike.baidu.com/item/刘德华"
    }
  ],
  "total": 5
}
```

#### 3. 百度百科

**请求示例:**
```json
POST /baidu/lemma_content
{
  "search_key": "刘德华",
  "search_type": "lemmaTitle"
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "lemma_id": 114923,
    "lemma_title": "刘德华",
    "lemma_desc": "华语影视男演员、流行乐歌手...",
    "summary": "刘德华，1961年9月27日出生于香港...",
    "abstract_plain": "刘德华，英文名Andy Lau...",
    "pic_url": "https://bkimg.cdn.bcebos.com/...",
    "classify": ["演员", "歌手"],
    "relations": [
      {
        "lemma_id": 63815079,
        "lemma_title": "朱丽蒨",
        "relation_name": "妻子",
        "square_pic_url": "https://..."
      }
    ],
    "videos": []
  }
}
```

#### 4. 秒懂百科视频

**请求示例:**
```json
POST /baidu/second_know
{
  "search_key": "刘德华",
  "search_type": "lemmaTitle",
  "limit": 3
}
```

**响应示例:**
```json
{
  "success": true,
  "data": [
    {
      "lemma_id": 114923,
      "lemma_title": "刘德华",
      "lemma_desc": "华语影视男演员、流行乐歌手...",
      "second_id": 65563140,
      "second_title": "一分钟了解刘德华",
      "cover_pic_url": "https://bkimg.cdn.bcebos.com/...",
      "forever_play_url_mp4": "https://baikevideo.cdn.bcebos.com/.../video.mp4",
      "play_time": 58,
      "second_type": 1
    }
  ],
  "total": 3
}
```

#### 5. 组合查询

**请求示例:**
```json
POST /baidu/comprehensive
{
  "keyword": "刘德华",
  "max_videos": 3
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "keyword": "刘德华",
    "baike": { /* 百度百科 */ },
    "videos": [ /* 秒懂视频 */ ]
  }
}
```

## 🎨 前端使用

### 导入服务

```typescript
import baiduService from '@/services/baiduService';
import {
  BaiduSearchResult,
  BaiduBaikeContent,
  BaiduVideoList
} from '@/components/baidu';
```

### 搜索示例

```typescript
import { webSearch, quickSearch } from '@/services/baiduService';

// POST 方式
const results = await webSearch({
  query: '北京旅游景点',
  top_k: 10,
  search_recency_filter: 'month'
});

// GET 快速搜索
const results = await quickSearch('北京旅游景点', 10);
```

### 百科查询示例

```typescript
import { comprehensiveSearch, quickBaike } from '@/services/baiduService';

// 组合查询（百科+视频）
const result = await comprehensiveSearch({
  keyword: '刘德华',
  max_videos: 3
});

// 快速百科查询
const result = await quickBaike('刘德华', true);
```

### 组件使用示例

```tsx
import { BaiduSearchResult, BaiduBaikeContent, BaiduVideoList } from '@/components/baidu';

function MyComponent() {
  const [searchResults, setSearchResults] = useState([]);
  const [baikeContent, setBaikeContent] = useState(null);
  const [videos, setVideos] = useState([]);

  return (
    <div>
      {/* 搜索结果 */}
      <BaiduSearchResult results={searchResults} />

      {/* 百科内容 */}
      <BaiduBaikeContent content={baikeContent} />

      {/* 视频列表 */}
      <BaiduVideoList videos={videos} />
    </div>
  );
}
```

## 🔧 后端使用

### Python 客户端

```python
from utils.baidu_client import get_baidu_client

# 获取客户端
client = get_baidu_client()

# 1. 网页搜索
search_result = await client.web_search(
    query="北京旅游景点",
    top_k=10,
    search_recency_filter="month"
)

# 2. 百科词条列表
lemma_list = await client.get_lemma_list(
    lemma_title="刘德华",
    top_k=5
)

# 3. 百度百科
baike_content = await client.get_lemma_content(
    search_key="刘德华",
    search_type="lemmaTitle"
)

# 4. 秒懂百科视频
videos = await client.search_second_know_video(
    search_key="刘德华",
    limit=3
)

# 5. 组合查询
comprehensive = await client.search_baike_comprehensive(
    keyword="刘德华",
    max_videos=3
)
```

### 在 Agent 中使用

```python
from agents.base_agent import BaseAgent
from utils.baidu_client import get_baidu_client

class MyBaiduAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.baidu_client = get_baidu_client()

    async def search_with_baidu(self, query: str):
        """使用百度搜索"""
        result = await self.baidu_client.web_search(query, top_k=5)

        # 格式化结果
        formatted = []
        for ref in result.get('references', []):
            formatted.append(f"- {ref['title']}: {ref['url']}")

        return '\n'.join(formatted)
```

## 📝 参数说明

### 搜索参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索关键词 |
| edition | string | 否 | 搜索版本 (standard/lite) |
| top_k | number | 否 | 返回数量 (1-50) |
| search_recency_filter | string | 否 | 时间过滤 (week/month/semiyear/year) |

### 百科参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lemma_title / search_key | string | 是 | 词条名称 |
| top_k | number | 否 | 返回数量 (1-100) |
| search_type | string | 否 | 检索类型 (lemmaTitle/lemmaId) |

### 视频参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| search_key | string | 是 | 检索关键字 |
| search_type | string | 否 | 检索类型 (lemmaTitle/lemmaId) |
| limit | number | 否 | 限制数量 (1-10) |
| video_type | number | 否 | 视频类型 (0=全部, 1=概述型) |
| platform | string | 否 | 视频来源 |

## 🧪 测试

运行后端测试：

```bash
cd /Users/gongfan/juben
python -m utils.baidu_client
```

这将测试所有四个百度 API 服务。

## 🔗 相关链接

- [百度千帆平台](https://qianfan.baidubce.com/)
- [API 认证文档](https://qianfan.baidubce.com/doc/AppBuilder/quick_start)
- [计费说明](https://qianfan.baidubce.com/price)

## 📚 更多示例

查看以下文件获取更多使用示例：
- `/Users/gongfan/juben/utils/baidu_client.py` - 后端客户端
- `/Users/gongfan/juben/frontend/src/services/baiduService.ts` - 前端服务
- `/Users/gongfan/juben/apis/baidu/api_routes_baidu.py` - API 路由

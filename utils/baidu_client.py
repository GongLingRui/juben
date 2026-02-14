"""
百度 API 客户端
集成四个百度服务：搜索、百科词条、百度百科、秒懂百科
"""
import os
import logging
import httpx
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 设置日志
logger = logging.getLogger(__name__)


class BaiduAPIClient:
    """百度 API 客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化百度 API 客户端

        Args:
            api_key: 百度 API Key，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv("BAIDU_API_KEY")
        if not self.api_key:
            logger.warning("百度 API Key 未设置")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = 30.0

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 其他请求参数

        Returns:
            响应数据
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"百度 API 请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"百度 API 请求异常: {e}")
            raise

    # ==================== 1. 百度搜索 API ====================

    async def web_search(
        self,
        query: str,
        edition: str = "standard",
        top_k: int = 10,
        search_recency_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        百度搜索 - 搜索全网实时信息

        免费额度: 每日 100 次
        最大限制: 每账号每天 100,000 次

        Args:
            query: 搜索关键词
            edition: 搜索版本 (standard=完整版, lite=标准版)
            top_k: 返回结果数量 (1-50)
            search_recency_filter: 时间过滤 (week/month/semiyear/year)

        Returns:
            搜索结果列表
        """
        url = "https://qianfan.baidubce.com/v2/ai_search/web_search"

        payload = {
            "messages": [
                {
                    "content": query,
                    "role": "user"
                }
            ],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [
                {"type": "web", "top_k": top_k}
            ]
        }

        if edition:
            payload["edition"] = edition

        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter

        logger.info(f"[百度搜索] 查询: {query}, top_k: {top_k}")
        result = await self._request("POST", url, json=payload)
        logger.info(f"[百度搜索] 返回 {len(result.get('references', []))} 条结果")
        return result

    # ==================== 2. 百科词条 API ====================

    async def get_lemma_list(
        self,
        lemma_title: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        百科词条 - 查询相关百科词条列表

        Args:
            lemma_title: 词条名称
            top_k: 返回结果数量 (1-100)

        Returns:
            词条列表
        """
        url = "https://appbuilder.baidu.com/v2/baike/lemma/get_list_by_title"

        params = {
            "lemma_title": lemma_title,
            "top_k": top_k
        }

        logger.info(f"[百科词条] 查询: {lemma_title}, top_k: {top_k}")
        result = await self._request("GET", url, params=params)
        logger.info(f"[百科词条] 返回 {len(result.get('result', {}).get('lemma_list', []))} 条结果")
        return result

    # ==================== 3. 百度百科 API ====================

    async def get_lemma_content(
        self,
        search_key: str,
        search_type: str = "lemmaTitle"
    ) -> Dict[str, Any]:
        """
        百度百科 - 查询词条详细内容

        Args:
            search_key: 检索关键字（词条名或词条ID）
            search_type: 检索类型 (lemmaTitle=按词条名, lemmaId=按词条ID)

        Returns:
            词条详细内容
        """
        url = "https://appbuilder.baidu.com/v2/baike/lemma/get_content"

        params = {
            "search_type": search_type,
            "search_key": search_key
        }

        logger.info(f"[百度百科] 查询: {search_key}, type: {search_type}")
        result = await self._request("GET", url, params=params)
        logger.info(f"[百度百科] 查询成功: {result.get('result', {}).get('lemma_title', '')}")
        return result

    # ==================== 4. 秒懂百科 API ====================

    async def search_second_know_video(
        self,
        search_key: str,
        search_type: str = "lemmaTitle",
        limit: int = 3,
        video_type: int = 0,
        platform: str = "user"
    ) -> Dict[str, Any]:
        """
        秒懂百科 - 查询百科视频内容

        Args:
            search_key: 检索关键字（词条名或词条ID）
            search_type: 检索类型 (lemmaTitle=按词条名, lemmaId=按词条ID)
            limit: 限制获取数量
            video_type: 视频类型 (0=全部, 1=概述型)
            platform: 视频来源 (user=高级用户, app=App用户, partner=合作方, pgc=PGC)

        Returns:
            视频列表
        """
        url = "https://appbuilder.baidu.com/v2/baike/second_know/search_video"

        params = {
            "search_type": search_type,
            "search_key": search_key,
            "limit": limit,
            "type": video_type,
            "platform": platform
        }

        logger.info(f"[秒懂百科] 查询: {search_key}, type: {search_type}, limit: {limit}")
        result = await self._request("GET", url, params=params)
        logger.info(f"[秒懂百科] 返回 {len(result.get('result', []))} 个视频")
        return result

    # ==================== 组合查询 ====================

    async def search_baike_comprehensive(
        self,
        keyword: str,
        max_videos: int = 3
    ) -> Dict[str, Any]:
        """
        组合查询：同时查询百科内容和秒懂视频

        Args:
            keyword: 关键词
            max_videos: 最大视频数量

        Returns:
            包含百科内容和视频的完整结果
        """
        import asyncio

        logger.info(f"[组合查询] 开始查询: {keyword}")

        # 并发查询
        tasks = [
            self.get_lemma_content(keyword),
            self.search_second_know_video(keyword, limit=max_videos)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            baike_result = results[0] if not isinstance(results[0], Exception) else None
            video_result = results[1] if not isinstance(results[1], Exception) else None

            return {
                "keyword": keyword,
                "baike": baike_result,
                "videos": video_result,
                "success": True
            }
        except Exception as e:
            logger.error(f"[组合查询] 失败: {e}")
            return {
                "keyword": keyword,
                "error": str(e),
                "success": False
            }


# ==================== 工厂函数 ====================

def get_baidu_client() -> BaiduAPIClient:
    """获取百度 API 客户端实例"""
    return BaiduAPIClient()


# ==================== 测试代码 ====================

if __name__ == "__main__":
    import asyncio

    async def test():
        """测试百度 API"""
        logger.info("=" * 60)
        logger.info("百度 API 测试")
        logger.info("=" * 60)

        client = get_baidu_client()

        # 测试 1: 网页搜索
        logger.info("\n1. 测试网页搜索:")
        logger.info("-" * 40)
        try:
            search_result = await client.web_search("北京旅游景点", top_k=3)
            logger.info(f"搜索结果: {len(search_result.get('references', []))} 条")
            for ref in search_result.get('references', [])[:2]:
                logger.info(f"  - {ref.get('title', '')}")
        except Exception as e:
            logger.error(f"搜索失败: {e}")

        # 测试 2: 百科词条列表
        logger.info("\n2. 测试百科词条列表:")
        logger.info("-" * 40)
        try:
            lemma_list = await client.get_lemma_list("刘德华", top_k=3)
            logger.info(f"词条列表: {len(lemma_list.get('result', {}).get('lemma_list', []))} 条")
        except Exception as e:
            logger.error(f"查询失败: {e}")

        # 测试 3: 百度百科内容
        logger.info("\n3. 测试百度百科:")
        logger.info("-" * 40)
        try:
            baike_content = await client.get_lemma_content("刘德华")
            result = baike_content.get('result', {})
            logger.info(f"词条: {result.get('lemma_title', '')}")
            logger.info(f"描述: {result.get('lemma_desc', '')}")
            logger.info(f"关系数: {len(result.get('relations', []))} 个")
        except Exception as e:
            logger.error(f"查询失败: {e}")

        # 测试 4: 秒懂百科视频
        logger.info("\n4. 测试秒懂百科:")
        logger.info("-" * 40)
        try:
            videos = await client.search_second_know_video("刘德华", limit=2)
            logger.info(f"视频数: {len(videos.get('result', []))} 个")
            for video in videos.get('result', [])[:2]:
                logger.info(f"  - {video.get('second_title', '')}")
        except Exception as e:
            logger.error(f"查询失败: {e}")

        # 测试 5: 组合查询
        logger.info("\n5. 测试组合查询:")
        logger.info("-" * 40)
        try:
            comprehensive = await client.search_baike_comprehensive("刘德华")
            logger.info(f"组合查询成功: {comprehensive.get('success', False)}")
        except Exception as e:
            logger.error(f"查询失败: {e}")

        logger.info("\n" + "=" * 60)
        logger.info("测试完成")
        logger.info("=" * 60)

    # 运行测试
    asyncio.run(test())

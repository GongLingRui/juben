"""
剧集信息客户端
用于获取电视剧的基础信息和分集剧情
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
import json


class SeriesInfoClient:
    """剧集信息客户端"""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        初始化剧集信息客户端
        
        Args:
            api_url: API接口URL，如果为None则使用模拟数据
        """
        self.api_url = api_url or "https://api.example.com/getSeriesInfo"  # 实际使用时需要替换为真实的API地址
        self.logger = None  # 可以后续注入logger
    
    async def get_series_info(self, series_name: str) -> Dict[str, Any]:
        """
        获取剧集信息
        
        Args:
            series_name: 剧集名称
            
        Returns:
            Dict[str, Any]: 剧集信息结果
        """
        try:
            # 构建请求数据
            request_data = {
                "seriesName": series_name
            }
            
            # 调用API获取剧集信息
            result = await self._call_series_info_api(request_data)
            
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取剧集信息失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "msg": f"获取剧集信息失败: {str(e)}",
                "code": -1,
                "data": {},
                "tv_episode_plot": "",
                "tv_info": ""
            }
    
    async def _call_series_info_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用剧集信息API
        
        Args:
            request_data: 请求数据
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        try:
            # 使用aiohttp进行异步HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # 标准化响应格式
                        return {
                            "success": True,
                            "msg": result.get("msg", "success"),
                            "code": result.get("code", 0),
                            "data": result.get("data", {}),
                            "tv_episode_plot": result.get("tv_episode_plot", ""),
                            "tv_info": result.get("tv_info", "")
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "msg": f"API调用失败: HTTP {response.status}",
                            "code": response.status,
                            "data": {},
                            "tv_episode_plot": "",
                            "tv_info": ""
                        }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "API调用超时",
                "msg": "请求超时",
                "code": -1,
                "data": {},
                "tv_episode_plot": "",
                "tv_info": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "msg": f"API调用异常: {str(e)}",
                "code": -1,
                "data": {},
                "tv_episode_plot": "",
                "tv_info": ""
            }
    
    async def get_mock_series_info(self, series_name: str) -> Dict[str, Any]:
        """
        获取模拟剧集信息（用于测试或API不可用时）
        
        Args:
            series_name: 剧集名称
            
        Returns:
            Dict[str, Any]: 模拟的剧集信息结果
        """
        try:
            # 生成模拟的剧集信息
            mock_result = {
                "success": True,
                "msg": "success",
                "code": 0,
                "data": {
                    "title": series_name,
                    "year": "2023",
                    "genre": "剧情",
                    "director": "示例导演",
                    "cast": "示例演员",
                    "rating": "8.5"
                },
                "tv_episode_plot": f"""
第1集：故事开始，主要角色登场，建立基本情境和人物关系。

第2集：冲突初现，主要矛盾开始显现，角色面临挑战。

第3集：情节发展，角色关系发生变化，故事走向转折点。

第4集：高潮来临，主要冲突达到顶点，角色做出重要决定。

第5集：故事收尾，解决主要矛盾，角色得到成长和启示。

第6集：新的开始，为后续剧情埋下伏笔，角色面临新的挑战。

第7集：深入发展，角色关系进一步复杂化，新的冲突出现。

第8集：转折点，故事方向发生重大改变，角色命运改变。

第9集：接近高潮，所有线索汇聚，为最终结局做准备。

第10集：大结局，所有矛盾得到解决，角色获得最终成长。
""",
                "tv_info": f"""
剧名：{series_name}
导演: 示例导演
编剧: 示例编剧
主演: 示例演员1 / 示例演员2 / 示例演员3
类型: 剧情 / 爱情
制片国家/地区: 中国大陆
语言: 汉语普通话
首播: 2023-01-01(中国大陆)
集数: 10
单集片长: 45分钟
又名: {series_name} (English)
豆瓣评分：8.5
"""
            }
            
            return mock_result
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成模拟剧集信息失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "msg": "模拟生成失败",
                "code": -1,
                "data": {},
                "tv_episode_plot": "",
                "tv_info": ""
            }
    
    def set_api_url(self, api_url: str):
        """设置API URL"""
        self.api_url = api_url
    
    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger
    
    def get_api_info(self) -> Dict[str, Any]:
        """获取API信息"""
        return {
            "api_url": self.api_url,
            "supported_formats": ["JSON"],
            "timeout": 30,
            "mock_data_available": True
        }

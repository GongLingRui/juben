"""
思维导图生成器
用于故事五元素分析系统的思维导图生成功能
"""
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional


class MindMapGenerator:
    """思维导图生成器"""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        初始化思维导图生成器
        
        Args:
            api_url: API接口URL，如果为None则使用默认的generateTreeMind接口
        """
        self.api_url = api_url or "https://api.example.com/generateTreeMind"  # 实际使用时需要替换为真实的API地址
        self.logger = None  # 可以后续注入logger
    
    async def generate_mind_map(self, query_text: str) -> Dict[str, Any]:
        """
        生成思维导图
        
        Args:
            query_text: 查询文本，用于生成思维导图
            
        Returns:
            Dict[str, Any]: 思维导图生成结果
        """
        try:
            # 限制输入文本长度
            if len(query_text) > 3000:
                query_text = query_text[:3000] + "..."
            
            # 构建请求数据
            request_data = {
                "query_text": query_text
            }
            
            # 调用API生成思维导图
            result = await self._call_mind_map_api(request_data)
            
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成思维导图失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": -1,
                "msg": f"生成失败: {str(e)}"
            }
    
    async def _call_mind_map_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用思维导图生成API
        
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
                            "status_code": result.get("status_code", 0),
                            "type_for_model": result.get("type_for_model", 2),
                            "code": result.get("code", 0),
                            "data": result.get("data", ""),
                            "data_struct": result.get("data_struct", {}),
                            "jump_link": result.get("data_struct", {}).get("jump_link", ""),
                            "pic": result.get("data_struct", {}).get("pic", ""),
                            "log_id": result.get("log_id", ""),
                            "msg": result.get("msg", "success")
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "code": response.status,
                            "msg": "API调用失败"
                        }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "API调用超时",
                "code": -1,
                "msg": "请求超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "code": -1,
                "msg": f"API调用异常: {str(e)}"
            }
    
    async def generate_mock_mind_map(self, query_text: str) -> Dict[str, Any]:
        """
        生成模拟思维导图（用于测试或API不可用时）
        
        Args:
            query_text: 查询文本
            
        Returns:
            Dict[str, Any]: 模拟的思维导图结果
        """
        try:
            # 生成模拟的思维导图数据
            mock_result = {
                "success": True,
                "status_code": 0,
                "type_for_model": 2,
                "code": 0,
                "data": f"![思维导图](https://example.com/mock_mind_map.png)\n\n[编辑思维导图](https://example.com/edit_mind_map)\n\n这是一个模拟的思维导图，用于演示目的。",
                "data_struct": {
                    "jump_link": "https://example.com/edit_mind_map",
                    "pic": "https://example.com/mock_mind_map.png"
                },
                "jump_link": "https://example.com/edit_mind_map",
                "pic": "https://example.com/mock_mind_map.png",
                "log_id": "mock_log_id_123456",
                "msg": "success"
            }
            
            return mock_result
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成模拟思维导图失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": -1,
                "msg": "模拟生成失败"
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
            "supported_formats": ["mind_map", "logic_diagram", "tree_diagram", "fishbone_diagram", "org_chart", "timeline"],
            "max_input_length": 3000,
            "timeout": 30
        }

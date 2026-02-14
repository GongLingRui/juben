"""
URL内容提取工具
用于提取网页、PDF、文档等URL内容
"""

import re
import requests
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from urllib.parse import urlparse


class URLExtractor:
    """URL内容提取器"""
    
    def __init__(self):
        self.session = None
        self.timeout = 30
    
    def extract_urls(self, text: str) -> List[str]:
        """从文本中提取URL"""
        if not text:
            return []
        
        # 匹配 URL（防止吃掉逗号、中文逗号、引号等分隔符）
        url_pattern = r'https?://[^\s,，\)\]\}\<\>\'"]+'
        
        # 提取全部 URL
        urls = re.findall(url_pattern, text)
        urls = [u.rstrip('.,，;；)）]\'"') for u in urls]
        
        return urls
    
    def clean_user_input(self, text: str) -> str:
        """清理用户输入，去除URL后返回纯文本"""
        if not text:
            return ""
        
        # 匹配 URL（防止吃掉逗号、中文逗号、引号等分隔符）
        url_pattern = r'https?://[^\s,，\)\]\}\<\>\'"]+'
        
        # 去除 URL 后剩下用户输入内容
        user_input = re.sub(url_pattern, '', text)
        user_input = re.sub(r'^[,，;；\s]+', '', user_input)
        user_input = re.sub(r'[,，;；\s]+$', '', user_input)
        user_input = re.sub(r'[,，;；\s]+', ' ', user_input).strip()
        
        return user_input
    
    async def extract_content(self, url: str) -> str:
        """提取URL内容"""
        try:
            # 初始化session
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            
            # 发送请求
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # 简单的HTML内容提取
                    extracted_text = self._extract_text_from_html(content)
                    return extracted_text
                else:
                    return f"无法访问URL: {url} (状态码: {response.status})"
                    
        except Exception as e:
            return f"URL内容提取失败: {str(e)}"
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """从HTML中提取文本内容"""
        try:
            # 简单的HTML标签清理
            import re
            
            # 移除script和style标签
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除HTML标签
            html_content = re.sub(r'<[^>]+>', '', html_content)
            
            # 清理多余的空白字符
            html_content = re.sub(r'\s+', ' ', html_content)
            html_content = html_content.strip()
            
            # 限制长度
            if len(html_content) > 5000:
                html_content = html_content[:5000] + "..."
            
            return html_content
            
        except Exception as e:
            return f"HTML内容提取失败: {str(e)}"
    
    async def extract_multiple_contents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """批量提取多个URL的内容"""
        if not urls:
            return []
        
        # 创建并发任务
        tasks = [self._extract_single_url(url) for url in urls]
        
        # 执行并发任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _extract_single_url(self, url: str) -> Dict[str, Any]:
        """提取单个URL的内容"""
        try:
            content = await self.extract_content(url)
            return {
                "url": url,
                "content": content,
                "success": True
            }
        except Exception as e:
            return {
                "url": url,
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    def is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def close(self):
        """关闭session"""
        if self.session:
            await self.session.close()
            self.session = None
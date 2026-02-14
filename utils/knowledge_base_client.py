"""
知识库客户端
基于阿里云embedding模型，提供zhishiku知识库的检索功能
"""
import os
import logging
import json
import numpy as np
import asyncio
import aiofiles
from collections import OrderedDict
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

# 导入阿里云embedding客户端
from .aliyun_embedding_client import aliyun_embedding_client


class KnowledgeBaseClient:
    """知识库客户端"""
    
    def __init__(self, milvus_client=None):
        """初始化知识库客户端"""
        self.logger = logger
        self.embedding_client = aliyun_embedding_client
        self.milvus_client = milvus_client

        # 嵌入缓存
        self._embedding_cache: OrderedDict[str, List[float]] = OrderedDict()
        self._embedding_cache_max = 1000
        
        # zhishiku知识库配置
        self.zhishiku_path = Path(__file__).parent.parent.parent / "logs" / "zhishiku"
        self.collections = {
            "script_segments": {
                "name": "剧本桥段库",
                "description": "包含各种经典剧本桥段和情节模板",
                "path": self.zhishiku_path,
                "files": []
            },
            "drama_highlights": {
                "name": "短剧高能情节库", 
                "description": "包含短剧中的高能情节和爆点设计",
                "path": self.zhishiku_path,
                "files": []
            }
        }
        
        # 初始化知识库文件索引
        self._init_knowledge_base()
        
        self.logger.info("知识库客户端初始化成功")
    
    def _init_knowledge_base(self):
        """初始化知识库文件索引"""
        try:
            if self.zhishiku_path.exists():
                # 扫描zhishiku目录下的所有txt文件
                txt_files = list(self.zhishiku_path.glob("*.txt"))
                self.logger.info(f"发现{len(txt_files)}个知识库文件")
                
                # 为每个集合分配文件
                for collection_name, collection_info in self.collections.items():
                    collection_info["files"] = txt_files
                    self.logger.info(f"集合 {collection_name} 包含 {len(txt_files)} 个文件")
            else:
                self.logger.warning(f"知识库目录不存在: {self.zhishiku_path}")
        except Exception as e:
            self.logger.error(f"初始化知识库失败: {e}")
    
    async def search(self, query: str, collection: str = "script_segments", top_k: int = 5) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            collection: 集合名称
            top_k: 返回结果数量
            
        Returns:
            Dict: 搜索结果
        """
        try:
            self.logger.info(f"开始知识库搜索: {query}, 集合: {collection}")
            
            # 获取查询向量（异步，带缓存）
            query_embedding = await self._get_embedding(query)
            if not query_embedding:
                self.logger.error("查询向量化失败")
                return {
                    "success": False,
                    "error": "查询向量化失败",
                    "query": query,
                    "results": []
                }
            
            # 优先使用Milvus
            if self.milvus_client:
                results = await self._search_milvus(query_embedding, collection, top_k)
            else:
                # 搜索相关文档
                results = await self._search_documents(query, query_embedding, collection, top_k)
            
            return {
                "success": True,
                "query": query,
                "collection": collection,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            self.logger.error(f"知识库搜索失败: {e}")
            return {
                "success": False,
                "error": f"知识库搜索失败: {str(e)}",
                "query": query,
                "results": []
            }
    
    async def _search_documents(self, query: str, query_embedding: List[float], collection: str, top_k: int) -> List[Dict[str, Any]]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            query_embedding: 查询向量
            collection: 集合名称
            top_k: 返回结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            collection_info = self.collections.get(collection)
            if not collection_info or not collection_info.get("files"):
                self.logger.warning(f"集合 {collection} 没有可用文件")
                return []
            
            results = []
            query_vec = np.array(query_embedding)
            
            # 遍历所有文件
            for file_path in collection_info["files"]:
                try:
                    # 异步读取文件内容
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                    
                    # 分段处理（每段1000字符）
                    chunks = self._split_text(content, chunk_size=1000)
                    
                    for i, chunk in enumerate(chunks):
                        if len(chunk.strip()) < 50:  # 跳过太短的段落
                            continue
                        
                        # 计算相似度（异步缓存）
                        chunk_embedding = await self._get_embedding(chunk)
                        if chunk_embedding:
                            chunk_vec = np.array(chunk_embedding)
                            similarity = self._cosine_similarity(query_vec, chunk_vec)
                            
                            if similarity > 0.3:  # 相似度阈值
                                results.append({
                                    "title": f"{file_path.stem} - 段落{i+1}",
                                    "content": chunk[:500] + "..." if len(chunk) > 500 else chunk,
                                    "similarity": float(similarity),
                                    "source": str(file_path),
                                    "chunk_index": i
                                })
                
                except Exception as e:
                    self.logger.error(f"处理文件 {file_path} 失败: {e}")
                    continue
            
            # 按相似度排序，返回top_k结果
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"文档搜索失败: {e}")
            return []

    async def _search_milvus(self, query_embedding: List[float], collection: str, top_k: int) -> List[Dict[str, Any]]:
        """使用Milvus进行向量检索（可选）"""
        try:
            if not hasattr(self.milvus_client, "search"):
                return []
            return await self.milvus_client.search(
                collection=collection,
                vector=query_embedding,
                top_k=top_k
            )
        except Exception as e:
            self.logger.error(f"Milvus搜索失败: {e}")
            return []

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取嵌入向量（带缓存）"""
        cache_key = str(hash(text))
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        try:
            embedding = await asyncio.to_thread(self.embedding_client.embed_text, text)
            if embedding:
                self._embedding_cache[cache_key] = embedding
                if len(self._embedding_cache) > self._embedding_cache_max:
                    self._embedding_cache.popitem(last=False)
            return embedding
        except Exception as e:
            self.logger.error(f"生成嵌入失败: {e}")
            return None
    
    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """将文本分割成块"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                # 尝试在句号处分割
                last_period = text.rfind('。', start, end)
                if last_period > start:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end
        
        return chunks
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except:
            return 0.0
    
    
    def get_collection_info(self, collection: str) -> Dict[str, Any]:
        """获取集合信息"""
        return self.collections.get(collection, {})
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return list(self.collections.keys())


# 创建全局实例
knowledge_base_client = KnowledgeBaseClient()

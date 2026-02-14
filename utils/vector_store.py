"""
Juben项目向量存储管理器
集成Milvus向量数据库，提供向量化存储和相似性搜索功能
"""
import os
import asyncio
from typing import Optional, List, Dict, Any, Union
from utils.logger import JubenLogger
from utils.milvus_client import get_milvus_client
from utils.knowledge_base_client import KnowledgeBaseClient


class VectorStore:
    """向量存储管理器"""
    
    def __init__(self):
        self.logger = JubenLogger("vector_store")
        self.milvus_client = None
        self.knowledge_client = KnowledgeBaseClient()
        
        # 默认集合配置
        self.default_collections = {
            "script_segments": {
                "name": "script_segments_collection",
                "description": "剧本桥段库",
                "dimension": 768,
                "metric_type": "COSINE",
                "top_k": 5,
                "score_threshold": 0.7
            },
            "drama_highlights": {
                "name": "drama_highlights_collection", 
                "description": "短剧高能情节库",
                "dimension": 768,
                "metric_type": "COSINE",
                "top_k": 5,
                "score_threshold": 0.7
            },
            "character_profiles": {
                "name": "character_profiles_collection",
                "description": "角色档案库",
                "dimension": 768,
                "metric_type": "COSINE",
                "top_k": 5,
                "score_threshold": 0.7
            },
            "plot_points": {
                "name": "plot_points_collection",
                "description": "情节要点库",
                "dimension": 768,
                "metric_type": "COSINE",
                "top_k": 5,
                "score_threshold": 0.7
            }
        }
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """初始化向量存储"""
        try:
            self.logger.info("🚀 开始初始化向量存储管理器...")
            
            # 初始化Milvus客户端
            self.milvus_client = await get_milvus_client()
            
            # 创建默认集合
            for collection_key, config in self.default_collections.items():
                await self.milvus_client.create_collection(
                    collection_name=config["name"],
                    dimension=config["dimension"],
                    metric_type=config["metric_type"],
                    description=config["description"]
                )
            
            self._initialized = True
            self.logger.info("✅ 向量存储管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 向量存储管理器初始化失败: {e}")
            return False
    
    def ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            raise Exception("向量存储管理器未初始化，请先调用initialize()方法")
    
    async def add_documents(
        self, 
        collection_name: str,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> bool:
        """添加文档到向量存储"""
        try:
            self.ensure_initialized()
            
            # 批量处理文档
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # 准备数据
                text_ids = []
                contents = []
                vectors = []
                metadata_list = []
                
                for doc in batch:
                    text_ids.append(doc.get("id", f"doc_{i}"))
                    contents.append(doc.get("content", ""))
                    metadata_list.append(doc.get("metadata", {}))
                    
                    # 获取向量
                    vector = await self._get_embedding(doc.get("content", ""))
                    if vector:
                        vectors.append(vector)
                    else:
                        self.logger.warning(f"文档 {doc.get('id')} 向量化失败")
                        continue
                
                # 插入到Milvus
                if vectors:
                    success = await self.milvus_client.insert_vectors(
                        collection_name=collection_name,
                        text_ids=text_ids,
                        contents=contents,
                        vectors=vectors,
                        metadata_list=metadata_list
                    )
                    
                    if success:
                        self.logger.info(f"✅ 批量插入 {len(vectors)} 个文档到集合 {collection_name}")
                    else:
                        self.logger.error(f"❌ 批量插入文档到集合 {collection_name} 失败")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 添加文档到向量存储失败: {e}")
            return False
    
    async def search_similar(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        metadata_filter: str = None
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            self.ensure_initialized()
            
            # 获取查询向量
            query_vector = await self._get_embedding(query)
            if not query_vector:
                self.logger.error("查询向量化失败")
                return []
            
            # 在Milvus中搜索
            results = await self.milvus_client.search_vectors(
                collection_name=collection_name,
                query_vectors=[query_vector],
                top_k=top_k,
                score_threshold=score_threshold,
                metadata_filter=metadata_filter
            )
            
            if results:
                return results[0]  # 返回第一个查询的结果
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"❌ 搜索相似文档失败: {e}")
            return []
    
    async def search_multiple_collections(
        self,
        collections: List[str],
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """在多个集合中搜索"""
        try:
            self.ensure_initialized()
            
            results = {}
            for collection_name in collections:
                collection_results = await self.search_similar(
                    collection_name=collection_name,
                    query=query,
                    top_k=top_k,
                    score_threshold=score_threshold
                )
                results[collection_name] = collection_results
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 多集合搜索失败: {e}")
            return {}
    
    async def get_collection_stats(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取集合统计信息"""
        try:
            self.ensure_initialized()
            return await self.milvus_client.get_collection_info(collection_name)
        except Exception as e:
            self.logger.error(f"❌ 获取集合统计信息失败: {e}")
            return None
    
    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            self.ensure_initialized()
            return await self.milvus_client.list_collections()
        except Exception as e:
            self.logger.error(f"❌ 列出集合失败: {e}")
            return []
    
    async def delete_documents(
        self, 
        collection_name: str, 
        text_ids: List[str]
    ) -> bool:
        """删除文档"""
        try:
            self.ensure_initialized()
            
            collection = await self.milvus_client.get_collection(collection_name)
            if not collection:
                return False
            
            # 构建删除表达式
            expr = f"text_id in {text_ids}"
            
            # 执行删除
            collection.delete(expr)
            collection.flush()
            
            self.logger.info(f"✅ 从集合 {collection_name} 删除 {len(text_ids)} 个文档")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 删除文档失败: {e}")
            return False
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示"""
        try:
            # 使用阿里云embedding服务
            embedding = await self.knowledge_client.get_embedding(text)
            if embedding:
                return embedding
            else:
                self.logger.warning("阿里云embedding服务失败，尝试本地embedding")
                # 这里可以添加本地embedding模型作为备用
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 获取文本向量失败: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self._initialized:
                return {"status": "not_initialized", "message": "向量存储管理器未初始化"}
            
            # 检查Milvus连接
            milvus_health = await self.milvus_client.health_check()
            
            # 检查知识库客户端
            knowledge_health = await self.knowledge_client.health_check()
            
            return {
                "status": "healthy" if milvus_health["status"] == "connected" else "unhealthy",
                "milvus": milvus_health,
                "knowledge_base": knowledge_health,
                "collections": await self.list_collections()
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def close(self):
        """关闭向量存储"""
        try:
            if self.milvus_client:
                await self.milvus_client.disconnect()
            self.logger.info("✅ 向量存储管理器已关闭")
        except Exception as e:
            self.logger.error(f"❌ 关闭向量存储管理器失败: {e}")


# 全局向量存储实例
vector_store = VectorStore()


async def get_vector_store() -> VectorStore:
    """获取向量存储实例"""
    global vector_store
    if not vector_store._initialized:
        await vector_store.initialize()
    return vector_store


async def test_vector_store() -> bool:
    """测试向量存储"""
    try:
        store = await get_vector_store()
        health = await store.health_check()
        return health["status"] == "healthy"
    except Exception as e:
        logger = JubenLogger("vector_store_test")
        logger.error(f"❌ 向量存储测试失败: {e}")
        return False

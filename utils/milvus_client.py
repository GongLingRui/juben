"""
Juben项目Milvus向量数据库客户端
支持向量存储、相似性搜索和集合管理
"""
import os
import asyncio
import time
from typing import Optional, List, Dict, Any, Union
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
    MilvusException
)
from utils.logger import JubenLogger
import numpy as np


class MilvusClient:
    """Milvus向量数据库客户端"""

    # 默认配置
    DEFAULT_TIMEOUT = 30
    DEFAULT_CONNECT_TIMEOUT = 10
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_HEALTH_CHECK_INTERVAL = 60  # 健康检查间隔（秒）

    def __init__(self):
        self.logger = JubenLogger("milvus_client")
        self.connection_alias = "default"
        self.collections: Dict[str, Collection] = {}

        # 连接配置
        self.host = os.getenv('MILVUS_HOST', 'localhost')
        self.port = os.getenv('MILVUS_PORT', '19530')
        self.user = os.getenv('MILVUS_USER', '')
        self.password = os.getenv('MILVUS_PASSWORD', '')

        # 连接状态
        self._connected = False
        self._last_health_check = 0
        self._connection_lock = asyncio.Lock()
        self._reconnecting = False
    
    async def connect(self) -> bool:
        """连接到Milvus服务器，支持重试"""
        async with self._connection_lock:
            # 如果已连接，先检查连接是否有效
            if self._connected:
                if await self._check_connection():
                    return True
                # 连接失效，标记为未连接
                self._connected = False

            # 尝试连接
            for attempt in range(self.DEFAULT_RETRY_ATTEMPTS):
                try:
                    # 构建连接参数
                    connection_params = {
                        'host': self.host,
                        'port': self.port,
                        'timeout': self.DEFAULT_CONNECT_TIMEOUT
                    }

                    if self.user and self.password:
                        connection_params.update({
                            'user': self.user,
                            'password': self.password
                        })

                    # 建立连接
                    connections.connect(
                        alias=self.connection_alias,
                        **connection_params
                    )

                    # 测试连接
                    if utility.get_server_version():
                        self._connected = True
                        self._last_health_check = time.time()
                        self.logger.info(f"✅ Milvus连接成功: {self.host}:{self.port}")
                        return True
                    else:
                        self.logger.error(f"❌ Milvus连接失败（尝试 {attempt + 1}/{self.DEFAULT_RETRY_ATTEMPTS}）：无法获取服务器版本")

                except Exception as e:
                    self.logger.warning(f"⚠️ Milvus连接失败（尝试 {attempt + 1}/{self.DEFAULT_RETRY_ATTEMPTS}）: {e}")

                    # 最后一次尝试失败，不再等待
                    if attempt < self.DEFAULT_RETRY_ATTEMPTS - 1:
                        # 指数退避
                        delay = self.DEFAULT_RETRY_DELAY * (2 ** attempt)
                        await asyncio.sleep(delay)

            self.logger.error(f"❌ Milvus连接失败，已达到最大重试次数")
            return False

    async def _check_connection(self) -> bool:
        """检查当前连接是否有效"""
        try:
            if not self._connected:
                return False
            # 尝试获取服务器版本
            version = utility.get_server_version()
            return version is not None
        except Exception:
            return False

    async def ensure_connected_with_retry(self) -> bool:
        """确保已连接，如果断开会尝试重连"""
        if not self._connected or not await self._check_connection():
            self.logger.warning("⚠️ Milvus连接断开，尝试重连...")
            return await self.connect()
        return True
    
    async def disconnect(self):
        """断开Milvus连接"""
        try:
            if self._connected:
                connections.disconnect(alias=self.connection_alias)
                self._connected = False
                self.logger.info("✅ Milvus连接已断开")
        except Exception as e:
            self.logger.error(f"❌ 断开Milvus连接失败: {e}")
    
    def ensure_connected(self):
        """确保已连接到Milvus（同步方法，用于向后兼容）"""
        if not self._connected:
            raise Exception("Milvus未连接，请先调用connect()方法")

    async def ensure_connected_async(self):
        """确保已连接到Milvus（异步方法，支持自动重连）"""
        if not self._connected or not await self._check_connection():
            success = await self.connect()
            if not success:
                raise Exception("无法连接到Milvus服务器")
        return True
    
    async def create_collection(
        self, 
        collection_name: str, 
        dimension: int = 768,
        metric_type: str = "COSINE",
        description: str = ""
    ) -> bool:
        """创建集合"""
        try:
            self.ensure_connected()
            
            # 检查集合是否已存在
            if utility.has_collection(collection_name):
                self.logger.info(f"集合 {collection_name} 已存在")
                return True
            
            # 定义字段
            fields = [
                FieldSchema(
                    name="id", 
                    dtype=DataType.INT64, 
                    is_primary=True, 
                    auto_id=True
                ),
                FieldSchema(
                    name="text_id", 
                    dtype=DataType.VARCHAR, 
                    max_length=512
                ),
                FieldSchema(
                    name="content", 
                    dtype=DataType.VARCHAR, 
                    max_length=65535
                ),
                FieldSchema(
                    name="metadata", 
                    dtype=DataType.JSON
                ),
                FieldSchema(
                    name="vector", 
                    dtype=DataType.FLOAT_VECTOR, 
                    dim=dimension
                )
            ]
            
            # 创建集合模式
            schema = CollectionSchema(
                fields=fields,
                description=description or f"Collection for {collection_name}"
            )
            
            # 创建集合
            collection = Collection(
                name=collection_name,
                schema=schema,
                using='default',
                shards_num=2
            )
            
            # 创建索引
            index_params = {
                "metric_type": metric_type,
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            
            collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            
            self.logger.info(f"✅ 集合 {collection_name} 创建成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 创建集合 {collection_name} 失败: {e}")
            return False
    
    async def get_collection(self, collection_name: str) -> Optional[Collection]:
        """获取集合对象，支持自动重连"""
        try:
            # 确保已连接
            await self.ensure_connected_async()

            if collection_name in self.collections:
                return self.collections[collection_name]

            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                self.collections[collection_name] = collection
                return collection
            else:
                self.logger.warning(f"集合 {collection_name} 不存在")
                return None

        except Exception as e:
            self.logger.error(f"❌ 获取集合 {collection_name} 失败: {e}")
            return None

    async def insert_vectors(
        self,
        collection_name: str,
        text_ids: List[str],
        contents: List[str],
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]] = None
    ) -> bool:
        """插入向量数据，支持重试"""
        for attempt in range(self.DEFAULT_RETRY_ATTEMPTS):
            try:
                # 确保已连接
                await self.ensure_connected_async()

                collection = await self.get_collection(collection_name)
                if not collection:
                    return False

                # 准备数据
                if metadata_list is None:
                    metadata_list = [{}] * len(vectors)

                # 确保所有列表长度一致
                min_length = min(len(text_ids), len(contents), len(vectors), len(metadata_list))
                text_ids = text_ids[:min_length]
                contents = contents[:min_length]
                vectors = vectors[:min_length]
                metadata_list = metadata_list[:min_length]

                # 插入数据
                data = [
                    text_ids,
                    contents,
                    metadata_list,
                    vectors
                ]

                collection.insert(data)
                collection.flush()

                self.logger.info(f"✅ 向集合 {collection_name} 插入 {len(vectors)} 条向量数据")
                return True

            except Exception as e:
                self.logger.warning(f"⚠️ 插入向量数据到集合 {collection_name} 失败（尝试 {attempt + 1}/{self.DEFAULT_RETRY_ATTEMPTS}）: {e}")

                if attempt < self.DEFAULT_RETRY_ATTEMPTS - 1:
                    # 尝试重新连接
                    await self.ensure_connected_async()
                    # 指数退避
                    delay = self.DEFAULT_RETRY_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"❌ 插入向量数据到集合 {collection_name} 失败，已达到最大重试次数")
                    return False

        return False

    async def search_vectors(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        top_k: int = 5,
        score_threshold: float = 0.0,
        metadata_filter: str = None
    ) -> List[List[Dict[str, Any]]]:
        """搜索相似向量，支持重试"""
        for attempt in range(self.DEFAULT_RETRY_ATTEMPTS):
            try:
                # 确保已连接
                await self.ensure_connected_async()

                collection = await self.get_collection(collection_name)
                if not collection:
                    return []

                # 加载集合到内存
                collection.load()

                # 构建搜索参数
                search_params = {
                    "metric_type": "COSINE",
                    "params": {"nprobe": 10}
                }

                # 执行搜索
                results = collection.search(
                    data=query_vectors,
                    anns_field="vector",
                    param=search_params,
                    limit=top_k,
                    expr=metadata_filter,
                    output_fields=["text_id", "content", "metadata"]
                )

                # 格式化结果
                formatted_results = []
                for result in results:
                    hits = []
                    for hit in result:
                        if hit.score >= score_threshold:
                            hits.append({
                                "id": hit.id,
                                "text_id": hit.entity.get("text_id"),
                                "content": hit.entity.get("content"),
                                "metadata": hit.entity.get("metadata"),
                                "score": hit.score
                            })
                    formatted_results.append(hits)

                self.logger.info(f"✅ 在集合 {collection_name} 中搜索到 {sum(len(hits) for hits in formatted_results)} 条结果")
                return formatted_results

            except Exception as e:
                self.logger.warning(f"⚠️ 在集合 {collection_name} 中搜索向量失败（尝试 {attempt + 1}/{self.DEFAULT_RETRY_ATTEMPTS}）: {e}")

                if attempt < self.DEFAULT_RETRY_ATTEMPTS - 1:
                    # 尝试重新连接
                    await self.ensure_connected_async()
                    # 指数退避
                    delay = self.DEFAULT_RETRY_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"❌ 在集合 {collection_name} 中搜索向量失败，已达到最大重试次数")
                    return []

        return []
    
    async def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        try:
            self.ensure_connected()
            
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                if collection_name in self.collections:
                    del self.collections[collection_name]
                self.logger.info(f"✅ 集合 {collection_name} 删除成功")
                return True
            else:
                self.logger.warning(f"集合 {collection_name} 不存在")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 删除集合 {collection_name} 失败: {e}")
            return False

    async def delete_by_expr(self, collection_name: str, expr: str) -> bool:
        """按条件删除向量数据"""
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return False
            collection.delete(expr)
            collection.flush()
            self.logger.info(f"✅ 从集合 {collection_name} 删除数据，条件: {expr}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 删除向量数据失败: {e}")
            return False
    
    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取集合信息"""
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            # 获取集合统计信息
            stats = collection.get_stats()
            
            return {
                "name": collection_name,
                "description": collection.description,
                "num_entities": stats.get("row_count", 0),
                "schema": {
                    "fields": [field.to_dict() for field in collection.schema.fields]
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取集合 {collection_name} 信息失败: {e}")
            return None
    
    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            self.ensure_connected()
            collections = utility.list_collections()
            return collections
        except Exception as e:
            self.logger.error(f"❌ 列出集合失败: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self._connected:
                return {"status": "disconnected", "message": "未连接到Milvus"}
            
            # 获取服务器版本
            version = utility.get_server_version()
            
            return {
                "status": "connected",
                "version": version,
                "host": self.host,
                "port": self.port,
                "collections_count": len(await self.list_collections())
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}


# 全局Milvus客户端实例
milvus_client = MilvusClient()


async def get_milvus_client() -> MilvusClient:
    """获取Milvus客户端实例"""
    if not milvus_client._connected:
        await milvus_client.connect()
    return milvus_client


async def test_milvus_connection() -> bool:
    """测试Milvus连接"""
    try:
        client = await get_milvus_client()
        health = await client.health_check()
        return health["status"] == "connected"
    except Exception as e:
        logger = JubenLogger("milvus_test")
        logger.error(f"❌ Milvus连接测试失败: {e}")
        return False

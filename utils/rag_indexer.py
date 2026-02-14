"""
RAG 索引器
负责将项目文件切分、向量化并写入 Milvus

功能增强：
- 智能分块（语义感知、结构感知）
- 混合检索（向量+BM25）
- LLM重排序
"""
import json
import re
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import JubenLogger
from utils.aliyun_embedding_client import aliyun_embedding_client
from utils.milvus_client import get_milvus_client


class ChunkingStrategy(Enum):
    """分块策略"""
    FIXED = "fixed"           # 固定大小分块
    SEMANTIC = "semantic"     # 语义感知分块
    STRUCTURAL = "structural" # 结构感知分块
    ADAPTIVE = "adaptive"     # 自适应分块


@dataclass
class ChunkInfo:
    """分块信息"""
    content: str
    chunk_index: int
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """搜索结果"""
    doc_id: str
    content: str
    score: float
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rerank_score: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RagIndexer:
    """项目文件索引器"""

    COLLECTION_NAME = "file_fragments"
    CHUNK_SIZE = 800
    OVERLAP = 120

    # 语义分块参数
    MIN_CHUNK_SIZE = 200
    MAX_CHUNK_SIZE = 1500
    SENTENCE_ENDINGS = ['。', '！', '？', '.', '!', '?']
    PARAGRAPH_SEPARATOR = '\n\n'

    def __init__(self, chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC):
        self.logger = JubenLogger("rag_indexer")
        self.embedding_client = aliyun_embedding_client
        self.chunking_strategy = chunking_strategy
        self._bm25_index = None  # BM25索引缓存

    async def _ensure_collection(self) -> bool:
        client = await get_milvus_client()
        return await client.create_collection(
            collection_name=self.COLLECTION_NAME,
            dimension=self.embedding_client.dimension,
            metric_type="COSINE",
            description="Project file fragments for RAG"
        )

    def _chunk_text(self, text: str) -> List[str]:
        """
        智能分块 - 根据策略选择分块方法
        """
        if not text:
            return []

        if self.chunking_strategy == ChunkingStrategy.FIXED:
            return self._fixed_chunking(text)
        elif self.chunking_strategy == ChunkingStrategy.SEMANTIC:
            return self._semantic_chunking(text)
        elif self.chunking_strategy == ChunkingStrategy.STRUCTURAL:
            return self._structural_chunking(text)
        else:  # ADAPTIVE
            return self._adaptive_chunking(text)

    def _fixed_chunking(self, text: str) -> List[str]:
        """固定大小分块（原有方法）"""
        chunks = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + self.CHUNK_SIZE, length)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.OVERLAP
            if start < 0:
                start = 0
        return chunks

    def _semantic_chunking(self, text: str) -> List[str]:
        """
        语义感知分块 - 在句子边界处分块
        """
        chunks = []
        paragraphs = text.split(self.PARAGRAPH_SEPARATOR)
        current_chunk = ""
        current_start = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            sentences = self._split_sentences(para)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                test_chunk = current_chunk + ("\n\n" if current_chunk else "") + sentence
                test_size = len(test_chunk)

                if test_size <= self.MAX_CHUNK_SIZE:
                    current_chunk = test_chunk
                else:
                    # 当前块已满，保存并开始新块
                    if current_chunk:
                        chunks.append(current_chunk)

                    # 如果单句超过最大块大小，强制分割
                    if len(sentence) > self.MAX_CHUNK_SIZE:
                        sub_chunks = self._split_long_sentence(sentence)
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1] if sub_chunks else ""
                    else:
                        current_chunk = sentence

        # 添加最后一块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        sentences = []
        current = ""
        i = 0

        while i < len(text):
            char = text[i]
            current += char

            # 检查是否是句子结束符
            if char in self.SENTENCE_ENDINGS:
                # 检查是否是引用（如"..."）
                if i > 0 and text[i-1] == '.' and char == '.':
                    i += 1
                    continue
                sentences.append(current)
                current = ""

            i += 1

        if current:
            sentences.append(current)

        return sentences

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """分割过长的句子"""
        chunks = []
        pos = 0
        while pos < len(sentence):
            end = min(pos + self.CHUNK_SIZE, len(sentence))
            # 尝试在逗号或空格处分割
            if end < len(sentence):
                comma_pos = sentence.rfind(',', pos, end)
                space_pos = sentence.rfind(' ', pos, end)
                split_pos = max(comma_pos, space_pos)
                if split_pos > pos:
                    end = split_pos + 1
            chunks.append(sentence[pos:end].strip())
            pos = end
        return [c for c in chunks if c]

    def _structural_chunking(self, text: str) -> List[str]:
        """
        结构感知分块 - 检测Markdown、JSON等结构
        """
        # 检测是否是JSON
        if text.strip().startswith('{') or text.strip().startswith('['):
            return self._json_chunking(text)

        # 检测是否是Markdown
        if text.strip().startswith('#'):
            return self._markdown_chunking(text)

        # 默认使用语义分块
        return self._semantic_chunking(text)

    def _json_chunking(self, text: str) -> List[str]:
        """JSON结构分块"""
        try:
            data = json.loads(text)
            chunks = []

            if isinstance(data, dict):
                for key, value in data.items():
                    chunk = json.dumps({key: value}, ensure_ascii=False, indent=2)
                    if len(chunk) > self.MAX_CHUNK_SIZE:
                        # 继续分割
                        sub_chunks = self._semantic_chunking(chunk)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(chunk)
            elif isinstance(data, list):
                for item in data:
                    chunk = json.dumps(item, ensure_ascii=False, indent=2)
                    if len(chunk) > self.MAX_CHUNK_SIZE:
                        sub_chunks = self._semantic_chunking(chunk)
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(chunk)
            else:
                chunks.append(text)

            return chunks
        except:
            return self._semantic_chunking(text)

    def _markdown_chunking(self, text: str) -> List[str]:
        """Markdown结构分块"""
        chunks = []
        current_chunk = ""
        current_header = ""

        lines = text.split('\n')
        for line in lines:
            # 检测标题
            if line.strip().startswith('#'):
                # 保存前一块
                if current_chunk:
                    chunks.append(current_chunk)

                current_header = line.strip()
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'

            # 检查块大小
            if len(current_chunk) >= self.MAX_CHUNK_SIZE:
                chunks.append(current_chunk)
                current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _adaptive_chunking(self, text: str) -> List[str]:
        """
        自适应分块 - 根据内容特征自动选择策略
        """
        # 检测结构化内容
        if text.strip().startswith(('{', '[', '#')):
            return self._structural_chunking(text)

        # 检测段落结构
        if self.PARAGRAPH_SEPARATOR in text:
            para_count = len([p for p in text.split(self.PARAGRAPH_SEPARATOR) if p.strip()])
            if para_count > 3:
                return self._semantic_chunking(text)

        # 默认使用固定大小分块
        return self._fixed_chunking(text)

    async def delete_project_file_chunks(self, project_id: str, file_id: str) -> None:
        try:
            client = await get_milvus_client()
            expr = f'text_id like "{project_id}:{file_id}:%"'
            await client.delete_by_expr(self.COLLECTION_NAME, expr)
        except Exception as e:
            self.logger.warning(f"删除旧向量失败: {e}")

    async def index_project_file(
        self,
        project_id: str,
        file_id: str,
        filename: str,
        content: Any,
        file_type: Optional[str] = None,
        agent_source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        reindex: bool = True
    ) -> None:
        try:
            if content is None:
                return

            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, indent=2)

            if not content.strip():
                return

            if reindex:
                await self.delete_project_file_chunks(project_id, file_id)

            await self._ensure_collection()

            chunks = self._chunk_text(content)
            if not chunks:
                return

            vectors = self.embedding_client.embed_texts(chunks)
            if not vectors or len(vectors) != len(chunks):
                self.logger.warning("向量化失败或数量不匹配")
                return

            text_ids = [f"{project_id}:{file_id}:{idx}" for idx in range(len(chunks))]
            metadata_list: List[Dict[str, Any]] = []
            for idx in range(len(chunks)):
                metadata_list.append({
                    "project_id": project_id,
                    "file_id": file_id,
                    "filename": filename,
                    "file_type": file_type,
                    "agent_source": agent_source,
                    "tags": tags or [],
                    "chunk_index": idx
                })

            client = await get_milvus_client()
            await client.insert_vectors(
                collection_name=self.COLLECTION_NAME,
                text_ids=text_ids,
                contents=chunks,
                vectors=vectors,
                metadata_list=metadata_list
            )
        except Exception as e:
            self.logger.error(f"索引项目文件失败: {e}")

    # ==================== 增强检索功能 ====================

    async def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
        use_rerank: bool = False,
        llm_client=None
    ) -> List[SearchResult]:
        """
        增强检索 - 向量搜索（支持可选的LLM重排序）

        Args:
            query: 查询文本
            project_id: 项目ID过滤
            top_k: 返回结果数量
            score_threshold: 分数阈值
            use_rerank: 是否使用LLM重排序
            llm_client: LLM客户端（用于重排序）

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        try:
            client = await get_milvus_client()
            if not client:
                self.logger.warning("Milvus客户端不可用")
                return []

            query_vector = self.embedding_client.embed_text(query)
            if not query_vector:
                self.logger.warning("查询向量化失败")
                return []

            # 构建过滤条件
            metadata_filter = None
            if project_id:
                metadata_filter = f'project_id == "{project_id}"'

            results = await client.search_vectors(
                collection_name=self.COLLECTION_NAME,
                query_vectors=[query_vector],
                top_k=top_k * 2,  # 获取更多结果用于重排序
                score_threshold=score_threshold,
                metadata_filter=metadata_filter
            )

            if not results or not results[0]:
                return []

            # 转换为SearchResult
            search_results = []
            for hit in results[0][:top_k]:
                search_results.append(SearchResult(
                    doc_id=hit.get("text_id", ""),
                    content=hit.get("content", ""),
                    score=hit.get("score", 0.0),
                    vector_score=hit.get("score", 0.0),
                    metadata=hit.get("metadata", {})
                ))

            # LLM重排序
            if use_rerank and llm_client:
                search_results = await self._rerank_results(
                    query, search_results, llm_client
                )

            return search_results

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        project_id: Optional[str] = None,
        top_k: int = 5,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        use_rerank: bool = False,
        llm_client=None
    ) -> List[SearchResult]:
        """
        混合搜索 - 向量搜索 + BM25搜索

        Args:
            query: 查询文本
            project_id: 项目ID过滤
            top_k: 返回结果数量
            vector_weight: 向量搜索权重
            bm25_weight: BM25搜索权重
            use_rerank: 是否使用LLM重排序
            llm_client: LLM客户端

        Returns:
            List[SearchResult]: 混合搜索结果
        """
        try:
            # 执行向量搜索
            vector_results = await self.search(
                query=query,
                project_id=project_id,
                top_k=top_k * 2,
                score_threshold=0.0,
                use_rerank=False
            )

            # 获取BM25索引
            if not self._bm25_index:
                await self._build_bm25_index(project_id)

            if not self._bm25_index:
                # BM25不可用，仅使用向量结果
                return vector_results[:top_k]

            # 执行BM25搜索
            bm25_results = self._bm25_index.search(query, top_k=top_k * 2)

            # 合并结果
            combined_results = self._combine_search_results(
                vector_results,
                bm25_results,
                vector_weight,
                bm25_weight
            )

            # 排序并返回top_k
            combined_results.sort(key=lambda r: r.score, reverse=True)
            results = combined_results[:top_k]

            # LLM重排序
            if use_rerank and llm_client:
                results = await self._rerank_results(query, results, llm_client)

            return results

        except Exception as e:
            self.logger.error(f"混合搜索失败: {e}")
            return []

    async def _build_bm25_index(self, project_id: Optional[str] = None) -> None:
        """构建BM25索引"""
        try:
            from utils.bm25_retriever import BM25Retriever

            # 获取所有文档
            client = await get_milvus_client()
            if not client:
                return

            # 这里简化处理，实际应该从数据库或缓存中获取文档
            self._bm25_index = BM25Retriever()

        except Exception as e:
            self.logger.warning(f"构建BM25索引失败: {e}")

    def _combine_search_results(
        self,
        vector_results: List[SearchResult],
        bm25_results: List[Any],
        vector_weight: float,
        bm25_weight: float
    ) -> List[SearchResult]:
        """合并向量搜索和BM25搜索结果"""
        # 归一化分数
        vec_scores = {r.doc_id: r.vector_score for r in vector_results}
        bm25_scores = {r.doc_id: r.score for r in bm25_results}

        max_vec = max(vec_scores.values()) if vec_scores else 1.0
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0

        combined = {}

        # 处理向量结果
        for vr in vector_results:
            vec_norm = vr.vector_score / max_vec if max_vec > 0 else 0
            bm25_norm = bm25_scores.get(vr.doc_id, 0) / max_bm25 if max_bm25 > 0 else 0

            combined_score = vec_norm * vector_weight + bm25_norm * bm25_weight

            combined[vr.doc_id] = SearchResult(
                doc_id=vr.doc_id,
                content=vr.content,
                score=combined_score,
                vector_score=vr.vector_score,
                bm25_score=bm25_scores.get(vr.doc_id, 0),
                metadata=vr.metadata
            )

        # 处理仅BM25命中的结果
        for br in bm25_results:
            if br.doc_id not in combined:
                bm25_norm = br.score / max_bm25 if max_bm25 > 0 else 0
                combined_score = bm25_norm * bm25_weight

                combined[br.doc_id] = SearchResult(
                    doc_id=br.doc_id,
                    content=br.content,
                    score=combined_score,
                    vector_score=0.0,
                    bm25_score=br.score,
                    metadata=br.metadata
                )

        return list(combined.values())

    async def _rerank_results(
        self,
        query: str,
        results: List[SearchResult],
        llm_client
    ) -> List[SearchResult]:
        """使用LLM重排序结果"""
        try:
            from utils.llm_reranker import LLMReranker, ScoringStrategy

            reranker = LLMReranker(llm_client, strategy=ScoringStrategy.COMPREHENSIVE)

            candidates = [
                {
                    "doc_id": r.doc_id,
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata
                }
                for r in results
            ]

            rerank_results = await reranker.rerank(query, candidates)

            # 更新分数
            for i, rr in enumerate(rerank_results):
                if i < len(results):
                    results[i].rerank_score = rr.rerank_score
                    results[i].score = rr.rerank_score

            # 按重排序分数排序
            results.sort(key=lambda r: r.rerank_score, reverse=True)

            return results

        except Exception as e:
            self.logger.warning(f"LLM重排序失败: {e}")
            return results


_rag_indexer: Optional[RagIndexer] = None


def get_rag_indexer(chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC) -> RagIndexer:
    global _rag_indexer
    if _rag_indexer is None:
        _rag_indexer = RagIndexer(chunking_strategy=chunking_strategy)
    return _rag_indexer

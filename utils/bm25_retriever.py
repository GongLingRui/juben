"""
BM25 文本检索模块
基于BM25算法的关键词匹配检索，补充向量检索的不足

BM25是一种概率检索函数，用于评估文档与查询的相关性
它基于词频和逆文档频率，但考虑了文档长度归一化

代码作者：宫灵瑞
创建时间：2026年2月7日

参考：
- BM25算法：https://en.wikipedia.org/wiki/Okapi_BM25
- 用于短剧剧本的关键词检索
"""
import math
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
import jieba


@dataclass
class BM25Document:
    """BM25文档"""
    doc_id: str                      # 文档ID
    content: str                     # 文档内容
    tokens: List[str]                # 分词结果
    metadata: Dict[str, Any]         # 元数据


@dataclass
class SearchResult:
    """搜索结果"""
    doc_id: str                      # 文档ID
    content: str                     # 文档内容
    score: float                     # BM25得分
    metadata: Dict[str, Any]         # 元数据


class BM25Retriever:
    """
    BM25检索器

    参数说明：
    - k1: 词频饱和参数（默认1.5，控制词频的影响）
    - b: 长度归一化参数（默认0.75，控制文档长度的影响）
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        use_jieba: bool = True,
        stop_words: Optional[List[str]] = None
    ):
        """
        初始化BM25检索器

        Args:
            k1: 词频饱和参数，通常在1.2-2.0之间
            b: 长度归一化参数，通常在0.5-0.8之间
            use_jieba: 是否使用jieba分词
            stop_words: 停用词列表
        """
        self.k1 = k1
        self.b = b
        self.use_jieba = use_jieba
        self.stop_words = set(stop_words or [])

        # 文档存储
        self.documents: List[BM25Document] = []

        # 统计信息
        self.doc_count: int = 0                    # 文档总数
        self.doc_lengths: List[int] = []           # 各文档长度
        self.avg_doc_length: float = 0.0           # 平均文档长度

        # 词频统计
        self.doc_freqs: Dict[str, int] = {}        # 词项文档频率
        self.term_freqs: List[Dict[str, int]] = [] # 各文档的词频

        # 默认停用词
        self._init_default_stop_words()

    def _init_default_stop_words(self):
        """初始化默认停用词"""
        default_stops = [
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "里",
            "我们", "你们", "他们", "她们", "它们", "这个", "那个",
            "啊", "吗", "呢", "吧", "哦", "呀", "哈", "嘿", "嗯"
        ]
        self.stop_words.update(default_stops)

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        添加文档到索引

        Args:
            documents: 文档列表，每个文档应包含 doc_id 和 content
        """
        for doc in documents:
            doc_id = doc.get("doc_id", str(len(self.documents)))
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            # 分词
            tokens = self._tokenize(content)

            # 创建文档对象
            bm25_doc = BM25Document(
                doc_id=doc_id,
                content=content,
                tokens=tokens,
                metadata=metadata
            )
            self.documents.append(bm25_doc)

            # 更新统计
            self.doc_lengths.append(len(tokens))
            self._update_term_stats(tokens)

        # 更新统计信息
        self.doc_count = len(self.documents)
        self.avg_doc_length = sum(self.doc_lengths) / self.doc_count if self.doc_count > 0 else 0

    def _tokenize(self, text: str) -> List[str]:
        """
        对文本进行分词

        Args:
            text: 输入文本

        Returns:
            List[str]: 分词结果
        """
        # 预处理：移除特殊字符，保留中文、英文、数字
        text = re.sub(r'[^\u4e00-\u9fff\w]', ' ', text)

        # 分词
        if self.use_jieba:
            tokens = list(jieba.cut(text))
        else:
            tokens = text.split()

        # 过滤停用词和短词
        tokens = [
            t.lower() for t in tokens
            if t.strip() and len(t) > 1 and t not in self.stop_words
        ]

        return tokens

    def _update_term_stats(self, tokens: List[str]) -> None:
        """更新词项统计"""
        # 当前文档的词频
        term_freq = Counter(tokens)
        self.term_freqs.append(dict(term_freq))

        # 更新文档频率
        for term in term_freq.keys():
            self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        使用BM25算法搜索文档

        Args:
            query: 查询文本
            top_k: 返回前k个结果
            min_score: 最小得分阈值

        Returns:
            List[SearchResult]: 搜索结果列表，按得分降序排列
        """
        if not self.documents:
            return []

        # 对查询进行分词
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # 计算每个文档的BM25得分
        scores = []
        for doc_idx, doc in enumerate(self.documents):
            score = self._calculate_bm25_score(query_tokens, doc_idx)
            if score >= min_score:
                scores.append((doc_idx, score))

        # 按得分降序排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 构建结果
        results = []
        for doc_idx, score in scores[:top_k]:
            doc = self.documents[doc_idx]
            results.append(SearchResult(
                doc_id=doc.doc_id,
                content=doc.content,
                score=score,
                metadata=doc.metadata
            ))

        return results

    def _calculate_bm25_score(self, query_tokens: List[str], doc_idx: int) -> float:
        """
        计算BM25得分

        BM25公式：
        score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D| / avgdl))

        其中：
        - qi: 查询中的词项
        - f(qi,D): 词项qi在文档D中的词频
        - |D|: 文档D的长度（词数）
        - avgdl: 平均文档长度
        - k1, b: 调节参数
        - IDF(qi): 词项qi的逆文档频率

        Args:
            query_tokens: 查询分词结果
            doc_idx: 文档索引

        Returns:
            float: BM25得分
        """
        score = 0.0
        doc_len = self.doc_lengths[doc_idx]
        doc_term_freqs = self.term_freqs[doc_idx]

        for term in query_tokens:
            # 词项在文档中的频率
            f_qi_D = doc_term_freqs.get(term, 0)

            if f_qi_D == 0:
                continue

            # 逆文档频率
            # IDF(qi) = log((N - df(qi) + 0.5) / (df(qi) + 0.5))
            # 使用平滑版本避免负值
            N = self.doc_count
            df_qi = self.doc_freqs.get(term, 0)

            if df_qi == 0:
                continue

            idf_qi = math.log((N - df_qi + 0.5) / (df_qi + 0.5) + 1)

            # BM25分子分母
            numerator = f_qi_D * (self.k1 + 1)
            denominator = f_qi_D + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)

            score += idf_qi * (numerator / denominator)

        return score

    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> Dict[str, List[SearchResult]]:
        """
        批量搜索

        Args:
            queries: 查询列表
            top_k: 每个查询返回的结果数量

        Returns:
            Dict[str, List[SearchResult]]: 查询到结果的映射
        """
        results = {}
        for query in queries:
            results[query] = self.search(query, top_k)
        return results

    def get_document_by_id(self, doc_id: str) -> Optional[BM25Document]:
        """根据ID获取文档"""
        for doc in self.documents:
            if doc.doc_id == doc_id:
                return doc
        return None

    def clear(self) -> None:
        """清空索引"""
        self.documents = []
        self.doc_count = 0
        self.doc_lengths = []
        self.avg_doc_length = 0.0
        self.doc_freqs = {}
        self.term_freqs = []

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            "doc_count": self.doc_count,
            "avg_doc_length": self.avg_doc_length,
            "vocab_size": len(self.doc_freqs),
            "total_terms": sum(self.doc_lengths),
            "parameters": {
                "k1": self.k1,
                "b": self.b
            }
        }


class HybridSearchResult:
    """混合搜索结果（向量+BM25）"""

    def __init__(
        self,
        doc_id: str,
        content: str,
        vector_score: float,
        bm25_score: float,
        combined_score: float,
        metadata: Dict[str, Any]
    ):
        self.doc_id = doc_id
        self.content = content
        self.vector_score = vector_score
        self.bm25_score = bm25_score
        self.combined_score = combined_score
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "vector_score": self.vector_score,
            "bm25_score": self.bm25_score,
            "combined_score": self.combined_score,
            "metadata": self.metadata
        }


class HybridRetriever:
    """
    混合检索器

    结合向量检索和BM25检索，提供更全面的搜索能力
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4
    ):
        """
        初始化混合检索器

        Args:
            bm25_retriever: BM25检索器实例
            vector_weight: 向量检索权重
            bm25_weight: BM25检索权重
        """
        self.bm25_retriever = bm25_retriever
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    def hybrid_search(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[HybridSearchResult]:
        """
        执行混合搜索

        Args:
            query: 查询文本
            vector_results: 向量检索结果列表，每项包含 doc_id, score, content 等
            top_k: 返回结果数量

        Returns:
            List[HybridSearchResult]: 混合搜索结果
        """
        # 执行BM25检索
        bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)

        # 构建BM25得分映射
        bm25_scores = {r.doc_id: r.score for r in bm25_results}

        # 归一化得分
        max_vector = max([r.get("score", 0) for r in vector_results], default=1.0)
        max_bm25 = max(bm25_scores.values(), default=1.0)

        # 合并结果
        combined_scores = {}  # doc_id -> (vector_score, bm25_score, combined_score)

        # 处理向量结果
        for vr in vector_results:
            doc_id = vr.get("doc_id", "")
            vec_score = vr.get("score", 0) / max_vector if max_vector > 0 else 0
            bm25_score = bm25_scores.get(doc_id, 0) / max_bm25 if max_bm25 > 0 else 0

            combined = vec_score * self.vector_weight + bm25_score * self.bm25_weight
            combined_scores[doc_id] = (vec_score, bm25_score, combined, vr.get("content", ""))

        # 处理仅BM25命中的结果
        for doc_id, bm25_score in bm25_scores.items():
            if doc_id not in combined_scores:
                bm25_norm = bm25_score / max_bm25 if max_bm25 > 0 else 0
                combined = bm25_norm * self.bm25_weight

                doc = self.bm25_retriever.get_document_by_id(doc_id)
                content = doc.content if doc else ""

                combined_scores[doc_id] = (0, bm25_norm, combined, content)

        # 构建结果
        results = []
        for doc_id, (vec_s, bm25_s, combined, content) in combined_scores.items():
            results.append(HybridSearchResult(
                doc_id=doc_id,
                content=content,
                vector_score=vec_s,
                bm25_score=bm25_s,
                combined_score=combined,
                metadata={}
            ))

        # 按综合得分排序
        results.sort(key=lambda r: r.combined_score, reverse=True)

        return results[:top_k]


# 便捷函数
def create_bm25_index(
    documents: List[Dict[str, Any]],
    k1: float = 1.5,
    b: float = 0.75
) -> BM25Retriever:
    """
    创建BM25索引

    Args:
        documents: 文档列表
        k1: BM25参数k1
        b: BM25参数b

    Returns:
        BM25Retriever: BM25检索器实例
    """
    retriever = BM25Retriever(k1=k1, b=b)
    retriever.add_documents(documents)
    return retriever


def search_with_bm25(
    documents: List[Dict[str, Any]],
    query: str,
    top_k: int = 10,
    k1: float = 1.5,
    b: float = 0.75
) -> List[SearchResult]:
    """
    使用BM25搜索文档（便捷函数）

    Args:
        documents: 文档列表
        query: 查询文本
        top_k: 返回结果数量
        k1: BM25参数k1
        b: BM25参数b

    Returns:
        List[SearchResult]: 搜索结果
    """
    retriever = BM25Retriever(k1=k1, b=b)
    retriever.add_documents(documents)
    return retriever.search(query, top_k=top_k)

"""
LLM 重排序模块
使用大语言模型对检索结果进行二次排序，提升相关性

代码作者：宫灵瑞
创建时间：2026年2月7日

功能：
1. 基于LLM的相关性评分
2. 批量重排序
3. 多策略评分（语义匹配、信息丰富度、情感共鸣）
4. 性能优化（批量处理、缓存）
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from datetime import datetime, timedelta


class ScoringStrategy(Enum):
    """评分策略"""
    SEMANTIC = "semantic"           # 语义相似度
    COMPREHENSIVE = "comprehensive"  # 综合评分
    EMOTIONAL = "emotional"         # 情感共鸣度
    INFORMATIVENESS = "informativeness"  # 信息丰富度


@dataclass
class RerankResult:
    """重排序结果"""
    doc_id: str                     # 文档ID
    content: str                    # 文档内容
    original_score: float           # 原始得分
    rerank_score: float             # 重排序得分
    reasoning: str                  # 评分理由
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "reasoning": self.reasoning,
            "metadata": self.metadata
        }


@dataclass
class CacheEntry:
    """缓存条目"""
    query_doc_hash: str
    score: float
    reasoning: str
    timestamp: datetime


class LLMReranker:
    """
    LLM重排序器

    使用大语言模型对检索结果进行重新排序，提升相关性
    """

    def __init__(
        self,
        llm_client,
        strategy: ScoringStrategy = ScoringStrategy.COMPREHENSIVE,
        cache_ttl: int = 3600,
        max_batch_size: int = 5
    ):
        """
        初始化重排序器

        Args:
            llm_client: LLM客户端实例
            strategy: 评分策略
            cache_ttl: 缓存生存时间（秒）
            max_batch_size: 最大批处理大小
        """
        self.llm_client = llm_client
        self.strategy = strategy
        self.cache_ttl = cache_ttl
        self.max_batch_size = max_batch_size

        # 评分缓存
        self.score_cache: Dict[str, CacheEntry] = {}

        # 统计信息
        self.stats = {
            "total_reranks": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    async def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        preserve_original_order: bool = False
    ) -> List[RerankResult]:
        """
        对候选结果进行重排序

        Args:
            query: 查询文本
            candidates: 候选文档列表，每项包含 doc_id, content, score 等
            top_k: 返回前k个结果（None表示返回全部）
            preserve_original_order: 是否保持原始顺序（仅更新得分）

        Returns:
            List[RerankResult]: 重排序后的结果
        """
        if not candidates:
            return []

        self.stats["total_reranks"] += len(candidates)

        # 批量评分
        rerank_results = await self._batch_score(query, candidates)

        # 按重排序得分排序
        if not preserve_original_order:
            rerank_results.sort(key=lambda r: r.rerank_score, reverse=True)

        # 返回top_k
        if top_k is not None:
            rerank_results = rerank_results[:top_k]

        return rerank_results

    async def _batch_score(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[RerankResult]:
        """批量评分"""
        results = []

        # 分批处理
        for i in range(0, len(candidates), self.max_batch_size):
            batch = candidates[i:i + self.max_batch_size]
            batch_results = await self._score_batch(query, batch)
            results.extend(batch_results)

        # 清理过期缓存
        self._cleanup_cache()

        return results

    async def _score_batch(
        self,
        query: str,
        batch: List[Dict[str, Any]]
    ) -> List[RerankResult]:
        """对一批候选进行评分"""
        tasks = [
            self._score_single(query, candidate)
            for candidate in batch
        ]

        scores = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for candidate, score_result in zip(batch, scores):
            if isinstance(score_result, Exception):
                # 评分失败，使用原始得分
                results.append(RerankResult(
                    doc_id=candidate.get("doc_id", ""),
                    content=candidate.get("content", ""),
                    original_score=candidate.get("score", 0.0),
                    rerank_score=candidate.get("score", 0.0),
                    reasoning=f"评分失败: {str(score_result)}",
                    metadata=candidate.get("metadata", {})
                ))
            else:
                score, reasoning = score_result
                results.append(RerankResult(
                    doc_id=candidate.get("doc_id", ""),
                    content=candidate.get("content", ""),
                    original_score=candidate.get("score", 0.0),
                    rerank_score=score,
                    reasoning=reasoning,
                    metadata=candidate.get("metadata", {})
                ))

        return results

    async def _score_single(
        self,
        query: str,
        candidate: Dict[str, Any]
    ) -> tuple[float, str]:
        """对单个候选进行评分"""
        doc_id = candidate.get("doc_id", "")
        content = candidate.get("content", "")

        # 检查缓存
        cache_key = self._get_cache_key(query, content)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            self.stats["cache_hits"] += 1
            return cached.score, cached.reasoning

        self.stats["cache_misses"] += 1

        # 构建评分提示词
        prompt = self._build_scoring_prompt(query, content)

        try:
            # 调用LLM
            response = await self.llm_client.chat([{"role": "user", "content": prompt}])

            # 解析响应
            score, reasoning = self._parse_response(response)

            # 缓存结果
            self._add_to_cache(cache_key, score, reasoning)

            return score, reasoning

        except Exception as e:
            # 失败时返回中等分数
            return 0.5, f"评分失败: {str(e)}"

    def _build_scoring_prompt(self, query: str, content: str) -> str:
        """构建评分提示词"""
        # 截断过长内容
        max_content_length = 500
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        # 根据策略构建不同的提示词
        if self.strategy == ScoringStrategy.SEMANTIC:
            return self._semantic_prompt(query, content)
        elif self.strategy == ScoringStrategy.EMOTIONAL:
            return self._emotional_prompt(query, content)
        elif self.strategy == ScoringStrategy.INFORMATIVENESS:
            return self._informativeness_prompt(query, content)
        else:  # COMPREHENSIVE
            return self._comprehensive_prompt(query, content)

    def _semantic_prompt(self, query: str, content: str) -> str:
        """语义相似度评分提示词"""
        return f"""请评估以下文档与查询的语义相似度。

查询：{query}

文档内容：
{content}

请从以下几个方面评估：
1. 主题相关性：文档是否与查询讨论同一主题
2. 意图匹配：文档是否回答了查询的问题
3. 语义一致：文档内容是否与查询意图一致

请按以下格式回复：
分数：[0-1之间的数字]
理由：[简短说明评分理由]

示例：
分数：0.85
理由：文档详细回答了查询关于剧本创作的问题，主题高度相关。"""

    def _emotional_prompt(self, query: str, content: str) -> str:
        """情感共鸣度评分提示词"""
        return f"""请评估以下文档对用户查询的情感共鸣能力。

查询：{query}

文档内容：
{content}

请从以下几个方面评估：
1. 情感冲击：文档是否能引发强烈的情感反应
2. 情绪匹配：文档情绪是否与查询意图匹配
3. 共情能力：文档是否能与用户产生情感共鸣

请按以下格式回复：
分数：[0-1之间的数字]
理由：[简短说明评分理由]

示例：
分数：0.75
理由：文档描述了主角的困境，能引发同情和共鸣。"""

    def _informativeness_prompt(self, query: str, content: str) -> str:
        """信息丰富度评分提示词"""
        return f"""请评估以下文档的信息丰富度。

查询：{query}

文档内容：
{content}

请从以下几个方面评估：
1. 信息量：文档是否包含大量有用信息
2. 完整性：文档是否完整回答了查询
3. 价值性：文档信息是否对用户有价值

请按以下格式回复：
分数：[0-1之间的数字]
理由：[简短说明评分理由]

示例：
分数：0.90
理由：文档包含详细的剧本创作技巧和方法，信息丰富。"""

    def _comprehensive_prompt(self, query: str, content: str) -> str:
        """综合评分提示词"""
        return f"""请评估以下文档与查询的相关性（综合评分）。

查询：{query}

文档内容：
{content}

请从以下几个方面综合评估：
1. 语义相关性：文档是否与查询相关（权重40%）
2. 信息丰富度：文档是否提供有价值的信息（权重30%）
3. 情感共鸣度：文档是否能引发情感共鸣（权重20%）
4. 内容质量：文档内容是否清晰准确（权重10%）

请按以下格式回复：
分数：[0-1之间的数字，保留两位小数]
理由：[一句话说明评分理由]

示例：
分数：0.82
理由：文档与查询高度相关，内容丰富且情感充沛。"""

    def _parse_response(self, response: str) -> tuple[float, str]:
        """解析LLM响应"""
        try:
            # 提取分数
            score_match = None
            for pattern in ["分数[：:]\s*([0-9.]+)", "score[：:]\s*([0-9.]+)"]:
                import re
                match = re.search(pattern, response)
                if match:
                    score_match = match
                    break

            if score_match:
                score = float(score_match.group(1))
                # 限制在0-1范围
                score = max(0.0, min(1.0, score))
            else:
                # 无法提取分数，使用默认值
                score = 0.5

            # 提取理由
            reasoning_match = None
            for pattern in ["理由[：:]\s*(.+)", "reasoning[：:]\s*(.+)"]:
                import re
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    reasoning_match = match
                    break

            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                # 限制理由长度
                reasoning = reasoning[:200]
            else:
                reasoning = "无详细理由"

            return score, reasoning

        except Exception as e:
            # 解析失败
            return 0.5, f"解析失败: {str(e)}"

    def _get_cache_key(self, query: str, content: str) -> str:
        """生成缓存键"""
        combined = f"{query}|{content[:200]}"  # 只使用前200字符生成键
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[CacheEntry]:
        """从缓存获取"""
        entry = self.score_cache.get(cache_key)
        if entry:
            # 检查是否过期
            if datetime.now() - entry.timestamp < timedelta(seconds=self.cache_ttl):
                return entry
            else:
                # 过期，删除
                del self.score_cache[cache_key]
        return None

    def _add_to_cache(self, cache_key: str, score: float, reasoning: str) -> None:
        """添加到缓存"""
        self.score_cache[cache_key] = CacheEntry(
            query_doc_hash=cache_key,
            score=score,
            reasoning=reasoning,
            timestamp=datetime.now()
        )

    def _cleanup_cache(self) -> None:
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.score_cache.items()
            if now - entry.timestamp >= timedelta(seconds=self.cache_ttl)
        ]
        for key in expired_keys:
            del self.score_cache[key]

    def clear_cache(self) -> None:
        """清空缓存"""
        self.score_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_hit_rate = (
            self.stats["cache_hits"] / max(self.stats["total_reranks"], 1) * 100
            if self.stats["total_reranks"] > 0
            else 0
        )

        return {
            **self.stats,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "cache_size": len(self.score_cache)
        }


class MultiStrategyReranker:
    """
    多策略重排序器

    使用多种评分策略进行重排序，然后综合结果
    """

    def __init__(
        self,
        llm_client,
        strategies: List[ScoringStrategy] = None,
        weights: Dict[ScoringStrategy, float] = None
    ):
        """
        初始化多策略重排序器

        Args:
            llm_client: LLM客户端
            strategies: 使用的策略列表
            weights: 各策略的权重
        """
        self.llm_client = llm_client

        # 默认使用所有策略
        if strategies is None:
            strategies = [
                ScoringStrategy.SEMANTIC,
                ScoringStrategy.EMOTIONAL,
                ScoringStrategy.INFORMATIVENESS
            ]
        self.strategies = strategies

        # 默认权重
        if weights is None:
            weights = {
                ScoringStrategy.SEMANTIC: 0.5,
                ScoringStrategy.EMOTIONAL: 0.3,
                ScoringStrategy.INFORMATIVENESS: 0.2
            }
        self.weights = weights

        # 创建各策略的重排序器
        self.rerankers = {
            strategy: LLMReranker(llm_client, strategy=strategy)
            for strategy in strategies
        }

    async def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[RerankResult]:
        """
        使用多策略进行重排序

        Args:
            query: 查询文本
            candidates: 候选文档列表
            top_k: 返回前k个结果

        Returns:
            List[RerankResult]: 重排序后的结果
        """
        if not candidates:
            return []

        # 并行执行各策略的评分
        strategy_tasks = [
            self._rerank_with_strategy(query, candidates, strategy)
            for strategy in self.strategies
        ]

        strategy_results = await asyncio.gather(*strategy_tasks)

        # 合并各策略的得分
        combined_results = self._combine_strategy_scores(
            candidates,
            strategy_results,
            self.strategies
        )

        # 按综合得分排序
        combined_results.sort(key=lambda r: r.rerank_score, reverse=True)

        # 返回top_k
        if top_k is not None:
            combined_results = combined_results[:top_k]

        return combined_results

    async def _rerank_with_strategy(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        strategy: ScoringStrategy
    ) -> List[RerankResult]:
        """使用指定策略进行重排序"""
        reranker = self.rerankers[strategy]
        return await reranker.rerank(query, candidates, preserve_original_order=True)

    def _combine_strategy_scores(
        self,
        candidates: List[Dict[str, Any]],
        strategy_results: List[List[RerankResult]],
        strategies: List[ScoringStrategy]
    ) -> List[RerankResult]:
        """合并各策略的得分"""
        # 创建doc_id到结果的映射
        doc_results = {c.get("doc_id", ""): c for c in candidates}

        combined = []

        for candidate in candidates:
            doc_id = candidate.get("doc_id", "")
            content = candidate.get("content", "")
            original_score = candidate.get("score", 0.0)

            # 收集各策略的得分
            strategy_scores = {}
            strategy_reasonings = []

            for strategy, results in zip(strategies, strategy_results):
                for result in results:
                    if result.doc_id == doc_id:
                        strategy_scores[strategy] = result.rerank_score
                        strategy_reasonings.append(f"{strategy.value}:{result.rerank_score:.2f}")
                        break

            # 计算加权得分
            combined_score = 0.0
            total_weight = 0.0

            for strategy, weight in self.weights.items():
                if strategy in strategy_scores:
                    combined_score += strategy_scores[strategy] * weight
                    total_weight += weight

            # 归一化
            if total_weight > 0:
                combined_score /= total_weight

            combined.append(RerankResult(
                doc_id=doc_id,
                content=content,
                original_score=original_score,
                rerank_score=combined_score,
                reasoning=f"综合评分: {', '.join(strategy_reasonings)}",
                metadata={"strategy_scores": strategy_scores}
            ))

        return combined


# 便捷函数
async def rerank_results(
    llm_client,
    query: str,
    candidates: List[Dict[str, Any]],
    strategy: ScoringStrategy = ScoringStrategy.COMPREHENSIVE,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    使用LLM重排序结果（便捷函数）

    Args:
        llm_client: LLM客户端
        query: 查询文本
        candidates: 候选文档列表
        strategy: 评分策略
        top_k: 返回结果数量

    Returns:
        List[Dict]: 重排序后的结果
    """
    reranker = LLMReranker(llm_client, strategy=strategy)
    results = await reranker.rerank(query, candidates, top_k=top_k)
    return [r.to_dict() for r in results]

"""
批处理器
用于故事五元素分析系统的批处理功能
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime


class BatchProcessor:
    """批处理器"""

    def __init__(self, parallel_limit: int = 10, max_iterations: int = 100):
        """
        初始化批处理器（增强版：带参数验证）

        Args:
            parallel_limit: 并行处理限制
            max_iterations: 最大迭代次数
        """
        # ========== 参数验证 ==========
        if parallel_limit <= 0:
            parallel_limit = 10
        if max_iterations <= 0:
            max_iterations = 100

        self.parallel_limit = parallel_limit
        self.max_iterations = max_iterations
        self.logger = None  # 可以后续注入logger
    
    async def process_batch(
        self, 
        items: List[Any], 
        processor_func: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        批处理项目列表
        
        Args:
            items: 要处理的项目列表
            processor_func: 处理函数
            *args: 处理函数的额外参数
            **kwargs: 处理函数的关键字参数
            
        Returns:
            List[Any]: 处理结果列表
        """
        try:
            if not items:
                return []
            
            # 创建信号量限制并发
            semaphore = asyncio.Semaphore(self.parallel_limit)
            
            async def process_item(item):
                async with semaphore:
                    try:
                        if asyncio.iscoroutinefunction(processor_func):
                            return await processor_func(item, *args, **kwargs)
                        else:
                            return processor_func(item, *args, **kwargs)
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"处理项目失败: {e}")
                        return None
            
            # 并发处理所有项目
            results = await asyncio.gather(
                *[process_item(item) for item in items],
                return_exceptions=True
            )
            
            # 过滤掉异常结果
            valid_results = [result for result in results if not isinstance(result, Exception)]
            
            return valid_results
        except Exception as e:
            if self.logger:
                self.logger.error(f"批处理失败: {e}")
            return []
    
    async def process_with_retry(
        self,
        items: List[Any],
        processor_func: Callable,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        带重试机制的批处理（增强版：带参数验证）

        Args:
            items: 要处理的项目列表
            processor_func: 处理函数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            *args: 处理函数的额外参数
            **kwargs: 处理函数的关键字参数

        Returns:
            List[Any]: 处理结果列表
        """
        try:
            # ========== 参数验证 ==========
            if not items or not isinstance(items, list):
                return []

            if max_retries < 0:
                max_retries = 3

            if retry_delay < 0:
                retry_delay = 1.0

            results = []
            failed_items = items.copy()

            for attempt in range(max_retries + 1):
                if not failed_items:
                    break

                if attempt > 0:
                    if self.logger:
                        self.logger.info(f"重试第 {attempt} 次，剩余 {len(failed_items)} 个项目")
                    await asyncio.sleep(retry_delay)

                # 处理失败的项目
                batch_results = await self.process_batch(
                    failed_items, processor_func, *args, **kwargs
                )

                # 分离成功和失败的结果
                new_results = []
                still_failed = []

                for i, result in enumerate(batch_results):
                    if result is not None:
                        new_results.append(result)
                    else:
                        still_failed.append(failed_items[i])

                results.extend(new_results)
                failed_items = still_failed

            if failed_items and self.logger:
                self.logger.warning(f"批处理完成，仍有 {len(failed_items)} 个项目处理失败")

            return results
        except Exception as e:
            if self.logger:
                self.logger.error(f"带重试的批处理失败: {e}")
            return []
    
    async def process_iteratively(
        self,
        items: List[Any],
        processor_func: Callable,
        batch_size: Optional[int] = None,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        迭代式批处理，分批处理大量数据（增强版：带参数验证）

        Args:
            items: 要处理的项目列表
            processor_func: 处理函数
            batch_size: 批处理大小，如果为None则使用parallel_limit
            *args: 处理函数的额外参数
            **kwargs: 处理函数的关键字参数

        Returns:
            List[Any]: 处理结果列表
        """
        try:
            # ========== 参数验证 ==========
            if not items or not isinstance(items, list):
                return []

            if batch_size is None:
                batch_size = self.parallel_limit
            elif batch_size <= 0:
                self.logger.warning(f"batch_size参数不合法({batch_size})，使用parallel_limit")
                batch_size = self.parallel_limit

            all_results = []

            # 分批处理
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]

                if self.logger:
                    self.logger.info(f"处理批次 {i//batch_size + 1}/{(len(items)-1)//batch_size + 1}")

                batch_results = await self.process_batch(
                    batch, processor_func, *args, **kwargs
                )

                all_results.extend(batch_results)

            return all_results
        except Exception as e:
            if self.logger:
                self.logger.error(f"迭代式批处理失败: {e}")
            return []
    
    def set_parallel_limit(self, limit: int):
        """设置并行限制"""
        self.parallel_limit = limit
    
    def set_max_iterations(self, max_iter: int):
        """设置最大迭代次数"""
        self.max_iterations = max_iter
    
    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger

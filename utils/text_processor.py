"""
文本处理工具
基于coze工作流中的文本处理功能，提供文本截断和分割功能
"""
import asyncio
from typing import List, Optional, Any
from datetime import datetime


class TextTruncator:
    """
    文本截断工具
    
    核心功能：
    1. 文本截断处理
    2. 支持多种截断策略
    3. 保持文本完整性
    """
    
    def __init__(self):
        """初始化文本截断工具"""
        self.default_max_length = 50000
    
    async def truncate_text(
        self,
        text: str,
        max_length: Optional[int] = None
    ) -> str:
        """
        截断文本（增强版：带参数验证）

        Args:
            text: 输入文本
            max_length: 最大长度

        Returns:
            str: 截断后的文本
        """
        # ========== 参数验证 ==========
        if not text or not isinstance(text, str):
            return ""

        if max_length is None:
            max_length = self.default_max_length

        if max_length <= 0:
            max_length = self.default_max_length

        if len(text) <= max_length:
            return text

        # 截断文本，保持完整性
        truncated = text[:max_length]

        # 尝试在句号、问号、感叹号处截断
        for i in range(len(truncated) - 1, -1, -1):
            if truncated[i] in '。！？':
                return truncated[:i + 1]

        # 如果没有找到合适的截断点，直接截断
        return truncated
    
    async def truncate_text_smart(
        self, 
        text: str, 
        max_length: Optional[int] = None
    ) -> str:
        """
        智能截断文本，保持段落完整性
        
        Args:
            text: 输入文本
            max_length: 最大长度
            
        Returns:
            str: 截断后的文本
        """
        if max_length is None:
            max_length = self.default_max_length
        
        if len(text) <= max_length:
            return text
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        result = []
        current_length = 0
        
        for paragraph in paragraphs:
            if current_length + len(paragraph) + 2 <= max_length:
                result.append(paragraph)
                current_length += len(paragraph) + 2
            else:
                break
        
        return '\n\n'.join(result)


class TextSplitter:
    """
    文本分割工具
    
    核心功能：
    1. 按指定长度分割文本
    2. 保持文本完整性
    3. 支持重叠分割
    """
    
    def __init__(self):
        """初始化文本分割工具"""
        self.default_chunk_size = 10000
        self.default_overlap = 200
    
    async def split_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[str]:
        """
        分割文本（增强版：带参数验证）

        Args:
            text: 输入文本
            chunk_size: 每段大小
            overlap: 重叠长度

        Returns:
            List[str]: 分割后的文本列表
        """
        # ========== 参数验证 ==========
        if not text or not isinstance(text, str):
            return []

        if chunk_size is None:
            chunk_size = self.default_chunk_size

        if overlap is None:
            overlap = self.default_overlap

        if chunk_size <= 0:
            chunk_size = self.default_chunk_size

        if overlap < 0:
            overlap = 0

        if overlap >= chunk_size:
            overlap = chunk_size - 1

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        # 防止无限循环的安全机制
        max_iterations = (len(text) // max(1, chunk_size - overlap)) + 100
        iteration = 0

        while start < len(text):
            iteration += 1
            if iteration > max_iterations:
                # 安全机制：防止无限循环
                break

            end = start + chunk_size

            if end >= len(text):
                chunks.append(text[start:])
                break

            # 尝试在句号、问号、感叹号处分割
            split_point = end
            for i in range(end - 1, start + chunk_size // 2, -1):
                if text[i] in '。！？':
                    split_point = i + 1
                    break

            chunks.append(text[start:split_point])
            start = split_point - overlap

            if start < 0:
                start = split_point

        return chunks
    
    async def split_text_by_paragraphs(
        self, 
        text: str, 
        max_chunk_size: Optional[int] = None
    ) -> List[str]:
        """
        按段落分割文本
        
        Args:
            text: 输入文本
            max_chunk_size: 最大段落大小
            
        Returns:
            List[str]: 分割后的文本列表
        """
        if max_chunk_size is None:
            max_chunk_size = self.default_chunk_size
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            if current_length + len(paragraph) + 2 <= max_chunk_size:
                current_chunk.append(paragraph)
                current_length += len(paragraph) + 2
            else:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = len(paragraph)
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    async def split_text_smart(
        self, 
        text: str, 
        chunk_size: Optional[int] = None
    ) -> List[str]:
        """
        智能分割文本，保持语义完整性
        
        Args:
            text: 输入文本
            chunk_size: 每段大小
            
        Returns:
            List[str]: 分割后的文本列表
        """
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        
        if len(text) <= chunk_size:
            return [text]
        
        # 首先尝试按段落分割
        paragraph_chunks = await self.split_text_by_paragraphs(text, chunk_size)
        
        # 如果段落分割结果合适，直接返回
        if all(len(chunk) <= chunk_size for chunk in paragraph_chunks):
            return paragraph_chunks
        
        # 否则按固定长度分割
        return await self.split_text(text, chunk_size)


class BatchProcessor:
    """
    批处理器
    
    核心功能：
    1. 批处理管理
    2. 并行处理控制
    3. 错误处理
    """
    
    def __init__(self):
        """初始化批处理器"""
        self.parallel_limit = 10
        self.max_iterations = 100
        self.retry_count = 3
    
    def configure(
        self, 
        parallel_limit: Optional[int] = None,
        max_iterations: Optional[int] = None,
        retry_count: Optional[int] = None
    ):
        """
        配置批处理器
        
        Args:
            parallel_limit: 并行处理数量
            max_iterations: 最大迭代次数
            retry_count: 重试次数
        """
        if parallel_limit is not None:
            self.parallel_limit = parallel_limit
        if max_iterations is not None:
            self.max_iterations = max_iterations
        if retry_count is not None:
            self.retry_count = retry_count
    
    async def process_batch(
        self, 
        inputs: List[str], 
        processor_func,
        **kwargs
    ) -> List[Any]:
        """
        批处理处理
        
        Args:
            inputs: 输入列表
            processor_func: 处理函数
            **kwargs: 其他参数
            
        Returns:
            List[Any]: 处理结果列表
        """
        results = []
        semaphore = asyncio.Semaphore(self.parallel_limit)
        
        async def process_single(input_item, index):
            async with semaphore:
                for attempt in range(self.retry_count):
                    try:
                        result = await processor_func(input_item, index, **kwargs)
                        return result
                    except Exception as e:
                        if attempt == self.retry_count - 1:
                            return {"error": str(e), "index": index}
                        await asyncio.sleep(1)  # 重试前等待
        
        # 创建任务
        tasks = [process_single(input_item, i) for i, input_item in enumerate(inputs)]
        
        # 执行批处理
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def process_batch_with_progress(
        self, 
        inputs: List[str], 
        processor_func,
        progress_callback=None,
        **kwargs
    ) -> List[Any]:
        """
        带进度的批处理
        
        Args:
            inputs: 输入列表
            processor_func: 处理函数
            progress_callback: 进度回调函数
            **kwargs: 其他参数
            
        Returns:
            List[Any]: 处理结果列表
        """
        results = []
        semaphore = asyncio.Semaphore(self.parallel_limit)
        completed = 0
        total = len(inputs)
        
        async def process_single(input_item, index):
            nonlocal completed
            async with semaphore:
                for attempt in range(self.retry_count):
                    try:
                        result = await processor_func(input_item, index, **kwargs)
                        completed += 1
                        if progress_callback:
                            await progress_callback(completed, total, result)
                        return result
                    except Exception as e:
                        if attempt == self.retry_count - 1:
                            completed += 1
                            if progress_callback:
                                await progress_callback(completed, total, {"error": str(e)})
                            return {"error": str(e), "index": index}
                        await asyncio.sleep(1)
        
        # 创建任务
        tasks = [process_single(input_item, i) for i, input_item in enumerate(inputs)]
        
        # 执行批处理
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
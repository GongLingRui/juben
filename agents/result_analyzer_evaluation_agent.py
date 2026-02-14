"""
结果分析评估智能体
基于agent as tool机制，实现智能体间的模块化外包和上下文隔离
"""
import asyncio
import json
import re
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from .base_juben_agent import BaseJubenAgent


class ResultAnalyzerEvaluationAgent(BaseJubenAgent):
    """
    结果分析评估智能体
    
    功能：
    1. 分析多次评估结果
    2. 提取评分信息并进行统计分析
    3. 生成评级和建议
    4. 汇总评估报告
    """
    
    def __init__(self):
        super().__init__("result_analyzer_evaluation_agent")
        self.logger.info("📊 结果分析评估智能体初始化完成")
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理结果分析请求
        
        Args:
            request_data: 包含评估结果的请求数据
            context: 上下文信息
            
        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 提取请求参数
            evaluation_results = request_data.get("output", [])
            evaluation_type = request_data.get("type", "ip")  # ip 或 script
            
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)
            
            # 发送开始分析事件
            yield await self._emit_event("system_message", "📊 开始分析评估结果...")
            
            # 分析评估结果
            analysis_result = await self._analyze_evaluation_results(
                evaluation_results, evaluation_type
            )
            
            # 发送分析结果
            yield await self._emit_event("llm_chunk", analysis_result)
            
            # 发送完成事件
            yield await self._emit_event("system_message", "✅ 结果分析完成")
            
            # 保存分析结果
            await self.save_chat_message(
                user_id, session_id, "result_analysis", 
                analysis_result, {"type": evaluation_type, "agent": self.agent_name}
            )
            
        except Exception as e:
            self.logger.error(f"❌ 结果分析失败: {e}")
            yield await self._emit_event("error", f"结果分析失败: {str(e)}")
    
    async def _analyze_evaluation_results(
        self, 
        evaluation_results: List[str], 
        evaluation_type: str
    ) -> str:
        """
        分析评估结果
        
        Args:
            evaluation_results: 评估结果列表
            evaluation_type: 评估类型 (ip 或 script)
            
        Returns:
            str: 分析结果
        """
        try:
            if not evaluation_results:
                return "没有正确拿到输入数据"
            
            outputs_dicts = []
            scores = []
            loop_num = len(evaluation_results)
            
            # 提取每次评估的评分
            for output in evaluation_results:
                # 尝试匹配总评分
                pattern = r"总评分\D*(\d+(\.\d+)?)"
                match = re.search(pattern, output)
                
                if match:
                    score = float(match.group(1))
                else:
                    # 尝试匹配总体评价评分
                    pattern = r"总体评价\D*(\d+(\.\d+)?)"
                    match = re.search(pattern, output)
                    if match:
                        score = float(match.group(1))
                    else:
                        # 未匹配到分数
                        score = "-"
                        loop_num -= 1
                
                scores.append(score)
                outputs_dict = {
                    "score": score,
                    "text": output
                }
                outputs_dicts.append(outputs_dict)
            
            # 统计有效评分
            num_scores = [item for item in scores if isinstance(item, float)]
            if not num_scores:
                return "没有抓到任何评分"
            
            # 计算统计数据
            high_scores = [s for s in num_scores if s >= 8.0]
            very_high_scores = [s for s in num_scores if s >= 8.5]
            
            # 确定关注等级
            attention_level = self._determine_attention_level(
                len(num_scores), len(high_scores), len(very_high_scores)
            )
            
            # 计算统计指标
            min_score = min(num_scores)
            max_score = max(num_scores)
            first_score = num_scores[0]
            avg = round((sum(num_scores) / loop_num), 2)
            avg_without_top_and_left = round(
                ((sum(num_scores) - min_score - max_score) / (loop_num - 2)) if loop_num > 2 else 0, 2
            )
            
            # 生成分析报告
            summary = self._generate_analysis_summary(
                attention_level, loop_num, avg_without_top_and_left, avg,
                first_score, scores, max_score, min_score, evaluation_type
            )
            
            # 添加每次执行结果
            for i, v in enumerate(outputs_dicts):
                output = v["text"]
                summary += f"\n## 第{i + 1}次执行结果: \n{output}\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ 分析评估结果失败: {e}")
            return f"分析评估结果失败: {str(e)}"
    
    def _determine_attention_level(
        self, 
        total_scores: int, 
        high_scores: int, 
        very_high_scores: int
    ) -> str:
        """
        确定关注等级
        
        Args:
            total_scores: 总评分次数
            high_scores: 高分次数 (>=8.0)
            very_high_scores: 极高分次数 (>=8.5)
            
        Returns:
            str: 关注等级
        """
        if not total_scores == 10:
            return '运行失败'
        elif very_high_scores > 0:
            return "S 强烈关注"
        elif high_scores >= 8:
            return "S 强烈关注"
        elif high_scores >= 5:
            return "A 建议关注"
        else:
            return "B 普通"
    
    def _generate_analysis_summary(
        self,
        attention_level: str,
        loop_num: int,
        avg_without_top_and_left: float,
        avg: float,
        first_score: float,
        scores: List,
        max_score: float,
        min_score: float,
        evaluation_type: str
    ) -> str:
        """
        生成分析摘要
        
        Args:
            attention_level: 关注等级
            loop_num: 循环次数
            avg_without_top_and_left: 去除最高最低分的平均分
            avg: 平均分
            first_score: 首次评分
            scores: 所有评分
            max_score: 最高分
            min_score: 最低分
            evaluation_type: 评估类型
            
        Returns:
            str: 分析摘要
        """
        content_type = "IP" if evaluation_type == "ip" else "剧本"
        
        summary = f"""
# AI评级: {attention_level}
# 结果 
- 评估次数: {loop_num} 次. 评估结果: {avg_without_top_and_left if avg_without_top_and_left else avg}
    - 首次评分 {first_score}
    - 复评分数依次为 {'、'.join([str(x) for x in scores[1:]]) if len(scores) > 1 else '-'}
    - 最高分 {max_score}
    - 最低分 {min_score}
    - 平均分 {avg}
# 评估参考
- 以评估十次为基准：
    - 当出现不及五次8.0及以上评分时，表示该{content_type} "普通"，对应评级为B。 
    - 当出现至少五次8.0及以上评分时，表示该{content_type}可 "建议关注"，对应评级为A。 
    - 当出现至少八次8.0及以上评分时，表示该{content_type}可 "强烈关注"，对应评级为S。
    - 当出现至少一次8.5及以上评分时，无论其他评分如何，均表示该{content_type}可 "强烈关注"，对应评级为S。
"""
        return summary

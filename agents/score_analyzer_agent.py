from typing import AsyncGenerator, Dict, Any, Optional, List

"""
评分分析工具智能体 - 支持Agent as Tool机制

业务处理逻辑：
1. 输入处理：接收多轮评估结果和评分数据
2. 统计分析：对多轮评分进行统计分析，计算平均值、标准差等
3. 评级计算：基于评分标准进行评级逻辑计算（A/B/C/D等级）
4. 趋势分析：分析评分趋势和变化规律
5. 异常检测：识别评分异常和异常值
6. 报告生成：生成综合的评分分析报告
7. 建议输出：基于分析结果提供评级建议
8. 输出格式化：返回结构化的评分分析数据
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
from datetime import datetime
try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.base_juben_agent import BaseJubenAgent

class ScoreAnalyzerAgent(BaseJubenAgent):
    """
    评分分析工具智能体
    
    核心功能：
    1. 多轮评分统计分析
    2. 评级逻辑计算
    3. 评分趋势分析
    4. 综合评估报告生成
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        """初始化评分分析工具智能体"""
        super().__init__("score_analyzer", model_provider)
        
        # 系统提示词配置
        self.logger.info("评分分析工具智能体初始化完成")
    
    # 系统提示词由基类自动加载，无需重写
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理请求 - 支持Agent as Tool机制

        Args:
            request_data: 请求数据
            context: 上下文信息
                - user_id: 用户ID
                - session_id: 会话ID
                - parent_agent: 父智能体名称（Agent as Tool模式）
                - tool_call: 是否为工具调用

        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            input_text = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            parent_agent = context.get("parent_agent", "") if context else ""
            tool_call = context.get("tool_call", False) if context else False

            if tool_call:
                self.logger.info(f"🔧 Agent as Tool模式，父智能体: {parent_agent}")

            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始事件
            yield {
                "event_type": "tool_start",
                "data": {
                    "tool_name": "score_analyzer",
                    "timestamp": datetime.now().isoformat()
                }
            }

            # 解析输入参数
            evaluation_results = request_data.get("evaluation_results", [])
            
            if not evaluation_results:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": "评估结果为空",
                        "message": "请提供有效的评估结果"
                    }
                }
                return
            
            # 发送处理开始事件
            yield {
                "event_type": "tool_processing",
                "data": {
                    "message": "正在进行评分分析...",
                    "total_rounds": len(evaluation_results)
                }
            }
            
            # 执行评分分析
            analysis_result = await self._analyze_scores(evaluation_results)
            
            # 发送最终结果
            yield {
                "event_type": "tool_complete",
                "data": {
                    "tool_name": "score_analyzer",
                    "result": analysis_result,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理评分分析请求时发生错误: {str(e)}")
            yield {
                "event_type": "error",
                "data": {
                    "error": str(e),
                    "message": "评分分析过程中发生错误"
                }
            }
    
    async def _analyze_scores(self, evaluation_results: List[str]) -> Dict[str, Any]:
        """
        分析评分结果
        
        Args:
            evaluation_results: 评估结果列表
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            scores = []
            outputs_dicts = []
            loop_num = len(evaluation_results)
            
            # 提取各轮评分
            for i, output in enumerate(evaluation_results):
                # 尝试提取总评分
                pattern = r"总评分\D*(\d+(\.\d+)?)"
                match = re.search(pattern, output)
                if match:
                    score = float(match.group(1))
                else:
                    # 尝试其他评分模式
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
            
            # 过滤有效评分
            num_scores = [item for item in scores if isinstance(item, float)]
            if not num_scores:
                return {
                    "error": "没有抓到任何评分",
                    "scores": [],
                    "analysis": "评分分析失败"
                }
            
            # 统计分析
            high_scores = [s for s in num_scores if s >= 8.0]
            very_high_scores = [s for s in num_scores if s >= 8.5]
            
            # 确定评级
            if not len(num_scores) == 10:
                attention_level = '运行失败'
            elif len(very_high_scores) > 0:
                attention_level = "S 强烈关注"
            elif len(high_scores) >= 8:
                attention_level = "S 强烈关注"
            elif len(high_scores) >= 5:
                attention_level = "A 建议关注"
            else:
                attention_level = "B 普通"
            
            # 计算统计指标
            min_score = min(num_scores)
            max_score = max(num_scores)
            first_score = num_scores[0]
            avg = round((sum(num_scores) / len(num_scores)), 2)
            
            # 计算去除最高最低分的平均分
            if len(num_scores) > 2:
                scores_sorted = sorted(num_scores)
                avg_without_top_and_bottom = round(
                    (sum(scores_sorted[1:-1]) / (len(scores_sorted) - 2)), 2)
            else:
                avg_without_top_and_bottom = avg
            
            # 生成分析报告
            summary = f"""
# AI评级: {attention_level}
# 结果 
- 评估次数: {loop_num} 次. 评估结果: {avg_without_top_and_bottom if avg_without_top_and_bottom else avg}
    - 首次评分 {first_score}
    - 复评分数依次为 {'、'.join([str(x) for x in scores[1:]]) if len(scores) > 1 else '-'}
    - 最高分 {max_score}
    - 最低分 {min_score}
    - 平均分 {avg}
# 评估参考
- 以评估十次为基准：
    - 当出现不及五次8.0及以上评分时，表示该大纲 "普通"，对应评级为B。 
    - 当出现至少五次8.0及以上评分时，表示该大纲可 "建议关注"，对应评级为A。 
    - 当出现至少八次8.0及以上评分时，表示该大纲可 "强烈关注"，对应评级为S。
    - 当出现至少一次8.5及以上评分时，无论其他评分如何，均表示该大纲可 "强烈关注"，对应评级为S。
"""
            
            # 添加详细评估结果
            for i, v in enumerate(outputs_dicts):
                output = v["text"]
                summary += f"\n## 第{i + 1}次执行结果: \n{output}\n"
            
            analysis_result = {
                "attention_level": attention_level,
                "total_rounds": loop_num,
                "scores": scores,
                "statistics": {
                    "min_score": min_score,
                    "max_score": max_score,
                    "avg_score": avg,
                    "avg_without_extremes": avg_without_top_and_bottom,
                    "first_score": first_score,
                    "high_scores_count": len(high_scores),
                    "very_high_scores_count": len(very_high_scores)
                },
                "evaluation_summary": summary,
                "detailed_results": outputs_dicts
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"评分分析失败: {str(e)}")
            return {
                "error": str(e),
                "scores": [],
                "analysis": "评分分析失败"
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "tool_name": "score_analyzer",
            "description": "评分分析工具智能体",
            "function": "对多轮评估结果进行统计分析，生成评级建议",
            "input_parameters": {
                "evaluation_results": "list - 多轮评估结果列表"
            },
            "output": {
                "attention_level": "str - 评级等级",
                "total_rounds": "int - 评估轮次",
                "scores": "list - 评分列表",
                "statistics": "dict - 统计指标",
                "evaluation_summary": "str - 评估总结",
                "detailed_results": "list - 详细结果"
            },
            "rating_levels": {
                "S": "强烈关注 - 出现至少一次8.5分或至少八次8.0分",
                "A": "建议关注 - 出现至少五次8.0分",
                "B": "普通 - 不及五次8.0分"
            },
            "statistics_metrics": [
                "min_score - 最低分",
                "max_score - 最高分", 
                "avg_score - 平均分",
                "avg_without_extremes - 去除极值平均分",
                "first_score - 首次评分",
                "high_scores_count - 高分次数",
                "very_high_scores_count - 极高分次数"
            ]
        }
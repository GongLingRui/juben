from typing import AsyncGenerator, Dict, Any, Optional, List
import asyncio
import random
import re
import time

"""
故事大纲评估与分析智能体 - 基于Agent as Tool机制
实现coze工作流的故事大纲评估功能

业务处理逻辑：
1. 输入处理：接收故事大纲文本，支持长文本截断和分割处理
2. 多轮评估：循环10次对故事大纲进行深度评估分析
3. 评分机制：对故事结构、人物塑造、情节发展、语言表达等维度评分
4. 评级逻辑：根据评分统计结果进行A/B/C/D等级评定
5. 子智能体调用：使用Agent as Tool机制调用专业评估子智能体
6. 上下文隔离：确保每次评估的独立性和准确性
7. 结果统计：汇总多轮评估结果，生成统计报告
8. 文档生成：生成完整的评估报告和可视化结果
9. 输出格式化：返回结构化的评估数据和评级结果

代码作者：宫灵瑞
创建时间：2024年10月19日
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


class StoryOutlineEvaluationAgent(BaseJubenAgent):
    """
    故事大纲评估与分析智能体
    
    核心功能：
    1. 文本截断和分割处理
    2. 多轮故事大纲评估（循环10次）
    3. 评分统计和评级逻辑
    4. 文档生成和结果输出
    5. Agent as Tool机制：调用子智能体作为工具
    6. 模块化外包：智能体间相互调用，上下文隔离
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        """初始化故事大纲评估智能体"""
        super().__init__("story_outline_evaluation", model_provider)
        
        # 系统提示词配置
        # 工作流配置
        self.max_chunk_size = 10000  # 文本块最大大小
        self.evaluation_rounds = 10  # 评估轮次
        self.max_parallel_evaluations = 5  # 最大并行评估数量
        
        # 初始化子智能体（作为工具使用）
        self.text_truncator_agent = None
        self.story_outline_evaluator_agent = None
        self.score_analyzer_agent = None
        self.document_generator_agent = None
        
        self.logger.info("故事大纲评估与分析智能体初始化完成")
    
    # 系统提示词由基类自动加载，无需重写
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理故事大纲评估请求

        Args:
            request_data: 包含file, theme, length_size等参数
            context: 上下文信息

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 提取请求信息
            input_text = request_data.get("input", request_data.get("file", ""))
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
                "event_type": "workflow_start",
                "data": {
                    "workflow_name": "story_outline_evaluation",
                    "timestamp": datetime.now().isoformat()
                }
            }

            # 解析输入参数
            file_content = request_data.get("file", input_text)
            theme = request_data.get("theme", "都市爱情")
            length_size = request_data.get("length_size", 10000)

            if not file_content:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": "文件内容为空",
                        "message": "请提供有效的故事大纲内容"
                    }
                }
                return

            # 发送处理开始事件
            yield {
                "event_type": "workflow_processing",
                "data": {
                    "message": "开始故事大纲评估工作流...",
                    "theme": theme,
                    "text_length": len(file_content)
                }
            }
            
            # 步骤1：文本截断处理
            yield {
                "event_type": "step_start",
                "data": {
                    "step_name": "text_truncation",
                    "message": "正在进行文本截断处理..."
                }
            }
            
            truncated_text = await self._truncate_text(file_content, length_size)
            
            yield {
                "event_type": "step_complete",
                "data": {
                    "step_name": "text_truncation",
                    "result": {
                        "original_length": len(file_content),
                        "truncated_length": len(truncated_text)
                    }
                }
            }
            
            # 步骤2：多轮评估
            yield {
                "event_type": "step_start",
                "data": {
                    "step_name": "multi_round_evaluation",
                    "message": f"开始进行{self.evaluation_rounds}轮评估..."
                }
            }
            
            evaluation_results = []
            for round_num in range(1, self.evaluation_rounds + 1):
                yield {
                    "event_type": "evaluation_round",
                    "data": {
                        "round": round_num,
                        "total_rounds": self.evaluation_rounds,
                        "message": f"正在进行第{round_num}轮评估..."
                    }
                }
                
                # 调用故事大纲评估智能体
                evaluation_result = await self._call_story_outline_evaluator(
                    truncated_text, theme, round_num
                )
                evaluation_results.append(evaluation_result)
                
                # 添加随机延迟，模拟真实评估过程
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            yield {
                "event_type": "step_complete",
                "data": {
                    "step_name": "multi_round_evaluation",
                    "result": {
                        "total_rounds": self.evaluation_rounds,
                        "completed_rounds": len(evaluation_results)
                    }
                }
            }
            
            # 步骤3：评分分析
            yield {
                "event_type": "step_start",
                "data": {
                    "step_name": "score_analysis",
                    "message": "正在进行评分分析..."
                }
            }
            
            analysis_result = await self._analyze_scores(evaluation_results)
            
            yield {
                "event_type": "step_complete",
                "data": {
                    "step_name": "score_analysis",
                    "result": analysis_result
                }
            }
            
            # 步骤4：文档生成
            yield {
                "event_type": "step_start",
                "data": {
                    "step_name": "document_generation",
                    "message": "正在生成评估报告文档..."
                }
            }
            
            document_result = await self._generate_document(analysis_result, evaluation_results)
            
            yield {
                "event_type": "step_complete",
                "data": {
                    "step_name": "document_generation",
                    "result": document_result
                }
            }
            
            # 发送最终结果
            yield {
                "event_type": "workflow_complete",
                "data": {
                    "workflow_name": "story_outline_evaluation",
                    "result": {
                        "analysis_result": analysis_result,
                        "document_result": document_result,
                        "evaluation_results": evaluation_results,
                        "theme": theme,
                        "total_rounds": self.evaluation_rounds
                    },
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理故事大纲评估请求时发生错误: {str(e)}")
            yield {
                "event_type": "error",
                "data": {
                    "error": str(e),
                    "message": "故事大纲评估过程中发生错误"
                }
            }
    
    async def _truncate_text(self, text: str, max_length: int) -> str:
        """
        截断文本到指定长度（增强版：带参数验证）

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            str: 截断后的文本
        """
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return ""

            if max_length <= 0:
                self.logger.warning(f"max_length参数不合法({max_length})，使用默认值10000")
                max_length = 10000

            if len(text) <= max_length:
                return text

            # 在句号处截断，保持语义完整性
            truncated = text[:max_length]
            last_period = truncated.rfind('。')
            if last_period > max_length * 0.8:  # 如果句号位置合理
                return truncated[:last_period + 1]
            else:
                return truncated + "..."

        except Exception as e:
            self.logger.error(f"文本截断失败: {str(e)}")
            # 降级处理：使用安全的截断
            safe_length = max(1, min(max_length if max_length > 0 else 10000, len(text)))
            return text[:safe_length]
    
    async def _call_story_outline_evaluator(
        self, 
        text: str, 
        theme: str, 
        round_num: int
    ) -> str:
        """
        调用故事大纲评估智能体
        
        Args:
            text: 要评估的文本
            theme: 题材类型
            round_num: 评估轮次
            
        Returns:
            str: 评估结果
        """
        try:
            # 这里应该调用实际的故事大纲评估智能体
            # 为了演示，我们生成一个模拟的评估结果
            await asyncio.sleep(random.uniform(1, 3))  # 模拟评估时间
            
            # 生成模拟评估结果
            evaluation_result = f"""
【version:2.0】
【题材类型与受众洞察】：
- 题材类型：该故事大纲属于{theme}类型，具有明显的类型特征。评分：{random.uniform(7.0, 9.0):.1f}
- 受众洞察：目标受众定位清晰，符合{theme}类故事的受众需求。评分：{random.uniform(7.0, 9.0):.1f}

【角色设计】：
- 男主角塑造：角色设定合理，性格特点鲜明。评分：{random.uniform(7.0, 9.0):.1f}
- 女主角塑造：角色形象生动，具有吸引力。评分：{random.uniform(7.0, 9.0):.1f}
- 主要配角塑造：配角设计合理，有助于推动剧情发展。评分：{random.uniform(7.0, 9.0):.1f}

【主线情境】：
- 情境阶段：故事情境发展合理，阶段分明。评分：{random.uniform(7.0, 9.0):.1f}
- 情境呈现：情境呈现效果良好，具有戏剧张力。评分：{random.uniform(7.0, 9.0):.1f}

【总体评价】：
- 该故事大纲整体质量良好，具有开发价值。总评分：{random.uniform(7.0, 9.0):.1f}

【跟进建议】：
- 建议进一步优化角色设定和情节发展
- 可以考虑增加一些戏剧冲突点
- 整体方向正确，值得继续开发
"""
            return evaluation_result
            
        except Exception as e:
            self.logger.error(f"调用故事大纲评估智能体失败: {str(e)}")
            return f"第{round_num}轮评估失败: {str(e)}"
    
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
            for result in evaluation_results:
                # 提取总评分
                pattern = r"总评分[：:]\s*(\d+(?:\.\d+)?)"
                match = re.search(pattern, result)
                if match:
                    score = float(match.group(1))
                    scores.append(score)
            
            if not scores:
                return {
                    "error": "未能提取到有效评分",
                    "scores": [],
                    "analysis": "评分分析失败"
                }
            
            # 统计分析
            num_scores = len(scores)
            high_scores = [s for s in scores if s >= 8.0]
            very_high_scores = [s for s in scores if s >= 8.5]
            
            # 确定评级
            if len(very_high_scores) > 0:
                attention_level = "S 强烈关注"
            elif len(high_scores) >= 8:
                attention_level = "S 强烈关注"
            elif len(high_scores) >= 5:
                attention_level = "A 建议关注"
            else:
                attention_level = "B 普通"
            
            # 计算统计信息
            min_score = min(scores)
            max_score = max(scores)
            avg_score = sum(scores) / len(scores)
            first_score = scores[0] if scores else 0
            
            # 计算去除最高最低分的平均分
            if len(scores) > 2:
                scores_without_extremes = sorted(scores)[1:-1]
                avg_without_extremes = sum(scores_without_extremes) / len(scores_without_extremes)
            else:
                avg_without_extremes = avg_score
            
            analysis_result = {
                "attention_level": attention_level,
                "total_rounds": num_scores,
                "scores": scores,
                "statistics": {
                    "min_score": min_score,
                    "max_score": max_score,
                    "avg_score": round(avg_score, 2),
                    "avg_without_extremes": round(avg_without_extremes, 2),
                    "first_score": first_score,
                    "high_scores_count": len(high_scores),
                    "very_high_scores_count": len(very_high_scores)
                },
                "evaluation_summary": f"""
# AI评级: {attention_level}
# 结果 
- 评估次数: {num_scores} 次. 评估结果: {avg_without_extremes if avg_without_extremes else avg_score}
    - 首次评分 {first_score}
    - 复评分数依次为 {'、'.join([str(x) for x in scores[1:]]) if len(scores) > 1 else '-'}
    - 最高分 {max_score}
    - 最低分 {min_score}
    - 平均分 {avg_score}
# 评估参考
- 以评估十次为基准：
    - 当出现不及五次8.0及以上评分时，表示该大纲 "普通"，对应评级为B。 
    - 当出现至少五次8.0及以上评分时，表示该大纲可 "建议关注"，对应评级为A。 
    - 当出现至少八次8.0及以上评分时，表示该大纲可 "强烈关注"，对应评级为S。
    - 当出现至少一次8.5及以上评分时，无论其他评分如何，均表示该大纲可 "强烈关注"，对应评级为S。
"""
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"评分分析失败: {str(e)}")
            return {
                "error": str(e),
                "scores": [],
                "analysis": "评分分析失败"
            }
    
    async def _generate_document(
        self, 
        analysis_result: Dict[str, Any], 
        evaluation_results: List[str]
    ) -> Dict[str, Any]:
        """
        生成评估报告文档
        
        Args:
            analysis_result: 分析结果
            evaluation_results: 评估结果列表
            
        Returns:
            Dict[str, Any]: 文档生成结果
        """
        try:
            # 构建文档内容
            document_content = analysis_result.get("evaluation_summary", "")
            
            # 添加详细评估结果
            for i, result in enumerate(evaluation_results, 1):
                document_content += f"\n## 第{i}次执行结果: \n{result}\n"
            
            # 模拟文档生成
            document_url = f"https://example.com/document/{int(time.time())}"
            document_title = f"故事大纲评估报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            document_result = {
                "url": document_url,
                "title": document_title,
                "content": document_content,
                "status": "success"
            }
            
            return document_result
            
        except Exception as e:
            self.logger.error(f"文档生成失败: {str(e)}")
            return {
                "error": str(e),
                "url": "",
                "title": "",
                "content": "",
                "status": "failed"
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "tool_name": "story_outline_evaluation",
            "description": "故事大纲评估与分析智能体",
            "function": "对故事大纲进行多维度评估和分析",
            "input_parameters": {
                "file": "str - 故事大纲文件内容",
                "theme": "str - 故事题材类型",
                "length_size": "int - 文本截断长度"
            },
            "output": {
                "analysis_result": "dict - 评分分析结果",
                "document_result": "dict - 文档生成结果",
                "evaluation_results": "list - 详细评估结果",
                "theme": "str - 故事题材类型",
                "total_rounds": "int - 评估轮次"
            },
            "workflow_steps": [
                "text_truncation - 文本截断处理",
                "multi_round_evaluation - 多轮评估",
                "score_analysis - 评分分析",
                "document_generation - 文档生成"
            ],
            "evaluation_rounds": self.evaluation_rounds,
            "max_chunk_size": self.max_chunk_size
        }

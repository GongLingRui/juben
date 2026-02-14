from typing import AsyncGenerator, Dict, Any, Optional

"""
故事评估智能体 - 支持Agent as Tool机制

业务处理逻辑：
1. 输入处理：接收故事文本和评估参数，支持多种输入格式
2. 深度阅读：对故事文本进行深入阅读和理解
3. 多维度评估：从市场潜力、创新属性、内容亮点、总体评价四个维度评估
4. 严格评分：按照Story Evaluation Framework进行严格、细致的评分
5. 评分标准：8.5分及以上优秀，8.0-8.4分良好，7.5-7.9分合格，7.4分及以下较差
6. 开发建议：结合评分结果给出是否值得进一步开发成影视剧的建议
7. 输出格式化：返回结构化的评估结果和详细评分
8. Agent as Tool：支持被其他智能体调用，实现上下文隔离

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

class StoryEvaluationAgent(BaseJubenAgent):
    """
    故事评估智能体
    
    核心功能：
    1. 对提供的故事文本进行深入阅读
    2. 根据题材与类型类故事的评估重点，从各个维度对该故事进行判断、评分
    3. 结合判断，为用户后续是否要开发该故事给出意见
    4. 严格、细致要求下的分析与打分
    5. 多维度评估：市场潜力、创新属性、内容亮点、总体评价
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        """初始化故事评估智能体"""
        super().__init__("story_evaluation", model_provider)
        
        # 系统提示词配置
        self.logger.info("故事评估智能体初始化完成")
    
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
                    "tool_name": "story_evaluation",
                    "timestamp": datetime.now().isoformat()
                }
            }

            # 解析输入参数
            story_text = request_data.get("story_text", "")
            theme = request_data.get("theme", "小说")
            round_num = request_data.get("round", 1)
            
            if not story_text:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": "故事文本为空",
                        "message": "请提供有效的故事文本内容"
                    }
                }
                return
            
            # 发送处理开始事件
            yield {
                "event_type": "tool_processing",
                "data": {
                    "message": f"正在进行第{round_num}轮故事评估...",
                    "theme": theme,
                    "text_length": len(story_text)
                }
            }
            
            # 构建用户提示词
            user_prompt = f"""
题材类型为：{theme}
用户输入如下
-----------------
{story_text}
"""
            
            # 调用LLM生成故事评估
            evaluation_chunks = []
            async for event in self._call_llm(user_prompt, context):
                if event.get("event_type") == "llm_chunk":
                    chunk = event.get("data", "")
                    evaluation_chunks.append(chunk)
                    yield event
            
            # 整合生成的评估结果
            full_evaluation = "".join(evaluation_chunks)
            
            # 验证和优化评估结果
            optimized_evaluation = await self._optimize_evaluation(full_evaluation, round_num)
            
            # 提取评分信息
            scores = self._extract_scores(optimized_evaluation)
            
            # 发送最终结果
            yield {
                "event_type": "tool_complete",
                "data": {
                    "tool_name": "story_evaluation",
                    "result": {
                        "evaluation": optimized_evaluation,
                        "scores": scores,
                        "round": round_num,
                        "theme": theme
                    },
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理故事评估请求时发生错误: {str(e)}")
            yield {
                "event_type": "error",
                "data": {
                    "error": str(e),
                    "message": "故事评估过程中发生错误"
                }
            }
    
    async def _optimize_evaluation(self, evaluation: str, round_num: int) -> str:
        """
        优化评估结果，确保格式正确
        
        Args:
            evaluation: 原始评估文本
            round_num: 评估轮次
            
        Returns:
            str: 优化后的评估结果
        """
        try:
            # 清理文本
            evaluation = evaluation.strip()
            
            # 确保包含必要的评估维度
            required_sections = [
                "【市场潜力】", "【创新属性】", "【内容亮点】", 
                "【总体评价】", "【跟进建议】"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in evaluation:
                    missing_sections.append(section)
            
            # 如果有缺失的部分，尝试补充
            if missing_sections:
                self.logger.warning(f"评估结果缺少必要部分: {missing_sections}")
                # 这里可以根据需要实现补充逻辑
            
            # 确保包含版本信息
            if "【version2.9】" not in evaluation:
                evaluation = "【version2.9】\n" + evaluation
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"优化评估结果失败: {str(e)}")
            return evaluation
    
    def _extract_scores(self, evaluation: str) -> Dict[str, float]:
        """
        从评估结果中提取评分信息
        
        Args:
            evaluation: 评估结果文本
            
        Returns:
            Dict[str, float]: 评分信息字典
        """
        try:
            scores = {}
            
            # 定义评分提取模式
            score_patterns = {
                "audience_suitability": r"受众适合度.*?评分[：:]\s*(\d+\.?\d*)",
                "discussion_heat": r"讨论热度.*?评分[：:]\s*(\d+\.?\d*)",
                "scarcity": r"稀缺性.*?评分[：:]\s*(\d+\.?\d*)",
                "playback_data": r"播放数据.*?评分[：:]\s*(\d+\.?\d*)",
                "core_selection": r"核心选点.*?评分[：:]\s*(\d+\.?\d*)",
                "story_concept": r"故事概念.*?评分[：:]\s*(\d+\.?\d*)",
                "story_design": r"故事设计.*?评分[：:]\s*(\d+\.?\d*)",
                "theme_meaning": r"主题立意.*?评分[：:]\s*(\d+\.?\d*)",
                "story_situation": r"故事情境.*?评分[：:]\s*(\d+\.?\d*)",
                "character_setting": r"人物设定.*?评分[：:]\s*(\d+\.?\d*)",
                "character_relationship": r"人物关系.*?评分[：:]\s*(\d+\.?\d*)",
                "plot_bridge": r"情节桥段.*?评分[：:]\s*(\d+\.?\d*)",
                "total_score": r"总评分[：:]\s*(\d+\.?\d*)"
            }
            
            # 提取各项评分
            for key, pattern in score_patterns.items():
                match = re.search(pattern, evaluation)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                    except ValueError:
                        continue
            
            return scores
            
        except Exception as e:
            self.logger.error(f"提取评分信息失败: {str(e)}")
            return {}
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "tool_name": "story_evaluation",
            "description": "故事评估智能体",
            "function": "对故事文本进行多维度评估和评分",
            "input_parameters": {
                "story_text": "str - 需要评估的故事文本内容",
                "theme": "str - 故事题材类型",
                "round": "int - 评估轮次"
            },
            "output": {
                "evaluation": "str - 完整的评估结果",
                "scores": "dict - 各项评分信息",
                "round": "int - 评估轮次",
                "theme": "str - 故事题材类型"
            },
            "evaluation_dimensions": {
                "market_potential": ["受众适合度", "讨论热度", "稀缺性", "播放数据"],
                "innovation_attributes": ["核心选点", "故事概念", "故事设计"],
                "content_highlights": ["主题立意", "故事情境", "人物设定", "人物关系", "情节桥段"],
                "overall_evaluation": ["总体评价"]
            },
            "scoring_standards": {
                "excellent": "8.5分及以上 - 优秀，极强竞争力",
                "good": "8.0-8.4分 - 良好，较强竞争力",
                "qualified": "7.5-7.9分 - 合格，中规中矩",
                "poor": "7.4分及以下 - 较差，竞争力弱"
            }
        }

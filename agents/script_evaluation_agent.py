from typing import AsyncGenerator, Dict, Any, Optional

"""
剧本评估智能体
基于agent as tool机制，实现智能体间的模块化外包和上下文隔离

业务处理逻辑：
1. 输入处理：接收影视剧本内容，支持多种输入格式
2. 剧本深度分析：对影视剧本进行深入评估分析
3. 三维度评估：基于思想性、艺术性、观赏性三个维度进行评分
4. 剧本质量评估：评估剧本的完整性、逻辑性、可拍性
5. 修改建议：提供具体的剧本修改和推进建议
6. 商业价值评估：评估剧本的商业价值和市场潜力
7. 输出格式化：返回结构化的剧本评估数据
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
class ScriptEvaluationAgent(BaseJubenAgent):
    """
    剧本评估智能体
    
    核心功能：
    1. 对影视剧本进行深入评估分析
    2. 基于思想性、艺术性、观赏性三个维度进行评分
    3. 提供剧本修改和推进建议
    4. 支持Agent as Tool机制
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        super().__init__("script_evaluation", model_provider)
        
        # 系统提示词配置
        # 剧本评估配置
        self.evaluation_dimensions = ["思想性", "艺术性", "观赏性"]
        self.script_factors = ["故事结构", "人物塑造", "对话质量", "场景设置", "节奏控制"]
        self.commercial_factors = ["市场潜力", "制作可行性", "成本控制", "档期安排"]
        
        self.logger.info("🎬 剧本评估智能体初始化完成")
        self.logger.info(f"📊 评估维度: {len(self.evaluation_dimensions)}个")
        self.logger.info(f"🎯 剧本因素: {len(self.script_factors)}个")
        self.logger.info(f"💰 商业因素: {len(self.commercial_factors)}个")
    
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

            # 提取请求参数
            script_content = request_data.get("input", "")
            theme = request_data.get("theme", "")
            genre = request_data.get("genre", "")
            
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            
            # 发送开始处理事件
            yield {
                "type": "processing_start",
                "message": "开始剧本评估分析",
                "timestamp": datetime.now().isoformat(),
                "theme": theme,
                "genre": genre
            }
            
            # 构建评估提示词
            evaluation_prompt = f"""
请对以下影视剧本进行评估分析：

主题：{theme}
类型：{genre}
剧本内容：{script_content}

请从以下维度进行评估：
1. 思想性评估
2. 艺术性评估
3. 观赏性评估

同时评估剧本质量因素：
- 故事结构
- 人物塑造
- 对话质量
- 场景设置
- 节奏控制

最后评估商业价值：
- 市场潜力
- 制作可行性
- 成本控制

请给出详细的评估结果和修改建议。
"""
            
            # 调用LLM进行评估
            async for chunk in self.llm_client.astream_chat(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": evaluation_prompt}
                ]
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "type": "content",
                        "content": chunk.choices[0].delta.content,
                        "timestamp": datetime.now().isoformat()
                    }
            
            # 发送完成事件
            yield {
                "type": "processing_complete",
                "message": "剧本评估分析完成",
                "timestamp": datetime.now().isoformat(),
                "theme": theme,
                "genre": genre
            }
            
        except Exception as e:
            self.logger.error(f"剧本评估失败: {e}")
            yield {
                "type": "error",
                "message": f"剧本评估失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def evaluate_script(
        self,
        script_content: str,
        theme: str = "",
        genre: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agent as Tool: 评估剧本
        
        Args:
            script_content: 剧本内容
            theme: 主题
            genre: 类型
            context: 上下文信息
            
        Returns:
            Dict[str, Any]: 评估结果
        """
        request_data = {
            "input": script_content,
            "theme": theme,
            "genre": genre
        }
        
        result = {
            "script_content": script_content,
            "theme": theme,
            "genre": genre,
            "evaluation_result": "",
            "modification_suggestions": "",
            "commercial_value": ""
        }
        
        # 收集流式输出
        async for event in self.process_request(request_data, context):
            if event["type"] == "content":
                result["evaluation_result"] += event["content"]
        
        return result
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "agent_name": "剧本评估智能体",
            "agent_type": "evaluation",
            "description": "对影视剧本进行深入评估分析，从思想性、艺术性、观赏性三个维度进行专业评估",
            "capabilities": [
                "思想性评估",
                "艺术性评估",
                "观赏性评估",
                "剧本质量评估",
                "修改建议提供",
                "商业价值评估",
                "Agent as Tool支持"
            ],
            "evaluation_dimensions": self.evaluation_dimensions,
            "script_factors": self.script_factors,
            "commercial_factors": self.commercial_factors,
            "supported_formats": ["剧本文本", "剧本文档", "剧本链接"],
            "output_format": "结构化评估报告"
        }

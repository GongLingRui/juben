"""
工作流管理器
负责管理竖屏短剧策划的各种工作流定义和执行

🆕 增强功能：
- 支持动态工作流计划解析
- 工作流步骤状态追踪
- 引用数据管理
- 质量评估集成
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json
import re
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self):
        """初始化工作流管理器"""
        self.workflows = {
            "story_analysis": {
                "name": "故事分析工作流",
                "description": "分析现有故事、IP评估、市场定位",
                "steps": [
                    {
                        "name": "故事内容分析",
                        "agent_type": "story_analysis_agent",
                        "instruction": "分析故事的核心内容、主题和结构",
                        "config": {"analysis_depth": "comprehensive"}
                    },
                    {
                        "name": "市场定位分析",
                        "agent_type": "market_analysis_agent", 
                        "instruction": "分析故事的市场定位和受众群体",
                        "config": {"market_scope": "domestic"}
                    },
                    {
                        "name": "IP价值评估",
                        "agent_type": "ip_evaluation_agent",
                        "instruction": "评估IP的商业价值和改编潜力",
                        "config": {"evaluation_criteria": "comprehensive"}
                    }
                ]
            },
            "story_creation": {
                "name": "故事创作工作流",
                "description": "从零开始创作竖屏短剧故事",
                "steps": [
                    {
                        "name": "创意构思",
                        "agent_type": "creative_brainstorming_agent",
                        "instruction": "基于用户需求进行创意构思",
                        "config": {"brainstorming_mode": "structured"}
                    },
                    {
                        "name": "故事大纲设计",
                        "agent_type": "story_outline_agent",
                        "instruction": "设计完整的故事大纲和结构",
                        "config": {"outline_type": "detailed"}
                    },
                    {
                        "name": "角色设定",
                        "agent_type": "character_development_agent",
                        "instruction": "创建主要角色和人物关系",
                        "config": {"character_depth": "comprehensive"}
                    },
                    {
                        "name": "情节设计",
                        "agent_type": "plot_development_agent",
                        "instruction": "设计核心情节和情节点",
                        "config": {"plot_complexity": "medium"}
                    }
                ]
            },
            "character_development": {
                "name": "角色开发工作流",
                "description": "专门的角色设定和关系分析",
                "steps": [
                    {
                        "name": "角色档案创建",
                        "agent_type": "character_profile_agent",
                        "instruction": "创建详细的角色档案",
                        "config": {"profile_depth": "comprehensive"}
                    },
                    {
                        "name": "人物关系分析",
                        "agent_type": "character_relationship_agent",
                        "instruction": "分析角色间的关系网络",
                        "config": {"relationship_scope": "all"}
                    },
                    {
                        "name": "角色弧光设计",
                        "agent_type": "character_arc_agent",
                        "instruction": "设计角色的成长弧线",
                        "config": {"arc_type": "emotional"}
                    }
                ]
            },
            "plot_development": {
                "name": "情节开发工作流",
                "description": "专门的情节设计和结构分析",
                "steps": [
                    {
                        "name": "情节点分析",
                        "agent_type": "plot_points_agent",
                        "instruction": "分析现有情节点或设计新情节点",
                        "config": {"analysis_type": "comprehensive"}
                    },
                    {
                        "name": "戏剧冲突设计",
                        "agent_type": "drama_conflict_agent",
                        "instruction": "设计戏剧冲突和张力点",
                        "config": {"conflict_intensity": "high"}
                    },
                    {
                        "name": "节奏控制",
                        "agent_type": "pacing_control_agent",
                        "instruction": "优化故事节奏和观众体验",
                        "config": {"pacing_style": "dynamic"}
                    }
                ]
            },
            "drama_evaluation": {
                "name": "短剧评估工作流",
                "description": "剧本评估和市场分析",
                "steps": [
                    {
                        "name": "剧本质量评估",
                        "agent_type": "script_evaluation_agent",
                        "instruction": "评估剧本的文学质量和商业价值",
                        "config": {"evaluation_scope": "comprehensive"}
                    },
                    {
                        "name": "市场竞争力分析",
                        "agent_type": "market_competitiveness_agent",
                        "instruction": "分析剧本的市场竞争力",
                        "config": {"market_scope": "domestic"}
                    },
                    {
                        "name": "风险评估",
                        "agent_type": "risk_assessment_agent",
                        "instruction": "评估投资和制作风险",
                        "config": {"risk_categories": "all"}
                    }
                ]
            },
            "series_analysis": {
                "name": "剧集分析工作流",
                "description": "已播剧集分析和竞品研究",
                "steps": [
                    {
                        "name": "剧集内容分析",
                        "agent_type": "series_content_analysis_agent",
                        "instruction": "分析剧集的内容特点和成功要素",
                        "config": {"analysis_depth": "comprehensive"}
                    },
                    {
                        "name": "观众反馈分析",
                        "agent_type": "audience_feedback_agent",
                        "instruction": "分析观众反馈和评价",
                        "config": {"feedback_sources": "multiple"}
                    },
                    {
                        "name": "竞品对比分析",
                        "agent_type": "competitor_analysis_agent",
                        "instruction": "与竞品进行对比分析",
                        "config": {"comparison_scope": "comprehensive"}
                    }
                ]
            }
        }
    
    def get_supported_workflows(self) -> List[str]:
        """获取支持的工作流类型列表"""
        return list(self.workflows.keys())
    
    def get_workflow_definition(self, workflow_type: str) -> Optional[Dict[str, Any]]:
        """获取工作流定义"""
        return self.workflows.get(workflow_type)
    
    async def create_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        instruction: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建工作流实例
        
        Args:
            workflow_id: 工作流ID
            workflow_type: 工作流类型
            instruction: 用户指令
            user_id: 用户ID
            session_id: 会话ID
            context: 上下文信息
            
        Returns:
            Dict: 工作流实例
        """
        workflow_def = self.get_workflow_definition(workflow_type)
        if not workflow_def:
            raise ValueError(f"不支持的工作流类型: {workflow_type}")
        
        # 创建工作流实例
        workflow_instance = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "name": workflow_def["name"],
            "description": workflow_def["description"],
            "instruction": instruction,
            "user_id": user_id,
            "session_id": session_id,
            "steps": workflow_def["steps"].copy(),
            "context": context or {},
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "current_step": 0,
            "results": [],
            "metadata": {
                "total_steps": len(workflow_def["steps"]),
                "estimated_duration": self._estimate_duration(workflow_def["steps"])
            }
        }
        
        return workflow_instance
    
    def _estimate_duration(self, steps: List[Dict[str, Any]]) -> int:
        """估算工作流执行时间（分钟）"""
        # 基于步骤数量和类型估算
        base_time = len(steps) * 2  # 每个步骤基础2分钟
        
        # 根据Agent类型调整时间
        time_multipliers = {
            "story_analysis_agent": 1.5,
            "market_analysis_agent": 1.2,
            "ip_evaluation_agent": 1.3,
            "creative_brainstorming_agent": 2.0,
            "story_outline_agent": 1.8,
            "character_development_agent": 1.5,
            "plot_development_agent": 1.6,
            "script_evaluation_agent": 1.4,
            "series_content_analysis_agent": 1.3
        }
        
        total_time = 0
        for step in steps:
            agent_type = step.get("agent_type", "")
            multiplier = time_multipliers.get(agent_type, 1.0)
            total_time += 2 * multiplier
        
        return int(total_time)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[str]:
        """获取工作流状态"""
        # 这里可以实现工作流状态查询逻辑
        # 实际实现中可能需要从数据库或缓存中获取
        return "running"
    
    def update_workflow_status(self, workflow_id: str, status: str) -> bool:
        """更新工作流状态"""
        # 这里可以实现工作流状态更新逻辑
        return True
    
    def get_workflow_metrics(self) -> Dict[str, Any]:
        """获取工作流指标"""
        return {
            "total_workflows": len(self.workflows),
            "supported_types": list(self.workflows.keys()),
            "average_steps": sum(len(w["steps"]) for w in self.workflows.values()) / len(self.workflows)
        }

    # ==================== 🆕 工作流计划解析功能 ====================

    def parse_workflow_plan_from_text(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        从文本中解析工作流计划

        支持格式：
        - JSON格式: {"workflow_plan": [...]}
        - XML格式: <workflow_plan>[...]</workflow_plan>
        - Markdown代码块: ```json ... ```

        Args:
            text: 包含工作流计划的文本

        Returns:
            解析后的工作流步骤列表
        """
        try:
            # 方法1: 尝试从JSON中提取
            workflow_plan = self._extract_workflow_plan_from_json(text)
            if workflow_plan:
                return workflow_plan

            # 方法2: 尝试从XML中提取
            workflow_plan = self._extract_workflow_plan_from_xml(text)
            if workflow_plan:
                return workflow_plan

            return None
        except Exception as e:
            logger.error(f"解析工作流计划失败: {e}")
            return None

    def _extract_workflow_plan_from_json(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """从JSON格式中提取工作流计划"""
        try:
            # 尝试提取markdown代码块中的JSON
            json_pattern = r'```json\s*\n?(.*?)\n?```'
            match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)

            if match:
                json_str = match.group(1).strip()
                json_obj = json.loads(json_str)
                if "workflow_plan" in json_obj:
                    return json_obj["workflow_plan"]

            # 尝试直接解析整个文本
            json_obj = json.loads(text.strip())
            if "workflow_plan" in json_obj:
                return json_obj["workflow_plan"]

            return None
        except (json.JSONDecodeError, KeyError):
            return None

    def _extract_workflow_plan_from_xml(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """从XML格式中提取工作流计划"""
        try:
            # 提取 <workflow_plan> 标签内容
            pattern = r'<workflow_plan>\s*:?\s*(\[.*?\])\s*</workflow_plan>'
            match = re.search(pattern, text, re.DOTALL)

            if match:
                plan_str = match.group(1).strip()

                # 尝试JSON解析
                try:
                    return json.loads(plan_str.replace("'", '"'))
                except json.JSONDecodeError:
                    pass

                # 尝试ast.literal_eval
                import ast
                try:
                    return ast.literal_eval(plan_str)
                except (ValueError, SyntaxError):
                    pass

            return None
        except Exception:
            return None

    # ==================== 🆕 工作流步骤状态管理 ====================

    def update_step_status(
        self,
        workflow_id: str,
        step_index: int,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新工作流步骤状态

        Args:
            workflow_id: 工作流ID
            step_index: 步骤索引
            status: 新状态 (pending/in_progress/completed/failed)
            result: 步骤执行结果

        Returns:
            是否更新成功
        """
        # 实际实现中应该更新到数据库或缓存
        # 这里提供一个简单的接口
        return True

    def get_step_progress(self, workflow_id: str) -> Dict[str, Any]:
        """
        获取工作流步骤进度

        Args:
            workflow_id: 工作流ID

        Returns:
            进度信息
        """
        # 实际实现中应该从数据库或缓存中获取
        return {
            "total_steps": 0,
            "completed_steps": 0,
            "progress_percentage": 0.0,
            "current_step": None
        }

    # ==================== 🆕 引用数据管理 ====================

    def format_references_for_agent(
        self,
        references: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        将引用数据格式化为适合agent使用的文本格式

        Args:
            references: 引用项目列表，每个引用包含type和content

        Returns:
            格式化后的引用文本
        """
        if not references:
            return ""

        formatted_refs = []
        ref_counter = 1

        for ref in references:
            ref_type = ref.get("type", "未知类型")
            ref_content = ref.get("content", "")
            if ref_content:  # 只处理有内容的引用
                formatted_refs.append(f"引用{ref_counter} ({ref_type}):\n{ref_content}")
                ref_counter += 1

        if formatted_refs:
            return "\n\n📚 可用引用资料：\n" + "\n\n".join(formatted_refs) + "\n"

        return ""

    # ==================== 🆕 质量评估集成 ====================

    def evaluate_step_output(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估工作流步骤输出质量

        Args:
            content: 要评估的内容
            context: 上下文信息

        Returns:
            评估结果
        """
        try:
            from .content_quality_evaluator import evaluate_content_quality

            report = evaluate_content_quality(content, context)

            return {
                "passed": report.passed,
                "overall_score": report.overall_score,
                "dimension_scores": [
                    {
                        "dimension": score.dimension,
                        "score": score.score,
                        "details": score.details
                    }
                    for score in report.dimension_scores
                ],
                "suggestions": report.improvement_suggestions
            }
        except ImportError:
            return {
                "passed": True,
                "overall_score": 0,
                "dimension_scores": [],
                "suggestions": [],
                "error": "质量评估模块未安装"
            }


# ==================== 🆕 数据类定义 ====================

@dataclass
class WorkflowStep:
    """工作流步骤数据类"""
    stage: str  # Agent名称或阶段名称
    instruction: str  # 执行指令
    status: str = "pending"  # pending/in_progress/completed/failed
    completed: bool = False
    max_rounds: int = 1  # 最大执行轮次
    current_round: int = 0
    requires_confirmation: bool = False  # 是否需要人工确认
    result: Optional[Dict[str, Any]] = None  # 执行结果
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)  # 工具调用记录
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class WorkflowPlan:
    """工作流计划数据类"""
    steps: List[WorkflowStep]
    current_step_index: int = 0
    status: str = "created"  # created/running/completed/failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_current_step(self) -> Optional[WorkflowStep]:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance_to_next_step(self) -> bool:
        """前进到下一步骤"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def mark_step_completed(self, result: Optional[Dict[str, Any]] = None):
        """标记当前步骤为已完成"""
        current_step = self.get_current_step()
        if current_step:
            current_step.status = "completed"
            current_step.completed = True
            current_step.result = result or {}
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "steps": [
                {
                    "stage": step.stage,
                    "instruction": step.instruction,
                    "status": step.status,
                    "completed": step.completed,
                    "max_rounds": step.max_rounds,
                    "current_round": step.current_round,
                    "requires_confirmation": step.requires_confirmation,
                    "result": step.result,
                    "tool_calls": step.tool_calls,
                    "metadata": step.metadata
                }
                for step in self.steps
            ],
            "current_step_index": self.current_step_index,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }

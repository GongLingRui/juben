"""
大情节点与详细情节点交互式工作流
支持分阶段执行、状态持久化、用户反馈注入

核心功能：
1. 分阶段执行（大纲 -> 角色 -> 大情节点 -> 详细情节点 -> 思维导图）
2. 每阶段完成后暂停，等待用户反馈
3. 状态持久化到 Redis/Database
4. 支持从任意阶段恢复执行

代码作者：宫灵瑞
创建时间：2024年
优化时间：2026年2月7日
"""
import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
import uuid

try:
    from agents.plot_points_workflow_agent import PlotPointsWorkflowAgent
    from agents.story_summary_generator_agent import StorySummaryGeneratorAgent
    from agents.major_plot_points_agent import MajorPlotPointsAgent
    from agents.mind_map_agent import MindMapAgent
    from agents.detailed_plot_points_agent import DetailedPlotPointsAgent
    from agents.output_formatter_agent import OutputFormatterAgent
    from agents.character_profile_generator_agent import CharacterProfileGeneratorAgent
except ImportError:
    PlotPointsWorkflowAgent = None
    StorySummaryGeneratorAgent = None
    MajorPlotPointsAgent = None
    MindMapAgent = None
    DetailedPlotPointsAgent = None
    OutputFormatterAgent = None
    CharacterProfileGeneratorAgent = None

try:
    from agents.text_truncator_agent import TextTruncatorAgent
    from agents.text_splitter_agent import TextSplitterAgent
except ImportError:
    TextTruncatorAgent = None
    TextSplitterAgent = None


# ==================== 工作流阶段定义 ====================

class WorkflowStage(Enum):
    """工作流阶段枚举"""
    INPUT_VALIDATION = "input_validation"        # 输入验证
    TEXT_PREPROCESSING = "text_preprocessing"    # 文本预处理
    STORY_OUTLINE = "story_outline"              # 故事大纲
    CHARACTER_PROFILES = "character_profiles"    # 人物小传
    MAJOR_PLOT_POINTS = "major_plot_points"      # 大情节点
    DETAILED_PLOT_POINTS = "detailed_plot_points"  # 详细情节点
    MIND_MAP = "mind_map"                        # 思维导图
    RESULT_FORMATTING = "result_formatting"      # 结果格式化
    COMPLETED = "completed"                      # 已完成
    FAILED = "failed"                            # 失败
    CANCELLED = "cancelled"                      # 已取消


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    INITIALIZED = "initialized"                  # 已初始化
    IN_PROGRESS = "in_progress"                  # 进行中
    WAITING_FOR_USER = "waiting_for_user"        # 等待用户反馈
    PAUSED = "paused"                            # 已暂停
    COMPLETED = "completed"                      # 已完成
    FAILED = "failed"                            # 失败


class NodeEventStatus(Enum):
    """节点事件状态枚举"""
    WAITING = "waiting"                          # 等待执行
    PROCESSING = "processing"                    # 执行中
    SUCCESS = "success"                          # 执行成功
    FAILED = "failed"                            # 执行失败


# ==================== 工作流状态数据结构 ====================

@dataclass
class StageResult:
    """阶段执行结果"""
    stage: WorkflowStage
    status: WorkflowStatus
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    user_feedback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "user_feedback": self.user_feedback
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageResult":
        """从字典创建"""
        return cls(
            stage=WorkflowStage(data.get("stage", WorkflowStage.STORY_OUTLINE.value)),
            status=WorkflowStatus(data.get("status", WorkflowStatus.IN_PROGRESS.value)),
            output=data.get("output", {}),
            error=data.get("error"),
            started_at=data.get("started_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
            user_feedback=data.get("user_feedback")
        )


@dataclass
class WorkflowState:
    """工作流完整状态"""
    workflow_id: str
    project_id: str
    user_id: str
    session_id: str
    status: WorkflowStatus = WorkflowStatus.INITIALIZED
    current_stage: WorkflowStage = WorkflowStage.INPUT_VALIDATION
    input_data: Dict[str, Any] = field(default_factory=dict)
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "input_data": self.input_data,
            "stage_results": {
                k: v.to_dict() if isinstance(v, StageResult) else v
                for k, v in self.stage_results.items()
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "config": self.config
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """从字典创建"""
        stage_results = {}
        for k, v in data.get("stage_results", {}).items():
            if isinstance(v, dict):
                stage_results[k] = StageResult.from_dict(v)
            else:
                stage_results[k] = v

        return cls(
            workflow_id=data["workflow_id"],
            project_id=data.get("project_id", ""),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            status=WorkflowStatus(data.get("status", WorkflowStatus.INITIALIZED.value)),
            current_stage=WorkflowStage(data.get("current_stage", WorkflowStage.INPUT_VALIDATION.value)),
            input_data=data.get("input_data", {}),
            stage_results=stage_results,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
            config=data.get("config", {})
        )


# ==================== 工作流状态管理器 ====================

class WorkflowStateManager:
    """
    工作流状态管理器

    负责：
    1. 状态持久化到 Redis
    2. 从 Redis 恢复状态
    3. 状态生命周期管理
    """

    def __init__(self):
        from utils.logger import JubenLogger
        self.logger = JubenLogger("WorkflowStateManager")
        self._redis_client = None

    async def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis_client is None:
            try:
                from utils.redis_client import get_redis_client
                self._redis_client = await get_redis_client()
            except Exception as e:
                self.logger.warning(f"Redis 客户端初始化失败: {e}")
        return self._redis_client

    def _get_state_key(self, workflow_id: str) -> str:
        """获取状态存储键"""
        return f"workflow:state:{workflow_id}"

    async def save_state(self, state: WorkflowState) -> bool:
        """
        保存工作流状态

        Args:
            state: 工作流状态

        Returns:
            bool: 是否成功
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                self.logger.warning("Redis 不可用，状态将不会被持久化")
                return False

            key = self._get_state_key(state.workflow_id)
            state.updated_at = datetime.now().isoformat()

            # 保存状态（7天过期）
            success = await redis_client.set(
                key,
                state.to_dict(),
                expire=7 * 24 * 3600
            )

            if success:
                self.logger.info(f"💾 保存工作流状态: {state.workflow_id}, 阶段: {state.current_stage.value}")

            return success

        except Exception as e:
            self.logger.error(f"保存状态失败: {e}")
            return False

    async def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        获取工作流状态

        Args:
            workflow_id: 工作流 ID

        Returns:
            Optional[WorkflowState]: 工作流状态
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return None

            key = self._get_state_key(workflow_id)
            data = await redis_client.get(key)

            if data:
                return WorkflowState.from_dict(data)

            return None

        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            return None

    async def delete_state(self, workflow_id: str) -> bool:
        """删除工作流状态"""
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            key = self._get_state_key(workflow_id)
            await redis_client.delete(key)
            self.logger.info(f"🗑️ 删除工作流状态: {workflow_id}")
            return True

        except Exception as e:
            self.logger.error(f"删除状态失败: {e}")
            return False

    async def list_active_workflows(self, user_id: str = None) -> List[str]:
        """
        列出活跃的工作流

        Args:
            user_id: 用户 ID（可选，用于筛选）

        Returns:
            List[str]: 工作流 ID 列表
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return []

            # 扫描所有工作流状态键
            pattern = "workflow:state:*"
            workflow_ids = []

            # 使用 scan 命令
            async for key in redis_client._client.scan_iter(match=pattern, count=100):
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                workflow_id = key_str.split(":")[-1]

                # 检查状态
                state = await self.get_state(workflow_id)
                if state and state.status != WorkflowStatus.COMPLETED:
                    if user_id is None or state.user_id == user_id:
                        workflow_ids.append(workflow_id)

            return workflow_ids

        except Exception as e:
            self.logger.error(f"列出工作流失败: {e}")
            return []

    async def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流执行进度

        Args:
            workflow_id: 工作流 ID

        Returns:
            Dict: 包含进度信息的字典
                {
                    "workflow_id": str,
                    "status": str,
                    "current_stage": str,
                    "current_stage_index": int,
                    "total_stages": int,
                    "progress_percentage": float,
                    "completed_stages": List[str],
                    "stage_results": Dict,
                    "created_at": str,
                    "updated_at": str,
                    "can_resume": bool
                }
        """
        try:
            state = await self.get_state(workflow_id)
            if not state:
                return None

            # 获取阶段序列
            stage_sequence = [
                WorkflowStage.INPUT_VALIDATION,
                WorkflowStage.TEXT_PREPROCESSING,
                WorkflowStage.STORY_OUTLINE,
                WorkflowStage.CHARACTER_PROFILES,
                WorkflowStage.MAJOR_PLOT_POINTS,
                WorkflowStage.DETAILED_PLOT_POINTS,
                WorkflowStage.MIND_MAP,
                WorkflowStage.RESULT_FORMATTING,
            ]

            # 计算当前阶段索引
            try:
                current_index = stage_sequence.index(state.current_stage)
            except ValueError:
                current_index = 0

            # 计算进度百分比
            total_stages = len(stage_sequence)
            progress_percentage = (current_index / total_stages) * 100

            # 获取已完成的阶段列表
            completed_stages = [
                stage_name for stage_name, result in state.stage_results.items()
                if result.status == WorkflowStatus.COMPLETED
            ]

            # 判断是否可以恢复（处于等待用户反馈状态或进行中）
            can_resume = state.status in [
                WorkflowStatus.WAITING_FOR_USER,
                WorkflowStatus.PAUSED,
                WorkflowStatus.IN_PROGRESS
            ]

            return {
                "workflow_id": state.workflow_id,
                "project_id": state.project_id,
                "user_id": state.user_id,
                "session_id": state.session_id,
                "status": state.status.value,
                "current_stage": state.current_stage.value,
                "current_stage_index": current_index,
                "total_stages": total_stages,
                "progress_percentage": round(progress_percentage, 2),
                "completed_stages": completed_stages,
                "stage_results": {
                    k: v.to_dict() if isinstance(v, StageResult) else v
                    for k, v in state.stage_results.items()
                },
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "completed_at": state.completed_at,
                "can_resume": can_resume,
                "awaiting_feedback": state.status == WorkflowStatus.WAITING_FOR_USER
            }

        except Exception as e:
            self.logger.error(f"获取工作流进度失败: {e}")
            return None


# ==================== 交互式工作流编排器 ====================

class InteractivePlotPointsWorkflow:
    """
    交互式情节点工作流编排器

    核心功能：
    1. 分阶段执行工作流
    2. 每阶段完成后暂停等待用户反馈
    3. 支持从任意阶段恢复
    4. 状态持久化
    """

    # 工作流阶段顺序定义
    STAGE_SEQUENCE = [
        WorkflowStage.INPUT_VALIDATION,
        WorkflowStage.TEXT_PREPROCESSING,
        WorkflowStage.STORY_OUTLINE,
        WorkflowStage.CHARACTER_PROFILES,
        WorkflowStage.MAJOR_PLOT_POINTS,
        WorkflowStage.DETAILED_PLOT_POINTS,
        WorkflowStage.MIND_MAP,
        WorkflowStage.RESULT_FORMATTING,
        WorkflowStage.COMPLETED
    ]

    def __init__(self):
        """初始化工作流编排器"""
        from utils.logger import JubenLogger
        self.logger = JubenLogger("InteractivePlotPointsWorkflow")

        # 状态管理器
        self.state_manager = WorkflowStateManager()

        # 子智能体（延迟加载）
        self.sub_agents = {}
        self._sub_agents_lock = asyncio.Lock()

        # 工作流配置
        self.config = {
            "chunk_size": 10000,
            "length_size": 50000,
            "enable_auto_advance": False,  # 是否自动进入下一阶段（需要用户确认）
            "output_format": "markdown",
            "agent_call_timeout": 300,
            "agent_concurrency_limit": 4
        }

        # 当前运行的工作流状态（内存中）
        self._running_states: Dict[str, WorkflowState] = {}

    # ==================== 🆕 事件上报方法 ====================

    def _get_node_name(self, stage: WorkflowStage) -> str:
        """
        获取阶段对应的前端节点名称

        Args:
            stage: 工作流阶段

        Returns:
            str: 前端节点 ID
        """
        node_mapping = {
            WorkflowStage.INPUT_VALIDATION: "input_validation",
            WorkflowStage.TEXT_PREPROCESSING: "text_preprocessing",
            WorkflowStage.STORY_OUTLINE: "story_outline",
            WorkflowStage.CHARACTER_PROFILES: "character_profiles",
            WorkflowStage.MAJOR_PLOT_POINTS: "major_plot_points",
            WorkflowStage.DETAILED_PLOT_POINTS: "detailed_plot_points",
            WorkflowStage.MIND_MAP: "mind_map",
            WorkflowStage.RESULT_FORMATTING: "result_formatting",
        }
        return node_mapping.get(stage, stage.value)

    def _generate_output_snapshot(self, stage: WorkflowStage, output: Dict[str, Any]) -> str:
        """
        生成输出摘要（用于事件 Payload）

        Args:
            stage: 工作流阶段
            output: 阶段输出

        Returns:
            str: 输出摘要
        """
        if not output:
            return "无输出"

        # 根据不同阶段生成不同的摘要
        if stage == WorkflowStage.STORY_OUTLINE:
            content = output.get("story_outline", "")
            if content:
                preview = content[:200] + "..." if len(content) > 200 else content
                return f"故事大纲已生成 (字数: {len(content)})\n预览: {preview}"
            return "故事大纲生成中..."

        elif stage == WorkflowStage.CHARACTER_PROFILES:
            content = output.get("character_profiles", "")
            if content:
                lines = content.count('\n')
                return f"人物小传已生成 (行数: {lines})"
            return "人物小传生成中..."

        elif stage == WorkflowStage.MAJOR_PLOT_POINTS:
            content = output.get("major_plot_points", "")
            if content:
                points = content.count('1.') + content.count('2.') + content.count('•')
                return f"大情节点已生成 (预估数量: {max(1, points // 3)})"
            return "大情节点生成中..."

        elif stage == WorkflowStage.DETAILED_PLOT_POINTS:
            content = output.get("detailed_plot_points", "")
            if content:
                return f"详细情节点已生成 (字数: {len(content)})"
            return "详细情节点生成中..."

        elif stage == WorkflowStage.MIND_MAP:
            mind_map = output.get("mind_map", {})
            if mind_map.get("pic"):
                return f"思维导图已生成 (图片链接: 已获取)"
            return "思维导图生成中..."

        elif stage == WorkflowStage.RESULT_FORMATTING:
            formatted = output.get("formatted_output", "")
            if formatted:
                return f"结果格式化完成 (字数: {len(formatted)})"
            return "结果格式化中..."

        return f"输出数据: {list(output.keys())}"

    async def _emit_event(
        self,
        workflow_id: str,
        node_name: str,
        status: NodeEventStatus,
        output_snapshot: str = "",
        error: str = None
    ) -> Dict[str, Any]:
        """
        发送工作流节点事件（用于 SSE 推送）

        Args:
            workflow_id: 工作流 ID
            node_name: 节点名称（对应前端节点 ID）
            status: 节点状态 (waiting, processing, success, failed)
            output_snapshot: 输出摘要
            error: 错误信息（如果失败）

        Returns:
            Dict[str, Any]: 事件数据（SSE 格式）
        """
        event = {
            "event_type": "workflow_node_event",
            "agent_source": "workflow_orchestrator",
            "timestamp": datetime.now().isoformat(),
            "data": "",
            "metadata": {
                "workflow_id": workflow_id,
                "node_name": node_name,
                "status": status.value,
                "output_snapshot": output_snapshot,
                "error": error
            }
        }
        return event

    async def execute_workflow(
        self,
        input_data: Dict[str, Any],
        user_id: str,
        session_id: str,
        project_id: str = None,
        start_stage: WorkflowStage = WorkflowStage.INPUT_VALIDATION,
        stop_at_stage: WorkflowStage = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行工作流（分阶段）

        Args:
            input_data: 输入数据
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID
            start_stage: 起始阶段
            stop_at_stage: 停止阶段（达到此阶段后暂停等待用户反馈）

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 创建工作流状态
            workflow_id = str(uuid.uuid4())
            project_id = project_id or f"{user_id}_{session_id}"

            state = WorkflowState(
                workflow_id=workflow_id,
                project_id=project_id,
                user_id=user_id,
                session_id=session_id,
                status=WorkflowStatus.IN_PROGRESS,
                current_stage=start_stage,
                input_data=input_data,
                config=self.config
            )

            # 保存初始状态
            await self.state_manager.save_state(state)
            self._running_states[workflow_id] = state

            # 🆕 发送工作流初始化事件
            init_event = await self._emit_event(
                workflow_id=workflow_id,
                node_name="workflow_init",
                status=NodeEventStatus.SUCCESS,
                output_snapshot=f"工作流初始化完成, 起始阶段: {start_stage.value}"
            )
            yield init_event

            yield {
                "type": "workflow_initialized",
                "message": "工作流初始化完成",
                "timestamp": datetime.now().isoformat(),
                "workflow_id": workflow_id,
                "project_id": project_id,
                "start_stage": start_stage.value
            }

            # 执行阶段序列
            current_stage = start_stage
            stages = self.STAGE_SEQUENCE[self.STAGE_SEQUENCE.index(current_stage):]

            for stage in stages:
                # 更新当前阶段
                state.current_stage = stage
                await self.state_manager.save_state(state)

                # 执行阶段
                async for event in self._execute_stage(state, stage):
                    yield event

                    # 检查是否需要暂停
                    if event.get("type") == "stage_waiting_for_user":
                        # 保存状态并暂停
                        state.status = WorkflowStatus.WAITING_FOR_USER
                        await self.state_manager.save_state(state)

                        # 如果指定了停止阶段，达到后停止
                        if stop_at_stage and stage == stop_at_stage:
                            yield {
                                "type": "workflow_paused",
                                "message": f"工作流已暂停，等待用户反馈",
                                "timestamp": datetime.now().isoformat(),
                                "workflow_id": workflow_id,
                                "current_stage": stage.value,
                                "awaiting_feedback": True
                            }
                            return

                        # 如果没有启用自动前进，暂停等待用户
                        if not self.config.get("enable_auto_advance", False):
                            yield {
                                "type": "workflow_paused",
                                "message": f"工作流已暂停，等待用户反馈",
                                "timestamp": datetime.now().isoformat(),
                                "workflow_id": workflow_id,
                                "current_stage": stage.value,
                                "awaiting_feedback": True
                            }
                            return

                    # 检查是否失败
                    if event.get("type") == "stage_failed":
                        state.status = WorkflowStatus.FAILED
                        state.completed_at = datetime.now().isoformat()
                        await self.state_manager.save_state(state)
                        return

            # 所有阶段完成
            state.status = WorkflowStatus.COMPLETED
            state.current_stage = WorkflowStage.COMPLETED
            state.completed_at = datetime.now().isoformat()
            await self.state_manager.save_state(state)

            # 🆕 发送工作流完成事件
            complete_event = await self._emit_event(
                workflow_id=workflow_id,
                node_name="workflow_complete",
                status=NodeEventStatus.SUCCESS,
                output_snapshot=f"工作流全部完成, 共完成 {len(state.stage_results)} 个阶段"
            )
            yield complete_event

            yield {
                "type": "workflow_completed",
                "message": "工作流执行完成",
                "timestamp": datetime.now().isoformat(),
                "workflow_id": workflow_id,
                "final_result": state.stage_results
            }

        except Exception as e:
            self.logger.error(f"工作流执行失败: {e}")
            # 🆕 发送工作流失败事件
            failed_event = await self._emit_event(
                workflow_id=state.workflow_id if 'state' in locals() else workflow_id,
                node_name="workflow_error",
                status=NodeEventStatus.FAILED,
                output_snapshot="",
                error=str(e)
            )
            yield failed_event

            yield {
                "type": "workflow_error",
                "message": f"工作流执行失败: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    async def _execute_stage(
        self,
        state: WorkflowState,
        stage: WorkflowStage
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行单个阶段

        Args:
            state: 工作流状态
            stage: 要执行的阶段

        Yields:
            Dict[str, Any]: 阶段事件
        """
        stage_result = StageResult(
            stage=stage,
            status=WorkflowStatus.IN_PROGRESS
        )

        # 获取节点名称
        node_name = self._get_node_name(stage)

        # 🆕 发送 waiting 状态事件
        waiting_event = await self._emit_event(
            workflow_id=state.workflow_id,
            node_name=node_name,
            status=NodeEventStatus.WAITING,
            output_snapshot=f"准备执行: {stage.value}"
        )
        yield waiting_event

        yield {
            "type": "stage_started",
            "message": f"开始执行阶段: {stage.value}",
            "timestamp": datetime.now().isoformat(),
            "stage": stage.value
        }

        # 🆕 发送 processing 状态事件
        processing_event = await self._emit_event(
            workflow_id=state.workflow_id,
            node_name=node_name,
            status=NodeEventStatus.PROCESSING,
            output_snapshot=f"正在执行: {stage.value}"
        )
        yield processing_event

        try:
            # 根据阶段类型执行不同逻辑
            if stage == WorkflowStage.INPUT_VALIDATION:
                await self._execute_input_validation(state, stage_result)
            elif stage == WorkflowStage.TEXT_PREPROCESSING:
                await self._execute_text_preprocessing(state, stage_result)
            elif stage == WorkflowStage.STORY_OUTLINE:
                await self._execute_story_outline(state, stage_result)
            elif stage == WorkflowStage.CHARACTER_PROFILES:
                await self._execute_character_profiles(state, stage_result)
            elif stage == WorkflowStage.MAJOR_PLOT_POINTS:
                await self._execute_major_plot_points(state, stage_result)
            elif stage == WorkflowStage.DETAILED_PLOT_POINTS:
                await self._execute_detailed_plot_points(state, stage_result)
            elif stage == WorkflowStage.MIND_MAP:
                await self._execute_mind_map(state, stage_result)
            elif stage == WorkflowStage.RESULT_FORMATTING:
                await self._execute_result_formatting(state, stage_result)
            else:
                stage_result.status = WorkflowStatus.COMPLETED
                stage_result.completed_at = datetime.now().isoformat()

            # 保存阶段结果
            stage_result.completed_at = datetime.now().isoformat()
            if stage_result.status == WorkflowStatus.IN_PROGRESS:
                stage_result.status = WorkflowStatus.COMPLETED

            state.stage_results[stage.value] = stage_result
            await self.state_manager.save_state(state)

            # 🆕 生成输出摘要
            output_snapshot = self._generate_output_snapshot(stage, stage_result.output)

            # 🆕 发送 success 状态事件
            success_event = await self._emit_event(
                workflow_id=state.workflow_id,
                node_name=node_name,
                status=NodeEventStatus.SUCCESS,
                output_snapshot=output_snapshot
            )
            yield success_event

            yield {
                "type": "stage_completed",
                "message": f"阶段完成: {stage.value}",
                "timestamp": datetime.now().isoformat(),
                "stage": stage.value,
                "output": stage_result.output
            }

            # 特殊处理：故事大纲阶段完成后，需要用户批准
            if stage == WorkflowStage.STORY_OUTLINE:
                yield {
                    "type": "need_approval",
                    "message": "故事大纲已生成，请审阅并提供反馈",
                    "timestamp": datetime.now().isoformat(),
                    "stage": stage.value,
                    "stage_output": stage_result.output,
                    "workflow_id": state.workflow_id,
                    "requires_approval": True,
                    "approval_message": "请审阅上述故事大纲，如需修改请提供反馈，或直接继续执行下一步"
                }
                # 故事大纲阶段总是暂停等待用户反馈
                yield {
                    "type": "stage_waiting_for_user",
                    "message": f"阶段 {stage.value} 已完成，等待用户反馈",
                    "timestamp": datetime.now().isoformat(),
                    "stage": stage.value,
                    "stage_output": stage_result.output,
                    "workflow_id": state.workflow_id
                }
                return  # 暂停执行

            # 如果不是最后阶段，发出等待用户反馈事件
            if stage != WorkflowStage.COMPLETED:
                yield {
                    "type": "stage_waiting_for_user",
                    "message": f"阶段 {stage.value} 已完成，等待用户反馈",
                    "timestamp": datetime.now().isoformat(),
                    "stage": stage.value,
                    "stage_output": stage_result.output,
                    "workflow_id": state.workflow_id
                }

        except Exception as e:
            stage_result.status = WorkflowStatus.FAILED
            stage_result.error = str(e)
            stage_result.completed_at = datetime.now().isoformat()
            state.stage_results[stage.value] = stage_result

            # 🆕 发送 failed 状态事件
            failed_event = await self._emit_event(
                workflow_id=state.workflow_id,
                node_name=node_name,
                status=NodeEventStatus.FAILED,
                output_snapshot="",
                error=str(e)
            )
            yield failed_event

            yield {
                "type": "stage_failed",
                "message": f"阶段执行失败: {stage.value}",
                "timestamp": datetime.now().isoformat(),
                "stage": stage.value,
                "error": str(e)
            }

    async def _execute_input_validation(self, state: WorkflowState, result: StageResult):
        """执行输入验证阶段"""
        required_params = ["input"]
        missing_params = [p for p in required_params if p not in state.input_data]

        if missing_params:
            raise ValueError(f"缺少必需参数: {', '.join(missing_params)}")

        # 更新配置
        state.config.update({
            "chunk_size": state.input_data.get("chunk_size", self.config["chunk_size"]),
            "length_size": state.input_data.get("length_size", self.config["length_size"]),
            "output_format": state.input_data.get("format", self.config["output_format"])
        })

        result.output = {
            "validated": True,
            "config": state.config
        }

    async def _execute_text_preprocessing(self, state: WorkflowState, result: StageResult):
        """执行文本预处理阶段"""
        if TextTruncatorAgent is None or TextSplitterAgent is None:
            # 跳过预处理
            result.output = {"chunks": [state.input_data["input"]]}
            return

        input_text = state.input_data["input"]
        length_size = state.config["length_size"]
        chunk_size = state.config["chunk_size"]

        # 文本截断
        from agents.text_truncator_agent import TextTruncator
        text_truncator = TextTruncator()
        truncated_text = await text_truncator.truncate_text(input_text, max_length=length_size)

        # 文本分割
        from agents.text_splitter_agent import TextSplitter
        text_splitter = TextSplitter()
        chunks = await text_splitter.split_text(truncated_text, chunk_size=chunk_size)

        result.output = {
            "original_length": len(input_text),
            "truncated_length": len(truncated_text),
            "chunks": chunks,
            "chunk_count": len(chunks)
        }

    async def _execute_story_outline(self, state: WorkflowState, result: StageResult):
        """执行故事大纲阶段"""
        agent = await self._get_agent("story_summary", StorySummaryGeneratorAgent)

        # 获取处理后的文本
        preprocessed = state.stage_results.get(WorkflowStage.TEXT_PREPROCESSING.value)
        if preprocessed:
            chunks = preprocessed.output.get("chunks", [])
            input_text = "\n".join(chunks)
        else:
            input_text = state.input_data["input"]

        # 注入之前的用户反馈
        input_text = await self._inject_user_feedback(state, input_text)

        content = await self._call_agent_stream(agent, {"input": input_text})

        result.output = {
            "story_outline": content,
            "type": "story_outline"
        }

    async def _execute_character_profiles(self, state: WorkflowState, result: StageResult):
        """执行人物小传阶段"""
        if CharacterProfileGeneratorAgent is None:
            result.output = {"message": "人物小传 Agent 不可用"}
            return

        agent = await self._get_agent("character_profiles", CharacterProfileGeneratorAgent)

        # 使用故事大纲作为输入
        outline_result = state.stage_results.get(WorkflowStage.STORY_OUTLINE.value)
        if outline_result:
            input_text = outline_result.output.get("story_outline", state.input_data["input"])
        else:
            input_text = state.input_data["input"]

        # 注入用户反馈
        input_text = await self._inject_user_feedback(state, input_text)

        content = await self._call_agent_stream(agent, {"input": input_text})

        result.output = {
            "character_profiles": content,
            "type": "character_profiles"
        }

    async def _execute_major_plot_points(self, state: WorkflowState, result: StageResult):
        """执行大情节点阶段"""
        agent = await self._get_agent("major_plot_points", MajorPlotPointsAgent)

        # 使用故事大纲作为输入
        outline_result = state.stage_results.get(WorkflowStage.STORY_OUTLINE.value)
        if outline_result:
            input_text = outline_result.output.get("story_outline", state.input_data["input"])
        else:
            input_text = state.input_data["input"]

        # 注入用户反馈和人物小传
        input_text = await self._inject_user_feedback(state, input_text)
        character_result = state.stage_results.get(WorkflowStage.CHARACTER_PROFILES.value)
        if character_result:
            input_text += f"\n\n人物小传:\n{character_result.output.get('character_profiles', '')}"

        content = await self._call_agent_stream(agent, {"input": input_text})

        result.output = {
            "major_plot_points": content,
            "type": "major_plot_points"
        }

    async def _execute_detailed_plot_points(self, state: WorkflowState, result: StageResult):
        """执行详细情节点阶段"""
        agent = await self._get_agent("detailed_plot_points", DetailedPlotPointsAgent)

        # 使用大情节点作为输入
        major_result = state.stage_results.get(WorkflowStage.MAJOR_PLOT_POINTS.value)
        if major_result:
            input_text = major_result.output.get("major_plot_points", state.input_data["input"])
        else:
            input_text = state.input_data["input"]

        # 注入用户反馈
        input_text = await self._inject_user_feedback(state, input_text)

        content = await self._call_agent_stream(agent, {"input": input_text})

        result.output = {
            "detailed_plot_points": content,
            "type": "detailed_plot_points"
        }

    async def _execute_mind_map(self, state: WorkflowState, result: StageResult):
        """执行思维导图阶段"""
        agent = await self._get_agent("mind_map", MindMapAgent)

        # 使用详细情节点作为输入
        detailed_result = state.stage_results.get(WorkflowStage.DETAILED_PLOT_POINTS.value)
        if detailed_result:
            input_text = detailed_result.output.get("detailed_plot_points", state.input_data["input"])
        else:
            input_text = state.input_data["input"]

        # 注入用户反馈
        input_text = await self._inject_user_feedback(state, input_text)

        output = {"pic": "", "jump_link": ""}
        async for event in agent.process_request({"input": input_text}):
            if event.get("type") == "mind_map_generated":
                result_data = event.get("result", {})
                output["pic"] = result_data.get("pic", "")
                output["jump_link"] = result_data.get("jump_link", "")

        result.output = {
            "mind_map": output,
            "type": "mind_map"
        }

    async def _execute_result_formatting(self, state: WorkflowState, result: StageResult):
        """执行结果格式化阶段"""
        agent = await self._get_agent("output_formatter", OutputFormatterAgent)

        # 整合所有阶段结果
        output_data = {
            "story_summary": state.stage_results.get(WorkflowStage.STORY_OUTLINE.value, {}).output.get("story_outline", ""),
            "character_profiles": state.stage_results.get(WorkflowStage.CHARACTER_PROFILES.value, {}).output.get("character_profiles", ""),
            "major_plot_points": state.stage_results.get(WorkflowStage.MAJOR_PLOT_POINTS.value, {}).output.get("major_plot_points", ""),
            "detailed_plot_points": state.stage_results.get(WorkflowStage.DETAILED_PLOT_POINTS.value, {}).output.get("detailed_plot_points", ""),
            "mind_map": state.stage_results.get(WorkflowStage.MIND_MAP.value, {}).output.get("mind_map", {}),
            "format": state.config.get("output_format", "markdown")
        }

        formatted_result = ""
        async for event in agent.process_request(output_data):
            if event.get("type") == "formatting_complete":
                formatted_result = event.get("formatted_output", "")

        result.output = {
            "formatted_output": formatted_result,
            "all_results": output_data,
            "type": "formatted_output"
        }

    async def _get_agent(self, name: str, agent_class):
        """获取或创建智能体"""
        async with self._sub_agents_lock:
            if name not in self.sub_agents:
                if agent_class is None:
                    raise ValueError(f"Agent {name} 不可用")
                self.sub_agents[name] = agent_class()
            return self.sub_agents[name]

    async def _call_agent_stream(self, agent, request_data: Dict[str, Any]) -> str:
        """调用智能体并收集流式输出"""
        content = ""
        async for event in agent.process_request(request_data):
            if event.get("type") == "content":
                content += event.get("content", "")
        return content

    async def _inject_user_feedback(self, state: WorkflowState, content: str) -> str:
        """注入用户反馈到内容中"""
        feedback_sections = []

        # 收集所有阶段的用户反馈
        for stage_name, stage_result in state.stage_results.items():
            if stage_result.user_feedback:
                feedback_sections.append(f"# {stage_name} 用户反馈\n{stage_result.user_feedback}")

        if feedback_sections:
            feedback_text = "\n\n".join(feedback_sections)
            return f"{content}\n\n--- 用户历史反馈 ---\n{feedback_text}"

        return content

    async def resume_workflow(
        self,
        workflow_id: str,
        user_feedback: str = None,
        auto_advance: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        恢复工作流执行

        Args:
            workflow_id: 工作流 ID
            user_feedback: 用户对当前阶段的反馈
            auto_advance: 是否自动进入下一阶段

        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 获取工作流状态
            state = await self.state_manager.get_state(workflow_id)
            if not state:
                yield {
                    "type": "workflow_error",
                    "message": f"工作流不存在: {workflow_id}",
                    "timestamp": datetime.now().isoformat()
                }
                return

            # 检查状态
            if state.status != WorkflowStatus.WAITING_FOR_USER and state.status != WorkflowStatus.IN_PROGRESS:
                yield {
                    "type": "workflow_error",
                    "message": f"工作流状态不允许恢复: {state.status.value}",
                    "timestamp": datetime.now().isoformat()
                }
                return

            # 更新配置
            if auto_advance:
                self.config["enable_auto_advance"] = True

            yield {
                "type": "workflow_resumed",
                "message": "工作流已恢复执行",
                "timestamp": datetime.now().isoformat(),
                "workflow_id": workflow_id,
                "current_stage": state.current_stage.value
            }

            # 处理用户反馈
            if user_feedback:
                current_stage_result = state.stage_results.get(state.current_stage.value)
                if current_stage_result:
                    current_stage_result.user_feedback = user_feedback
                    await self.state_manager.save_state(state)

                yield {
                    "type": "user_feedback_received",
                    "message": "用户反馈已接收",
                    "timestamp": datetime.now().isoformat(),
                    "feedback": user_feedback
                }

            # 获取下一阶段
            current_index = self.STAGE_SEQUENCE.index(state.current_stage)
            next_stage = self.STAGE_SEQUENCE[current_index + 1] if current_index + 1 < len(self.STAGE_SEQUENCE) else WorkflowStage.COMPLETED

            if next_stage == WorkflowStage.COMPLETED:
                # 工作流已完成
                state.status = WorkflowStatus.COMPLETED
                state.completed_at = datetime.now().isoformat()
                await self.state_manager.save_state(state)

                yield {
                    "type": "workflow_completed",
                    "message": "工作流已全部完成",
                    "timestamp": datetime.now().isoformat(),
                    "workflow_id": workflow_id,
                    "final_result": state.stage_results
                }
                return

            # 继续执行下一阶段
            state.status = WorkflowStatus.IN_PROGRESS
            await self.state_manager.save_state(state)

            # 执行后续阶段
            stages = self.STAGE_SEQUENCE[current_index + 1:]

            for stage in stages:
                # 更新当前阶段
                state.current_stage = stage
                await self.state_manager.save_state(state)

                # 执行阶段
                async for event in self._execute_stage(state, stage):
                    yield event

                    # 检查是否需要暂停
                    if event.get("type") == "stage_waiting_for_user":
                        state.status = WorkflowStatus.WAITING_FOR_USER
                        await self.state_manager.save_state(state)

                        if not self.config.get("enable_auto_advance", False):
                            yield {
                                "type": "workflow_paused",
                                "message": f"工作流已暂停，等待用户反馈",
                                "timestamp": datetime.now().isoformat(),
                                "workflow_id": workflow_id,
                                "current_stage": stage.value,
                                "awaiting_feedback": True
                            }
                            return

                    # 检查是否失败
                    if event.get("type") == "stage_failed":
                        state.status = WorkflowStatus.FAILED
                        state.completed_at = datetime.now().isoformat()
                        await self.state_manager.save_state(state)
                        return

            # 所有阶段完成
            state.status = WorkflowStatus.COMPLETED
            state.current_stage = WorkflowStage.COMPLETED
            state.completed_at = datetime.now().isoformat()
            await self.state_manager.save_state(state)

            yield {
                "type": "workflow_completed",
                "message": "工作流执行完成",
                "timestamp": datetime.now().isoformat(),
                "workflow_id": workflow_id,
                "final_result": state.stage_results
            }

        except Exception as e:
            self.logger.error(f"恢复工作流失败: {e}")
            yield {
                "type": "workflow_error",
                "message": f"恢复工作流失败: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流状态

        Args:
            workflow_id: 工作流 ID

        Returns:
            Optional[Dict]: 工作流状态信息
        """
        state = await self.state_manager.get_state(workflow_id)
        if state:
            return {
                "workflow_id": state.workflow_id,
                "project_id": state.project_id,
                "user_id": state.user_id,
                "status": state.status.value,
                "current_stage": state.current_stage.value,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "completed_at": state.completed_at,
                "stage_results": {
                    k: {
                        "stage": v.stage.value,
                        "status": v.status.value,
                        "has_output": bool(v.output),
                        "has_feedback": bool(v.user_feedback),
                        "completed_at": v.completed_at
                    }
                    for k, v in state.stage_results.items()
                }
            }
        return None

    async def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流执行进度

        返回详细的进度信息，包括：
        - 当前阶段和阶段索引（Step Index）
        - 总阶段数和进度百分比
        - 已完成的阶段列表
        - 是否可以恢复
        - 是否等待用户反馈

        Args:
            workflow_id: 工作流 ID

        Returns:
            Optional[Dict]: 进度信息
        """
        return await self.state_manager.get_workflow_progress(workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        取消工作流

        Args:
            workflow_id: 工作流 ID

        Returns:
            bool: 是否成功
        """
        state = await self.state_manager.get_state(workflow_id)
        if state and state.status in [WorkflowStatus.IN_PROGRESS, WorkflowStatus.WAITING_FOR_USER]:
            state.status = WorkflowStatus.CANCELLED
            state.completed_at = datetime.now().isoformat()
            await self.state_manager.save_state(state)

            # 从内存中移除
            if workflow_id in self._running_states:
                del self._running_states[workflow_id]

            return True
        return False

    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        删除工作流

        Args:
            workflow_id: 工作流 ID

        Returns:
            bool: 是否成功
        """
        success = await self.state_manager.delete_state(workflow_id)

        if workflow_id in self._running_states:
            del self._running_states[workflow_id]

        return success


# ==================== 工作流工厂函数 ====================

# 全局实例
_workflow_instance: Optional[InteractivePlotPointsWorkflow] = None


def get_interactive_workflow() -> InteractivePlotPointsWorkflow:
    """获取交互式工作流实例（单例模式）"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = InteractivePlotPointsWorkflow()
    return _workflow_instance


# ==================== 兼容性保留 ====================

class PlotPointsWorkflowOrchestrator(InteractivePlotPointsWorkflow):
    """
    兼容性包装器

    保留原有类名和接口，内部使用新的交互式工作流
    """

    def __init__(self):
        super().__init__()
        # 保留原有属性
        self.workflow_agent = None
        self.workflow_state = {}

    async def execute_workflow(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        兼容性方法：执行完整工作流（不暂停）

        如果需要分阶段交互，请直接使用 InteractivePlotPointsWorkflow
        """
        user_id = input_data.get("user_id", "unknown")
        session_id = input_data.get("session_id", "unknown")
        project_id = input_data.get("project_id", f"{user_id}_{session_id}")

        # 启用自动前进模式
        self.config["enable_auto_advance"] = True

        async for event in super().execute_workflow(
            input_data=input_data,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            stop_at_stage=None
        ):
            # 转换事件格式以兼容旧接口
            if event.get("type") == "stage_completed":
                yield {
                    "type": "agent_complete",
                    "message": f"阶段完成: {event.get('stage')}",
                    "timestamp": event.get("timestamp")
                }
            elif event.get("type") == "workflow_completed":
                yield {
                    "type": "workflow_complete",
                    "message": "大情节点与详细情节点生成工作流执行完成",
                    "timestamp": event.get("timestamp"),
                    "final_result": event.get("final_result")
                }
            else:
                yield event

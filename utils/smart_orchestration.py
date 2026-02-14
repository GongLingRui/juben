"""
智能协调系统 -  
提供智能协调、任务调度、工作流管理和系统协调
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path
import uuid

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStatus(Enum):
    """工作流状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CoordinationStrategy(Enum):
    """协调策略"""
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"          # 并行执行
    CONDITIONAL = "conditional"    # 条件执行
    LOOP = "loop"                  # 循环执行
    BRANCH = "branch"              # 分支执行


@dataclass
class Task:
    """任务"""
    task_id: str
    name: str
    description: str
    function: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300  # 5分钟
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    name: str
    task_id: str
    condition: Optional[Callable] = None
    timeout: int = 300
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    parallel: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """工作流"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    strategy: CoordinationStrategy = CoordinationStrategy.SEQUENTIAL
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationPlan:
    """协调计划"""
    plan_id: str
    name: str
    description: str
    workflows: List[str]
    schedule: Optional[Dict[str, Any]] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SmartOrchestration:
    """智能协调系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_orchestration")
        
        # 协调配置
        self.orchestration_enabled = True
        self.max_concurrent_tasks = 10
        self.task_timeout = 300  # 5分钟
        self.workflow_timeout = 3600  # 1小时
        self.retry_delay = 5  # 5秒
        self.max_retries = 3
        
        # 任务存储
        self.tasks: Dict[str, Task] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.coordination_plans: Dict[str, CoordinationPlan] = {}
        
        # 任务执行
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue: List[str] = []
        self.workflow_queue: List[str] = []
        
        # 协调监控
        self.monitoring_enabled = True
        self.performance_metrics: Dict[str, Any] = {}
        
        # 协调任务
        self.orchestration_tasks: List[asyncio.Task] = []
        
        # 协调回调
        self.task_callbacks: List[Callable] = []
        self.workflow_callbacks: List[Callable] = []
        self.coordination_callbacks: List[Callable] = []
        
        # 协调统计
        self.orchestration_stats: Dict[str, Any] = {}
        
        self.logger.info("🎭 智能协调系统初始化完成")
    
    async def initialize(self):
        """初始化协调系统"""
        try:
            # 启动协调任务
            if self.orchestration_enabled:
                await self._start_orchestration_tasks()
            
            # 启动监控
            if self.monitoring_enabled:
                await self._start_monitoring()
            
            self.logger.info("✅ 智能协调系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化协调系统失败: {e}")
    
    async def _start_orchestration_tasks(self):
        """启动协调任务"""
        try:
            # 启动任务调度任务
            task = asyncio.create_task(self._task_scheduler_task())
            self.orchestration_tasks.append(task)
            
            # 启动工作流执行任务
            task = asyncio.create_task(self._workflow_executor_task())
            self.orchestration_tasks.append(task)
            
            # 启动协调计划任务
            task = asyncio.create_task(self._coordination_planner_task())
            self.orchestration_tasks.append(task)
            
            self.logger.info("✅ 协调任务已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动协调任务失败: {e}")
    
    async def _start_monitoring(self):
        """启动监控"""
        try:
            # 启动性能监控任务
            task = asyncio.create_task(self._performance_monitoring_task())
            self.orchestration_tasks.append(task)
            
            # 启动健康检查任务
            task = asyncio.create_task(self._health_check_task())
            self.orchestration_tasks.append(task)
            
            self.logger.info("✅ 监控已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动监控失败: {e}")
    
    async def _task_scheduler_task(self):
        """任务调度任务"""
        try:
            while True:
                await asyncio.sleep(0.1)  # 每100ms检查一次
                
                # 处理任务队列
                if self.task_queue:
                    task_id = self.task_queue.pop(0)
                    await self._execute_task(task_id)
                
        except asyncio.CancelledError:
            self.logger.info("📋 任务调度任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 任务调度任务失败: {e}")
    
    async def _workflow_executor_task(self):
        """工作流执行任务"""
        try:
            while True:
                await asyncio.sleep(1)  # 每秒检查一次
                
                # 处理工作流队列
                if self.workflow_queue:
                    workflow_id = self.workflow_queue.pop(0)
                    await self._execute_workflow(workflow_id)
                
        except asyncio.CancelledError:
            self.logger.info("🔄 工作流执行任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 工作流执行任务失败: {e}")
    
    async def _coordination_planner_task(self):
        """协调计划任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 检查协调计划
                await self._check_coordination_plans()
                
        except asyncio.CancelledError:
            self.logger.info("📅 协调计划任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 协调计划任务失败: {e}")
    
    async def _performance_monitoring_task(self):
        """性能监控任务"""
        try:
            while True:
                await asyncio.sleep(300)  # 每5分钟检查一次
                
                # 监控性能
                await self._monitor_performance()
                
        except asyncio.CancelledError:
            self.logger.info("📊 性能监控任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 性能监控任务失败: {e}")
    
    async def _health_check_task(self):
        """健康检查任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 检查系统健康状态
                await self._check_system_health()
                
        except asyncio.CancelledError:
            self.logger.info("🏥 健康检查任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 健康检查任务失败: {e}")
    
    async def _execute_task(self, task_id: str):
        """执行任务"""
        try:
            if task_id not in self.tasks:
                self.logger.error(f"❌ 任务不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            
            # 检查依赖
            if not await self._check_task_dependencies(task):
                # 依赖未满足，重新加入队列
                self.task_queue.append(task_id)
                return
            
            # 检查并发限制
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                # 并发限制，重新加入队列
                self.task_queue.append(task_id)
                return
            
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # 创建异步任务
            async_task = asyncio.create_task(self._run_task(task))
            self.running_tasks[task_id] = async_task
            
            # 等待任务完成
            try:
                await async_task
            except Exception as e:
                self.logger.error(f"❌ 任务执行失败: {task_id} - {e}")
            
            # 从运行中移除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
        except Exception as e:
            self.logger.error(f"❌ 执行任务失败: {e}")
    
    async def _run_task(self, task: Task):
        """运行任务"""
        try:
            # 执行任务函数
            result = await asyncio.wait_for(
                task.function(*task.args, **task.kwargs),
                timeout=task.timeout
            )
            
            # 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            
            # 触发任务回调
            await self._trigger_task_callbacks(task)
            
            self.logger.info(f"✅ 任务完成: {task.name}")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = f"任务超时: {task.timeout}秒"
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                task.started_at = None
                task.completed_at = None
                task.error = None
                
                # 延迟后重新加入队列
                await asyncio.sleep(self.retry_delay)
                self.task_queue.append(task.task_id)
                
                self.logger.info(f"🔄 任务重试: {task.name} ({task.retry_count}/{task.max_retries})")
            else:
                self.logger.error(f"❌ 任务失败: {task.name} - 超时")
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                task.started_at = None
                task.completed_at = None
                task.error = None
                
                # 延迟后重新加入队列
                await asyncio.sleep(self.retry_delay)
                self.task_queue.append(task.task_id)
                
                self.logger.info(f"🔄 任务重试: {task.name} ({task.retry_count}/{task.max_retries})")
            else:
                self.logger.error(f"❌ 任务失败: {task.name} - {e}")
    
    async def _check_task_dependencies(self, task: Task) -> bool:
        """检查任务依赖"""
        try:
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    return False
                
                dep_task = self.tasks[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 检查任务依赖失败: {e}")
            return False
    
    async def _execute_workflow(self, workflow_id: str):
        """执行工作流"""
        try:
            if workflow_id not in self.workflows:
                self.logger.error(f"❌ 工作流不存在: {workflow_id}")
                return
            
            workflow = self.workflows[workflow_id]
            
            # 更新工作流状态
            workflow.status = WorkflowStatus.ACTIVE
            workflow.started_at = datetime.now()
            
            try:
                # 根据策略执行工作流
                if workflow.strategy == CoordinationStrategy.SEQUENTIAL:
                    await self._execute_sequential_workflow(workflow)
                elif workflow.strategy == CoordinationStrategy.PARALLEL:
                    await self._execute_parallel_workflow(workflow)
                elif workflow.strategy == CoordinationStrategy.CONDITIONAL:
                    await self._execute_conditional_workflow(workflow)
                elif workflow.strategy == CoordinationStrategy.LOOP:
                    await self._execute_loop_workflow(workflow)
                elif workflow.strategy == CoordinationStrategy.BRANCH:
                    await self._execute_branch_workflow(workflow)
                
                # 更新工作流状态
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                
                # 触发工作流回调
                await self._trigger_workflow_callbacks(workflow)
                
                self.logger.info(f"✅ 工作流完成: {workflow.name}")
                
            except Exception as e:
                workflow.status = WorkflowStatus.FAILED
                workflow.completed_at = datetime.now()
                self.logger.error(f"❌ 工作流失败: {workflow.name} - {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 执行工作流失败: {e}")
    
    async def _execute_sequential_workflow(self, workflow: Workflow):
        """执行顺序工作流"""
        try:
            for step in workflow.steps:
                # 检查步骤条件
                if step.condition and not step.condition():
                    continue
                
                # 执行步骤任务
                if step.task_id in self.tasks:
                    task = self.tasks[step.task_id]
                    
                    # 添加到任务队列
                    if task.status == TaskStatus.PENDING:
                        self.task_queue.append(task.task_id)
                    
                    # 等待任务完成
                    while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]:
                        await asyncio.sleep(0.1)
                    
                    # 检查任务结果
                    if task.status == TaskStatus.FAILED:
                        raise Exception(f"步骤失败: {step.name}")
                
        except Exception as e:
            self.logger.error(f"❌ 执行顺序工作流失败: {e}")
            raise e
    
    async def _execute_parallel_workflow(self, workflow: Workflow):
        """执行并行工作流"""
        try:
            # 创建并行任务
            parallel_tasks = []
            
            for step in workflow.steps:
                # 检查步骤条件
                if step.condition and not step.condition():
                    continue
                
                # 创建步骤任务
                if step.task_id in self.tasks:
                    task = self.tasks[step.task_id]
                    
                    if task.status == TaskStatus.PENDING:
                        async_task = asyncio.create_task(self._run_task(task))
                        parallel_tasks.append(async_task)
            
            # 等待所有任务完成
            if parallel_tasks:
                await asyncio.gather(*parallel_tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"❌ 执行并行工作流失败: {e}")
            raise e
    
    async def _execute_conditional_workflow(self, workflow: Workflow):
        """执行条件工作流"""
        try:
            for step in workflow.steps:
                # 检查步骤条件
                if step.condition and not step.condition():
                    continue
                
                # 执行步骤任务
                if step.task_id in self.tasks:
                    task = self.tasks[step.task_id]
                    
                    # 添加到任务队列
                    if task.status == TaskStatus.PENDING:
                        self.task_queue.append(task.task_id)
                    
                    # 等待任务完成
                    while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]:
                        await asyncio.sleep(0.1)
                    
                    # 检查任务结果
                    if task.status == TaskStatus.FAILED:
                        raise Exception(f"步骤失败: {step.name}")
                
        except Exception as e:
            self.logger.error(f"❌ 执行条件工作流失败: {e}")
            raise e
    
    async def _execute_loop_workflow(self, workflow: Workflow):
        """执行循环工作流"""
        try:
            # 循环执行工作流步骤
            max_iterations = workflow.metadata.get('max_iterations', 10)
            
            for iteration in range(max_iterations):
                for step in workflow.steps:
                    # 检查步骤条件
                    if step.condition and not step.condition():
                        continue
                    
                    # 执行步骤任务
                    if step.task_id in self.tasks:
                        task = self.tasks[step.task_id]
                        
                        # 重置任务状态
                        task.status = TaskStatus.PENDING
                        task.started_at = None
                        task.completed_at = None
                        task.result = None
                        task.error = None
                        
                        # 添加到任务队列
                        self.task_queue.append(task.task_id)
                        
                        # 等待任务完成
                        while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]:
                            await asyncio.sleep(0.1)
                        
                        # 检查任务结果
                        if task.status == TaskStatus.FAILED:
                            raise Exception(f"步骤失败: {step.name}")
                
        except Exception as e:
            self.logger.error(f"❌ 执行循环工作流失败: {e}")
            raise e
    
    async def _execute_branch_workflow(self, workflow: Workflow):
        """执行分支工作流"""
        try:
            # 根据条件选择分支
            branch_condition = workflow.metadata.get('branch_condition')
            
            if branch_condition:
                # 执行条件分支
                for step in workflow.steps:
                    if step.condition and step.condition():
                        # 执行步骤任务
                        if step.task_id in self.tasks:
                            task = self.tasks[step.task_id]
                            
                            # 添加到任务队列
                            if task.status == TaskStatus.PENDING:
                                self.task_queue.append(task.task_id)
                            
                            # 等待任务完成
                            while task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]:
                                await asyncio.sleep(0.1)
                            
                            # 检查任务结果
                            if task.status == TaskStatus.FAILED:
                                raise Exception(f"步骤失败: {step.name}")
            else:
                # 执行默认分支
                await self._execute_sequential_workflow(workflow)
                
        except Exception as e:
            self.logger.error(f"❌ 执行分支工作流失败: {e}")
            raise e
    
    async def _check_coordination_plans(self):
        """检查协调计划"""
        try:
            current_time = datetime.now()
            
            for plan_id, plan in self.coordination_plans.items():
                if not plan.enabled:
                    continue
                
                # 检查是否到了执行时间
                if plan.next_run and current_time >= plan.next_run:
                    # 执行协调计划
                    await self._execute_coordination_plan(plan)
                    
                    # 更新下次执行时间
                    if plan.schedule:
                        plan.last_run = current_time
                        plan.next_run = self._calculate_next_run(plan.schedule, current_time)
                
        except Exception as e:
            self.logger.error(f"❌ 检查协调计划失败: {e}")
    
    async def _execute_coordination_plan(self, plan: CoordinationPlan):
        """执行协调计划"""
        try:
            self.logger.info(f"📅 执行协调计划: {plan.name}")
            
            # 执行工作流
            for workflow_id in plan.workflows:
                if workflow_id in self.workflows:
                    workflow = self.workflows[workflow_id]
                    
                    # 添加到工作流队列
                    if workflow.status == WorkflowStatus.DRAFT:
                        self.workflow_queue.append(workflow_id)
            
            # 触发协调回调
            await self._trigger_coordination_callbacks(plan)
            
        except Exception as e:
            self.logger.error(f"❌ 执行协调计划失败: {e}")
    
    def _calculate_next_run(self, schedule: Dict[str, Any], current_time: datetime) -> datetime:
        """计算下次执行时间"""
        try:
            # 简单的调度逻辑
            interval = schedule.get('interval', 3600)  # 默认1小时
            return current_time + timedelta(seconds=interval)
            
        except Exception as e:
            self.logger.error(f"❌ 计算下次执行时间失败: {e}")
            return current_time + timedelta(hours=1)
    
    async def _monitor_performance(self):
        """监控性能"""
        try:
            # 计算性能指标
            total_tasks = len(self.tasks)
            completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
            failed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
            running_tasks = len(self.running_tasks)
            
            # 计算成功率
            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # 计算平均执行时间
            completed_task_times = []
            for task in self.tasks.values():
                if task.status == TaskStatus.COMPLETED and task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    completed_task_times.append(duration)
            
            avg_execution_time = sum(completed_task_times) / len(completed_task_times) if completed_task_times else 0
            
            # 更新性能指标
            self.performance_metrics = {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'running_tasks': running_tasks,
                'success_rate': success_rate,
                'avg_execution_time': avg_execution_time,
                'task_queue': len(self.task_queue),
                'workflow_queue': len(self.workflow_queue),
                'total_workflows': len(self.workflows),
                'active_workflows': len([w for w in self.workflows.values() if w.status == WorkflowStatus.ACTIVE]),
                'total_plans': len(self.coordination_plans),
                'active_plans': len([p for p in self.coordination_plans.values() if p.enabled])
            }
            
        except Exception as e:
            self.logger.error(f"❌ 监控性能失败: {e}")
    
    async def _check_system_health(self):
        """检查系统健康状态"""
        try:
            # 检查任务队列长度
            if len(self.task_queue) > 100:
                self.logger.warning("⚠️ 任务队列过长")
            
            # 检查运行中任务数量
            if len(self.running_tasks) > self.max_concurrent_tasks:
                self.logger.warning("⚠️ 运行中任务数量超过限制")
            
            # 检查失败任务数量
            failed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
            if failed_tasks > 10:
                self.logger.warning(f"⚠️ 失败任务数量过多: {failed_tasks}")
            
        except Exception as e:
            self.logger.error(f"❌ 检查系统健康状态失败: {e}")
    
    async def _trigger_task_callbacks(self, task: Task):
        """触发任务回调"""
        try:
            for callback in self.task_callbacks:
                try:
                    await callback(task)
                except Exception as e:
                    self.logger.error(f"❌ 任务回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发任务回调失败: {e}")
    
    async def _trigger_workflow_callbacks(self, workflow: Workflow):
        """触发工作流回调"""
        try:
            for callback in self.workflow_callbacks:
                try:
                    await callback(workflow)
                except Exception as e:
                    self.logger.error(f"❌ 工作流回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发工作流回调失败: {e}")
    
    async def _trigger_coordination_callbacks(self, plan: CoordinationPlan):
        """触发协调回调"""
        try:
            for callback in self.coordination_callbacks:
                try:
                    await callback(plan)
                except Exception as e:
                    self.logger.error(f"❌ 协调回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发协调回调失败: {e}")
    
    def register_task(
        self,
        name: str,
        description: str,
        function: Callable,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = 300,
        max_retries: int = 3,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """注册任务"""
        try:
            task_id = str(uuid.uuid4())
            
            task = Task(
                task_id=task_id,
                name=name,
                description=description,
                function=function,
                args=args,
                kwargs=kwargs or {},
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            self.tasks[task_id] = task
            
            self.logger.info(f"✅ 任务已注册: {name}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"❌ 注册任务失败: {e}")
            return ""
    
    def register_workflow(
        self,
        name: str,
        description: str,
        steps: List[WorkflowStep],
        strategy: CoordinationStrategy = CoordinationStrategy.SEQUENTIAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """注册工作流"""
        try:
            workflow_id = str(uuid.uuid4())
            
            workflow = Workflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                steps=steps,
                strategy=strategy,
                metadata=metadata or {}
            )
            
            self.workflows[workflow_id] = workflow
            
            self.logger.info(f"✅ 工作流已注册: {name}")
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"❌ 注册工作流失败: {e}")
            return ""
    
    def register_coordination_plan(
        self,
        name: str,
        description: str,
        workflows: List[str],
        schedule: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """注册协调计划"""
        try:
            plan_id = str(uuid.uuid4())
            
            plan = CoordinationPlan(
                plan_id=plan_id,
                name=name,
                description=description,
                workflows=workflows,
                schedule=schedule,
                enabled=enabled,
                metadata=metadata or {}
            )
            
            # 计算下次执行时间
            if schedule:
                plan.next_run = self._calculate_next_run(schedule, datetime.now())
            
            self.coordination_plans[plan_id] = plan
            
            self.logger.info(f"✅ 协调计划已注册: {name}")
            return plan_id
            
        except Exception as e:
            self.logger.error(f"❌ 注册协调计划失败: {e}")
            return ""
    
    async def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        try:
            if task_id not in self.tasks:
                raise ValueError(f"任务不存在: {task_id}")
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.PENDING:
                raise ValueError(f"任务状态不正确: {task.status}")
            
            # 添加到任务队列
            self.task_queue.append(task_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 执行任务失败: {e}")
            return False
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """执行工作流"""
        try:
            if workflow_id not in self.workflows:
                raise ValueError(f"工作流不存在: {workflow_id}")
            
            workflow = self.workflows[workflow_id]
            
            if workflow.status != WorkflowStatus.DRAFT:
                raise ValueError(f"工作流状态不正确: {workflow.status}")
            
            # 添加到工作流队列
            self.workflow_queue.append(workflow_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 执行工作流失败: {e}")
            return False
    
    def add_task_callback(self, callback: Callable):
        """添加任务回调"""
        try:
            self.task_callbacks.append(callback)
            self.logger.info("✅ 任务回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加任务回调失败: {e}")
    
    def add_workflow_callback(self, callback: Callable):
        """添加工作流回调"""
        try:
            self.workflow_callbacks.append(callback)
            self.logger.info("✅ 工作流回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加工作流回调失败: {e}")
    
    def add_coordination_callback(self, callback: Callable):
        """添加协调回调"""
        try:
            self.coordination_callbacks.append(callback)
            self.logger.info("✅ 协调回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加协调回调失败: {e}")
    
    def get_orchestration_stats(self) -> Dict[str, Any]:
        """获取协调统计"""
        try:
            return {
                'total_tasks': len(self.tasks),
                'total_workflows': len(self.workflows),
                'total_plans': len(self.coordination_plans),
                'running_tasks': len(self.running_tasks),
                'task_queue': len(self.task_queue),
                'workflow_queue': len(self.workflow_queue),
                'orchestration_enabled': self.orchestration_enabled,
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'task_timeout': self.task_timeout,
                'workflow_timeout': self.workflow_timeout,
                'retry_delay': self.retry_delay,
                'max_retries': self.max_retries,
                'monitoring_enabled': self.monitoring_enabled,
                'orchestration_tasks': len(self.orchestration_tasks),
                'performance_metrics': self.performance_metrics
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取协调统计失败: {e}")
            return {'error': str(e)}


# 全局智能协调实例
smart_orchestration = SmartOrchestration()


def get_smart_orchestration() -> SmartOrchestration:
    """获取智能协调实例"""
    return smart_orchestration

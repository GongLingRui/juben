"""
智能部署系统 -  
提供智能部署、版本管理、回滚和监控
"""
import asyncio
import json
import time
import subprocess
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import shutil
import os
from pathlib import Path

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


class DeploymentStatus(Enum):
    """部署状态"""
    PENDING = "pending"
    PREPARING = "preparing"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class DeploymentType(Enum):
    """部署类型"""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"


class Environment(Enum):
    """环境"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DeploymentConfig:
    """部署配置"""
    name: str
    version: str
    environment: Environment
    deployment_type: DeploymentType
    image_tag: str
    replicas: int = 1
    resources: Dict[str, Any] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    health_check: Dict[str, Any] = field(default_factory=dict)
    rollback_enabled: bool = True
    auto_rollback: bool = True
    rollback_threshold: float = 0.8


@dataclass
class Deployment:
    """部署"""
    deployment_id: str
    config: DeploymentConfig
    status: DeploymentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    previous_deployment_id: Optional[str] = None


@dataclass
class DeploymentMetrics:
    """部署指标"""
    deployment_id: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    response_time: float
    error_rate: float
    throughput: float
    active_connections: int


class SmartDeployment:
    """智能部署系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_deployment")
        
        # 部署配置
        self.deployment_enabled = True
        self.auto_deployment = False
        self.health_check_interval = 30  # 秒
        self.rollback_timeout = 300  # 秒
        self.max_deployments = 10
        
        # 部署存储
        self.deployments: Dict[str, Deployment] = {}
        self.deployment_configs: Dict[str, DeploymentConfig] = {}
        self.deployment_metrics: List[DeploymentMetrics] = []
        
        # 版本管理
        self.current_version: Optional[str] = None
        self.version_history: List[str] = []
        self.rollback_versions: List[str] = []
        
        # 环境管理
        self.environments: Dict[Environment, Dict[str, Any]] = {
            Environment.DEVELOPMENT: {
                'url': 'http://localhost:8000',
                'health_endpoint': '/health',
                'deployment_path': '/tmp/juben_dev'
            },
            Environment.STAGING: {
                'url': 'http://staging.juben.ai',
                'health_endpoint': '/health',
                'deployment_path': '/opt/juben_staging'
            },
            Environment.PRODUCTION: {
                'url': 'http://juben.ai',
                'health_endpoint': '/health',
                'deployment_path': '/opt/juben_prod'
            }
        }
        
        # 部署监控
        self.monitoring_enabled = True
        self.alert_thresholds: Dict[str, float] = {
            'cpu_usage': 80.0,
            'memory_usage': 80.0,
            'response_time': 5.0,
            'error_rate': 10.0
        }
        
        # 部署回调
        self.deployment_callbacks: List[Callable] = []
        self.rollback_callbacks: List[Callable] = []
        self.health_check_callbacks: List[Callable] = []
        
        # 部署统计
        self.deployment_stats: Dict[str, Any] = {}
        
        self.logger.info("🚀 智能部署系统初始化完成")
    
    async def initialize(self):
        """初始化部署系统"""
        try:
            # 创建部署目录
            await self._create_deployment_directories()
            
            # 启动部署监控
            if self.monitoring_enabled:
                await self._start_deployment_monitoring()
            
            # 启动健康检查
            await self._start_health_checks()
            
            self.logger.info("✅ 智能部署系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化部署系统失败: {e}")
    
    async def _create_deployment_directories(self):
        """创建部署目录"""
        try:
            for env, config in self.environments.items():
                deployment_path = config['deployment_path']
                Path(deployment_path).mkdir(parents=True, exist_ok=True)
                
                # 创建版本目录
                versions_path = Path(deployment_path) / 'versions'
                versions_path.mkdir(exist_ok=True)
                
                # 创建日志目录
                logs_path = Path(deployment_path) / 'logs'
                logs_path.mkdir(exist_ok=True)
                
                self.logger.info(f"✅ 部署目录已创建: {env.value} - {deployment_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 创建部署目录失败: {e}")
    
    async def _start_deployment_monitoring(self):
        """启动部署监控"""
        try:
            # 启动指标收集任务
            task = asyncio.create_task(self._metrics_collection_task())
            asyncio.create_task(task)
            
            # 启动告警检查任务
            task = asyncio.create_task(self._alert_check_task())
            asyncio.create_task(task)
            
            self.logger.info("✅ 部署监控已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动部署监控失败: {e}")
    
    async def _start_health_checks(self):
        """启动健康检查"""
        try:
            # 启动健康检查任务
            task = asyncio.create_task(self._health_check_task())
            asyncio.create_task(task)
            
            self.logger.info("✅ 健康检查已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动健康检查失败: {e}")
    
    async def _metrics_collection_task(self):
        """指标收集任务"""
        try:
            while True:
                await asyncio.sleep(self.health_check_interval)
                
                # 收集部署指标
                await self._collect_deployment_metrics()
                
        except asyncio.CancelledError:
            self.logger.info("📊 指标收集任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 指标收集任务失败: {e}")
    
    async def _alert_check_task(self):
        """告警检查任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 检查告警阈值
                await self._check_alert_thresholds()
                
        except asyncio.CancelledError:
            self.logger.info("🚨 告警检查任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 告警检查任务失败: {e}")
    
    async def _health_check_task(self):
        """健康检查任务"""
        try:
            while True:
                await asyncio.sleep(self.health_check_interval)
                
                # 检查所有部署的健康状态
                await self._check_deployment_health()
                
        except asyncio.CancelledError:
            self.logger.info("🏥 健康检查任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 健康检查任务失败: {e}")
    
    async def _collect_deployment_metrics(self):
        """收集部署指标"""
        try:
            for deployment_id, deployment in self.deployments.items():
                if deployment.status == DeploymentStatus.DEPLOYED:
                    # 收集指标
                    metrics = await self._get_deployment_metrics(deployment)
                    
                    if metrics:
                        self.deployment_metrics.append(metrics)
                        
                        # 更新部署指标
                        deployment.metrics = {
                            'cpu_usage': metrics.cpu_usage,
                            'memory_usage': metrics.memory_usage,
                            'response_time': metrics.response_time,
                            'error_rate': metrics.error_rate,
                            'throughput': metrics.throughput,
                            'active_connections': metrics.active_connections
                        }
            
        except Exception as e:
            self.logger.error(f"❌ 收集部署指标失败: {e}")
    
    async def _get_deployment_metrics(self, deployment: Deployment) -> Optional[DeploymentMetrics]:
        """获取部署指标"""
        try:
            # 这里应该从实际的监控系统获取指标
            # 为了演示，我们生成一些模拟数据
            import random
            
            metrics = DeploymentMetrics(
                deployment_id=deployment.deployment_id,
                timestamp=datetime.now(),
                cpu_usage=random.uniform(10, 80),
                memory_usage=random.uniform(20, 70),
                response_time=random.uniform(0.1, 2.0),
                error_rate=random.uniform(0, 5),
                throughput=random.uniform(100, 1000),
                active_connections=random.randint(10, 100)
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ 获取部署指标失败: {e}")
            return None
    
    async def _check_alert_thresholds(self):
        """检查告警阈值"""
        try:
            for deployment_id, deployment in self.deployments.items():
                if deployment.status == DeploymentStatus.DEPLOYED:
                    metrics = deployment.metrics
                    
                    if not metrics:
                        continue
                    
                    # 检查CPU使用率
                    if metrics.get('cpu_usage', 0) > self.alert_thresholds['cpu_usage']:
                        await self._trigger_alert(deployment_id, 'cpu_usage', metrics['cpu_usage'])
                    
                    # 检查内存使用率
                    if metrics.get('memory_usage', 0) > self.alert_thresholds['memory_usage']:
                        await self._trigger_alert(deployment_id, 'memory_usage', metrics['memory_usage'])
                    
                    # 检查响应时间
                    if metrics.get('response_time', 0) > self.alert_thresholds['response_time']:
                        await self._trigger_alert(deployment_id, 'response_time', metrics['response_time'])
                    
                    # 检查错误率
                    if metrics.get('error_rate', 0) > self.alert_thresholds['error_rate']:
                        await self._trigger_alert(deployment_id, 'error_rate', metrics['error_rate'])
            
        except Exception as e:
            self.logger.error(f"❌ 检查告警阈值失败: {e}")
    
    async def _trigger_alert(self, deployment_id: str, metric_name: str, value: float):
        """触发告警"""
        try:
            alert_message = f"部署告警: {deployment_id} - {metric_name}: {value}"
            
            # 触发告警回调
            for callback in self.health_check_callbacks:
                try:
                    await callback(deployment_id, metric_name, value, alert_message)
                except Exception as e:
                    self.logger.error(f"❌ 告警回调执行失败: {e}")
            
            self.logger.warning(f"🚨 {alert_message}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发告警失败: {e}")
    
    async def _check_deployment_health(self):
        """检查部署健康状态"""
        try:
            for deployment_id, deployment in self.deployments.items():
                if deployment.status == DeploymentStatus.DEPLOYED:
                    # 检查健康状态
                    is_healthy = await self._is_deployment_healthy(deployment)
                    
                    if not is_healthy:
                        # 如果启用了自动回滚，则执行回滚
                        if deployment.config.auto_rollback:
                            await self.rollback_deployment(deployment_id)
            
        except Exception as e:
            self.logger.error(f"❌ 检查部署健康状态失败: {e}")
    
    async def _is_deployment_healthy(self, deployment: Deployment) -> bool:
        """检查部署是否健康"""
        try:
            # 获取环境配置
            env_config = self.environments.get(deployment.config.environment)
            if not env_config:
                return False
            
            # 检查健康端点
            health_url = f"{env_config['url']}{env_config['health_endpoint']}"
            
            # 这里应该发送HTTP请求检查健康状态
            # 为了演示，我们返回True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 检查部署健康状态失败: {e}")
            return False
    
    def register_deployment_config(self, config: DeploymentConfig):
        """注册部署配置"""
        try:
            self.deployment_configs[config.name] = config
            self.logger.info(f"✅ 部署配置已注册: {config.name}")
            
        except Exception as e:
            self.logger.error(f"❌ 注册部署配置失败: {e}")
    
    async def deploy(self, config_name: str, version: str) -> str:
        """执行部署"""
        try:
            if config_name not in self.deployment_configs:
                raise ValueError(f"部署配置不存在: {config_name}")
            
            config = self.deployment_configs[config_name]
            config.version = version
            
            # 创建部署
            deployment_id = f"{config_name}_{version}_{int(time.time())}"
            deployment = Deployment(
                deployment_id=deployment_id,
                config=config,
                status=DeploymentStatus.PENDING,
                created_at=datetime.now()
            )
            
            self.deployments[deployment_id] = deployment
            
            # 执行部署流程
            await self._execute_deployment(deployment)
            
            return deployment_id
            
        except Exception as e:
            self.logger.error(f"❌ 执行部署失败: {e}")
            return ""
    
    async def _execute_deployment(self, deployment: Deployment):
        """执行部署流程"""
        try:
            deployment.status = DeploymentStatus.PREPARING
            deployment.started_at = datetime.now()
            
            # 触发部署回调
            await self._trigger_deployment_callbacks(deployment)
            
            # 准备部署
            await self._prepare_deployment(deployment)
            
            # 执行部署
            deployment.status = DeploymentStatus.DEPLOYING
            await self._perform_deployment(deployment)
            
            # 验证部署
            await self._verify_deployment(deployment)
            
            # 完成部署
            deployment.status = DeploymentStatus.DEPLOYED
            deployment.completed_at = datetime.now()
            deployment.duration = (deployment.completed_at - deployment.started_at).total_seconds()
            
            # 更新版本历史
            self.current_version = deployment.config.version
            self.version_history.append(deployment.config.version)
            
            # 触发部署回调
            await self._trigger_deployment_callbacks(deployment)
            
            self.logger.info(f"✅ 部署完成: {deployment.deployment_id}")
            
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = datetime.now()
            
            self.logger.error(f"❌ 部署失败: {deployment.deployment_id} - {e}")
            
            # 如果启用了自动回滚，则执行回滚
            if deployment.config.auto_rollback:
                await self.rollback_deployment(deployment.deployment_id)
    
    async def _prepare_deployment(self, deployment: Deployment):
        """准备部署"""
        try:
            # 创建部署目录
            env_config = self.environments[deployment.config.environment]
            deployment_path = Path(env_config['deployment_path'])
            version_path = deployment_path / 'versions' / deployment.config.version
            version_path.mkdir(parents=True, exist_ok=True)
            
            # 复制应用文件
            await self._copy_application_files(deployment, version_path)
            
            # 设置环境变量
            await self._setup_environment_variables(deployment, version_path)
            
            # 安装依赖
            await self._install_dependencies(deployment, version_path)
            
            self.logger.info(f"✅ 部署准备完成: {deployment.deployment_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 准备部署失败: {e}")
            raise e
    
    async def _copy_application_files(self, deployment: Deployment, target_path: Path):
        """复制应用文件"""
        try:
            # 这里应该复制实际的应用文件
            # 为了演示，我们创建一个简单的文件
            app_file = target_path / 'app.py'
            app_file.write_text(f"# JubenAI Application v{deployment.config.version}\nprint('Hello from JubenAI!')\n")
            
        except Exception as e:
            self.logger.error(f"❌ 复制应用文件失败: {e}")
            raise e
    
    async def _setup_environment_variables(self, deployment: Deployment, target_path: Path):
        """设置环境变量"""
        try:
            # 创建环境变量文件
            env_file = target_path / '.env'
            env_content = []
            
            for key, value in deployment.config.env_vars.items():
                env_content.append(f"{key}={value}")
            
            env_file.write_text('\n'.join(env_content))
            
        except Exception as e:
            self.logger.error(f"❌ 设置环境变量失败: {e}")
            raise e
    
    async def _install_dependencies(self, deployment: Deployment, target_path: Path):
        """安装依赖"""
        try:
            # 创建requirements.txt
            requirements_file = target_path / 'requirements.txt'
            requirements_file.write_text('fastapi\nuvicorn\npydantic\n')
            
            # 这里应该执行pip install
            # 为了演示，我们跳过实际安装
            
        except Exception as e:
            self.logger.error(f"❌ 安装依赖失败: {e}")
            raise e
    
    async def _perform_deployment(self, deployment: Deployment):
        """执行部署"""
        try:
            # 根据部署类型执行不同的部署策略
            if deployment.config.deployment_type == DeploymentType.BLUE_GREEN:
                await self._blue_green_deployment(deployment)
            elif deployment.config.deployment_type == DeploymentType.CANARY:
                await self._canary_deployment(deployment)
            elif deployment.config.deployment_type == DeploymentType.ROLLING:
                await self._rolling_deployment(deployment)
            elif deployment.config.deployment_type == DeploymentType.RECREATE:
                await self._recreate_deployment(deployment)
            
        except Exception as e:
            self.logger.error(f"❌ 执行部署失败: {e}")
            raise e
    
    async def _blue_green_deployment(self, deployment: Deployment):
        """蓝绿部署"""
        try:
            # 蓝绿部署逻辑
            self.logger.info(f"🔄 执行蓝绿部署: {deployment.deployment_id}")
            
            # 1. 部署到绿色环境
            # 2. 验证绿色环境
            # 3. 切换流量到绿色环境
            # 4. 停止蓝色环境
            
            await asyncio.sleep(2)  # 模拟部署时间
            
        except Exception as e:
            self.logger.error(f"❌ 蓝绿部署失败: {e}")
            raise e
    
    async def _canary_deployment(self, deployment: Deployment):
        """金丝雀部署"""
        try:
            # 金丝雀部署逻辑
            self.logger.info(f"🔄 执行金丝雀部署: {deployment.deployment_id}")
            
            # 1. 部署到小部分实例
            # 2. 监控指标
            # 3. 逐步扩大范围
            # 4. 完全切换
            
            await asyncio.sleep(3)  # 模拟部署时间
            
        except Exception as e:
            self.logger.error(f"❌ 金丝雀部署失败: {e}")
            raise e
    
    async def _rolling_deployment(self, deployment: Deployment):
        """滚动部署"""
        try:
            # 滚动部署逻辑
            self.logger.info(f"🔄 执行滚动部署: {deployment.deployment_id}")
            
            # 1. 逐个更新实例
            # 2. 等待实例就绪
            # 3. 继续下一个实例
            
            await asyncio.sleep(4)  # 模拟部署时间
            
        except Exception as e:
            self.logger.error(f"❌ 滚动部署失败: {e}")
            raise e
    
    async def _recreate_deployment(self, deployment: Deployment):
        """重建部署"""
        try:
            # 重建部署逻辑
            self.logger.info(f"🔄 执行重建部署: {deployment.deployment_id}")
            
            # 1. 停止所有实例
            # 2. 部署新版本
            # 3. 启动新实例
            
            await asyncio.sleep(2)  # 模拟部署时间
            
        except Exception as e:
            self.logger.error(f"❌ 重建部署失败: {e}")
            raise e
    
    async def _verify_deployment(self, deployment: Deployment):
        """验证部署"""
        try:
            # 验证部署是否成功
            is_healthy = await self._is_deployment_healthy(deployment)
            
            if not is_healthy:
                raise Exception("部署验证失败: 健康检查未通过")
            
            self.logger.info(f"✅ 部署验证通过: {deployment.deployment_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 部署验证失败: {e}")
            raise e
    
    async def rollback_deployment(self, deployment_id: str) -> bool:
        """回滚部署"""
        try:
            if deployment_id not in self.deployments:
                raise ValueError(f"部署不存在: {deployment_id}")
            
            deployment = self.deployments[deployment_id]
            
            if not deployment.config.rollback_enabled:
                raise ValueError("回滚未启用")
            
            deployment.status = DeploymentStatus.ROLLING_BACK
            
            # 触发回滚回调
            await self._trigger_rollback_callbacks(deployment)
            
            # 执行回滚
            await self._perform_rollback(deployment)
            
            deployment.status = DeploymentStatus.ROLLED_BACK
            deployment.completed_at = datetime.now()
            
            self.logger.info(f"✅ 部署已回滚: {deployment_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 回滚部署失败: {e}")
            return False
    
    async def _perform_rollback(self, deployment: Deployment):
        """执行回滚"""
        try:
            # 回滚逻辑
            self.logger.info(f"🔄 执行回滚: {deployment.deployment_id}")
            
            # 1. 停止当前部署
            # 2. 恢复到上一个版本
            # 3. 验证回滚结果
            
            await asyncio.sleep(2)  # 模拟回滚时间
            
        except Exception as e:
            self.logger.error(f"❌ 执行回滚失败: {e}")
            raise e
    
    async def _trigger_deployment_callbacks(self, deployment: Deployment):
        """触发部署回调"""
        try:
            for callback in self.deployment_callbacks:
                try:
                    await callback(deployment)
                except Exception as e:
                    self.logger.error(f"❌ 部署回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发部署回调失败: {e}")
    
    async def _trigger_rollback_callbacks(self, deployment: Deployment):
        """触发回滚回调"""
        try:
            for callback in self.rollback_callbacks:
                try:
                    await callback(deployment)
                except Exception as e:
                    self.logger.error(f"❌ 回滚回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发回滚回调失败: {e}")
    
    def add_deployment_callback(self, callback: Callable):
        """添加部署回调"""
        try:
            self.deployment_callbacks.append(callback)
            self.logger.info("✅ 部署回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加部署回调失败: {e}")
    
    def add_rollback_callback(self, callback: Callable):
        """添加回滚回调"""
        try:
            self.rollback_callbacks.append(callback)
            self.logger.info("✅ 回滚回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加回滚回调失败: {e}")
    
    def add_health_check_callback(self, callback: Callable):
        """添加健康检查回调"""
        try:
            self.health_check_callbacks.append(callback)
            self.logger.info("✅ 健康检查回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加健康检查回调失败: {e}")
    
    def get_deployment_stats(self) -> Dict[str, Any]:
        """获取部署统计"""
        try:
            # 计算统计信息
            total_deployments = len(self.deployments)
            successful_deployments = len([d for d in self.deployments.values() if d.status == DeploymentStatus.DEPLOYED])
            failed_deployments = len([d for d in self.deployments.values() if d.status == DeploymentStatus.FAILED])
            rolled_back_deployments = len([d for d in self.deployments.values() if d.status == DeploymentStatus.ROLLED_BACK])
            
            # 计算成功率
            success_rate = (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0
            
            # 计算平均部署时间
            if total_deployments > 0:
                avg_duration = sum(d.duration for d in self.deployments.values() if d.duration > 0) / total_deployments
            else:
                avg_duration = 0.0
            
            # 按环境统计
            env_stats = {}
            for deployment in self.deployments.values():
                env = deployment.config.environment.value
                env_stats[env] = env_stats.get(env, 0) + 1
            
            # 按部署类型统计
            type_stats = {}
            for deployment in self.deployments.values():
                deploy_type = deployment.config.deployment_type.value
                type_stats[deploy_type] = type_stats.get(deploy_type, 0) + 1
            
            return {
                'total_deployments': total_deployments,
                'successful_deployments': successful_deployments,
                'failed_deployments': failed_deployments,
                'rolled_back_deployments': rolled_back_deployments,
                'success_rate': success_rate,
                'avg_duration': avg_duration,
                'current_version': self.current_version,
                'version_history': self.version_history,
                'rollback_versions': self.rollback_versions,
                'env_stats': env_stats,
                'type_stats': type_stats,
                'deployment_configs': len(self.deployment_configs),
                'deployment_metrics': len(self.deployment_metrics),
                'deployment_enabled': self.deployment_enabled,
                'auto_deployment': self.auto_deployment,
                'monitoring_enabled': self.monitoring_enabled
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取部署统计失败: {e}")
            return {'error': str(e)}


# 全局智能部署实例
smart_deployment = SmartDeployment()


def get_smart_deployment() -> SmartDeployment:
    """获取智能部署实例"""
    return smart_deployment

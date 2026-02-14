"""
智能集成系统 -  
提供智能集成、API管理、数据同步和系统协调
"""
import asyncio
import json
import time
import aiohttp
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path
import yaml
import xml.etree.ElementTree as ET

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


class IntegrationType(Enum):
    """集成类型"""
    API = "api"                    # API集成
    DATABASE = "database"          # 数据库集成
    MESSAGE_QUEUE = "message_queue" # 消息队列集成
    FILE_SYSTEM = "file_system"    # 文件系统集成
    WEBHOOK = "webhook"            # Webhook集成
    SDK = "sdk"                    # SDK集成
    PLUGIN = "plugin"             # 插件集成


class IntegrationStatus(Enum):
    """集成状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DataFormat(Enum):
    """数据格式"""
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    CSV = "csv"
    PROTOBUF = "protobuf"
    AVRO = "avro"
    PARQUET = "parquet"


@dataclass
class IntegrationConfig:
    """集成配置"""
    name: str
    integration_type: IntegrationType
    endpoint: str
    authentication: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    data_format: DataFormat = DataFormat.JSON
    rate_limit: Optional[int] = None
    enabled: bool = True
    description: str = ""


@dataclass
class IntegrationConnection:
    """集成连接"""
    config: IntegrationConfig
    status: IntegrationStatus
    created_at: datetime
    last_used: datetime
    connection_pool: Optional[Any] = None
    session: Optional[aiohttp.ClientSession] = None
    error_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None


@dataclass
class IntegrationRequest:
    """集成请求"""
    request_id: str
    integration_name: str
    method: str
    url: str
    headers: Dict[str, str]
    data: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None
    timeout: int = 30
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class IntegrationResponse:
    """集成响应"""
    request_id: str
    status_code: int
    headers: Dict[str, str]
    data: Any
    response_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class SmartIntegration:
    """智能集成系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_integration")
        
        # 集成配置
        self.integration_enabled = True
        self.auto_retry = True
        self.connection_pool_size = 100
        self.max_connections = 1000
        self.connection_timeout = 30
        self.keep_alive_timeout = 60
        
        # 集成存储
        self.integrations: Dict[str, IntegrationConnection] = {}
        self.integration_configs: Dict[str, IntegrationConfig] = {}
        self.integration_requests: List[IntegrationRequest] = []
        self.integration_responses: List[IntegrationResponse] = []
        
        # 集成监控
        self.monitoring_enabled = True
        self.health_check_interval = 300  # 5分钟
        self.performance_metrics: Dict[str, Any] = {}
        
        # 集成任务
        self.integration_tasks: List[asyncio.Task] = []
        self.request_queue: List[IntegrationRequest] = []
        
        # 集成回调
        self.integration_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # 集成统计
        self.integration_stats: Dict[str, Any] = {}
        
        self.logger.info("🔗 智能集成系统初始化完成")
    
    async def initialize(self):
        """初始化集成系统"""
        try:
            # 启动集成任务
            if self.integration_enabled:
                await self._start_integration_tasks()
            
            # 启动健康检查
            if self.monitoring_enabled:
                await self._start_health_checks()
            
            self.logger.info("✅ 智能集成系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化集成系统失败: {e}")
    
    async def _start_integration_tasks(self):
        """启动集成任务"""
        try:
            # 启动请求处理任务
            task = asyncio.create_task(self._request_processing_task())
            self.integration_tasks.append(task)
            
            # 启动连接管理任务
            task = asyncio.create_task(self._connection_management_task())
            self.integration_tasks.append(task)
            
            # 启动性能监控任务
            task = asyncio.create_task(self._performance_monitoring_task())
            self.integration_tasks.append(task)
            
            self.logger.info("✅ 集成任务已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动集成任务失败: {e}")
    
    async def _start_health_checks(self):
        """启动健康检查"""
        try:
            # 启动健康检查任务
            task = asyncio.create_task(self._health_check_task())
            self.integration_tasks.append(task)
            
            self.logger.info("✅ 健康检查已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动健康检查失败: {e}")
    
    async def _request_processing_task(self):
        """请求处理任务"""
        try:
            while True:
                await asyncio.sleep(0.1)  # 每100ms检查一次
                
                # 处理请求队列
                if self.request_queue:
                    request = self.request_queue.pop(0)
                    await self._process_request(request)
                
        except asyncio.CancelledError:
            self.logger.info("📨 请求处理任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 请求处理任务失败: {e}")
    
    async def _connection_management_task(self):
        """连接管理任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 管理连接
                await self._manage_connections()
                
        except asyncio.CancelledError:
            self.logger.info("🔗 连接管理任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 连接管理任务失败: {e}")
    
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
                await asyncio.sleep(self.health_check_interval)
                
                # 检查集成健康状态
                await self._check_integration_health()
                
        except asyncio.CancelledError:
            self.logger.info("🏥 健康检查任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 健康检查任务失败: {e}")
    
    async def _process_request(self, request: IntegrationRequest):
        """处理请求"""
        try:
            # 获取集成连接
            integration = self.integrations.get(request.integration_name)
            if not integration:
                self.logger.error(f"❌ 集成不存在: {request.integration_name}")
                return
            
            # 检查连接状态
            if integration.status != IntegrationStatus.ACTIVE:
                self.logger.error(f"❌ 集成连接不可用: {request.integration_name}")
                return
            
            # 执行请求
            response = await self._execute_request(integration, request)
            
            # 记录响应
            self.integration_responses.append(response)
            
            # 更新统计
            if response.success:
                integration.success_count += 1
            else:
                integration.error_count += 1
                integration.last_error = response.error_message
            
            # 触发集成回调
            await self._trigger_integration_callbacks(response)
            
        except Exception as e:
            self.logger.error(f"❌ 处理请求失败: {e}")
    
    async def _execute_request(self, integration: IntegrationConnection, request: IntegrationRequest) -> IntegrationResponse:
        """执行请求"""
        try:
            start_time = time.time()
            
            # 构建完整URL
            full_url = f"{integration.config.endpoint}{request.url}"
            
            # 准备请求数据
            request_data = None
            if request.data:
                if integration.config.data_format == DataFormat.JSON:
                    request_data = json.dumps(request.data)
                elif integration.config.data_format == DataFormat.XML:
                    request_data = self._dict_to_xml(request.data)
                elif integration.config.data_format == DataFormat.YAML:
                    request_data = yaml.dump(request.data)
            
            # 准备请求头
            headers = {**integration.config.headers, **request.headers}
            
            # 执行HTTP请求
            async with integration.session.request(
                method=request.method,
                url=full_url,
                headers=headers,
                data=request_data,
                params=request.params,
                timeout=aiohttp.ClientTimeout(total=request.timeout)
            ) as response:
                # 读取响应数据
                response_data = await response.text()
                
                # 解析响应数据
                parsed_data = self._parse_response_data(response_data, integration.config.data_format)
                
                # 创建响应对象
                response_time = time.time() - start_time
                
                return IntegrationResponse(
                    request_id=request.request_id,
                    status_code=response.status,
                    headers=dict(response.headers),
                    data=parsed_data,
                    response_time=response_time,
                    success=200 <= response.status < 300,
                    error_message=None if 200 <= response.status < 300 else f"HTTP {response.status}"
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            
            return IntegrationResponse(
                request_id=request.request_id,
                status_code=0,
                headers={},
                data=None,
                response_time=response_time,
                success=False,
                error_message=str(e)
            )
    
    def _dict_to_xml(self, data: Dict[str, Any]) -> str:
        """将字典转换为XML"""
        try:
            root = ET.Element("root")
            self._dict_to_xml_element(root, data)
            return ET.tostring(root, encoding='unicode')
        except Exception as e:
            self.logger.error(f"❌ 转换字典为XML失败: {e}")
            return ""
    
    def _dict_to_xml_element(self, parent: ET.Element, data: Dict[str, Any]):
        """递归转换字典为XML元素"""
        try:
            for key, value in data.items():
                element = ET.SubElement(parent, key)
                if isinstance(value, dict):
                    self._dict_to_xml_element(element, value)
                else:
                    element.text = str(value)
        except Exception as e:
            self.logger.error(f"❌ 转换字典为XML元素失败: {e}")
    
    def _parse_response_data(self, data: str, data_format: DataFormat) -> Any:
        """解析响应数据"""
        try:
            if data_format == DataFormat.JSON:
                return json.loads(data)
            elif data_format == DataFormat.XML:
                root = ET.fromstring(data)
                return self._xml_to_dict(root)
            elif data_format == DataFormat.YAML:
                return yaml.safe_load(data)
            else:
                return data
                
        except Exception as e:
            self.logger.error(f"❌ 解析响应数据失败: {e}")
            return data
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """将XML元素转换为字典"""
        try:
            result = {}
            
            # 添加属性
            if element.attrib:
                result['@attributes'] = element.attrib
            
            # 添加文本内容
            if element.text and element.text.strip():
                if len(element) == 0:
                    return element.text.strip()
                else:
                    result['#text'] = element.text.strip()
            
            # 添加子元素
            for child in element:
                child_data = self._xml_to_dict(child)
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 转换XML为字典失败: {e}")
            return {}
    
    async def _manage_connections(self):
        """管理连接"""
        try:
            for name, integration in self.integrations.items():
                # 检查连接状态
                if integration.status == IntegrationStatus.ACTIVE:
                    # 检查连接是否超时
                    if (datetime.now() - integration.last_used).total_seconds() > self.keep_alive_timeout:
                        await self._close_connection(integration)
                        integration.status = IntegrationStatus.DISCONNECTED
                
                # 检查错误率
                total_requests = integration.success_count + integration.error_count
                if total_requests > 0:
                    error_rate = integration.error_count / total_requests
                    if error_rate > 0.5:  # 错误率超过50%
                        integration.status = IntegrationStatus.ERROR
                        self.logger.warning(f"⚠️ 集成错误率过高: {name} - {error_rate:.2%}")
            
        except Exception as e:
            self.logger.error(f"❌ 管理连接失败: {e}")
    
    async def _monitor_performance(self):
        """监控性能"""
        try:
            # 计算性能指标
            total_requests = len(self.integration_requests)
            successful_requests = len([r for r in self.integration_responses if r.success])
            failed_requests = total_requests - successful_requests
            
            # 计算平均响应时间
            if self.integration_responses:
                avg_response_time = sum(r.response_time for r in self.integration_responses) / len(self.integration_responses)
            else:
                avg_response_time = 0.0
            
            # 计算成功率
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            # 更新性能指标
            self.performance_metrics = {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'active_integrations': len([i for i in self.integrations.values() if i.status == IntegrationStatus.ACTIVE]),
                'error_integrations': len([i for i in self.integrations.values() if i.status == IntegrationStatus.ERROR])
            }
            
        except Exception as e:
            self.logger.error(f"❌ 监控性能失败: {e}")
    
    async def _check_integration_health(self):
        """检查集成健康状态"""
        try:
            for name, integration in self.integrations.items():
                if integration.status == IntegrationStatus.ACTIVE:
                    # 执行健康检查
                    is_healthy = await self._perform_health_check(integration)
                    
                    if not is_healthy:
                        integration.status = IntegrationStatus.ERROR
                        self.logger.warning(f"⚠️ 集成健康检查失败: {name}")
                    else:
                        self.logger.info(f"✅ 集成健康检查通过: {name}")
            
        except Exception as e:
            self.logger.error(f"❌ 检查集成健康状态失败: {e}")
    
    async def _perform_health_check(self, integration: IntegrationConnection) -> bool:
        """执行健康检查"""
        try:
            # 发送健康检查请求
            health_url = f"{integration.config.endpoint}/health"
            
            async with integration.session.get(health_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"❌ 执行健康检查失败: {e}")
            return False
    
    async def _close_connection(self, integration: IntegrationConnection):
        """关闭连接"""
        try:
            if integration.session:
                await integration.session.close()
                integration.session = None
            
        except Exception as e:
            self.logger.error(f"❌ 关闭连接失败: {e}")
    
    async def _trigger_integration_callbacks(self, response: IntegrationResponse):
        """触发集成回调"""
        try:
            for callback in self.integration_callbacks:
                try:
                    await callback(response)
                except Exception as e:
                    self.logger.error(f"❌ 集成回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发集成回调失败: {e}")
    
    def register_integration(self, config: IntegrationConfig):
        """注册集成"""
        try:
            # 创建集成连接
            connection = IntegrationConnection(
                config=config,
                status=IntegrationStatus.INACTIVE,
                created_at=datetime.now(),
                last_used=datetime.now()
            )
            
            self.integrations[config.name] = connection
            self.integration_configs[config.name] = config
            
            self.logger.info(f"✅ 集成已注册: {config.name}")
            
        except Exception as e:
            self.logger.error(f"❌ 注册集成失败: {e}")
    
    async def connect_integration(self, name: str) -> bool:
        """连接集成"""
        try:
            if name not in self.integrations:
                raise ValueError(f"集成不存在: {name}")
            
            integration = self.integrations[name]
            
            if integration.status == IntegrationStatus.ACTIVE:
                return True
            
            integration.status = IntegrationStatus.CONNECTING
            
            try:
                # 创建HTTP会话
                connector = aiohttp.TCPConnector(
                    limit=self.connection_pool_size,
                    limit_per_host=100,
                    keepalive_timeout=self.keep_alive_timeout
                )
                
                timeout = aiohttp.ClientTimeout(total=integration.config.timeout)
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers=integration.config.headers
                )
                
                integration.session = session
                integration.status = IntegrationStatus.ACTIVE
                
                self.logger.info(f"✅ 集成连接成功: {name}")
                return True
                
            except Exception as e:
                integration.status = IntegrationStatus.ERROR
                integration.last_error = str(e)
                self.logger.error(f"❌ 集成连接失败: {name} - {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ 连接集成失败: {e}")
            return False
    
    async def disconnect_integration(self, name: str) -> bool:
        """断开集成"""
        try:
            if name not in self.integrations:
                raise ValueError(f"集成不存在: {name}")
            
            integration = self.integrations[name]
            
            if integration.status == IntegrationStatus.INACTIVE:
                return True
            
            # 关闭连接
            await self._close_connection(integration)
            integration.status = IntegrationStatus.DISCONNECTED
            
            self.logger.info(f"✅ 集成断开成功: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 断开集成失败: {e}")
            return False
    
    async def send_request(
        self,
        integration_name: str,
        method: str,
        url: str,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> IntegrationResponse:
        """发送请求"""
        try:
            if integration_name not in self.integrations:
                raise ValueError(f"集成不存在: {integration_name}")
            
            integration = self.integrations[integration_name]
            
            if integration.status != IntegrationStatus.ACTIVE:
                raise ValueError(f"集成连接不可用: {integration_name}")
            
            # 创建请求
            request_id = f"req_{integration_name}_{int(time.time())}"
            request = IntegrationRequest(
                request_id=request_id,
                integration_name=integration_name,
                method=method,
                url=url,
                headers=headers or {},
                data=data,
                params=params,
                timeout=timeout or integration.config.timeout
            )
            
            # 添加到请求队列
            self.request_queue.append(request)
            self.integration_requests.append(request)
            
            # 等待响应
            max_wait_time = 60  # 最大等待60秒
            wait_time = 0
            while wait_time < max_wait_time:
                # 查找响应
                response = next((r for r in self.integration_responses if r.request_id == request_id), None)
                if response:
                    return response
                
                await asyncio.sleep(0.1)
                wait_time += 0.1
            
            # 超时返回错误响应
            return IntegrationResponse(
                request_id=request_id,
                status_code=0,
                headers={},
                data=None,
                response_time=0.0,
                success=False,
                error_message="请求超时"
            )
            
        except Exception as e:
            self.logger.error(f"❌ 发送请求失败: {e}")
            return IntegrationResponse(
                request_id="",
                status_code=0,
                headers={},
                data=None,
                response_time=0.0,
                success=False,
                error_message=str(e)
            )
    
    def add_integration_callback(self, callback: Callable):
        """添加集成回调"""
        try:
            self.integration_callbacks.append(callback)
            self.logger.info("✅ 集成回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加集成回调失败: {e}")
    
    def add_error_callback(self, callback: Callable):
        """添加错误回调"""
        try:
            self.error_callbacks.append(callback)
            self.logger.info("✅ 错误回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加错误回调失败: {e}")
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """获取集成统计"""
        try:
            return {
                'total_integrations': len(self.integrations),
                'active_integrations': len([i for i in self.integrations.values() if i.status == IntegrationStatus.ACTIVE]),
                'inactive_integrations': len([i for i in self.integrations.values() if i.status == IntegrationStatus.INACTIVE]),
                'error_integrations': len([i for i in self.integrations.values() if i.status == IntegrationStatus.ERROR]),
                'total_requests': len(self.integration_requests),
                'total_responses': len(self.integration_responses),
                'request_queue': len(self.request_queue),
                'integration_enabled': self.integration_enabled,
                'auto_retry': self.auto_retry,
                'connection_pool_size': self.connection_pool_size,
                'max_connections': self.max_connections,
                'connection_timeout': self.connection_timeout,
                'keep_alive_timeout': self.keep_alive_timeout,
                'monitoring_enabled': self.monitoring_enabled,
                'health_check_interval': self.health_check_interval,
                'integration_tasks': len(self.integration_tasks),
                'performance_metrics': self.performance_metrics
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取集成统计失败: {e}")
            return {'error': str(e)}


# 全局智能集成实例
smart_integration = SmartIntegration()


def get_smart_integration() -> SmartIntegration:
    """获取智能集成实例"""
    return smart_integration

"""
智能路由系统 -  
提供智能的任务路由、负载均衡和故障转移
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import random

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager
from .performance_monitor import get_performance_monitor


class RouteStrategy(Enum):
    """路由策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_RESPONSE_TIME = "least_response_time"
    RANDOM = "random"


class AgentStatus(Enum):
    """Agent状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class AgentInfo:
    """Agent信息"""
    name: str
    status: AgentStatus
    weight: int = 1
    max_connections: int = 10
    current_connections: int = 0
    response_time: float = 0.0
    error_rate: float = 0.0
    last_used: datetime = None
    health_check_interval: int = 30
    last_health_check: datetime = None


@dataclass
class RouteResult:
    """路由结果"""
    agent_name: str
    success: bool
    response_time: float
    error_message: Optional[str] = None
    retry_count: int = 0


class SmartRouter:
    """智能路由系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_router")
        
        # 路由配置
        self.default_strategy = RouteStrategy.LEAST_RESPONSE_TIME
        self.max_retries = 3
        self.retry_delay = 1.0  # 秒
        self.circuit_breaker_threshold = 5  # 连续失败次数
        self.circuit_breaker_timeout = 60  # 熔断超时时间
        
        # Agent管理
        self.agents: Dict[str, AgentInfo] = {}
        self.route_history: List[RouteResult] = []
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # 负载均衡
        self.round_robin_index = 0
        self.performance_monitor = get_performance_monitor()
        
        # 路由规则
        self.routing_rules: Dict[str, List[str]] = {
            "story_analysis": ["story_five_elements_agent", "story_evaluation_agent"],
            "story_creation": ["short_drama_creator_agent", "story_outline_evaluation_agent"],
            "character_development": ["character_profile_agent", "character_relationship_agent"],
            "plot_development": ["plot_points_agent", "major_plot_points_agent"],
            "drama_evaluation": ["short_drama_evaluation_agent", "script_evaluation_agent"],
            "series_analysis": ["series_analysis_agent", "series_info_agent"]
        }
        
        self.logger.info("🧭 智能路由系统初始化完成")
    
    def register_agent(self, agent_name: str, weight: int = 1, max_connections: int = 10):
        """注册Agent"""
        try:
            agent_info = AgentInfo(
                name=agent_name,
                status=AgentStatus.HEALTHY,
                weight=weight,
                max_connections=max_connections,
                last_used=datetime.now()
            )
            
            self.agents[agent_name] = agent_info
            self.circuit_breakers[agent_name] = {
                'failure_count': 0,
                'last_failure': None,
                'is_open': False
            }
            
            self.logger.info(f"✅ Agent已注册: {agent_name} (权重: {weight}, 最大连接: {max_connections})")
            
        except Exception as e:
            self.logger.error(f"❌ 注册Agent失败: {e}")
    
    def unregister_agent(self, agent_name: str):
        """注销Agent"""
        try:
            if agent_name in self.agents:
                del self.agents[agent_name]
                if agent_name in self.circuit_breakers:
                    del self.circuit_breakers[agent_name]
                
                self.logger.info(f"✅ Agent已注销: {agent_name}")
            
        except Exception as e:
            self.logger.error(f"❌ 注销Agent失败: {e}")
    
    async def route_request(
        self, 
        request_type: str, 
        request_data: Dict[str, Any],
        strategy: Optional[RouteStrategy] = None
    ) -> RouteResult:
        """路由请求"""
        try:
            strategy = strategy or self.default_strategy
            
            # 获取可用的Agent列表
            available_agents = await self._get_available_agents(request_type)
            
            if not available_agents:
                return RouteResult(
                    agent_name="",
                    success=False,
                    response_time=0.0,
                    error_message="没有可用的Agent"
                )
            
            # 选择最佳Agent
            selected_agent = await self._select_agent(available_agents, strategy)
            
            if not selected_agent:
                return RouteResult(
                    agent_name="",
                    success=False,
                    response_time=0.0,
                    error_message="无法选择Agent"
                )
            
            # 执行请求
            result = await self._execute_request(selected_agent, request_data)
            
            # 记录路由结果
            self.route_history.append(result)
            
            # 更新Agent状态
            await self._update_agent_status(selected_agent, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 路由请求失败: {e}")
            return RouteResult(
                agent_name="",
                success=False,
                response_time=0.0,
                error_message=str(e)
            )
    
    async def _get_available_agents(self, request_type: str) -> List[str]:
        """获取可用的Agent列表"""
        try:
            # 根据请求类型获取候选Agent
            candidate_agents = self.routing_rules.get(request_type, list(self.agents.keys()))
            
            available_agents = []
            
            for agent_name in candidate_agents:
                if agent_name not in self.agents:
                    continue
                
                agent_info = self.agents[agent_name]
                
                # 检查Agent状态
                if agent_info.status == AgentStatus.OFFLINE:
                    continue
                
                # 检查熔断器
                if self._is_circuit_breaker_open(agent_name):
                    continue
                
                # 检查连接数限制
                if agent_info.current_connections >= agent_info.max_connections:
                    continue
                
                available_agents.append(agent_name)
            
            return available_agents
            
        except Exception as e:
            self.logger.error(f"❌ 获取可用Agent失败: {e}")
            return []
    
    async def _select_agent(self, available_agents: List[str], strategy: RouteStrategy) -> Optional[str]:
        """选择Agent"""
        try:
            if not available_agents:
                return None
            
            if len(available_agents) == 1:
                return available_agents[0]
            
            if strategy == RouteStrategy.ROUND_ROBIN:
                return self._round_robin_select(available_agents)
            
            elif strategy == RouteStrategy.LEAST_CONNECTIONS:
                return self._least_connections_select(available_agents)
            
            elif strategy == RouteStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_round_robin_select(available_agents)
            
            elif strategy == RouteStrategy.LEAST_RESPONSE_TIME:
                return self._least_response_time_select(available_agents)
            
            elif strategy == RouteStrategy.RANDOM:
                return random.choice(available_agents)
            
            else:
                return available_agents[0]
                
        except Exception as e:
            self.logger.error(f"❌ 选择Agent失败: {e}")
            return None
    
    def _round_robin_select(self, available_agents: List[str]) -> str:
        """轮询选择"""
        try:
            agent = available_agents[self.round_robin_index % len(available_agents)]
            self.round_robin_index += 1
            return agent
        except Exception as e:
            self.logger.error(f"❌ 轮询选择失败: {e}")
            return available_agents[0] if available_agents else None
    
    def _least_connections_select(self, available_agents: List[str]) -> str:
        """最少连接选择"""
        try:
            return min(available_agents, key=lambda agent: self.agents[agent].current_connections)
        except Exception as e:
            self.logger.error(f"❌ 最少连接选择失败: {e}")
            return available_agents[0] if available_agents else None
    
    def _weighted_round_robin_select(self, available_agents: List[str]) -> str:
        """加权轮询选择"""
        try:
            # 计算总权重
            total_weight = sum(self.agents[agent].weight for agent in available_agents)
            
            # 随机选择
            random_value = random.uniform(0, total_weight)
            current_weight = 0
            
            for agent in available_agents:
                current_weight += self.agents[agent].weight
                if random_value <= current_weight:
                    return agent
            
            return available_agents[0]
            
        except Exception as e:
            self.logger.error(f"❌ 加权轮询选择失败: {e}")
            return available_agents[0] if available_agents else None
    
    def _least_response_time_select(self, available_agents: List[str]) -> str:
        """最少响应时间选择"""
        try:
            return min(available_agents, key=lambda agent: self.agents[agent].response_time)
        except Exception as e:
            self.logger.error(f"❌ 最少响应时间选择失败: {e}")
            return available_agents[0] if available_agents else None
    
    async def _execute_request(self, agent_name: str, request_data: Dict[str, Any]) -> RouteResult:
        """执行请求"""
        try:
            start_time = time.time()
            
            # 增加连接数
            self.agents[agent_name].current_connections += 1
            
            try:
                # 这里应该调用实际的Agent处理逻辑
                # 为了演示，我们模拟一个处理过程
                await asyncio.sleep(0.1)  # 模拟处理时间
                
                response_time = time.time() - start_time
                
                # 更新Agent状态
                self.agents[agent_name].response_time = response_time
                self.agents[agent_name].last_used = datetime.now()
                
                return RouteResult(
                    agent_name=agent_name,
                    success=True,
                    response_time=response_time
                )
                
            except Exception as e:
                response_time = time.time() - start_time
                
                # 记录失败
                self._record_failure(agent_name)
                
                return RouteResult(
                    agent_name=agent_name,
                    success=False,
                    response_time=response_time,
                    error_message=str(e)
                )
            
            finally:
                # 减少连接数
                self.agents[agent_name].current_connections = max(0, self.agents[agent_name].current_connections - 1)
            
        except Exception as e:
            self.logger.error(f"❌ 执行请求失败: {e}")
            return RouteResult(
                agent_name=agent_name,
                success=False,
                response_time=0.0,
                error_message=str(e)
            )
    
    def _is_circuit_breaker_open(self, agent_name: str) -> bool:
        """检查熔断器是否开启"""
        try:
            if agent_name not in self.circuit_breakers:
                return False
            
            breaker = self.circuit_breakers[agent_name]
            
            if not breaker['is_open']:
                return False
            
            # 检查是否应该尝试恢复
            if breaker['last_failure']:
                time_since_failure = (datetime.now() - breaker['last_failure']).total_seconds()
                if time_since_failure >= self.circuit_breaker_timeout:
                    # 尝试恢复
                    breaker['is_open'] = False
                    breaker['failure_count'] = 0
                    self.logger.info(f"🔄 熔断器恢复: {agent_name}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 检查熔断器失败: {e}")
            return False
    
    def _record_failure(self, agent_name: str):
        """记录失败"""
        try:
            if agent_name not in self.circuit_breakers:
                return
            
            breaker = self.circuit_breakers[agent_name]
            breaker['failure_count'] += 1
            breaker['last_failure'] = datetime.now()
            
            # 检查是否应该开启熔断器
            if breaker['failure_count'] >= self.circuit_breaker_threshold:
                breaker['is_open'] = True
                self.logger.warning(f"🚨 熔断器开启: {agent_name} (失败次数: {breaker['failure_count']})")
            
        except Exception as e:
            self.logger.error(f"❌ 记录失败失败: {e}")
    
    async def _update_agent_status(self, agent_name: str, result: RouteResult):
        """更新Agent状态"""
        try:
            if agent_name not in self.agents:
                return
            
            agent_info = self.agents[agent_name]
            
            # 更新响应时间
            if result.success:
                agent_info.response_time = result.response_time
                agent_info.error_rate = max(0, agent_info.error_rate - 0.1)  # 逐渐降低错误率
            else:
                agent_info.error_rate = min(100, agent_info.error_rate + 1.0)  # 增加错误率
            
            # 更新状态
            if agent_info.error_rate > 50:
                agent_info.status = AgentStatus.UNHEALTHY
            elif agent_info.error_rate > 20:
                agent_info.status = AgentStatus.DEGRADED
            else:
                agent_info.status = AgentStatus.HEALTHY
            
        except Exception as e:
            self.logger.error(f"❌ 更新Agent状态失败: {e}")
    
    async def health_check(self):
        """健康检查"""
        try:
            for agent_name, agent_info in self.agents.items():
                # 检查连接数
                if agent_info.current_connections > agent_info.max_connections * 0.8:
                    self.logger.warning(f"⚠️ Agent连接数过高: {agent_name} ({agent_info.current_connections}/{agent_info.max_connections})")
                
                # 检查响应时间
                if agent_info.response_time > 5.0:
                    self.logger.warning(f"⚠️ Agent响应时间过长: {agent_name} ({agent_info.response_time:.2f}s)")
                
                # 检查错误率
                if agent_info.error_rate > 30:
                    self.logger.warning(f"⚠️ Agent错误率过高: {agent_name} ({agent_info.error_rate:.1f}%)")
            
        except Exception as e:
            self.logger.error(f"❌ 健康检查失败: {e}")
    
    def get_router_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        try:
            # 计算成功率
            total_requests = len(self.route_history)
            successful_requests = len([r for r in self.route_history if r.success])
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            # 计算平均响应时间
            avg_response_time = 0
            if self.route_history:
                avg_response_time = sum(r.response_time for r in self.route_history) / len(self.route_history)
            
            # Agent状态统计
            agent_stats = {}
            for agent_name, agent_info in self.agents.items():
                agent_stats[agent_name] = {
                    'status': agent_info.status.value,
                    'current_connections': agent_info.current_connections,
                    'max_connections': agent_info.max_connections,
                    'response_time': agent_info.response_time,
                    'error_rate': agent_info.error_rate,
                    'last_used': agent_info.last_used.isoformat() if agent_info.last_used else None
                }
            
            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'active_agents': len(self.agents),
                'agent_stats': agent_stats,
                'circuit_breakers': {
                    name: {
                        'is_open': breaker['is_open'],
                        'failure_count': breaker['failure_count'],
                        'last_failure': breaker['last_failure'].isoformat() if breaker['last_failure'] else None
                    }
                    for name, breaker in self.circuit_breakers.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取路由统计失败: {e}")
            return {'error': str(e)}


# 全局智能路由器实例
smart_router = SmartRouter()


def get_smart_router() -> SmartRouter:
    """获取智能路由器实例"""
    return smart_router

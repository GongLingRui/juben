"""
端口监控服务
定期检查端口状态并在状态变化时发送告警

功能：
1. 定期检查配置的端口状态
2. 检测端口状态变化并告警
3. 响应时间监控
4. 健康状态统计
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime


class PortMonitorService:
    """
    端口监控服务

    功能：
    1. 定期检查端口状态
    2. 状态变化检测和告警
    3. 响应时间监控
    """

    def __init__(self, monitor_interval: int = 300):
        """
        初始化端口监控服务

        Args:
            monitor_interval: 监控间隔时间（秒），默认300秒（5分钟）
        """
        import logging
        self.logger = logging.getLogger(__name__)

        self.monitor_interval = monitor_interval

        # 从环境变量获取监控主机地址，默认为localhost
        self.monitor_host = os.getenv('MONITOR_HOST', 'localhost')

        # 端口配置（从环境变量读取）
        self.ports_config = self._load_ports_config()

        # 端口状态缓存（用于检测状态变化）
        self.port_status_cache: Dict[int, Dict[str, Any]] = {}

        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        self.running = False

        self.logger.info(f"🔧 端口监控服务初始化完成，监控间隔: {monitor_interval}秒")
        self.logger.info(f"🔧 监控主机: {self.monitor_host}")
        self.logger.info(f"🔧 监控端口数量: {len(self.ports_config)}")

    def _load_ports_config(self) -> List[Dict[str, Any]]:
        """
        从环境变量加载端口配置

        支持的环境变量格式：
        - MONITOR_PORTS: 逗号分隔的端口列表，如 "8000,8001,8099"
        - MONITOR_PORT_8000_NAME: 端口8000的名称
        - MONITOR_PORT_8000_ENV: 端口8000的环境类型

        Returns:
            List[Dict]: 端口配置列表
        """
        ports_config = []

        # 从环境变量读取端口列表
        ports_str = os.getenv('MONITOR_PORTS', '')
        if not ports_str:
            # 默认监控当前服务的端口
            default_port = int(os.getenv('PORT', '8000'))
            ports_str = str(default_port)

        ports = [int(p.strip()) for p in ports_str.split(',') if p.strip().isdigit()]

        for port in ports:
            port_name = os.getenv(f'MONITOR_PORT_{port}_NAME', f'Port_{port}')
            environment = os.getenv(f'MONITOR_PORT_{port}_ENV', 'production')

            ports_config.append({
                "port": port,
                "name": port_name,
                "description": f"{port_name}服务",
                "host": self.monitor_host,
                "environment": environment
            })

        return ports_config

    async def check_port_status(
        self,
        host: str,
        port: int,
        name: str,
        environment: str = "unknown"
    ) -> Dict[str, Any]:
        """
        检查单个端口状态

        Args:
            host: 主机地址
            port: 端口号
            name: 端口名称
            environment: 环境类型

        Returns:
            Dict[str, Any]: 端口状态信息
        """
        try:
            start_time = time.time()

            # 尝试连接端口
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=5.0)

            # 连接成功，关闭连接
            writer.close()
            await writer.wait_closed()

            response_time = round((time.time() - start_time) * 1000, 2)

            return {
                "port": port,
                "name": name,
                "environment": environment,
                "status": "healthy",
                "host": host,
                "response_time_ms": response_time,
                "last_check": datetime.now().isoformat(),
                "message": f"{name}服务正常运行"
            }

        except asyncio.TimeoutError:
            return {
                "port": port,
                "name": name,
                "environment": environment,
                "status": "timeout",
                "host": host,
                "response_time_ms": None,
                "last_check": datetime.now().isoformat(),
                "error": "连接超时",
                "message": f"{name}服务连接超时"
            }

        except ConnectionRefusedError:
            return {
                "port": port,
                "name": name,
                "environment": environment,
                "status": "unhealthy",
                "host": host,
                "response_time_ms": None,
                "last_check": datetime.now().isoformat(),
                "error": "连接被拒绝",
                "message": f"{name}服务可能已停止"
            }

        except Exception as e:
            return {
                "port": port,
                "name": name,
                "environment": environment,
                "status": "error",
                "host": host,
                "response_time_ms": None,
                "last_check": datetime.now().isoformat(),
                "error": str(e),
                "message": f"{name}服务状态异常"
            }

    async def check_all_ports(self) -> Dict[str, Any]:
        """检查所有配置的端口状态"""
        monitor_results = []
        overall_status = "healthy"

        for port_config in self.ports_config:
            port_status = await self.check_port_status(
                host=port_config["host"],
                port=port_config["port"],
                name=port_config["name"],
                environment=port_config.get("environment", "unknown")
            )
            monitor_results.append(port_status)

            # 检查状态变化并发送告警
            await self._check_status_change(port_status)

            # 更新整体状态
            if port_status["status"] not in ["healthy"]:
                overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "monitor_host": self.monitor_host,
            "ports": monitor_results,
            "summary": {
                "total_ports": len(self.ports_config),
                "healthy_ports": len([p for p in monitor_results if p["status"] == "healthy"]),
                "unhealthy_ports": len([p for p in monitor_results if p["status"] != "healthy"])
            }
        }

    async def _check_status_change(self, current_status: Dict[str, Any]):
        """检查端口状态变化并发送告警"""
        port = current_status["port"]
        current_health = current_status["status"]

        # 获取上次状态
        previous_status = self.port_status_cache.get(port, {})
        previous_health = previous_status.get("status")

        # 更新状态缓存
        self.port_status_cache[port] = current_status

        # 如果是首次检查，不发送告警
        if previous_health is None:
            self.logger.info(f"初始化端口 {port} ({current_status['name']}) 状态: {current_health}")
            return

        # 检查状态变化
        if previous_health != current_health:
            self.logger.warning(
                f"端口 {port} ({current_status['name']}) 状态变化: {previous_health} -> {current_health}"
            )

            # 发送告警
            await self._send_status_change_alert(current_status, previous_health, current_health)

    async def _send_status_change_alert(
        self,
        port_status: Dict[str, Any],
        previous_health: str,
        current_health: str
    ):
        """发送状态变化告警"""
        try:
            from utils.alert_manager import send_port_alert

            port = port_status["port"]
            port_name = port_status["name"]
            host = port_status["host"]
            error_message = port_status.get("error", port_status.get("message", ""))
            environment = port_status.get("environment", "unknown")

            # 确定状态变化类型
            if current_health == "healthy" and previous_health in ["unhealthy", "timeout", "error"]:
                status_change = "up"
            elif current_health == "timeout":
                status_change = "timeout"
            elif current_health in ["unhealthy", "error"]:
                status_change = "down"
            else:
                status_change = "unknown"

            # 发送告警（后台执行，不阻塞监控）
            asyncio.create_task(
                send_port_alert(
                    port=port,
                    port_name=port_name,
                    host=host,
                    error_message=error_message,
                    status_change=status_change,
                    environment=environment
                )
            )

            self.logger.info(f"端口监控告警已发送: {port_name} ({port}) - {status_change}")

        except Exception as e:
            self.logger.error(f"发送端口监控告警时出现异常: {e}")

    async def start_monitoring(self):
        """启动端口监控"""
        if self.running:
            self.logger.warning("端口监控服务已在运行中")
            return

        self.running = True
        self.logger.info(f"🚀 启动端口监控服务，监控间隔: {self.monitor_interval}秒")

        # 立即执行一次检查
        await self.check_all_ports()

        # 启动定期监控任务
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self):
        """停止端口监控"""
        if not self.running:
            return

        self.running = False
        self.logger.info("🛑 正在停止端口监控服务...")

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None

        self.logger.info("✅ 端口监控服务已停止")

    async def _monitor_loop(self):
        """监控循环"""
        try:
            while self.running:
                await asyncio.sleep(self.monitor_interval)
                if self.running:  # 再次检查，防止在睡眠期间被停止
                    try:
                        await self.check_all_ports()
                    except Exception as e:
                        self.logger.error(f"❌ 端口监控检查失败: {e}")
        except asyncio.CancelledError:
            self.logger.info("端口监控循环已取消")
        except Exception as e:
            self.logger.error(f"❌ 端口监控循环异常: {e}")

    def get_current_status(self) -> Dict[str, Any]:
        """获取当前端口状态缓存"""
        return {
            "running": self.running,
            "monitor_interval": self.monitor_interval,
            "monitor_host": self.monitor_host,
            "ports_count": len(self.ports_config),
            "ports_config": self.ports_config,
            "cached_status": self.port_status_cache,
            "last_check": max(
                (status.get("last_check", "") for status in self.port_status_cache.values()),
                default=""
            )
        }

    async def get_health_summary(self) -> Dict[str, Any]:
        """获取端口健康摘要"""
        results = await self.check_all_ports()
        return {
            "overall_status": results["status"],
            "timestamp": results["timestamp"],
            "summary": results["summary"],
            "ports": [
                {
                    "port": p["port"],
                    "name": p["name"],
                    "status": p["status"],
                    "response_time_ms": p.get("response_time_ms"),
                    "last_check": p["last_check"]
                }
                for p in results["ports"]
            ]
        }


# ==================== 全局实例 ====================

_port_monitor_service: Optional[PortMonitorService] = None


def get_port_monitor_service() -> PortMonitorService:
    """获取全局端口监控服务实例"""
    global _port_monitor_service
    if _port_monitor_service is None:
        _port_monitor_service = PortMonitorService()
    return _port_monitor_service


# ==================== 便捷函数 ====================

async def start_port_monitoring(monitor_interval: int = 300) -> PortMonitorService:
    """启动端口监控服务"""
    service = get_port_monitor_service()
    service.monitor_interval = monitor_interval
    await service.start_monitoring()
    return service


async def stop_port_monitoring():
    """停止端口监控服务"""
    service = get_port_monitor_service()
    await service.stop_monitoring()


def get_port_monitor_status() -> Dict[str, Any]:
    """获取端口监控状态"""
    service = get_port_monitor_service()
    return service.get_current_status()

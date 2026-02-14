"""
告警管理器
统一管理告警渠道和规则

功能：
1. 支持多种告警渠道（飞书、钉钉、邮件等）
2. 告警级别管理
3. 告警规则过滤
4. 告警重试机制


"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    SYSTEM_ERROR = "system_error"
    AGENT_FAILURE = "agent_failure"
    DATABASE_ERROR = "database_error"
    LLM_TIMEOUT = "llm_timeout"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    PORT_DOWN = "port_down"
    PERFORMANCE = "performance"


class JubenAlertManager:
    """
    Juben告警管理器

    功能：
    1. 统一告警接口
    2. 多渠道告警支持
    3. 告警级别管理
    4. 告警规则过滤
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.enabled = True
        self.alert_channels = {}

        # 从环境变量加载配置
        self._load_config()

        # 初始化告警渠道
        self._init_channels()

    def _load_config(self):
        """从环境变量加载配置"""
        self.enabled = os.getenv('ALERT_ENABLE', 'false').lower() == 'true'
        self.config = {
            'default_level': os.getenv('ALERT_LEVEL', 'WARNING'),
            'feishu_webhook': os.getenv('FEISHU_WEBHOOK_URL', ''),
            'feishu_secret': os.getenv('FEISHU_WEBHOOK_SECRET', ''),
            'retry_times': int(os.getenv('ALERT_RETRY_TIMES', '3')),
            'timeout': int(os.getenv('ALERT_TIMEOUT', '10'))
        }

        if self.enabled:
            self.logger.info("✅ 告警系统已启用")
        else:
            self.logger.info("⚠️ 告警系统已禁用")

    def _init_channels(self):
        """初始化告警渠道"""
        if not self.enabled:
            return

        # 初始化飞书告警
        if self.config['feishu_webhook']:
            self.alert_channels['feishu'] = {
                'webhook': self.config['feishu_webhook'],
                'secret': self.config['feishu_secret'],
                'enabled': True
            }
            self.logger.info("✅ 飞书告警渠道已初始化")

        if not self.alert_channels:
            self.logger.warning("⚠️ 没有可用的告警渠道")

    async def send_alert(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送告警消息

        Args:
            alert_type: 告警类型
            title: 告警标题
            message: 告警消息
            level: 告警级别
            extra_data: 额外数据

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled or not self.alert_channels:
            return False

        try:
            # 检查告警级别
            default_level = AlertLevel(self.config['default_level'])
            level_priority = {
                AlertLevel.INFO: 1,
                AlertLevel.WARNING: 2,
                AlertLevel.ERROR: 3,
                AlertLevel.CRITICAL: 4
            }

            if level_priority.get(level, 2) < level_priority.get(default_level, 2):
                self.logger.debug(f"告警级别过滤：{level.value} < {default_level.value}")
                return False

            # 并发发送到所有渠道
            send_tasks = []
            for channel_name, channel_config in self.alert_channels.items():
                if channel_config.get('enabled', False):
                    task = self._send_to_channel(
                        channel_name,
                        channel_config,
                        title,
                        message,
                        level,
                        extra_data
                    )
                    send_tasks.append(task)

            if not send_tasks:
                return False

            # 等待所有发送任务完成
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            success_count = sum(1 for result in results if result is True)

            if success_count > 0:
                self.logger.info(f"✅ 告警发送完成：{success_count}/{len(results)} 个渠道成功")
                return True
            else:
                self.logger.error(f"❌ 告警发送失败：0/{len(results)} 个渠道成功")
                return False

        except Exception as e:
            self.logger.error(f"❌ 发送告警失败: {e}")
            return False

    async def _send_to_channel(
        self,
        channel_name: str,
        channel_config: Dict[str, Any],
        title: str,
        message: str,
        level: AlertLevel,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """发送告警到指定渠道"""
        try:
            if channel_name == 'feishu':
                return await self._send_feishu_alert(
                    channel_config,
                    title,
                    message,
                    level,
                    extra_data
                )
            else:
                self.logger.warning(f"⚠️ 未知的告警渠道: {channel_name}")
                return False

        except Exception as e:
            self.logger.error(f"❌ 发送告警到 {channel_name} 失败: {e}")
            return False

    async def _send_feishu_alert(
        self,
        channel_config: Dict[str, Any],
        title: str,
        message: str,
        level: AlertLevel,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """发送飞书告警"""
        try:
            import hashlib
            import hmac
            import base64
            import time
            import json

            webhook_url = channel_config['webhook']
            secret = channel_config.get('secret', '')

            # 构建消息内容
            level_emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }

            emoji = level_emoji.get(level, "⚠️")

            content = {
                "msg_type": "text",
                "content": {
                    "text": f"{emoji} {title}\n\n{message}"
                }
            }

            # 如果有额外数据，添加到消息中
            if extra_data:
                extra_text = "\n\n**详细信息：**\n"
                for key, value in extra_data.items():
                    extra_text += f"- {key}: {value}\n"
                content["content"]["text"] += extra_text

            # 添加签名（如果配置了secret）
            headers = {"Content-Type": "application/json"}

            if secret:
                timestamp = str(int(time.time()))
                secret_enc = secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')

                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = base64.b64encode(hmac_code).decode('utf-8')

                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            # 发送请求
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config['timeout'])

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    webhook_url,
                    json=content,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('StatusCode') == 0:
                            return True
                        else:
                            self.logger.error(f"飞书告警失败: {result}")
                            return False
                    else:
                        error_text = await response.text()
                        self.logger.error(f"飞书告警HTTP错误: {response.status} - {error_text}")
                        return False

        except ImportError:
            self.logger.error("⚠️ aiohttp未安装，无法发送飞书告警")
            return False
        except Exception as e:
            self.logger.error(f"❌ 发送飞书告警异常: {e}")
            return False

    async def send_port_monitor_alert(
        self,
        port: int,
        port_name: str,
        host: str,
        error_message: str,
        status_change: str = "down",
        environment: str = "unknown"
    ) -> bool:
        """
        发送端口监控告警

        Args:
            port: 端口号
            port_name: 端口名称
            host: 主机地址
            error_message: 错误消息
            status_change: 状态变化（down/up/timeout）
            environment: 环境类型

        Returns:
            bool: 是否发送成功
        """
        # 环境标识
        env_tag = f"[{environment}]"

        # 根据状态变化确定告警级别和标题
        if status_change == "down":
            title = f"🚨 {env_tag}{port_name}服务异常"
            level = AlertLevel.CRITICAL
            message = f"{env_tag} 端口 {port} ({port_name}) 服务可能已停止或重启"
        elif status_change == "timeout":
            title = f"⚠️ {env_tag}{port_name}服务响应超时"
            level = AlertLevel.WARNING
            message = f"{env_tag} 端口 {port} ({port_name}) 连接超时，服务可能负载过高"
        elif status_change == "up":
            title = f"✅ {env_tag}{port_name}服务恢复正常"
            level = AlertLevel.INFO
            message = f"{env_tag} 端口 {port} ({port_name}) 服务已恢复正常运行"
        else:
            title = f"❌ {env_tag}{port_name}服务状态异常"
            level = AlertLevel.ERROR
            message = f"{env_tag} 端口 {port} ({port_name}) 服务状态异常"

        message += f"\n错误详情: {error_message}"

        extra_data = {
            "port": port,
            "port_name": port_name,
            "host": host,
            "status_change": status_change,
            "error_message": error_message,
            "environment": environment,
            "timestamp": datetime.now().isoformat()
        }

        return await self.send_alert(
            alert_type=AlertType.PORT_DOWN,
            title=title,
            message=message,
            level=level,
            extra_data=extra_data
        )

    async def send_system_error_alert(
        self,
        component: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送系统错误告警

        Args:
            component: 组件名称
            error_message: 错误消息
            error_details: 错误详情

        Returns:
            bool: 是否发送成功
        """
        title = f"{component} 系统错误"
        message = f"组件 {component} 发生错误：{error_message}"

        extra_data = {"component": component, "timestamp": datetime.now().isoformat()}
        if error_details:
            extra_data.update(error_details)

        return await self.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            title=title,
            message=message,
            level=AlertLevel.ERROR,
            extra_data=extra_data
        )

    def get_status(self) -> Dict[str, Any]:
        """获取告警系统状态"""
        return {
            "enabled": self.enabled,
            "channels": list(self.alert_channels.keys()),
            "default_level": self.config['default_level'],
            "config_loaded": bool(self.config)
        }


# ==================== 全局实例 ====================

_alert_manager: Optional[JubenAlertManager] = None


def get_alert_manager() -> JubenAlertManager:
    """获取告警管理器单例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = JubenAlertManager()
    return _alert_manager


# ==================== 便捷函数 ====================

async def send_alert(
    alert_type: AlertType,
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.WARNING,
    extra_data: Optional[Dict[str, Any]] = None
) -> bool:
    """发送告警"""
    manager = get_alert_manager()
    return await manager.send_alert(alert_type, title, message, level, extra_data)


async def send_port_alert(
    port: int,
    port_name: str,
    host: str,
    error_message: str,
    status_change: str = "down",
    environment: str = "unknown"
) -> bool:
    """发送端口监控告警"""
    manager = get_alert_manager()
    return await manager.send_port_monitor_alert(
        port, port_name, host, error_message, status_change, environment
    )


async def send_system_error_alert(
    component: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> bool:
    """发送系统错误告警"""
    manager = get_alert_manager()
    return await manager.send_system_error_alert(component, error_message, error_details)

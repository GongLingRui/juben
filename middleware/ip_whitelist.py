"""
IP 白名单中间件

限制只有白名单中的 IP 地址才能访问系统
"""
import os
from typing import Optional, List, Set, Callable, Awaitable
from ipaddress import ip_network, ip_address, IPv4Network, IPv6Network, AddressValueError
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN

from utils.logger import get_logger
from utils.constants import IPWhitelistConstants

logger = get_logger("IPWhitelistMiddleware")


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP 白名单中间件

    功能：
    1. 基于 IP 白名单控制访问
    2. 支持单个 IP 和 IP 范围（CIDR）
    3. 支持多种检查模式
    4. 自动识别代理和负载均衡器转发的真实 IP
    """

    def __init__(
        self,
        app,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
        mode: str = IPWhitelistConstants.MODE_ALLOW,
        cache_ttl: int = IPWhitelistConstants.CACHE_TTL,
        trusted_proxies: Optional[List[str]] = None,
    ):
        """
        初始化 IP 白名单中间件

        Args:
            app: ASGI 应用
            whitelist: IP 白名单列表
            blacklist: IP 黑名单列表
            mode: 检查模式 (allow/deny/hybrid)
            cache_ttl: 缓存时间（秒）
            trusted_proxies: 受信任的代理 IP 列表
        """
        super().__init__(app)
        self.mode = mode
        self.cache_ttl = cache_ttl
        self._ip_cache: dict[str, bool] = {}

        # 解析白名单
        self._whitelist_networks: Set[object] = set()
        self._whitelist_ips: Set[str] = set()

        if whitelist:
            for ip_entry in whitelist:
                self._parse_ip_entry(ip_entry, self._whitelist_networks, self._whitelist_ips)
        else:
            # 使用默认白名单
            for ip_entry in IPWhitelistConstants.DEFAULT_WHITELIST:
                self._parse_ip_entry(ip_entry, self._whitelist_networks, self._whitelist_ips)

        # 解析黑名单
        self._blacklist_networks: Set[object] = set()
        self._blacklist_ips: Set[str] = set()

        if blacklist:
            for ip_entry in blacklist:
                self._parse_ip_entry(ip_entry, self._blacklist_networks, self._blacklist_ips)

        # 解析受信任的代理
        self._trusted_proxy_networks: Set[object] = set()
        if trusted_proxies:
            for proxy_entry in trusted_proxies:
                self._parse_ip_entry(proxy_entry, self._trusted_proxy_networks, set())
        else:
            # 默认信任私有 IP 范围作为代理
            for network in IPWhitelistConstants.PRIVATE_IP_RANGES:
                try:
                    self._trusted_proxy_networks.add(ip_network(network))
                except ValueError:
                    pass

        logger.info(f"✅ IP 白名单中间件已初始化 (模式: {mode})")
        logger.info(f"   白名单: {len(self._whitelist_ips)} 个 IP, {len(self._whitelist_networks)} 个网络")
        logger.info(f"   黑名单: {len(self._blacklist_ips)} 个 IP, {len(self._blacklist_networks)} 个网络")

    def _parse_ip_entry(self, entry: str, networks_set: Set, ips_set: Set):
        """解析 IP 条目"""
        try:
            # 尝试解析为网络
            if "/" in entry:
                networks_set.add(ip_network(entry, strict=False))
            else:
                # 单个 IP
                ips_set.add(entry)
        except ValueError as e:
            logger.warning(f"⚠️ 无法解析 IP 条目 '{entry}': {e}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        client_ip = self._extract_client_ip(request)

        if not client_ip:
            # 无法获取 IP，放行
            return await call_next(request)

        # 检查 IP 是否被允许
        if not self._is_ip_allowed(client_ip):
            logger.warning(f"⚠️ IP 被拒绝访问: {client_ip} - {request.url.path}")
            return self._error_response(client_ip)

        return await call_next(request)

    def _extract_client_ip(self, request: Request) -> Optional[str]:
        """提取客户端真实 IP"""
        # 尝试从各种 header 中获取真实 IP
        headers_to_check = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",
            "x-client-ip",
            "true-client-ip"
        ]

        for header in headers_to_check:
            ip_value = request.headers.get(header)
            if ip_value:
                # x-forwarded-for 可能包含多个 IP
                ips = [ip.strip() for ip in ip_value.split(",")]
                for ip_str in ips:
                    if ip_str:
                        try:
                            ip_obj = ip_address(ip_str)
                            # 检查是否是受信任的代理
                            if self._is_trusted_proxy(ip_obj):
                                continue
                            return ip_str
                        except AddressValueError:
                            continue

        # 回退到直接连接的 IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None

    def _is_trusted_proxy(self, ip) -> bool:
        """检查 IP 是否为受信任的代理"""
        for network in self._trusted_proxy_networks:
            if ip in network:
                return True
        return False

    def _is_ip_allowed(self, ip_str: str) -> bool:
        """检查 IP 是否被允许"""
        # 检查缓存
        if ip_str in self._ip_cache:
            return self._ip_cache[ip_str]

        try:
            ip = ip_address(ip_str)
            result = self._check_ip_rules(ip)

            # 缓存结果
            self._ip_cache[ip_str] = result
            return result

        except AddressValueError:
            logger.warning(f"⚠️ 无效的 IP 地址: {ip_str}")
            return False

    def _check_ip_rules(self, ip) -> bool:
        """检查 IP 规则"""
        # 首先检查黑名单
        if self._is_ip_in_list(ip, self._blacklist_ips, self._blacklist_networks):
            return False

        # 如果是拒绝模式，不在黑名单就放行
        if self.mode == IPWhitelistConstants.MODE_DENY:
            return True

        # 如果是允许模式，必须在白名单中
        if self.mode == IPWhitelistConstants.MODE_ALLOW:
            return self._is_ip_in_list(ip, self._whitelist_ips, self._whitelist_networks)

        # 混合模式：在白名单或不在黑名单
        if self.mode == "hybrid":
            in_whitelist = self._is_ip_in_list(ip, self._whitelist_ips, self._whitelist_networks)
            return in_whitelist

        return True

    def _is_ip_in_list(self, ip, ips: Set[str], networks: Set) -> bool:
        """检查 IP 是否在列表中"""
        # 检查精确匹配
        if str(ip) in ips:
            return True

        # 检查网络范围
        for network in networks:
            if ip in network:
                return True

        return False

    def _error_response(self, ip: str) -> JSONResponse:
        """返回错误响应"""
        return JSONResponse(
            status_code=HTTP_403_FORBIDDEN,
            content={
                "detail": f"您的 IP 地址 ({ip}) 无权访问此资源",
                "code": "IP_NOT_ALLOWED"
            }
        )

    def add_whitelist_entry(self, ip_entry: str) -> bool:
        """动态添加白名单条目"""
        try:
            self._parse_ip_entry(ip_entry, self._whitelist_networks, self._whitelist_ips)
            # 清除缓存
            self._ip_cache.clear()
            logger.info(f"✅ 已添加白名单条目: {ip_entry}")
            return True
        except Exception as e:
            logger.error(f"❌ 添加白名单条目失败: {e}")
            return False

    def remove_whitelist_entry(self, ip_entry: str) -> bool:
        """动态移除白名单条目"""
        try:
            # 尝试移除单个 IP
            if ip_entry in self._whitelist_ips:
                self._whitelist_ips.remove(ip_entry)
            else:
                # 尝试移除网络
                network = ip_network(ip_entry, strict=False)
                if network in self._whitelist_networks:
                    self._whitelist_networks.remove(network)
                else:
                    return False

            # 清除缓存
            self._ip_cache.clear()
            logger.info(f"✅ 已移除白名单条目: {ip_entry}")
            return True
        except Exception as e:
            logger.error(f"❌ 移除白名单条目失败: {e}")
            return False

    def get_whitelist(self) -> dict:
        """获取当前白名单"""
        ips = list(self._whitelist_ips)
        networks = [str(n) for n in self._whitelist_networks]
        return {
            "ips": ips,
            "networks": networks,
            "mode": self.mode
        }


class IPWhitelistManager:
    """IP 白名单管理器"""

    def __init__(self):
        self._middleware: Optional[IPWhitelistMiddleware] = None

    def configure(
        self,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
        mode: str = IPWhitelistConstants.MODE_ALLOW,
    ):
        """配置 IP 白名单"""
        from main import app

        self._middleware = IPWhitelistMiddleware(
            app,
            whitelist=whitelist,
            blacklist=blacklist,
            mode=mode
        )

        return self._middleware

    def get_middleware(self) -> Optional[IPWhitelistMiddleware]:
        """获取中间件实例"""
        return self._middleware

    def add_ip(self, ip_entry: str) -> bool:
        """添加 IP 到白名单"""
        if self._middleware:
            return self._middleware.add_whitelist_entry(ip_entry)
        return False

    def remove_ip(self, ip_entry: str) -> bool:
        """从白名单移除 IP"""
        if self._middleware:
            return self._middleware.remove_whitelist_entry(ip_entry)
        return False

    def get_whitelist(self) -> Optional[dict]:
        """获取白名单"""
        if self._middleware:
            return self._middleware.get_whitelist()
        return None


# 全局 IP 白名单管理器实例
_ip_whitelist_manager: Optional[IPWhitelistManager] = None


def get_ip_whitelist_manager() -> IPWhitelistManager:
    """获取 IP 白名单管理器单例"""
    global _ip_whitelist_manager
    if _ip_whitelist_manager is None:
        _ip_whitelist_manager = IPWhitelistManager()
    return _ip_whitelist_manager


# 从环境变量加载配置
def load_ip_whitelist_from_env():
    """从环境变量加载 IP 白名单配置"""
    import os

    whitelist_str = os.getenv("IP_WHITELIST", "")
    blacklist_str = os.getenv("IP_BLACKLIST", "")
    mode = os.getenv("IP_WHITELIST_MODE", IPWhitelistConstants.MODE_ALLOW)

    whitelist = [ip.strip() for ip in whitelist_str.split(",") if ip.strip()] if whitelist_str else None
    blacklist = [ip.strip() for ip in blacklist_str.split(",") if ip.strip()] if blacklist_str else None

    manager = get_ip_whitelist_manager()
    return manager.configure(
        whitelist=whitelist,
        blacklist=blacklist,
        mode=mode
    )

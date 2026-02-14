"""
API 版本控制中间件

支持多版本 API 并行运行
"""
import re
from typing import Optional, Callable, Awaitable, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_410_GONE

from utils.logger import get_logger
from utils.constants import APIVersionConstants

logger = get_logger("APIVersioning")


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    API 版本控制中间件

    功能：
    1. 支持多版本 API
    2. 版本弃用警告
    3. 从请求中提取版本信息
    4. 自动添加版本响应头
    """

    def __init__(
        self,
        app,
        current_version: str = APIVersionConstants.CURRENT_VERSION,
        supported_versions: List[str] = None,
        deprecated_versions: dict = None,
        version_header: str = APIVersionConstants.VERSION_HEADER,
        version_query_param: str = APIVersionConstants.VERSION_QUERY_PARAM,
    ):
        """
        初始化 API 版本控制中间件

        Args:
            app: ASGI 应用
            current_version: 当前版本
            supported_versions: 支持的版本列表
            deprecated_versions: 弃用的版本 {version: deprecation_date}
            version_header: 版本 header 名称
            version_query_param: 版本查询参数名称
        """
        super().__init__(app)
        self.current_version = current_version
        self.supported_versions = supported_versions or APIVersionConstants.SUPPORTED_VERSIONS.copy()
        self.deprecated_versions = deprecated_versions or APIVersionConstants.DEPRECATED_VERSIONS.copy()
        self.version_header = version_header
        self.version_query_param = version_query_param

        logger.info(f"✅ API 版本控制已初始化 (当前版本: {current_version})")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 提取版本
        version = self._extract_version(request) or self.current_version

        # 验证版本
        error_response = self._validate_version(version, request)
        if error_response:
            return error_response

        # 将版本添加到 request.state
        request.state.api_version = version

        # 处理请求
        response = await call_next(request)

        # 添加版本响应头
        self._add_version_headers(response, version)

        return response

    def _extract_version(self, request: Request) -> Optional[str]:
        """从请求中提取版本"""
        # 1. 从 header 获取
        version = request.headers.get(self.version_header)
        if version:
            return version.lstrip("v")

        # 2. 从查询参数获取
        version = request.query_params.get(self.version_query_param)
        if version:
            return version.lstrip("v")

        # 3. 从 URL 路径获取
        # 例如: /api/v1/users -> v1
        match = re.match(r"^/api/v(\d+)", request.url.path)
        if match:
            return f"v{match.group(1)}"

        return None

    def _validate_version(self, version: str, request: Request) -> Optional[JSONResponse]:
        """验证版本"""
        # 标准化版本格式
        if not version.startswith("v"):
            version = f"v{version}"

        # 检查版本是否支持
        if version not in self.supported_versions:
            return JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content={
                    "detail": f"不支持的 API 版本: {version}",
                    "code": "UNSUPPORTED_API_VERSION",
                    "supported_versions": self.supported_versions
                }
            )

        # 检查版本是否已弃用
        if version in self.deprecated_versions:
            deprecation_date = self.deprecated_versions[version]
            logger.info(f"⚠️ 使用已弃用的 API 版本: {version} (弃用日期: {deprecation_date})")

            # 返回警告响应头
            response = JSONResponse(
                status_code=HTTP_410_GONE,
                content={
                    "detail": f"API 版本 {version} 已弃用，将在 {deprecation_date} 停止支持",
                    "code": "API_VERSION_DEPRECATED",
                    "current_version": self.current_version
                }
            )
            return response

        return None

    def _add_version_headers(self, response: Response, version: str):
        """添加版本响应头"""
        response.headers[APIVersionConstants.API_VERSION_HEADER] = version

        if version != self.current_version:
            response.headers["X-API-Current-Version"] = self.current_version

        if version in self.deprecated_versions:
            response.headers[APIVersionConstants.API_DEPRECATED_HEADER] = self.deprecated_versions[version]


class APIVersionRouter:
    """
    API 版本路由器

    帮助管理多版本 API 路由
    """

    def __init__(self):
        self._version_handlers: dict[str, dict] = {}  # version -> {path: handler}

    def add_route(
        self,
        version: str,
        path: str,
        handler: Callable,
        methods: List[str] = None
    ):
        """
        添加版本路由

        Args:
            version: API 版本 (v1, v2)
            path: 路径
            handler: 处理函数
            methods: 允许的 HTTP 方法
        """
        if version not in self._version_handlers:
            self._version_handlers[version] = {}

        self._version_handlers[version][path] = {
            "handler": handler,
            "methods": methods or ["GET"]
        }

        logger.info(f"✅ 添加路由: {version}{path}")

    def get_handler(self, version: str, path: str) -> Optional[Callable]:
        """获取指定版本和路径的处理函数"""
        version_routes = self._version_handlers.get(version)
        if version_routes:
            route = version_routes.get(path)
            if route:
                return route["handler"]

        # 如果没有找到，尝试在当前版本中查找
        current_routes = self._version_handlers.get(APIVersionConstants.CURRENT_VERSION)
        if current_routes and path in current_routes:
            logger.warning(f"⚠️ 路由 {path} 在版本 {version} 中不存在，使用当前版本")
            return current_routes[path]["handler"]

        return None

    def list_routes(self, version: Optional[str] = None) -> dict:
        """
        列出路由

        Args:
            version: 指定版本，None 表示所有版本

        Returns:
            路由字典
        """
        if version:
            return self._version_handlers.get(version, {})
        return self._version_handlers


# 全局 API 版本路由器实例
_api_version_router: Optional[APIVersionRouter] = None


def get_api_version_router() -> APIVersionRouter:
    """获取 API 版本路由器单例"""
    global _api_version_router
    if _api_version_router is None:
        _api_version_router = APIVersionRouter()
    return _api_version_router


# 版本化路由装饰器
def api_version(version: str, path: str = "", methods: List[str] = None):
    """
    API 版本化路由装饰器

    使用示例:
    @api_version("v1", "/users", methods=["GET", "POST"])
    async def get_users(request: Request):
        return {"users": []}
    """
    def decorator(func: Callable):
        router = get_api_version_router()
        router.add_route(version, path, func, methods)
        return func
    return decorator


# 版本兼容性检查
def check_version_compatibility(
    requested_version: str,
    min_version: Optional[str] = None,
    max_version: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    检查版本兼容性

    Args:
        requested_version: 请求的版本
        min_version: 最低支持版本
        max_version: 最高支持版本

    Returns:
        (是否兼容, 错误消息)
    """
    # 标准化版本
    if not requested_version.startswith("v"):
        requested_version = f"v{requested_version}"

    # 提取版本号
    match = re.match(r"v(\d+)", requested_version)
    if not match:
        return False, f"无效的版本格式: {requested_version}"

    version_num = int(match.group(1))

    # 检查最低版本
    if min_version:
        min_match = re.match(r"v(\d+)", min_version)
        if min_match:
            min_num = int(min_match.group(1))
            if version_num < min_num:
                return False, f"版本 {requested_version} 不支持，最低需要版本 {min_version}"

    # 检查最高版本
    if max_version:
        max_match = re.match(r"v(\d+)", max_version)
        if max_match:
            max_num = int(max_match.group(1))
            if version_num > max_num:
                return False, f"版本 {requested_version} 不支持，最高支持版本 {max_version}"

    return True, None

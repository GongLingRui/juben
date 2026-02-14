"""
CORS 中间件配置
支持前端跨域请求
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from typing import List


def add_cors_middleware(app: FastAPI) -> None:
    """
    添加 CORS 中间件到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    # 允许的源列表
    allow_origins: List[str] = [
        "http://localhost:5173",      # Vite 开发服务器
        "http://localhost:3000",      # 备用端口
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # 生产环境需要添加实际的域名
        "https://your-domain.com",
    ]

    # 如果是开发环境，允许所有源
    import os
    if os.getenv("DEBUG", "false").lower() == "true":
        allow_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False if allow_origins == ["*"] else True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


# CORS 配置类
class CORSMiddlewareConfig:
    """CORS 中间件配置"""

    ALLOW_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: List[str] = ["*"]
    ALLOW_HEADERS: List[str] = ["*"]
    EXPOSE_HEADERS: List[str] = ["*"]

    @classmethod
    def add_to_app(cls, app: FastAPI) -> None:
        """添加 CORS 中间件到应用"""
        import os

        allow_origins = cls.ALLOW_ORIGINS
        if os.getenv("DEBUG", "false").lower() == "true":
            allow_origins = ["*"]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=False if allow_origins == ["*"] else cls.ALLOW_CREDENTIALS,
            allow_methods=cls.ALLOW_METHODS,
            allow_headers=cls.ALLOW_HEADERS,
            expose_headers=cls.EXPOSE_HEADERS,
        )

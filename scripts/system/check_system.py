#!/usr/bin/env python3
"""
系统状态检查脚本
检查系统各组件的运行状态和配置
"""
import os
import sys
import logging
from pathlib import Path
from typing import List
import importlib

logger = logging.getLogger(__name__)


def check_python_version():
    """检查Python版本"""
    logger.info("🐍 Python版本检查:")
    logger.info(f"   版本: {sys.version}")
    logger.info(f"   路径: {sys.executable}")

    if sys.version_info < (3, 8):
        logger.warning("   ❌ Python版本过低，建议使用3.8+")
        return False
    else:
        logger.info("   ✅ Python版本符合要求")
        return True


def check_dependencies():
    """检查依赖包"""
    logger.info("\n📦 依赖包检查:")

    required_packages = [
        'fastapi', 'uvicorn', 'pydantic', 'pydantic_settings',
        'redis', 'pymilvus', 'asyncpg', 'numpy', 'psutil'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            importlib.import_module(package)
            logger.info(f"   ✅ {package}")
        except ImportError:
            logger.error(f"   ❌ {package} - 未安装")
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"\n   缺失的包: {', '.join(missing_packages)}")
        logger.info("   请运行: pip install -r requirements.txt")
        return False
    else:
        logger.info("   ✅ 所有依赖包已安装")
        return True


def check_database():
    """检查数据库连接"""
    logger.info("\n💾 数据库检查:")

    try:
        import psycopg2
        logger.info("   ✅ psycopg2 已安装")
        return True
    except ImportError:
        logger.error("   ❌ psycopg2 未安装")
        return False


def check_redis():
    """检查Redis连接"""
    logger.info("\n📮 Redis检查:")

    try:
        import redis
        logger.info("   ✅ Redis 客户端库已安装")
        return True
    except ImportError:
        logger.warning("   ⚠️ Redis 客户端库未安装（可选）")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🔍 剧本创作 Agent 平台 - 系统检查")
    logger.info("=" * 60)

    checks = []

    # 检查Python版本
    python_ok = check_python_version()
    checks.append(("Python版本", python_ok))

    # 检查依赖包
    deps_ok = check_dependencies()
    checks.append(("依赖包", deps_ok))

    # 检查数据库
    db_ok = check_database()
    checks.append(("PostgreSQL", db_ok))

    # 检查Redis
    redis_ok = check_redis()
    checks.append(("Redis", redis_ok))

    # 显示检查结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 检查结果汇总:")
    logger.info("=" * 60)

    for name, result in checks:
        status = "✅ 正常" if result else "❌ 异常"
        logger.info(f"{status} {name}")

    # 计算健康分数
    healthy_count = sum(1 for _, result in checks if result)
    health_score = (healthy_count / len(checks)) * 100

    logger.info("\n" + "=" * 60)
    logger.info(f"💚 系统健康度: {health_score:.0f}%")

    if health_score >= 80:
        logger.info("✅ 系统状态良好")
        return 0
    elif health_score >= 50:
        logger.warning("⚠️ 系统存在警告")
        return 1
    else:
        logger.error("❌ 系统存在严重问题")
        return 2


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n🛑 用户中断检查")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ 系统检查失败: {e}")
        sys.exit(1)

"""
启动验证模块
在应用启动前验证关键配置是否正确
"""
import os
import sys
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class StartupValidationError(Exception):
    """启动验证错误"""
    pass


def validate_jwt_config() -> Tuple[bool, str]:
    """验证 JWT 配置"""
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    default_secret = "your-secret-key-change-this-in-production-min-32-chars"

    # 检查是否为空
    if not jwt_secret:
        return False, "JWT_SECRET_KEY 环境变量未设置"

    # 检查长度
    if len(jwt_secret) < 32:
        return False, f"JWT_SECRET_KEY 长度不足: {len(jwt_secret)} < 32"

    # 检查是否为默认值
    if jwt_secret == default_secret:
        return False, "JWT_SECRET_KEY 使用默认值，存在安全风险"

    # 检查是否包含足够的熵（避免简单密码）
    if jwt_secret in ["secret", "password", "123456", "admin"]:
        return False, "JWT_SECRET_KEY 过于简单，容易被破解"

    return True, "OK"


def validate_database_config() -> Tuple[bool, str]:
    """验证数据库配置"""
    required_vars = []

    # PostgreSQL 配置
    if not os.getenv("DATABASE_URL"):
        required_vars.append("DATABASE_URL")

    # Redis 配置（可选但推荐）
    # if not os.getenv("REDIS_URL"):
    #     required_vars.append("REDIS_URL")

    if required_vars:
        return False, f"缺少必需的数据库配置: {', '.join(required_vars)}"

    return True, "OK"


def validate_admin_config() -> Tuple[bool, str]:
    """验证管理员配置"""
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username:
        return False, "ADMIN_USERNAME 环境变量未设置"

    if not admin_password:
        return False, "ADMIN_PASSWORD 环境变量未设置"

    if len(admin_password) < 8:
        return False, "ADMIN_PASSWORD 长度不足 8 位"

    # 检查默认密码
    if admin_password in ["admin123", "password", "12345678"]:
        return False, "ADMIN_PASSWORD 使用默认值，存在安全风险"

    return True, "OK"


def validate_api_config() -> Tuple[bool, str]:
    """验证 API 配置"""
    # 检查智谱 AI 配置
    zhipu_key = os.getenv("ZHIPUAI_API_KEY")
    if not zhipu_key:
        return False, "ZHIPUAI_API_KEY 环境变量未设置"

    return True, "OK"


def validate_cors_config() -> Tuple[bool, str]:
    """验证 CORS 配置"""
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "")

    # 检查是否允许所有来源
    if "*" in allowed_origins or allowed_origins == "":
        app_env = os.getenv("APP_ENV", "development")
        if app_env == "production":
            return False, "生产环境不能使用 '*' 作为 CORS 来源"

    return True, "OK"


def validate_environment() -> Tuple[bool, str]:
    """验证环境配置"""
    app_env = os.getenv("APP_ENV", "development")

    if app_env not in ["development", "staging", "production"]:
        return False, f"无效的 APP_ENV: {app_env}"

    return True, "OK"


def run_startup_validation(strict: bool = True) -> List[Tuple[str, bool, str]]:
    """
    运行启动验证

    Args:
        strict: 是否严格模式（失败则退出）

    Returns:
        验证结果列表 [(名称, 是否通过, 消息)]
    """
    validators = [
        ("环境配置", validate_environment),
        ("JWT 配置", validate_jwt_config),
        ("数据库配置", validate_database_config),
        ("管理员配置", validate_admin_config),
        ("API 配置", validate_api_config),
        ("CORS 配置", validate_cors_config),
    ]

    results = []
    all_passed = True

    logger.info("=" * 60)
    logger.info("🔍 启动配置验证")
    logger.info("=" * 60)

    for name, validator in validators:
        try:
            passed, message = validator()
            results.append((name, passed, message))

            status = "✅" if passed else "❌"
            logger.info(f"{status} {name}: {message}")

            if not passed:
                all_passed = False

        except Exception as e:
            results.append((name, False, f"验证异常: {str(e)}"))
            logger.error(f"❌ {name}: 验证异常 - {str(e)}")
            all_passed = False

    logger.info("=" * 60)

    if not all_passed:
        if strict:
            logger.error("❌ 配置验证失败，无法启动应用")
            logger.error("请修复上述问题后重试")
            raise StartupValidationError("配置验证失败")
        else:
            logger.warning("⚠️ 配置验证存在警告，但继续启动")
    else:
        logger.info("✅ 所有配置验证通过")

    return results


def get_startup_checklist() -> str:
    """获取启动检查清单"""
    return """
📋 启动前检查清单：

必需的环境变量：
  • JWT_SECRET_KEY (>=32 字符，非默认值)
  • DATABASE_URL
  • ADMIN_USERNAME
  • ADMIN_PASSWORD (>=8 字符，非默认值)
  • ZHIPUAI_API_KEY

可选的环境变量：
  • REDIS_URL (推荐，用于缓存和会话)
  • ALLOWED_ORIGINS (生产环境必须设置)
  • APP_ENV (development/staging/production)

示例 .env 文件：
  JWT_SECRET_KEY=your-production-secret-key-at-least-32-chars
  DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD=secure_password_here
  ZHIPUAI_API_KEY=your_zhipu_api_key
  ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  APP_ENV=production
"""


if __name__ == "__main__":
    # 直接运行此脚本进行配置检查
    try:
        run_startup_validation(strict=False)
        logger.info(get_startup_checklist())
    except StartupValidationError as e:
        logger.error(f"\n{get_startup_checklist()}")
        sys.exit(1)

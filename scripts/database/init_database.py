"""
Juben项目数据库初始化脚本
在PostgreSQL中创建所需的数据库表结构
"""
import os
import sys
import logging
from pathlib import Path
import asyncio

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)


async def init_database():
    """初始化数据库表结构"""
    logger.info("🚀 开始初始化Juben项目数据库...")
    logger.info("=" * 60)

    try:
        from utils.database_client import get_postgres_pool
        pool = await get_postgres_pool()
        logger.info("✅ PostgreSQL连接池获取成功")

        # 读取SQL文件
        sql_file = Path(__file__).parent / "migrations" / "0001_init.sql"
        if not sql_file.exists():
            logger.error(f"❌ SQL文件不存在: {sql_file}")
            return False

        sql_content = sql_file.read_text(encoding="utf-8")
        logger.info(f"📖 读取SQL文件成功: {len(sql_content)} 字符")

        # 执行SQL
        async with pool.acquire() as conn:
            await conn.execute(sql_content)

        logger.info("✅ 数据库初始化完成")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    logger.info("🚀 Juben项目数据库初始化工具")
    logger.info("=" * 80)

    success = asyncio.run(init_database())

    if success:
        logger.info("\n🎉 数据库初始化成功！")
    else:
        logger.error("\n⚠️ 数据库初始化失败！")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

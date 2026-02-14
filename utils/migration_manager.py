"""
数据库迁移管理器
支持Alembic和简化版迁移工具的统一接口
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.database_client import get_postgres_pool

logger = get_logger("MigrationManager")


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self):
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.versions_dir = self.migrations_dir / "versions"

    async def ensure_migration_table(self):
        """确保迁移记录表存在"""
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                );
                """
            )

    async def get_current_version(self) -> Optional[str]:
        """获取当前数据库版本"""
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchval(
                "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
            )
            return row

    async def get_applied_versions(self) -> List[str]:
        """获取所有已应用的迁移版本"""
        pool = await get_postgres_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT version_num FROM alembic_version")
            return [r["version_num"] for r in rows]

    async def get_pending_migrations(self) -> List[Path]:
        """获取待应用的迁移文件"""
        applied = set(await self.get_applied_versions())
        pending = []

        if self.versions_dir.exists():
            for migration_file in sorted(self.versions_dir.glob("*.py")):
                # 提取版本号（文件名第一部分）
                version = migration_file.name.split("_")[0]
                if version not in applied:
                    pending.append(migration_file)

        return pending

    async def apply_migration(self, migration_path: Path) -> bool:
        """应用单个迁移文件"""
        try:
            # 动态导入迁移模块
            module_name = migration_path.stem
            spec = __import__(
                f"migrations.versions.{module_name}",
                fromlist=["upgrade", "downgrade", "revision", "down_revision"]
            )

            revision = getattr(spec, "revision", None)
            if not revision:
                logger.error(f"迁移文件缺少 revision: {migration_path}")
                return False

            # 执行 upgrade
            logger.info(f"执行迁移: {revision} - {migration_path.name}")
            if hasattr(spec, "upgrade"):
                await spec.upgrade()

            # 记录版本
            pool = await get_postgres_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO alembic_version (version_num) VALUES ($1) "
                    "ON CONFLICT (version_num) DO NOTHING",
                    revision
                )

            logger.info(f"迁移成功: {revision}")
            return True

        except Exception as e:
            logger.error(f"应用迁移失败 {migration_path}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def upgrade(self, target_version: Optional[str] = None) -> bool:
        """升级数据库到指定版本或最新版本"""
        logger.info("=" * 60)
        logger.info("开始数据库迁移...")
        logger.info("=" * 60)

        await self.ensure_migration_table()

        current = await self.get_current_version()
        logger.info(f"当前数据库版本: {current or '无'}")

        pending = await self.get_pending_migrations()

        if not pending:
            logger.info("没有待应用的迁移")
            return True

        logger.info(f"发现 {len(pending)} 个待应用的迁移:")

        for migration_file in pending:
            logger.info(f"  - {migration_file.name}")
            success = await self.apply_migration(migration_file)
            if not success:
                logger.error(f"迁移失败，停止升级流程")
                return False

        logger.info("=" * 60)
        logger.info("数据库迁移完成")
        logger.info("=" * 60)
        return True

    async def downgrade(self, target_version: str) -> bool:
        """降级数据库到指定版本"""
        logger.warning("降级操作是危险操作，请谨慎使用")
        logger.info(f"目标版本: {target_version}")

        applied = await self.get_applied_versions()

        if target_version not in applied and target_version != "None":
            logger.error(f"目标版本 {target_version} 不在已应用版本中")
            return False

        # 找出需要回滚的迁移（倒序）
        to_rollback = []
        for version in reversed(applied):
            if version == target_version:
                break
            to_rollback.append(version)

        if not to_rollback:
            logger.info("无需回滚")
            return True

        logger.info(f"将回滚 {len(to_rollback)} 个迁移")

        for version in to_rollback:
            # 查找迁移文件
            migration_file = self.versions_dir / f"{version}_*.py"
            matches = list(self.versions_dir.glob(f"{version}_*.py"))

            if not matches:
                logger.error(f"找不到迁移文件: {version}")
                return False

            migration_path = matches[0]

            try:
                # 动态导入迁移模块
                module_name = migration_path.stem
                spec = __import__(
                    f"migrations.versions.{module_name}",
                    fromlist=["upgrade", "downgrade", "revision"]
                )

                # 执行 downgrade
                logger.info(f"回滚迁移: {version}")
                if hasattr(spec, "downgrade"):
                    await spec.downgrade()

                # 删除版本记录
                pool = await get_postgres_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "DELETE FROM alembic_version WHERE version_num = $1",
                        version
                    )

                logger.info(f"回滚成功: {version}")

            except Exception as e:
                logger.error(f"回滚失败 {version}: {e}")
                import traceback
                traceback.print_exc()
                return False

        logger.info("降级完成")
        return True

    async def status(self):
        """显示迁移状态"""
        await self.ensure_migration_table()

        current = await self.get_current_version()
        applied = await self.get_applied_versions()
        pending = await self.get_pending_migrations()

        logger.info("\n" + "=" * 60)
        logger.info("数据库迁移状态")
        logger.info("=" * 60)
        logger.info(f"当前版本: {current or '无'}")
        logger.info(f"已应用版本数: {len(applied)}")
        logger.info(f"待应用版本数: {len(pending)}")

        if applied:
            logger.info("\n已应用的迁移:")
            for version in applied:
                logger.info(f"  - {version}")

        if pending:
            logger.info("\n待应用的迁移:")
            for migration_file in pending:
                logger.info(f"  - {migration_file.name}")

        logger.info("=" * 60 + "\n")

    async def create_migration(
        self,
        name: str,
        message: Optional[str] = None
    ) -> Optional[Path]:
        """创建新的迁移文件（简化版，推荐使用 alembic revision 命令）"""
        logger.warning("推荐使用: alembic revision -m '<message>'")
        logger.info("或使用简化版本: python utils/migration_manager.py create <name>")

        # 生成版本号（基于时间戳）
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{version}_{name}.py"
        filepath = self.versions_dir / filename

        # 生成迁移模板
        template = f'''"""{message or name}

Revision ID: {version}
Revises:
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '{version}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库"""
    pass


def downgrade() -> None:
    """降级数据库"""
    pass
'''

        filepath.write_text(template, encoding="utf-8")
        logger.info(f"创建迁移文件: {filepath}")
        return filepath


async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # upgrade 命令
    upgrade_parser = subparsers.add_parser("upgrade", help="升级数据库")
    upgrade_parser.add_argument(
        "--version",
        help="目标版本（默认为最新）"
    )

    # downgrade 命令
    downgrade_parser = subparsers.add_parser("downgrade", help="降级数据库")
    downgrade_parser.add_argument(
        "version",
        help="目标版本"
    )

    # status 命令
    subparsers.add_parser("status", help="查看迁移状态")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建迁移文件")
    create_parser.add_argument("name", help="迁移名称")
    create_parser.add_argument("-m", "--message", help="迁移描述")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = MigrationManager()

    if args.command == "upgrade":
        success = await manager.upgrade(args.version)
        sys.exit(0 if success else 1)

    elif args.command == "downgrade":
        success = await manager.downgrade(args.version)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        await manager.status()

    elif args.command == "create":
        await manager.create_migration(args.name, args.message)


if __name__ == "__main__":
    asyncio.run(main())

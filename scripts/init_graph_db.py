"""
Neo4j 图数据库初始化脚本
用于在 juben 项目中集成图数据库

使用方法：
1. 确保 Neo4j 已安装并运行
2. 配置 .env 文件中的数据库连接信息
3. 运行此脚本: python scripts/init_graph_db.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.graph_manager import GraphDBManager
from config.graph_config import graph_settings


async def initialize_database():
    """初始化图数据库"""
    print("=" * 60)
    print("Neo4j 图数据库初始化")
    print("=" * 60)

    # 显示配置
    print(f"\n连接配置:")
    print(f"  URI: {graph_settings.NEO4J_URI}")
    print(f"  数据库: {graph_settings.NEO4J_DATABASE}")
    print(f"  用户名: {graph_settings.NEO4J_USERNAME}")
    print(f"  连接池大小: {graph_settings.NEO4J_MAX_CONNECTION_POOL_SIZE}")

    # 创建管理器
    graph_manager = GraphDBManager(
        uri=graph_settings.NEO4J_URI,
        username=graph_settings.NEO4J_USERNAME,
        password=graph_settings.NEO4J_PASSWORD,
        database=graph_settings.NEO4J_DATABASE,
        max_connection_pool_size=graph_settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
        max_connection_lifetime=graph_settings.NEO4J_MAX_CONNECTION_LIFETIME,
        connection_acquisition_timeout=graph_settings.NEO4J_CONNECTION_ACQUISITION_TIMEOUT,
        max_transaction_retry_time=graph_settings.NEO4J_MAX_TRANSACTION_RETRY_TIME,
    )

    try:
        print("\n正在连接数据库...")
        await graph_manager.initialize()
        print("✓ 数据库连接成功")

        print("\n正在创建 Schema 和索引...")
        # Schema 已在 initialize() 中自动创建
        print("✓ Schema 创建完成")

        # 验证连接
        print("\n正在验证连接...")
        is_connected = await graph_manager.verify_connectivity()
        if is_connected:
            print("✓ 连接验证成功")
        else:
            print("✗ 连接验证失败")
            return False

        # 显示统计信息
        print("\n数据库信息:")
        tx_stats = graph_manager.get_transaction_stats()
        print(f"  已执行事务: {tx_stats['total_transactions']}")
        print(f"  成功: {tx_stats['successful_transactions']}")
        print(f"  失败: {tx_stats['failed_transactions']}")

        print("\n" + "=" * 60)
        print("初始化完成！")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 查看 API 文档: http://localhost:8000/docs")
        print("  2. 运行示例: python examples/graph_example.py")
        print("  3. 阅读使用指南: docs/GRAPH_DATABASE_GUIDE.md")

        return True

    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
        print("\n故障排查:")
        print("  1. 确认 Neo4j 正在运行")
        print("  2. 检查 .env 文件中的连接配置")
        print("  3. 验证用户名和密码是否正确")
        print("  4. 查看日志获取详细错误信息")
        return False

    finally:
        await graph_manager.close()
        print("\n数据库连接已关闭")


async def create_sample_data():
    """创建示例数据（可选）"""
    from utils.graph_manager import (
        CharacterData,
        PlotNodeData,
        WorldRuleData,
        NodeType,
        CharacterStatus,
    )

    print("\n是否创建示例数据？(y/n): ", end="")
    choice = input().strip().lower()

    if choice != 'y':
        return

    graph_manager = GraphDBManager(
        uri=graph_settings.NEO4J_URI,
        username=graph_settings.NEO4J_USERNAME,
        password=graph_settings.NEO4J_PASSWORD,
        database=graph_settings.NEO4J_DATABASE,
    )

    try:
        await graph_manager.initialize()
        print("\n正在创建示例数据...")

        # 创建示例角色
        protagonist = CharacterData(
            character_id="example_char_001",
            name="示例主角",
            story_id="example_story",
            status=CharacterStatus.ALIVE,
            persona=["勇敢", "智慧"],
            arc=50.0,
            backstory="这是示例角色",
        )
        await graph_manager.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=protagonist,
        )

        # 创建示例情节
        plot = PlotNodeData(
            plot_id="example_plot_001",
            story_id="example_story",
            title="示例情节",
            description="这是一个示例情节",
            sequence_number=1,
            tension_score=70.0,
        )
        await graph_manager.merge_story_element(
            element_type=NodeType.PLOT_NODE,
            element_data=plot,
        )

        # 创建示例规则
        rule = WorldRuleData(
            rule_id="example_rule_001",
            story_id="example_story",
            name="示例规则",
            description="这是一个示例规则",
            rule_type="magic",
            severity="moderate",
        )
        await graph_manager.merge_story_element(
            element_type=NodeType.WORLD_RULE,
            element_data=rule,
        )

        print("✓ 示例数据创建完成")
        print("\n你可以在 Neo4j Browser 中查看示例数据:")
        print(f"  地址: http://localhost:7474")
        print(f"  查询: MATCH (n) WHERE n.story_id = 'example_story' RETURN n")

    except Exception as e:
        print(f"✗ 创建示例数据失败: {e}")

    finally:
        await graph_manager.close()


async def main():
    """主函数"""
    success = await initialize_database()

    if success:
        await create_sample_data()


if __name__ == "__main__":
    asyncio.run(main())

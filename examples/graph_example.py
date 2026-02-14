"""
图数据库使用示例
Graph Database Usage Examples

演示如何使用 GraphDBManager 进行剧本创作图谱管理
"""

import asyncio
import logging
from datetime import datetime, timezone

from utils.graph_manager import (
    GraphDBManager,
    CharacterData,
    PlotNodeData,
    WorldRuleData,
    NodeType,
    CharacterStatus,
)


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """
    基础使用示例：
    1. 创建角色
    2. 创建情节节点
    3. 创建世界观规则
    4. 建立关系
    """
    # 初始化图数据库管理器
    graph_manager = GraphDBManager(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="your_password",
        database="neo4j",
    )

    try:
        # 初始化连接
        await graph_manager.initialize()
        logger.info("图数据库连接成功")

        # ============ 创建角色 ============
        protagonist = CharacterData(
            character_id="char_001",
            name="林萧",
            story_id="story_001",
            status=CharacterStatus.ALIVE,
            location="京城",
            persona=["勇敢", "正义", "冲动"],
            arc=30.0,  # 初始成长值
            backstory="一名年轻的武林侠客，身负血海深仇",
            motivations=["复仇", "保护爱人", "查明真相"],
            flaws=["冲动", "过于信任他人"],
            strengths=["武艺高强", "剑法精湛"],
            first_appearance=1,
        )

        result = await graph_manager.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=protagonist,
            version=1,
        )
        logger.info(f"创建主角: {result['success']}")

        # 创建更多角色
        mentor = CharacterData(
            character_id="char_002",
            name="白云飞",
            story_id="story_001",
            status=CharacterStatus.ALIVE,
            location="白云山",
            persona=["智慧", "神秘", "慈祥"],
            arc=80.0,
            backstory="武林前辈，隐居白云山",
            motivations=["培养下一代", "守护武林秘籍"],
            flaws=["过于谨慎"],
            strengths=["内功深厚", "见多识广"],
            first_appearance=2,
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=mentor,
        )

        antagonist = CharacterData(
            character_id="char_003",
            name="黑风",
            story_id="story_001",
            status=CharacterStatus.ALIVE,
            location="暗夜谷",
            persona=["邪恶", "狡诈", "野心"],
            arc=-50.0,
            backstory="暗黑教教主，意图称霸武林",
            motivations=["统治武林", "获得秘籍"],
            flaws=["傲慢", "轻敌"],
            strengths=["毒功深厚", "手下众多"],
            first_appearance=3,
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=antagonist,
        )

        # ============ 创建情节节点 ============
        plot1 = PlotNodeData(
            plot_id="plot_001",
            story_id="story_001",
            title="初入江湖",
            description="林萧离开家乡，踏上复仇之路",
            sequence_number=1,
            tension_score=30.0,
            chapter=1,
            characters_involved=["char_001"],
            locations=["家乡", "京城郊外"],
            themes=["成长", "离别"],
            importance=60.0,
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.PLOT_NODE,
            element_data=plot1,
        )

        plot2 = PlotNodeData(
            plot_id="plot_002",
            story_id="story_001",
            title="拜师学艺",
            description="林萧偶遇白云飞，被收为弟子",
            sequence_number=2,
            tension_score=45.0,
            chapter=2,
            characters_involved=["char_001", "char_002"],
            locations=["白云山"],
            themes=["师徒", "传承"],
            importance=75.0,
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.PLOT_NODE,
            element_data=plot2,
        )

        plot3 = PlotNodeData(
            plot_id="plot_003",
            story_id="story_001",
            title="血战暗夜谷",
            description="林萧与黑风正面对决",
            sequence_number=10,
            tension_score=95.0,
            chapter=10,
            characters_involved=["char_001", "char_003"],
            locations=["暗夜谷"],
            conflicts=["正邪对决"],
            themes=["复仇", "正义"],
            importance=100.0,
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.PLOT_NODE,
            element_data=plot3,
        )

        # ============ 创建世界观规则 ============
        rule1 = WorldRuleData(
            rule_id="rule_001",
            story_id="story_001",
            name="武功不可逆练",
            description="武功秘籍一旦修炼，无法逆向，否则走火入魔",
            rule_type="magic",
            severity="strict",
            consequences=["走火入魔", "经脉尽断", "武功全废"],
            exceptions=["无"],
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.WORLD_RULE,
            element_data=rule1,
        )

        rule2 = WorldRuleData(
            rule_id="rule_002",
            story_id="story_001",
            name="禁地不可擅闯",
            description="白云山禁地只有掌门可进入",
            rule_type="social",
            severity="moderate",
            consequences=["被逐出师门", "废除武功"],
            exceptions=["掌门许可"],
        )

        await graph_manager.merge_story_element(
            element_type=NodeType.WORLD_RULE,
            element_data=rule2,
        )

        # ============ 创建关系 ============
        # 师徒关系
        await graph_manager.create_social_bond(
            character_id_1="char_001",
            character_id_2="char_002",
            trust_level=85,
            bond_type="family",
            hidden_relation="白师父暗中知道林萧的身世之秘",
        )

        # 敌对关系
        await graph_manager.create_social_bond(
            character_id_1="char_001",
            character_id_2="char_003",
            trust_level=-90,
            bond_type="enemy",
            hidden_relation="黑风是杀害林萧父母的幕后黑手",
        )

        # 情节影响
        await graph_manager.create_influence(
            from_element_id="plot_001",
            to_element_id="plot_002",
            impact_score=80,
            influence_type="direct",
            description="林萧初入江湖的遭遇导致他拜师学艺",
        )

        await graph_manager.create_influence(
            from_element_id="plot_002",
            to_element_id="plot_003",
            impact_score=90,
            influence_type="catalytic",
            description="拜师学艺为最终决战埋下伏笔",
        )

        logger.info("基础示例执行完成")

    finally:
        await graph_manager.close()


async def example_network_analysis():
    """
    网络分析示例：
    1. 获取角色网络
    2. 分析统计数据
    """
    graph_manager = GraphDBManager(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="your_password",
    )

    try:
        await graph_manager.initialize()

        # 获取主角的网络（深度2）
        network = await graph_manager.get_character_network(
            character_id="char_001",
            depth=2,
            include_hidden=True,
        )

        logger.info("角色网络分析:")
        logger.info(f"  总连接数: {network['statistics']['total_connections']}")
        logger.info(f"  社交连接数: {network['statistics']['social_connections']}")
        logger.info(f"  平均信任度: {network['statistics']['average_trust_level']:.2f}")
        logger.info(f"  平均影响力: {network['statistics']['average_impact_score']:.2f}")
        logger.info(f"  隐藏关系数: {network['statistics']['hidden_relations_count']}")

        # 获取故事统计
        stats = await graph_manager.get_story_statistics("story_001")
        logger.info(f"故事统计:")
        logger.info(f"  角色数: {stats['character_count']}")
        logger.info(f"  情节数: {stats['plot_count']}")
        logger.info(f"  规则数: {stats['rule_count']}")
        logger.info(f"  平均张力: {stats['average_tension']:.2f}")

        # 搜索角色
        characters = await graph_manager.search_characters(
            story_id="story_001",
            min_arc=50,
        )
        logger.info(f"高成长值角色: {len(characters)} 个")

    finally:
        await graph_manager.close()


async def example_advanced_query():
    """
    高级查询示例：
    1. 按张力排序获取情节
    2. 查询特定类型的规则
    3. 事务统计
    """
    graph_manager = GraphDBManager(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="your_password",
    )

    try:
        await graph_manager.initialize()

        # 按张力排序获取情节
        plots = await graph_manager.get_plot_by_story(
            story_id="story_001",
            order_by="tension_score",
        )
        logger.info(f"按张力排序的情节 (共 {len(plots)} 个):")
        for plot in plots[:5]:  # 只显示前5个
            logger.info(f"  {plot['title']}: 张力 {plot['tension_score']}")

        # 获取魔法类规则
        magic_rules = await graph_manager.get_world_rules(
            story_id="story_001",
            rule_type="magic",
        )
        logger.info(f"魔法类规则: {len(magic_rules)} 个")

        # 获取事务统计
        tx_stats = graph_manager.get_transaction_stats()
        logger.info(f"事务统计:")
        logger.info(f"  总事务数: {tx_stats['total_transactions']}")
        logger.info(f"  成功: {tx_stats['successful_transactions']}")
        logger.info(f"  失败: {tx_stats['failed_transactions']}")

    finally:
        await graph_manager.close()


async def example_batch_operations():
    """
    批量操作示例：
    高效地创建大量节点和关系
    """
    graph_manager = GraphDBManager(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="your_password",
    )

    try:
        await graph_manager.initialize()

        # 批量创建配角
        side_characters = [
            CharacterData(
                character_id=f"side_char_{i:03d}",
                name=f"配角{i}",
                story_id="story_001",
                status=CharacterStatus.ALIVE,
                persona=["普通"],
                arc=0.0,
            )
            for i in range(1, 21)  # 创建20个配角
        ]

        for i, char in enumerate(side_characters):
            await graph_manager.merge_story_element(
                element_type=NodeType.CHARACTER,
                element_data=char,
                version=1,
            )
            if (i + 1) % 5 == 0:
                logger.info(f"已创建 {i + 1} 个配角")

        logger.info("批量操作完成")

    finally:
        await graph_manager.close()


async def main():
    """运行所有示例"""
    logger.info("=" * 60)
    logger.info("示例 1: 基础使用")
    logger.info("=" * 60)
    await example_basic_usage()

    logger.info("\n" + "=" * 60)
    logger.info("示例 2: 网络分析")
    logger.info("=" * 60)
    await example_network_analysis()

    logger.info("\n" + "=" * 60)
    logger.info("示例 3: 高级查询")
    logger.info("=" * 60)
    await example_advanced_query()

    logger.info("\n" + "=" * 60)
    logger.info("示例 4: 批量操作")
    logger.info("=" * 60)
    await example_batch_operations()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())

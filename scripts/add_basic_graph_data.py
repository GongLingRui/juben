#!/usr/bin/env python3
"""
超简单的图数据库测试数据添加脚本
只使用基本 Neo4j Python 驱动
"""
from neo4j import AsyncGraphDatabase


async def add_test_data():
    """添加测试数据到图数据库"""

    # 创建驱动器，使用默认认证（neo4j/password）
    driver = AsyncGraphDatabase.driver(
        uri="bolt://localhost:7687",
        auth=("neo4j", "password")
    )

    try:
        await driver.verify_connectivity()
        print("✅ 图数据库连接成功")

        # ========== 创建人物节点 ==========
        print("\n📝 创建人物节点...")

        # 创建人物
        characters_cypher = """
            CREATE (c:Character:Character {
                id: 'char_li_ming',
                name: '李明',
                title: '男主角',
                description: '26岁，互联网公司CEO，性格沉稳冷静',
                age: 26,
                gender: '男',
                occupation: 'CEO'
            })
        """
        characters_cypher += """
            CREATE (c:Character:Character {
                id: 'char_lin_xia',
                name: '林夏',
                title: '女主角',
                description: '24岁，才华横溢的设计师，性格独立坚韧',
                age: 24,
                gender: '女',
                occupation: '设计总监'
            })
        """
        characters_cypher += """
            CREATE (c:Character:Character {
                id: 'char_wang_wei',
                name: '王伟',
                title: '男二号/竞争对手',
                description: '27岁，李明的大学同学，商业对手',
                age: 27,
                gender: '男',
                occupation: '科技公司创始人'
            })
        """
        characters_cypher += """
            CREATE (c:Character:Character {
                id: 'char_su_ya',
                name: '苏雅',
                title: '林夏闺蜜',
                description: '24岁，林夏大学室友兼闺蜜',
                age: 24,
                gender: '女',
                occupation: '时尚编辑'
            })
        """
        characters_cypher += """
            CREATE (c:Character:Character {
                id: 'char_zhao',
                name: '赵浩',
                title: '李明助理',
                description: '25岁，李明的得力助手',
                age: 25,
                gender: '男',
                occupation: '行政助理'
            })
        """

        async with driver.session() as session:
            await session.run(characters_cypher)
            print("  ✅ 创建人物: 李明")
            await session.run(characters_cypher)
            print("  ✅ 创建人物: 林夏")
            await session.run(characters_cypher)
            print("  ✅ 创建人物: 王伟")
            await session.run(characters_cypher)
            print("  ✅ 创建人物: 苏雅")
            await session.run(characters_cypher)
            print("  ✅ 创建人物: 赵浩")

        # ========== 创建人物关系 ==========
        print("\n🔗 创建人物关系...")

        relationships_cypher = """
            MATCH (li_ming {id: 'char_li_ming'}), (lin_xia {id: 'char_lin_xia'})
            CREATE (li_ming)-[:LOVES]->(lin_xia:Character) {
                description: '从商业竞争对手发展为恋人',
                since: '第3集'
            })
        """
        relationships_cypher += """
            MATCH (li_ming {id: 'char_li_ming'}), (wang_wei {id: 'char_wang_wei'})
            CREATE (li_ming)-[:COMPETES]->(wang_wei:Character) {
                description: '大学同学，现为商业对手'
            })
        """
        relationships_cypher += """
            MATCH (wang_wei {id: 'char_wang_wei'}), (lin_xia {id: 'char_lin_xia'})
            CREATE (wang_wei)-[:LEADS_TO]->(lin_xia:Character) {
                description: '王伟追求林夏',
                since: '第5集'
            })
        """
        relationships_cypher += """
            MATCH (su_ya {id: 'char_su_ya'}), (lin_xia {id: 'char_lin_xia'})
            CREATE (su_ya)-[:BEST_FRIEND]->(lin_xia:Character) {
                description: '大学室友兼闺蜜',
                since: '大一'
            })
        """
        relationships_cypher += """
            MATCH (zhao {id: 'char_zhao'}), (li_ming {id: 'char_li_ming'})
            CREATE (zhao)-[:WORKS_FOR]->(li_ming:Character) {
                description: '忠诚的助理',
                since: '2年'
            })
        """

        async with driver.session() as session:
            await session.run(relationships_cypher)
            print("  ✅ 创建关系: 李明 -> 林夏 (恋人)")
            await session.run(relationships_cypher)
            print("  ✅ 创建关系: 李明 -> 王伟 (竞争对手)")
            await session.run(relationships_cypher)
            print("  ✅ 创建关系: 王伟 -> 林夏 (追求)")
            await session.run(relationships_cypher)
            print("  ✅ 创建关系: 林夏 -> 苏雅 (闺蜜)")
            await session.run(relationships_cypher)
            print("  ✅ 创建关系: 赵浩 -> 李明 (助理)")

        # ========== 统计信息 ==========
        print("\n📊 数据库统计:")

        async with driver.session() as session:
            # 统计人物数
            char_result = await session.run("MATCH (c:Character) RETURN count(c) AS char_count")
            # 统计关系数
            rel_result = await session.run("""
                MATCH ()-[:LOVES|:COMPETES|:LEADS_TO|:BEST_FRIEND|:WORKS_FOR]->()
                RETURN count(r) AS rel_count
            """)

            print(f"  总人物数: {char_result[0]}")
            print(f"  总关系数: {rel_result[0]}")

        print("\n✅ 测试数据添加完成！")
        print("💡 现在可以在前端 http://localhost:5173/graph 查看图谱可视化")

    except Exception as e:
        print(f"❌ 添加测试数据失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await driver.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(add_test_data())

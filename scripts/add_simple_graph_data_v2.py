#!/usr/bin/env python3
"""
超简单的图数据库测试数据添加脚本
只使用最基本的 Cypher 查询
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

        async with driver.session() as session:
            # ========== 创建人物 ==========
            print("\n📝 创建人物节点...")

            # 李明
            await session.run("""
                CREATE (c:Character:LiMing {
                    id: 'char_li_ming',
                    name: '李明',
                    title: '男主角',
                    description: '26岁，互联网公司CEO，性格沉稳冷静',
                    age: 26,
                    gender: '男',
                    occupation: 'CEO'
                })
                """)
            print("  ✅ 创建人物: 李明")

            # 林夏
            await session.run("""
                CREATE (c:Character:LinXia {
                    id: 'char_lin_xia',
                    name: '林夏',
                    title: '女主角',
                    description: '24岁，才华横溢的设计师，性格独立坚韧',
                    age: 24,
                    gender: '女',
                    occupation: '设计总监'
                })
                """)
            print("  ✅ 创建人物: 林夏")

            # 王伟
            await session.run("""
                CREATE (c:Character:WangWei {
                    id: 'char_wang_wei',
                    name: '王伟',
                    title: '男二号/竞争对手',
                    description: '27岁，李明的大学同学，商业对手',
                    age: 27,
                    gender: '男',
                    occupation: '科技公司创始人'
                })
                """)
            print("  ✅ 创建人物: 王伟")

            # 苏雅
            await session.run("""
                CREATE (c:Character:SuYa {
                    id: 'char_su_ya',
                    name: '苏雅',
                    title: '林夏闺蜜',
                    description: '24岁，林夏大学室友兼闺蜜',
                    age: 24,
                    gender: '女',
                    occupation: '时尚编辑'
                })
                """)
            print("  ✅ 创建人物: 苏雅")

            # 赵浩
            await session.run("""
                CREATE (c:Character:ZhaoHao {
                    id: 'char_zhao_hao',
                    name: '赵浩',
                    title: '李明助理',
                    description: '25岁，李明的得力助手',
                    age: 25,
                    gender: '男',
                    occupation: '行政助理'
                })
                """)
            print("  ✅ 创建人物: 赵浩")

            # 李母
            await session.run("""
                CREATE (c:Character:LiMom {
                    id: 'char_li_mom',
                    name: '李母',
                    title: '李明母亲',
                    description: '55岁，退休教师',
                    age: 55,
                    gender: '女',
                    occupation: '退休教师'
                })
                """)
            print("  ✅ 创建人物: 李母")

            # 林父
            await session.run("""
                CREATE (c:Character:LinDad {
                    id: 'char_lin_dad',
                    name: '林父',
                    title: '林夏父亲',
                    description: '58岁，知名建筑师',
                    age: 58,
                    gender: '男',
                    occupation: '建筑师'
                })
                """)
            print("  ✅ 创建人物: 林父")

            # ========== 创建人物关系 ==========
            print("\n🔗 创建人物关系...")

            # 李明 -> 林夏 (恋人)
            await session.run("""
                MATCH (li {id: 'char_li_ming'}), (lin {id: 'char_lin_xia'})
                CREATE (li)-[:LOVES]->(lin) {
                    description: '从商业竞争对手发展为恋人',
                    strength: 0.9,
                    since: '第3集'
                })
                """)
            print("  ✅ 创建关系: 李明 -> 林夏 (恋人)")

            # 李明 -> 王伟 (竞争对手)
            await session.run("""
                MATCH (li {id: 'char_li_ming'}), (wang {id: 'char_wang_wei'})
                CREATE (li)-[:COMPETITORS]->(wang) {
                    description: '大学同学，现为商业对手',
                    strength: -0.7,
                    since: '大学时期'
                })
                """)
            print("  ✅ 创建关系: 李明 -> 王伟 (竞争对手)")

            # 李母 -> 李明 (母子)
            await session.run("""
                MATCH (mom {id: 'char_li_mom'}), (li {id: 'char_li_ming'})
                CREATE (mom)-[:PARENT_OF]->(li) {
                    description: '母子关系',
                    strength: 0.8
                })
                """)
            print("  ✅ 创建关系: 李母 -> 李明 (母子)")

            # 林夏 -> 苏雅 (闺蜜)
            await session.run("""
                MATCH (lin {id: 'char_lin_xia'}), (su {id: 'char_su_ya'})
                CREATE (lin)-[:SOCIAL_BOND]->(su) {
                    description: '大学室友兼闺蜜',
                    strength: 0.9,
                    since: '大一'
                })
                """)
            print("  ✅ 创建关系: 林夏 -> 苏雅 (闺蜜)")

            # 林父 -> 林夏 (父女)
            await session.run("""
                MATCH (dad {id: 'char_lin_dad'}), (lin {id: 'char_lin_xia'})
                CREATE (dad)-[:PARENT_OF]->(lin) {
                    description: '父女关系，父亲比较严厉',
                    strength: 0.7
                })
                """)
            print("  ✅ 创建关系: 林父 -> 林夏 (父女)")

            # 王伟 -> 林夏 (追求)
            await session.run("""
                MATCH (wang {id: 'char_wang_wei'}), (lin {id: 'char_lin_xia'})
                CREATE (wang)-[:PURSUES]->(lin) {
                    description: '王伟追求林夏',
                    strength: 0.3,
                    since: '第5集'
                })
                """)
            print("  ✅ 创建关系: 王伟 -> 林夏 (追求)")

            # ========== 统计信息 ==========
            print("\n📊 数据库统计:")

            async with driver.session() as stats_session:
                # 统计人物数
                char_count = await stats_session.run(
                    "MATCH (c:Character) RETURN count(c) AS char_count"
                )

                # 统计关系数
                rel_count = await stats_session.run(
                    """MATCH ()-[:LOVES|:COMPETITORS|:PARENT_OF|:SOCIAL_BOND|:PURSUES]->()
                    RETURN count(r) AS rel_count
                    """
                )

                print(f"  总人物数: {char_count[0]}")
                print(f"  总关系数: {rel_count[0]}")
                print(f"  总节点数: {char_count[0] + rel_count[0]}")

        print("\n✅ 测试数据添加完成！")
        print("💡 现在可以在前端 http://localhost:5173/graph 查看图谱可视化")

    except Exception as e:
        print(f"❌ 添加测试数据失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(add_test_data())

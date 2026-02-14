#!/usr/bin/env python3
"""
最简单有效的图数据库测试数据脚本
"""
import asyncio
from neo4j import AsyncGraphDatabase


async def add_test_data():
    """添加测试数据到图数据库"""

    # 创建驱动器
    driver = AsyncGraphDatabase.driver(
        uri="bolt://localhost:7687",
        auth=("neo4j", "password")
    )

    try:
        await driver.verify_connectivity()
        print("✅ 图数据库连接成功")

        async with driver.session() as session:
            # 创建人物
            print("\n📝 创建人物...")

            result = await session.run("""
                CREATE (li:Character {
                    name: '李明',
                    title: '男主角',
                    description: '26岁，互联网公司CEO，性格沉稳冷静',
                    age: 26,
                    gender: '男',
                    occupation: 'CEO'
                })
                """)
            print("  ✅ 李明")

            result = await session.run("""
                CREATE (lin:Character {
                    name: '林夏',
                    title: '女主角',
                    description: '24岁，才华横溢的设计师，性格独立坚韧',
                    age: 24,
                    gender: '女',
                    occupation: '设计总监'
                })
                """)
            print("  ✅ 林夏")

            result = await session.run("""
                CREATE (wang:Character {
                    name: '王伟',
                    title: '男二号/竞争对手',
                    description: '27岁，李明的大学同学，商业对手',
                    age: 27,
                    gender: '男',
                    occupation: '科技公司创始人'
                })
                """)
            print("  ✅ 王伟")

            result = await session.run("""
                CREATE (su:Character {
                    name: '苏雅',
                    title: '林夏闺蜜',
                    description: '24岁，林夏大学室友兼闺蜜',
                    age: 24,
                    gender: '女',
                    occupation: '时尚编辑'
                })
                """)
            print("  ✅ 苏雅")

            # 创建情节
            print("\n🎬 创建情节节点...")

            result = await session.run("""
                CREATE (main:Plot {
                    name: '商业竞争与爱情',
                    title: '主线剧情',
                    description: '李明和王伟争夺市场份额，同时李明和林夏相恋的故事',
                    act: 1,
                    theme: '商业竞争+都市爱情'
                })
                """)
            print("  ✅ 商业竞争与爱情")

            result = await session.run("""
                CREATE (family:Plot {
                    name: '家庭反对',
                    title: '副线剧情',
                    description: '林父反对女儿和穷小子（李明早期）在一起',
                    act: 2,
                    theme: '家庭伦理+门第观念'
                })
                """)
            print("  ✅ 家庭反对")

            # 创建关系
            print("\n🔗 创建人物关系...")

            result = await session.run("""
                MATCH (li {id: 'li_ming'}), (lin {id: 'lin_xia'})
                CREATE (li)-[:LOVES {lin}
                """)
            print("  ✅ 李明 -> 林夏 (恋人)")

            result = await session.run("""
                MATCH (li {id: 'li_ming'}), (wang {id: 'wang_wei'})
                CREATE (li)-[:COMPETITORS {wang}
                """)
            print("  ✅ 李明 -> 王伟 (竞争对手)")

            result = await session.run("""
                MATCH (wang {id: 'wang_wei'}), (lin {id: 'lin_xia'})
                CREATE (wang)-[:LEADS_TO {lin}
                """)
            print("  ✅ 王伟 -> 林夏 (追求)")

            result = await session.run("""
                MATCH (li_ming {id: 'li_ming'}), (main {id: 'main_love'})
                CREATE (li_ming)-[:FEATURES {main}
                """)
            print("  ✅ 商业竞争与爱情 -> 李明")

            result = await session.run("""
                MATCH (wang {id: 'wang_wei'}), (main {id: 'main_love'})
                CREATE (wang)-[:FEATURES {main}
                """)
            print("  ✅ 商业竞争与爱情 -> 王伟")

            # 统计
            print("\n📊 数据库统计:")

            result = await session.run("MATCH (n:Character) RETURN count(n) AS char_count")
            char_count = result[0]

            result = await session.run("MATCH (n:Plot) RETURN count(p) AS plot_count")
            plot_count = result[0]

            result = await session.run("MATCH ()-[:LOVES|:COMPETITORS|:PARENT_OF|:BEST_FRIEND|:WORKS_FOR|:LEADS_TO|:OPPOSES|:FEATURES|:CONTAINS] RETURN count(r) AS rel_count")
            rel_count = result[0]

            print(f"  人物数: {char_count}")
            print(f"  情节数: {plot_count}")
            print(f"  关系数: {rel_count}")
            print(f"  总节点数: {char_count + plot_count}")

        print("\n✅ 测试数据添加完成！")
        print("💡 现在可以在前端 http://localhost:5173/graph 查看图谱可视化")

    except Exception as e:
        print(f"❌ 添加测试数据失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_test_data())

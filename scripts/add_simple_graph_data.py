#!/usr/bin/env python3
"""
简化版图数据库测试数据添加脚本
直接使用 Neo4j 驱动，不依赖复杂的包装类
"""
import asyncio
from neo4j import AsyncGraphDatabase


class GraphDataLoader:
    """简单的图数据库加载器"""

    def __init__(self, uri: str = "bolt://localhost:7687", username: str = "neo4j", password: str = "password"):
        from neo4j import AsyncGraphDatabase

        # 使用基本认证
        auth_token = f"{username}:{password}"
        self.driver = AsyncGraphDatabase.driver(uri, auth=auth_token)
        self.uri = uri

    async def __aenter__(self):
        await self.driver.verify_connectivity()
        return self

    async def __aexit__(self, exc_type, exc_val, tb):
        await self.driver.close()

    async def create_character(self, char_data: dict):
        """创建人物节点"""
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (c:Character {
                    id: $id,
                    name: $name,
                    title: $title,
                    description: $description,
                    age: $age,
                    gender: $gender,
                    occupation: $occupation,
                    personality: $personality,
                    background: $background,
                    status: $status
                }
                """,
                **char_data
            )
            print(f"  ✅ 创建人物: {char_data['name']}")

    async def create_plot(self, plot_data: dict):
        """创建情节节点"""
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (p:PlotNode {
                    id: $id,
                    name: $name,
                    title: $title,
                    description: $description,
                    act: $act,
                    theme: $theme,
                    importance: $importance
                }
                """,
                **plot_data
            )
            print(f"  ✅ 创建情节: {plot_data['name']}")

    async def create_relationship(self, rel_data: dict):
        """创建关系"""
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (source)-[:.RelationshipType {
                    (source)-[:RELATIONSHIP_TYPE]->(target)
                }
                """,
                source=rel_data["source"],
                target=rel_data["target"],
                    rel_type=rel_data["type"],
                    properties=rel_data.get("properties", {})
            )
            print(f"  ✅ 创建关系: {rel_data['source']} -> {rel_data['target']}")


async def add_test_data():
    """添加测试数据"""
    loader = GraphDataLoader()

    try:
        async with loader:
            # 人物节点
            characters = [
                {
                    "id": "char_li_ming",
                    "name": "李明",
                    "title": "男主角",
                    "description": "26岁，互联网公司CEO，性格沉稳冷静",
                    "age": 26,
                    "gender": "男",
                    "occupation": "CEO",
                    "personality": ["沉稳", "冷静", "理性"],
                    "background": "出身普通家庭，白手起家",
                    "status": "alive"
                },
                {
                    "id": "char_lin_xia",
                    "name": "林夏",
                    "title": "女主角",
                    "description": "24岁，才华横溢的设计师，性格独立坚韧",
                    "age": 24,
                    "gender": "女",
                    "occupation": "设计总监",
                    "personality": ["独立", "坚韧", "有才华"],
                    "background": "艺术世家，父母都是知名设计师",
                    "status": "alive"
                },
                {
                    "id": "char_wang_wei",
                    "name": "王伟",
                    "title": "男二号/竞争对手",
                    "description": "27岁，李明的大学同学，商业对手",
                    "age": 27,
                    "gender": "男",
                    "occupation": "科技公司创始人",
                    "personality": ["野心", "自信", "强势"],
                    "background": "富裕家庭，一直想超越李明",
                    "status": "alive"
                },
                {
                    "id": "char_su_ya",
                    "name": "苏雅",
                    "title": "林夏闺蜜",
                    "description": "24岁，林夏大学室友兼闺蜜",
                    "age": 24,
                    "gender": "女",
                    "occupation": "时尚编辑",
                    "personality": ["活泼", "直率", "讲义气"],
                    "background": "和林夏从大一就是好朋友",
                    "status": "alive"
                },
                {
                    "id": "char_li_mom",
                    "name": "李母",
                    "title": "李明母亲",
                    "description": "55岁，退休教师",
                    "age": 55,
                    "gender": "女",
                    "occupation": "退休教师",
                    "personality": ["慈爱", "传统", "固执"],
                    "background": "希望儿子早日结婚",
                    "status": "alive"
                },
                {
                    "id": "char_lin_dad",
                    "name": "林父",
                    "title": "林夏父亲",
                    "description": "58岁，知名建筑师",
                    "age": 58,
                    "gender": "男",
                    "occupation": "建筑师",
                    "personality": ["严厉", "专业", "爱女心切"],
                    "background": "对女婿要求很高",
                    "status": "alive"
                }
            ]

            # 情节节点
            plots = [
                {
                    "id": "plot_main_love",
                    "name": "商业竞争与爱情",
                    "title": "主线剧情",
                    "description": "李明和王伟争夺市场份额，同时李明和林夏相恋的故事",
                    "act": 1,
                    "theme": "商业竞争+都市爱情",
                    "importance": "high"
                },
                {
                    "id": "plot_family_conflict",
                    "name": "家庭反对",
                    "title": "副线剧情",
                    "description": "林父反对女儿和穷小子（李明早期）在一起",
                    "act": 2,
                    "theme": "家庭伦理+门第观念",
                    "importance": "medium"
                },
                {
                    "id": "plot_business_war",
                    "name": "商场较量",
                    "title": "冲突升级",
                    "description": "王伟恶意竞争，李明公司面临危机",
                    "act": 3,
                    "theme": "商业战争+背叛",
                    "importance": "high"
                },
                {
                    "id": "plot_reconciliation",
                    "name": "和解与成长",
                    "title": "高潮与结局",
                    "description": "误会解除，王伟洗心革面，林父认可李明",
                    "act": 4,
                    "theme": "宽恕+成长+大团圆",
                    "importance": "high"
                }
            ]

            # 关系
            relationships = [
                {
                    "source": "char_li_ming",
                    "target": "char_lin_xia",
                    "type": "LOVES",
                    "properties": {
                        "description": "从商业竞争对手发展为恋人",
                        "since": "第3集"
                    }
                },
                {
                    "source": "char_li_ming",
                    "target": "char_wang_wei",
                    "type": "COMPETITORS",
                    "properties": {
                        "description": "大学同学，现为商业对手",
                        "since": "大学时期"
                    }
                },
                {
                    "source": "char_li_mom",
                    "target": "char_li_ming",
                    "type": "PARENT_OF",
                    "properties": {
                        "description": "母子关系"
                    }
                },
                {
                    "source": "char_lin_xia",
                    "target": "char_su_ya",
                    "type": "BEST_FRIEND",
                    "properties": {
                        "description": "大学室友兼闺蜜",
                        "since": "大一"
                    }
                },
                {
                    "source": "char_lin_dad",
                    "target": "char_lin_xia",
                    "type": "PARENT_OF",
                    "properties": {
                        "description": "父女关系，父亲比较严厉"
                    }
                },
                {
                    "source": "char_wang_wei",
                    "target": "char_lin_xia",
                    "type": "PURSUES",
                    "properties": {
                        "description": "王伟追求林夏",
                        "since": "第5集"
                    }
                },
                {
                    "source": "char_li_mom",
                    "target": "char_lin_xia",
                    "type": "OPPOSES",
                    "properties": {
                        "description": "李母起初也反对林夏",
                        "since": "第6集"
                    }
                },
                {
                    "source": "plot_main_love",
                    "target": "char_li_ming",
                    "type": "FEATURES",
                    "properties": {
                        "description": "李明处于主线冲突中心"
                    }
                },
                {
                    "source": "plot_main_love",
                    "target": "char_wang_wei",
                    "type": "FEATURES",
                    "properties": {
                        "description": "王伟处于主线冲突中心"
                    }
                },
                {
                    "source": "plot_family_conflict",
                    "target": "char_lin_dad",
                    "type": "TRIGGERS",
                    "properties": {
                        "description": "林父制造家庭冲突"
                    }
                },
                {
                    "source": "plot_reconciliation",
                    "target": "plot_main_love",
                    "type": "LEADS_TO",
                    "properties": {
                        "description": "冲突最终和解"
                    }
                }
            ]

            print("📝 创建人物节点...")
            for char in characters:
                await loader.create_character(char)

            print("\n🎬 创建情节节点...")
            for plot in plots:
                await loader.create_plot(plot)

            print("\n🔗 创建关系...")
            for rel in relationships:
                await loader.create_relationship(rel)

            # 统计
            async with loader.driver.session() as session:
                result = await session.run("MATCH (c:Character) RETURN count(c) AS char_count")
                result2 = await session.run("MATCH (p:PlotNode) RETURN count(p) AS plot_count")
                result3 = await session.run("MATCH ()-[:RELATIONSHIP_TYPE]->() RETURN count(r) AS rel_count")

                print(f"\n📊 数据库统计:")
                print(f"  人物数: {result[0]}")
                print(f"  情节数: {result2[0]}")
                print(f"  关系数: {result3[0]}")
                print(f"  总节点数: {result[0] + result2[0]}")

            print("\n✅ 测试数据添加完成！")
            print("💡 现在可以在前端 http://localhost:5173/graph 查看图谱可视化")

    except Exception as e:
        print(f"❌ 添加数据失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_test_data())

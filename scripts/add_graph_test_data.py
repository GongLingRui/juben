#!/usr/bin/env python3
"""
为图数据库添加测试数据
包括：人物关系、情节发展、世界观规则
"""
import asyncio
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.graph_manager import (
    GraphDBManager,
    NodeType,
    RelationType,
    CharacterStatus
)


async def add_test_data():
    """添加测试数据到图数据库"""

    # 使用图数据库管理器
    graph_db = GraphDBManager(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password",
        database="neo4j"
    )

    try:
        await graph_db.initialize()
        print("✅ 图数据库连接成功")

        # ========== 创建人物节点 ==========
        print("\n📝 创建人物节点...")

        characters = [
            # 主角
            {
                "id": "char_protagonist_li_ming",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "李明",
                    "title": "男主角",
                    "description": "26岁，互联网公司CEO，性格沉稳冷静",
                    "age": 26,
                    "gender": "男",
                    "occupation": "CEO",
                    "personality": ["沉稳", "冷静", "理性"],
                    "background": "出身普通家庭，白手起家",
                    "status": CharacterStatus.ALIVE
                }
            },
            {
                "id": "char_protagonist_lin_xia",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "林夏",
                    "title": "女主角",
                    "description": "24岁，才华横溢的设计师，性格独立坚韧",
                    "age": 24,
                    "gender": "女",
                    "occupation": "设计总监",
                    "personality": ["独立", "坚韧", "有才华"],
                    "background": "艺术世家，父母都是知名设计师",
                    "status": CharacterStatus.ALIVE
                }
            },
            # 配角
            {
                "id": "char_rival_wang_wei",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "王伟",
                    "title": "男二号/竞争对手",
                    "description": "27岁，李明的大学同学，商业对手",
                    "age": 27,
                    "gender": "男",
                    "occupation": "科技公司创始人",
                    "personality": ["野心", "自信", "强势"],
                    "background": "富裕家庭，一直想超越李明",
                    "status": CharacterStatus.ALIVE
                }
            },
            {
                "id": "char_bestfriend_su_ya",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "苏雅",
                    "title": "林夏闺蜜",
                    "description": "24岁，林夏大学室友兼闺蜜",
                    "age": 24,
                    "gender": "女",
                    "occupation": "时尚编辑",
                    "personality": ["活泼", "直率", "讲义气"],
                    "background": "和林夏从大一就是好朋友",
                    "status": CharacterStatus.ALIVE
                }
            },
            {
                "id": "char_assistant_zhao",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "赵浩",
                    "title": "李明助理",
                    "description": "25岁，李明的得力助手",
                    "age": 25,
                    "gender": "男",
                    "occupation": "行政助理",
                    "personality": ["忠诚", "细心", "高效"],
                    "background": "农村出身，靠努力进入大公司",
                    "status": CharacterStatus.ALIVE
                }
            },
            # 家人
            {
                "id": "char_li_mother",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "李母",
                    "title": "李明母亲",
                    "description": "55岁，退休教师",
                    "age": 55,
                    "gender": "女",
                    "occupation": "退休教师",
                    "personality": ["慈爱", "传统", "固执"],
                    "background": "希望儿子早日结婚",
                    "status": CharacterStatus.ALIVE
                }
            },
            {
                "id": "char_lin_father",
                "type": NodeType.CHARACTER,
                "properties": {
                    "name": "林父",
                    "title": "林夏父亲",
                    "description": "58岁，知名建筑师",
                    "age": 58,
                    "gender": "男",
                    "occupation": "建筑师",
                    "personality": ["严厉", "专业", "爱女心切"],
                    "background": "对女婿要求很高",
                    "status": CharacterStatus.ALIVE
                }
            }
        ]

        for char_data in characters:
            try:
                await graph_db.create_node(
                    node_type=char_data["type"],
                    properties=char_data["properties"]
                )
                print(f"  ✅ 创建人物: {char_data['properties']['name']}")
            except Exception as e:
                print(f"  ❌ 创建人物失败 {char_data['properties']['name']}: {e}")

        # ========== 创建故事/世界元素 ==========
        print("\n🌍 创建故事/世界元素...")

        story_elements = [
            # 故事线
            {
                "id": "plot_main_conflict",
                "type": NodeType.MAJOR_PLOT,
                "properties": {
                    "name": "商业竞争与爱情",
                    "title": "主线剧情",
                    "description": "李明和王伟争夺市场份额，同时李明和林夏相恋的故事",
                    "act": 1,
                    "theme": "商业竞争+都市爱情",
                    "importance": "high"
                }
            },
            {
                "id": "plot_family_opposition",
                "type": NodeType.MAJOR_PLOT,
                "properties": {
                    "name": "家庭反对",
                    "title": "副线剧情",
                    "description": "林父反对女儿和穷小子（李明早期）在一起",
                    "act": 2,
                    "theme": "家庭伦理+门第观念",
                    "importance": "medium"
                }
            },
            {
                "id": "plot_business_rivalry",
                "type": NodeType.MAJOR_PLOT,
                "properties": {
                    "name": "商场较量",
                    "title": "冲突升级",
                    "description": "王伟恶意竞争，李明公司面临危机",
                    "act": 3,
                    "theme": "商业战争+背叛",
                    "importance": "high"
                }
            },
            {
                "id": "plot_reconciliation",
                "type": NodeType.MAJOR_PLOT,
                "properties": {
                    "name": "和解与成长",
                    "title": "高潮与结局",
                    "description": "误会解除，王伟洗心革面，林父认可李明",
                    "act": 4,
                    "theme": "宽恕+成长+大团圆",
                    "importance": "high"
                }
            },
            # 世界观设定
            {
                "id": "world_business_world",
                "type": NodeType.STORY_TYPE,
                "properties": {
                    "name": "都市商业世界",
                    "title": "世界观背景",
                    "description": "现代都市，商业竞争激烈，科技行业高速发展",
                    "era": "现代",
                    "tone": "现实主义",
                    "rules": [
                        "商场如战场，胜负瞬息万变",
                        "真情最珍贵，金钱买不到爱情",
                        "家人关系需要理解包容",
                        "经历挫折才能成长"
                    ]
                }
            },
            {
                "id": "world_social_class",
                "type": NodeType.STORY_TYPE,
                "properties": {
                    "name": "社会阶层",
                    "title": "世界观设定",
                    "description": "不同家庭背景造成的阶层差异",
                    "era": "现代",
                    "tone": "社会观察",
                    "rules": [
                        "门第观念依然存在",
                        "真爱能跨越阶层",
                        "个人奋斗可以改变命运",
                        "家庭压力是现实问题"
                    ]
                }
            }
        ]

        for element_data in story_elements:
            try:
                await graph_db.create_node(
                    node_type=element_data["type"],
                    properties=element_data["properties"]
                )
                print(f"  ✅ 创建元素: {element_data['properties']['name']}")
            except Exception as e:
                print(f"  ❌ 创建元素失败 {element_data['properties']['name']}: {e}")

        # ========== 创建人物关系 ==========
        print("\n🔗 创建人物关系...")

        relationships = [
            # 李明的关系
            {
                "source": "char_protagonist_li_ming",
                "target": "char_protagonist_lin_xia",
                "type": RelationType.ROMANTIC_BOND,
                "properties": {
                    "description": "从商业竞争对手发展为恋人",
                    "strength": 0.9,
                    "status": "dating",
                    "since": "第3集"
                }
            },
            {
                "source": "char_protagonist_li_ming",
                "target": "char_rival_wang_wei",
                "type": RelationType.COMPETITORS,
                "properties": {
                    "description": "大学同学，现为商业对手",
                    "strength": -0.7,
                    "status": "hostile",
                    "since": "大学时期"
                }
            },
            {
                "source": "char_li_mother",
                "target": "char_protagonist_li_ming",
                "type": RelationType.PARENT_OF,
                "properties": {
                    "description": "母子关系",
                    "strength": 0.8,
                    "status": "close",
                    "since": "出生"
                }
            },
            # 林夏的关系
            {
                "source": "char_protagonist_lin_xia",
                "target": "char_bestfriend_su_ya",
                "type": RelationType.SOCIAL_BOND,
                "properties": {
                    "description": "大学室友兼闺蜜",
                    "strength": 0.9,
                    "status": "best_friends",
                    "since": "大一"
                }
            },
            {
                "source": "char_lin_father",
                "target": "char_protagonist_lin_xia",
                "type": RelationType.PARENT_OF,
                "properties": {
                    "description": "父女关系，父亲比较严厉",
                    "strength": 0.7,
                    "status": "somewhat_strained",
                    "since": "出生"
                }
            },
            {
                "source": "char_rival_wang_wei",
                "target": "char_protagonist_lin_xia",
                "type": RelationType.LEADS_TO,
                "properties": {
                    "description": "王伟追求林夏",
                    "strength": 0.3,
                    "status": "unrequited",
                    "since": "第5集"
                }
            },
            # 赵浩的关系
            {
                "source": "char_assistant_zhao",
                "target": "char_protagonist_li_ming",
                "type": RelationType.WORKS_FOR,
                "properties": {
                    "description": "忠诚的助理",
                    "strength": 0.6,
                    "status": "professional",
                    "since": "2年"
                }
            },
            # 家庭冲突关系
            {
                "source": "char_li_mother",
                "target": "char_protagonist_lin_xia",
                "type": RelationType.OPPOSES,
                "properties": {
                    "description": "李母起初也反对林夏",
                    "strength": -0.4,
                    "status": "reluctant",
                    "since": "第6集"
                }
            },
            # 剧情节点关系
            {
                "source": "plot_main_conflict",
                "target": "char_protagonist_li_ming",
                "type": RelationType.CONTAINS,
                "properties": {
                    "description": "李明处于主线冲突中心"
                }
            },
            {
                "source": "plot_main_conflict",
                "target": "char_rival_wang_wei",
                "type": RelationType.CONTAINS,
                "properties": {
                    "description": "王伟处于主线冲突中心"
                }
            },
            {
                "source": "plot_family_opposition",
                "target": "char_lin_father",
                "type": RelationType.CONTAINS,
                "properties": {
                    "description": "林父制造家庭冲突"
                }
            },
            {
                "source": "plot_reconciliation",
                "target": "plot_main_conflict",
                "type": RelationType.LEADS_TO,
                "properties": {
                    "description": "冲突最终和解"
                }
            }
        ]

        for rel_data in relationships:
            try:
                await graph_db.create_relationship(
                    source=rel_data["source"],
                    target=rel_data["target"],
                    rel_type=rel_data["type"],
                    properties=rel_data.get("properties", {})
                )
                print(f"  ✅ 创建关系: {rel_data['type']}")
            except Exception as e:
                print(f"  ❌ 创建关系失败 {rel_data['type']}: {e}")

        # ========== 统计信息 ==========
        stats = await graph_db.get_statistics()
        print("\n📊 数据库统计:")
        print(f"  总节点数: {stats.get('total_nodes', 0)}")
        print(f"  总关系数: {stats.get('total_relationships', 0)}")
        print(f"  人物数: {stats.get('character_count', 0)}")
        print(f"  关系数: {stats.get('relationship_count', 0)}")

        print("\n✅ 测试数据添加完成！")
        print("💡 现在可以在前端 http://localhost:5173/graph 查看图谱可视化")

    except Exception as e:
        print(f"❌ 添加测试数据失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await graph_db.close()


if __name__ == "__main__":
    asyncio.run(add_test_data())

import logging

"""
增强型上下文管理使用示例
========================

演示如何使用新的上下文管理功能来处理长剧本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.drama_workflow_agent import DramaWorkflowAgent
from utils.context_mixin import rebuild_context_with_health_check, safe_process_long_content

logger = logging.getLogger(__name__)


async def example_1_basic_context_management():
    """示例1: 基础上下文管理"""
    logger.info("\n" + "="*60)
    logger.info("示例1: 基础上下文管理")
    logger.info("="*60)

    # 创建agent
    agent = DramaWorkflowAgent()

    # 用户和会话ID
    user_id = "test_user"
    session_id = "test_session_001"

    # 添加多条消息到上下文
    messages = [
        ("user", "请帮我创作一个关于复仇的短剧"),
        ("assistant", "好的，我来帮您创作。请问主角的背景是什么？"),
        ("user", "主角是一个被冤枉的律师，想要洗清自己的罪名"),
        ("assistant", "明白。复仇主题的短剧需要有强烈的冲突。让我来构思..."),
        # 添加更多消息来测试滚动窗口
        ("user", "加入一些意想不到的转折"),
        ("assistant", "我会设计几个令人惊讶的反转情节"),
        ("user", "记得加入情感冲突"),
        ("assistant", "情感冲突是短剧的核心，我会重点刻画"),
        ("user", "最后需要一个开放式的结局"),
        ("assistant", "开放式结局能让观众有更多想象空间"),
    ]

    for role, content in messages:
        await agent.add_message_to_context(session_id, user_id, role, content)
        logger.info(f"✓ 添加消息: {role} - {content[:30]}...")

    # 获取上下文健康报告
    health = await agent.get_context_health_report(session_id, user_id)
    logger.info(f"\n📊 上下文健康报告:")
    logger.info(f"  状态: {health['status']}")
    logger.info(f"  使用率: {health['usage_ratio']}")
    logger.info(f"  消息数: {health['message_count']}")
    logger.info(f"  压缩次数: {health['compression_count']}")

    # 重建优化的上下文
    new_message = "现在请生成完整的短剧大纲"
    optimized_messages = await agent.rebuild_optimized_context(
        session_id, user_id, new_message
    )

    logger.info(f"\n✅ 重建后的上下文: {len(optimized_messages)}条消息")
    logger.info(f"  - System: {sum(1 for m in optimized_messages if m['role'] == 'system')}")
    logger.info(f"  - User: {sum(1 for m in optimized_messages if m['role'] == 'user')}")
    logger.info(f"  - Assistant: {sum(1 for m in optimized_messages if m['role'] == 'assistant')}")


async def example_2_long_script_chunking():
    """示例2: 长剧本分块处理"""
    logger.info("\n" + "="*60)
    logger.info("示例2: 长剧本分块处理")
    logger.info("="*60)

    # 创建agent
    agent = DramaWorkflowAgent()

    user_id = "test_user"
    session_id = "test_session_002"

    # 模拟一个长剧本
    long_script = """
【第一场：律师事务所 - 日】
张律师: 这个案子我一定要查清楚，还自己一个清白！
助手: 可是证据都在对方手里，我们该怎么办？
张律师: 只要有决心，就一定能找到突破口。
（张律师翻看文件，眉头紧锁）

【第二场：法院走廊 - 日】
李法官: 张律师，你这个案子很难打啊。
张法官: 是啊，对方准备得很充分。
张律师: 谢谢关心，我相信正义终会到来。

【第三场：法庭 - 日】
原告律师: 被告律师，你有什么证据证明你的当事人无罪？
张律师: 当然有！（拿出一份文件）这是新发现的证据！
原告律师: （脸色一变）这...这不可能！
张律师: 一切皆有可能，真相终将大白。

【第四场：律师事务所外 - 夜】
记者: 张律师，请问您是如何翻案的？
张律师: 只要坚持真理，就能找到正义。
助手: 太棒了！我们终于成功了！
张律师: 这只是开始，还有很多冤案需要我们去平反。

【第五场：家中 - 夜】
张律师: （看着窗外的夜景）这条路虽然艰难，但值得走下去。
妻子: 我为你感到骄傲。
张律师: 谢谢你的支持，没有你我做不到这些。
（两人相拥而泣）
"""

    # 对长剧本进行语义分块
    chunks = await agent.chunk_long_content(long_script, "scene")

    logger.info(f"\n📝 剧本分块结果: 共{len(chunks)}个场景")
    for i, chunk in enumerate(chunks):
        logger.info(f"\n场景 {i+1} (ID: {chunk['id']}):")
        logger.info(f"  类型: {chunk['type']}")
        logger.info(f"  Tokens: {chunk['tokens']}")
        logger.info(f"  重要性: {chunk['importance']:.2f}")
        logger.info(f"  角色: {', '.join(chunk['characters']) if chunk['characters'] else '无'}")
        logger.info(f"  内容预览: {chunk['content'][:50]}...")


async def example_3_script_memory():
    """示例3: 剧本记忆管理"""
    logger.info("\n" + "="*60)
    logger.info("示例3: 剧本记忆管理")
    logger.info("="*60)

    # 创建agent
    agent = DramaWorkflowAgent()

    user_id = "test_user"
    session_id = "test_session_003"

    # 创建剧本记忆
    await agent.create_script_memory(user_id, session_id)
    logger.info("✓ 创建剧本记忆")

    # 添加角色信息
    characters = [
        {
            "name": "张律师",
            "description": "被冤枉的律师，执着追求真相",
            "personality": "坚韧、正义、不屈不挠",
            "background": "曾是知名的刑事律师，被陷害后失去执业资格"
        },
        {
            "name": "助手",
            "description": "张律师的忠实助手",
            "personality": "忠诚、细心、机智",
            "background": "曾是张律师的学生，坚信老师无罪"
        },
        {
            "name": "原告律师",
            "description": "对手律师，狡猾但有原则",
            "personality": "聪明、谨慎、正义感",
            "background": "知名律师，接手此案前不知道有隐情"
        }
    ]

    for char in characters:
        await agent.update_character(
            user_id, session_id,
            character_name=char["name"],
            description=char["description"],
            personality=char["personality"],
            background=char["background"]
        )
        logger.info(f"✓ 添加角色: {char['name']}")

    # 添加情节线
    plot_threads = [
        "主线：张律师洗清冤屈",
        "支线1：发现关键证据",
        "支线2：与对手律师的对抗",
        "支线3：家庭关系的考验"
    ]

    for plot in plot_threads:
        await agent.add_plot_thread(user_id, session_id, plot)
        logger.info(f"✓ 添加情节线: {plot}")

    # 获取剧本摘要
    summary = await agent.get_script_summary(user_id, session_id)
    logger.info(f"\n📋 剧本记忆摘要:\n{summary}")


async def example_4_health_check():
    """示例4: 上下文健康检查与自动压缩"""
    logger.info("\n" + "="*60)
    logger.info("示例4: 上下文健康检查与自动压缩")
    logger.info("="*60)

    # 创建agent
    agent = DramaWorkflowAgent()

    user_id = "test_user"
    session_id = "test_session_004"

    # 模拟大量对话
    logger.info("添加大量消息来测试压缩机制...")
    for i in range(50):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"这是第{i+1}条消息，用于测试滚动窗口和自动压缩机制。"
        await agent.add_message_to_context(session_id, user_id, role, content)

    # 检查健康状态
    health = await agent.get_context_health_report(session_id, user_id)
    logger.info(f"\n📊 上下文健康报告:")
    logger.info(f"  状态: {health['status']}")
    logger.info(f"  使用率: {health['usage_ratio']}")
    logger.info(f"  即时记忆: {health['immediate_count']}")
    logger.info(f"  近期记忆: {health['recent_count']}")
    logger.info(f"  工作记忆: {health['working_count']}")
    logger.info(f"  压缩次数: {health['compression_count']}")

    # 显示建议
    recommendations = health.get('recommendations', [])
    if recommendations:
        logger.info(f"\n💡 建议:")
        for rec in recommendations:
            logger.info(f"  {rec}")

    # 检查是否需要压缩
    should_compress = await agent.should_compress_context(session_id, user_id)
    logger.info(f"\n是否需要压缩: {'是' if should_compress else '否'}")

    # 如果需要，强制压缩
    if should_compress:
        logger.info("\n执行强制压缩...")
        await agent.force_compress_context(session_id, user_id)
        logger.info("✓ 压缩完成")


async def example_5_integrated_workflow():
    """示例5: 集成工作流"""
    logger.info("\n" + "="*60)
    logger.info("示例5: 集成工作流 - 处理长剧本")
    logger.info("="*60)

    # 创建agent
    agent = DramaWorkflowAgent()

    user_id = "test_user"
    session_id = "test_session_005"

    # 模拟长剧本输入
    long_script_content = """
    [这里是一个很长的剧本内容，包含多个场景、对话和情节...
    实际使用时替换为真实的剧本内容]
    """ * 100  # 模拟长内容

    logger.info(f"剧本长度: {agent.count_tokens(long_script_content)} tokens")

    # 使用安全处理长内容的方法
    try:
        result = await safe_process_long_content(
            agent,
            long_script_content,
            user_id,
            session_id,
            max_tokens=50000
        )
        logger.info(f"\n✅ 处理完成")
        logger.info(f"结果预览: {result[:200]}...")
    except Exception as e:
        logger.info(f"\n❌ 处理失败: {e}")

    # 记录最终状态
    await agent.log_context_status(session_id, user_id)


async def main():
    """运行所有示例"""
    logger.info("\n" + "="*60)
    logger.info("增强型上下文管理 - 使用示例")
    logger.info("="*60)

    try:
        # 运行示例
        await example_1_basic_context_management()
        await example_2_long_script_chunking()
        await example_3_script_memory()
        await example_4_health_check()
        await example_5_integrated_workflow()

        logger.info("\n" + "="*60)
        logger.info("所有示例运行完成！")
        logger.info("="*60)

    except Exception as e:
        logger.info(f"\n❌ 运行示例时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

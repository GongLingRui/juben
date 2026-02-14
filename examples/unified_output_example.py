"""
统一输出格式 - Agent使用示例
============================

演示如何使用BaseJubenAgent的统一输出格式化方法
"""
import asyncio
import sys
from pathlib import Path
import logging


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_juben_agent import BaseJubenAgent


# 示例1: 简单Agent - 剧本生成器
class ScriptGeneratorAgent(BaseJubenAgent):
    """剧本生成Agent示例"""

    def __init__(self):
        super().__init__("script_generator")

    async def process_request(self, request_data, context=None):
        """处理剧本生成请求"""
        try:
            # 获取参数
            plot_type = request_data.get("plot_type", "爱情")
            scene_count = request_data.get("scene_count", 5)

            # 参数验证
            if scene_count < 1 or scene_count > 20:
                return self.format_error(
                    error="scene_count必须在1-20之间",
                    message="参数范围错误",
                    code=400
                )

            # 生成剧本（模拟）
            script = await self._generate_script(plot_type, scene_count)

            # 返回统一格式
            return self.format_success(
                data={
                    "script": script,
                    "metadata": {
                        "plot_type": plot_type,
                        "scene_count": scene_count,
                        "word_count": len(str(script))
                    }
                },
                message=f"剧本生成成功，共{scene_count}场戏",
                metadata={
                    "genre": plot_type,
                    "estimated_duration": f"{scene_count * 2}分钟"
                }
            )

        except Exception as e:
            self.logger.error(f"剧本生成失败: {e}")
            return self.format_error(
                error=str(e),
                message="剧本生成失败，请重试",
                code=500
            )

    async def _generate_script(self, plot_type, scene_count):
        """模拟剧本生成"""
        return {
            "title": f"{plot_type}剧本",
            "scenes": [
                {
                    "scene_number": i + 1,
                    "location": "场景地点",
                    "characters": ["角色A", "角色B"],
                    "dialogue": f"第{i+1}场的对话内容..."
                }
                for i in range(scene_count)
            ]
        }


# 示例2: 流式Agent - 进度跟踪
class StreamingAnalysisAgent(BaseJubenAgent):
    """流式分析Agent示例"""

    def __init__(self):
        super().__init__("streaming_analysis")

    async def process_request(self, request_data, context=None):
        """处理分析请求（流式输出）"""

        try:
            # 发送开始事件
            yield self.format_stream_event(
                event_type="start",
                message="开始分析剧本"
            )

            # 步骤1: 读取剧本
            yield self.format_stream_event(
                event_type="progress",
                data={"step": 1, "total": 4, "step_name": "读取剧本"},
                message="正在读取剧本内容..."
            )
            await asyncio.sleep(0.5)

            # 步骤2: 分析角色
            yield self.format_stream_event(
                event_type="progress",
                data={"step": 2, "total": 4, "step_name": "分析角色"},
                message="正在分析角色关系..."
            )
            characters = await self._analyze_characters(request_data)
            yield self.format_stream_event(
                event_type="step_complete",
                data={"characters": characters},
                message=f"角色分析完成，识别到{len(characters)}个角色"
            )

            # 步骤3: 分析情节
            yield self.format_stream_event(
                event_type="progress",
                data={"step": 3, "total": 4, "step_name": "分析情节"},
                message="正在分析情节线..."
            )
            plots = await self._analyze_plots(request_data)

            # 步骤4: 生成报告
            yield self.format_stream_event(
                event_type="progress",
                data={"step": 4, "total": 4, "step_name": "生成报告"},
                message="正在生成分析报告..."
            )

            report = {
                "characters": characters,
                "plots": plots,
                "summary": "分析完成"
            }

            # 发送最终结果
            yield self.format_stream_event(
                event_type="complete",
                data=report,
                message="剧本分析完成"
            )

        except Exception as e:
            self.logger.error(f"分析失败: {e}")
            yield self.format_stream_event(
                event_type="error",
                data={"error": str(e)},
                message="分析过程中出现错误"
            )

    async def _analyze_characters(self, request_data):
        """模拟角色分析"""
        await asyncio.sleep(0.3)
        return [
            {"name": "张三", "role": "主角", "importance": 0.9},
            {"name": "李四", "role": "配角", "importance": 0.6},
            {"name": "王五", "role": "反派", "importance": 0.7}
        ]

    async def _analyze_plots(self, request_data):
        """模拟情节分析"""
        await asyncio.sleep(0.3)
        return [
            {"type": "主线", "description": "复仇与救赎", "intensity": 0.8},
            {"type": "支线", "description": "感情线", "intensity": 0.6}
        ]


# 示例3: 批量处理Agent
class BatchEvaluationAgent(BaseJubenAgent):
    """批量评估Agent示例"""

    def __init__(self):
        super().__init__("batch_evaluation")

    async def process_request(self, request_data, context=None):
        """批量评估多个剧本"""

        scripts = request_data.get("scripts", [])
        results = []
        successful = 0
        failed = 0

        try:
            for i, script in enumerate(scripts):
                try:
                    # 评估单个剧本
                    score = await self._evaluate_script(script)
                    results.append({
                        "script_id": script.get("id", i),
                        "success": True,
                        "score": score,
                        "grade": self._get_grade(score)
                    })
                    successful += 1

                    # 发送进度
                    yield self.format_stream_event(
                        event_type="progress",
                        data={
                            "current": i + 1,
                            "total": len(scripts),
                            "successful": successful,
                            "failed": failed
                        },
                        message=f"已评估 {i+1}/{len(scripts)}"
                    )

                except Exception as e:
                    results.append({
                        "script_id": script.get("id", i),
                        "success": False,
                        "error": str(e)
                    })
                    failed += 1

            # 返回批量结果
            yield self.format_batch_results(
                results=results,
                total=len(scripts),
                successful=successful,
                failed=failed,
                message=f"批量评估完成: {successful}/{len(scripts)} 通过"
            )

        except Exception as e:
            yield self.format_error(
                error=str(e),
                message="批量评估失败"
            )

    async def _evaluate_script(self, script):
        """模拟评估"""
        await asyncio.sleep(0.2)
        import random
        return random.uniform(60, 95)

    def _get_grade(self, score):
        """根据分数获取等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "中等"
        elif score >= 60:
            return "及格"
        else:
            return "不及格"


# 示例4: 错误处理Agent
class RobustAgent(BaseJubenAgent):
    """演示各种错误处理场景的Agent"""

    def __init__(self):
        super().__init__("robust_agent")

    async def process_request(self, request_data, context=None):
        """演示错误处理"""

        action = request_data.get("action", "")

        # 场景1: 参数缺失
        if action == "missing_param":
            return self.format_error(
                error="缺少必需参数: content",
                message="请求参数不完整",
                code=400
            )

        # 场景2: 参数格式错误
        if action == "invalid_format":
            return self.format_error(
                error="scene_count必须是整数",
                message="参数格式错误",
                code=400,
                metadata={
                    "expected_type": "integer",
                    "received": str(type(request_data.get("scene_count")))
                }
            )

        # 场景3: 资源未找到
        if action == "not_found":
            return self.format_error(
                error="未找到指定的剧本",
                message="剧本不存在",
                code=404,
                metadata={"script_id": request_data.get("script_id")}
            )

        # 场景4: 服务超时
        if action == "timeout":
            return self.format_error(
                error="LLM服务响应超时（30秒）",
                message="服务暂时不可用，请稍后重试",
                code=504,
                metadata={"timeout": 30, "retry_after": 5}
            )

        # 场景5: 成功响应
        return self.format_success(
            data={"result": "操作成功"},
            message="请求处理完成"
        )


# ==================== 测试函数 ====================

async def test_simple_agent():
    """测试简单Agent"""
    logger.info("\n" + "="*60)
    logger.info("测试1: 简单Agent - 剧本生成器")
    logger.info("="*60)

    agent = ScriptGeneratorAgent()

    # 测试成功场景
    logger.info("\n✓ 测试成功场景:")
    result = await agent.process_request({
        "plot_type": "悬疑",
        "scene_count": 3
    })
    logger.info(agent.to_json(result))

    # 测试参数错误
    logger.info("\n✓ 测试参数错误:")
    result = await agent.process_request({
        "plot_type": "悬疑",
        "scene_count": 25  # 超出范围
    })
    logger.info(agent.to_json(result))


async def test_streaming_agent():
    """测试流式Agent"""
    logger.info("\n" + "="*60)
    logger.info("测试2: 流式Agent - 分析器")
    logger.info("="*60)

    agent = StreamingAnalysisAgent()

    logger.info("\n✓ 测试流式输出:")
    async for event in agent.process_request({"content": "测试剧本内容"}):
        event_type = event.get("type")
        message = event.get("message")
        data = event.get("data")

        if event_type == "progress":
            step = data.get("step")
            total = data.get("total")
            logger.info(f"  [{event_type}] 步骤 {step}/{total}: {message}")
        elif event_type == "step_complete":
            logger.info(f"  [{event_type}] {message}")
            logger.info(f"    数据: {data}")
        elif event_type == "complete":
            logger.info(f"  [{event_type}] {message}")
        else:
            logger.info(f"  [{event_type}] {message}")


async def test_batch_agent():
    """测试批量处理Agent"""
    logger.info("\n" + "="*60)
    logger.info("测试3: 批量处理Agent - 评估器")
    logger.info("="*60)

    agent = BatchEvaluationAgent()

    scripts = [
        {"id": "script1", "content": "剧本1内容"},
        {"id": "script2", "content": "剧本2内容"},
        {"id": "script3", "content": "剧本3内容"},
    ]

    logger.info("\n✓ 测试批量处理:")
    async for event in agent.process_request({"scripts": scripts}):
        if event.get("type") == "progress":
            data = event.get("data", {})
            logger.info(f"  进度: {data['current']}/{data['total']} "
                  f"(成功: {data['successful']}, 失败: {data['failed']})")
        elif event.get("type") == "complete" or "code" in event:
            logger.info(f"\n最终结果:")
            logger.info(agent.to_json(event))


async def test_error_handling():
    """测试错误处理"""
    logger.info("\n" + "="*60)
    logger.info("测试4: 错误处理Agent")
    logger.info("="*60)

    agent = RobustAgent()

    test_cases = [
        ("missing_param", "参数缺失"),
        ("invalid_format", "参数格式错误"),
        ("not_found", "资源未找到"),
        ("timeout", "服务超时"),
        ("success", "成功响应")
    ]

    for action, desc in test_cases:
        logger.info(f"\n✓ 测试: {desc}")
        result = await agent.process_request({"action": action})
        logger.info(f"  Code: {result['code']}")
        logger.info(f"  Success: {result['success']}")
        logger.info(f"  Message: {result['message']}")
        if result.get('error'):
            logger.info(f"  Error: {result['error']}")


async def test_validation():
    """测试输出验证"""
    logger.info("\n" + "="*60)
    logger.info("测试5: 输出格式验证")
    logger.info("="*60)

    agent = ScriptGeneratorAgent()

    # 生成标准输出
    valid_output = await agent.process_request({
        "plot_type": "爱情",
        "scene_count": 2
    })

    logger.info("\n✓ 验证标准输出:")
    is_valid = await agent.validate_output_format(valid_output)
    logger.info(f"  验证结果: {'通过' if is_valid else '失败'}")

    # 生成错误输出
    logger.info("\n✓ 验证缺少字段的输出:")
    invalid_output = {"success": True, "message": "测试"}
    is_valid = await agent.validate_output_format(invalid_output)
    logger.info(f"  验证结果: {'通过' if is_valid else '失败'}")


async def test_json_conversion():
    """测试JSON转换"""
    logger.info("\n" + "="*60)
    logger.info("测试6: JSON转换")
    logger.info("="*60)

    agent = ScriptGeneratorAgent()

    result = await agent.process_request({
        "plot_type": "动作",
        "scene_count": 1
    })

    logger.info("\n✓ JSON输出 (ensure_ascii=False):")
    json_str = agent.to_json(result, ensure_ascii=False)
    logger.info(json_str[:500] + "...")

    logger.info("\n✓ JSON输出 (ensure_ascii=True):")
    json_str = agent.to_json(result, ensure_ascii=True)
    logger.info(json_str[:500] + "...")


async def main():
    """运行所有测试"""
    logger.info("\n" + "="*60)
    logger.info("统一输出格式 - 完整测试")
    logger.info("="*60)

    try:
        await test_simple_agent()
        await test_streaming_agent()
        await test_batch_agent()
        await test_error_handling()
        await test_validation()
        await test_json_conversion()

        logger.info("\n" + "="*60)
        logger.info("所有测试完成！")
        logger.info("="*60)

    except Exception as e:
        logger.info(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    asyncio.run(main())

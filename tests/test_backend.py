"""
剧本创作 Agent 平台 - 后端API测试脚本
使用智谱AI免费模型测试所有主要API端点
"""
import asyncio
import aiohttp
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BackendTester:
    """后端API测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "response": response_data
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
        if details:
            logger.info(f"   Details: {details}")
        if response_data and not success:
            logger.info(f"   Response: {json.dumps(response_data, ensure_ascii=False)[:200]}")

    async def test_health_check(self):
        """测试健康检查端点"""
        try:
            async with self.session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Health Check", True, f"Status: {data.get('status')}", data)
                else:
                    self.log_result("Health Check", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Health Check", False, str(e))

    async def test_models_list(self):
        """测试模型列表API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/models?provider=zhipu") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    model_count = data.get("total_count", 0)
                    self.log_result("Models List", True, f"Found {model_count} models", data)
                else:
                    text = await resp.text()
                    self.log_result("Models List", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result("Models List", False, str(e))

    async def test_models_by_type(self):
        """测试按类型获取模型列表"""
        try:
            async with self.session.get(f"{self.base_url}/juben/models/types") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Models By Type", True, f"Categories: {list(data.get('models', {}).keys())}", data)
                else:
                    text = await resp.text()
                    self.log_result("Models By Type", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result("Models By Type", False, str(e))

    async def test_agents_list(self):
        """测试Agents列表API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/agents/list") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    agent_count = data.get("total", 0)
                    self.log_result("Agents List", True, f"Found {agent_count} agents", data)
                else:
                    text = await resp.text()
                    self.log_result("Agents List", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result("Agents List", False, str(e))

    async def test_agents_categories(self):
        """测试Agents分类API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/agents/categories") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    categories = list(data.get("categories", {}).keys())
                    self.log_result("Agents Categories", True, f"Categories: {categories}", data)
                else:
                    text = await resp.text()
                    self.log_result("Agents Categories", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result("Agents Categories", False, str(e))

    async def test_config(self):
        """测试系统配置API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/config") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("System Config", True, "Config retrieved successfully")
                else:
                    text = await resp.text()
                    self.log_result("System Config", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result("System Config", False, str(e))

    async def test_chat_api(self, model: str = "glm-4-flash"):
        """测试聊天API - 使用指定的智谱免费模型"""
        try:
            payload = {
                "input": "你好，请用一句话介绍一下你自己。",
                "user_id": "test_user",
                "model": model,
                "enable_web_search": False,
                "enable_knowledge_base": False
            }
            async with self.session.post(
                f"{self.base_url}/juben/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    # 读取流式响应
                    content = await resp.text()
                    if content and len(content) > 0:
                        self.log_result(f"Chat API ({model})", True, f"Response length: {len(content)} chars")
                    else:
                        self.log_result(f"Chat API ({model})", False, "Empty response")
                else:
                    text = await resp.text()
                    self.log_result(f"Chat API ({model})", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result(f"Chat API ({model})", False, str(e))

    async def test_intent_analyze(self):
        """测试意图分析API"""
        try:
            payload = {
                "input": "我想创作一个关于都市爱情的短剧"
            }
            async with self.session.post(
                f"{self.base_url}/juben/intent/analyze",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Intent Analysis", True, "Intent analyzed successfully", data)
                else:
                    text = await resp.text()
                    self.log_result("Intent Analysis", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result("Intent Analysis", False, str(e))

    async def test_agent_info(self, agent_id: str):
        """测试获取Agent信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/agents/{agent_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    name = data.get("display_name", agent_id)
                    self.log_result(f"Agent Info ({agent_id})", True, f"Agent: {name}")
                else:
                    text = await resp.text()
                    self.log_result(f"Agent Info ({agent_id})", False, f"Status Code: {resp.status}", text)
        except Exception as e:
            self.log_result(f"Agent Info ({agent_id})", False, str(e))

    async def test_recommended_model(self):
        """测试推荐模型API"""
        try:
            purposes = ["default", "reasoning", "vision", "latest"]
            for purpose in purposes:
                async with self.session.get(
                    f"{self.base_url}/juben/models/recommend",
                    params={"purpose": purpose}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        model_name = data.get("recommended_model", {}).get("name", "")
                        self.log_result(f"Recommended Model ({purpose})", True, f"Model: {model_name}")
                    else:
                        self.log_result(f"Recommended Model ({purpose})", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Recommended Model", False, str(e))

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 70)
        logger.info("剧本创作 Agent 平台 - 后端API测试")
        logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"测试目标: {self.base_url}")
        logger.info("=" * 70)
        logger.info()

        # 基础API测试
        logger.info("【基础API测试】")
        await self.test_health_check()
        await self.test_config()
        logger.info()

        # 模型API测试
        logger.info("【模型API测试】")
        await self.test_models_list()
        await self.test_models_by_type()
        await self.test_recommended_model()
        logger.info()

        # Agents API测试
        logger.info("【Agents API测试】")
        await self.test_agents_list()
        await self.test_agents_categories()

        # 测试几个特定Agent
        test_agents = ["short_drama_planner", "short_drama_creator", "short_drama_evaluation"]
        for agent_id in test_agents:
            await self.test_agent_info(agent_id)
        logger.info()

        # 聊天功能测试（使用不同的免费模型）
        logger.info("【聊天API测试 - 智谱免费模型】")
        test_models = [
            "glm-4-flash",        # 基础免费模型
            "glm-4.7-flash",      # 最新免费模型
        ]

        for model in test_models:
            await self.test_chat_api(model)
            await asyncio.sleep(0.5)  # 避免请求过快
        logger.info()

        # 意图分析测试
        logger.info("【意图分析测试】")
        await self.test_intent_analyze()
        logger.info()

        # 打印测试摘要
        self.print_summary()

    def print_summary(self):
        """打印测试摘要"""
        logger.info("=" * 70)
        logger.info("【测试摘要】")
        logger.info("=" * 70)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过: {passed_tests} ✅")
        logger.info(f"失败: {failed_tests} ❌")
        logger.info(f"通过率: {(passed_tests/total_tests*100):.1f}%")
        logger.info()

        if failed_tests > 0:
            logger.info("【失败的测试】")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  - {result['test_name']}: {result['details']}")
        logger.info()

        # 保存测试结果到JSON文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        logger.info(f"测试结果已保存到: {filename}")


async def check_server_running(base_url: str) -> bool:
    """检查服务器是否运行"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
    except:
        return False


async def main():
    """主函数"""
    base_url = "http://localhost:8000"

    # 检查服务器是否运行
    logger.info("检查后端服务状态...")
    if not await check_server_running(base_url):
        logger.info(f"❌ 后端服务未运行！")
        logger.info(f"请先启动后端服务: python main.py")
        logger.info(f"或使用: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    logger.info(f"✅ 后端服务正在运行: {base_url}")
    logger.info()

    # 运行测试
    async with BackendTester(base_url) as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

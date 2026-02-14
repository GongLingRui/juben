"""
剧本创作 Agent 平台 - 完整后端API测试脚本
使用智谱AI免费模型测试所有API端点
"""
import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class BackendTester:
    """后端API完整测试器"""

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
        print(f"{status} - {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, ensure_ascii=False)[:200]}")

    # ==================== 基础API ====================

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

    async def test_juben_health(self):
        """测试juben健康检查"""
        try:
            async with self.session.get(f"{self.base_url}/juben/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Juben Health Check", True, f"Message: {data.get('message')}")
                else:
                    self.log_result("Juben Health Check", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Juben Health Check", False, str(e))

    # ==================== 模型API ====================

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
                    self.log_result("Models By Type", True, f"Categories: {list(data.get('models', {}).keys())}")
                else:
                    self.log_result("Models By Type", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Models By Type", False, str(e))

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

    # ==================== Agents API ====================

    async def test_agents_list(self):
        """测试Agents列表API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/agents/list") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    agent_count = data.get("total", 0)
                    self.log_result("Agents List", True, f"Found {agent_count} agents")
                else:
                    self.log_result("Agents List", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Agents List", False, str(e))

    async def test_agents_categories(self):
        """测试Agents分类API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/agents/categories") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    categories = list(data.get("categories", {}).keys())
                    self.log_result("Agents Categories", True, f"Categories: {categories}")
                else:
                    self.log_result("Agents Categories", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Agents Categories", False, str(e))

    async def test_agent_info(self, agent_id: str):
        """测试获取Agent信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/agents/{agent_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    name = data.get("display_name", agent_id)
                    self.log_result(f"Agent Info ({agent_id})", True, f"Agent: {name}")
                else:
                    self.log_result(f"Agent Info ({agent_id})", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result(f"Agent Info ({agent_id})", False, str(e))

    async def test_agents_search(self):
        """测试Agents搜索API"""
        try:
            async with self.session.get(
                f"{self.base_url}/juben/agents/search",
                params={"query": "创作"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = data.get("total", 0)
                    self.log_result("Agents Search", True, f"Found {count} agents")
                else:
                    self.log_result("Agents Search", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Agents Search", False, str(e))

    # ==================== 聊天API ====================

    async def test_chat_api(self, model: str = "glm-4-flash"):
        """测试聊天API"""
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
            payload = {"input": "我想创作一个关于都市爱情的短剧"}
            async with self.session.post(
                f"{self.base_url}/juben/intent/analyze",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Intent Analysis", True, "Intent analyzed successfully")
                else:
                    self.log_result("Intent Analysis", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Intent Analysis", False, str(e))

    # ==================== 创作助手 API ====================

    async def test_creator_chat(self):
        """测试创作助手聊天API"""
        try:
            payload = {
                "input": "帮我创作一个悬疑短剧的开场场景",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/creator/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Creator Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Creator Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Creator Chat", False, str(e))

    async def test_creator_info(self):
        """测试创作助手信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/creator/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Creator Info", True, "Creator agent info retrieved")
                else:
                    self.log_result("Creator Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Creator Info", False, str(e))

    # ==================== 评估助手 API ====================

    async def test_evaluation_chat(self):
        """测试评估助手聊天API"""
        try:
            payload = {
                "input": "请评估这个短剧创意：一个关于时间旅行的爱情故事",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/evaluation/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Evaluation Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Evaluation Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Evaluation Chat", False, str(e))

    async def test_evaluation_info(self):
        """测试评估助手信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/evaluation/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Evaluation Info", True, "Evaluation agent info retrieved")
                else:
                    self.log_result("Evaluation Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Evaluation Info", False, str(e))

    async def test_evaluation_score(self):
        """测试评分计算API"""
        try:
            payload = {
                "scores": {
                    "情节": 85,
                    "人物": 90,
                    "对话": 80,
                    "创意": 88
                }
            }
            async with self.session.post(
                f"{self.base_url}/juben/evaluation/score",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    score = data.get("overall_score", 0)
                    self.log_result("Evaluation Score", True, f"Overall score: {score}")
                else:
                    self.log_result("Evaluation Score", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Evaluation Score", False, str(e))

    # ==================== 网络搜索 API ====================

    async def test_websearch_chat(self):
        """测试网络搜索聊天API"""
        try:
            payload = {
                "input": "搜索2025年短剧市场趋势",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/websearch/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("WebSearch Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("WebSearch Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("WebSearch Chat", False, str(e))

    async def test_websearch_info(self):
        """测试网络搜索信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/websearch/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("WebSearch Info", True, "WebSearch agent info retrieved")
                else:
                    self.log_result("WebSearch Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("WebSearch Info", False, str(e))

    async def test_search_web(self):
        """测试Web搜索API"""
        try:
            payload = {"query": "短剧创作技巧", "count": 5}
            async with self.session.post(
                f"{self.base_url}/juben/search/web",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Search Web", True, "Web search completed")
                else:
                    self.log_result("Search Web", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Search Web", False, str(e))

    # ==================== 知识库 API ====================

    async def test_knowledge_chat(self):
        """测试知识库聊天API"""
        try:
            payload = {
                "input": "查询短剧反转技巧",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/knowledge/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Knowledge Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Knowledge Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Knowledge Chat", False, str(e))

    async def test_knowledge_info(self):
        """测试知识库信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/knowledge/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Knowledge Info", True, "Knowledge agent info retrieved")
                else:
                    self.log_result("Knowledge Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Knowledge Info", False, str(e))

    async def test_knowledge_collections(self):
        """测试知识库集合API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/knowledge/collections") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Knowledge Collections", True, "Collections retrieved")
                else:
                    self.log_result("Knowledge Collections", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Knowledge Collections", False, str(e))

    async def test_knowledge_search(self):
        """测试知识库搜索API"""
        try:
            payload = {"query": "短剧", "collection": "script_segments"}
            async with self.session.post(
                f"{self.base_url}/juben/knowledge/search",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Knowledge Search", True, "Knowledge search completed")
                else:
                    self.log_result("Knowledge Search", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Knowledge Search", False, str(e))

    # ==================== 文件引用 API ====================

    async def test_file_reference_chat(self):
        """测试文件引用聊天API"""
        try:
            payload = {
                "input": "引用文件: @example.txt",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/file-reference/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("File Reference Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("File Reference Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("File Reference Chat", False, str(e))

    async def test_file_reference_info(self):
        """测试文件引用信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/file-reference/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("File Reference Info", True, "File reference agent info retrieved")
                else:
                    self.log_result("File Reference Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("File Reference Info", False, str(e))

    # ==================== 故事分析 API ====================

    async def test_story_analysis_analyze(self):
        """测试故事五元素分析API"""
        try:
            payload = {
                "input": "这是一个关于青年追梦的故事，主人公历经挫折最终成功",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/story-analysis/analyze",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Story Analysis", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Story Analysis", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Story Analysis", False, str(e))

    async def test_story_analysis_info(self):
        """测试故事分析信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/story-analysis/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Story Analysis Info", True, "Story analysis agent info retrieved")
                else:
                    self.log_result("Story Analysis Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Story Analysis Info", False, str(e))

    # ==================== 剧集分析 API ====================

    async def test_series_analysis_analyze(self):
        """测试已播剧集分析API"""
        try:
            payload = {
                "input": "分析这个剧集的特点和亮点",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/series-analysis/analyze",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Series Analysis", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Series Analysis", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Series Analysis", False, str(e))

    async def test_series_analysis_info(self):
        """测试剧集分析信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/series-analysis/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Series Analysis Info", True, "Series analysis agent info retrieved")
                else:
                    self.log_result("Series Analysis Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Series Analysis Info", False, str(e))

    # ==================== 情节点工作流 API ====================

    async def test_plot_points_workflow_execute(self):
        """测试情节点工作流执行API"""
        try:
            payload = {
                "input": "生成一个都市爱情短剧的完整情节点",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/plot-points-workflow/execute",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Plot Points Workflow", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Plot Points Workflow", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Plot Points Workflow", False, str(e))

    async def test_plot_points_workflow_info(self):
        """测试情节点工作流信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/plot-points-workflow/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Plot Points Workflow Info", True, "Workflow info retrieved")
                else:
                    self.log_result("Plot Points Workflow Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Plot Points Workflow Info", False, str(e))

    # ==================== 故事大纲 API ====================

    async def test_story_summary_chat(self):
        """测试故事大纲生成API"""
        try:
            payload = {
                "input": "生成一个科幻悬疑短剧的故事大纲",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/story-summary/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Story Summary Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Story Summary Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Story Summary Chat", False, str(e))

    async def test_story_summary_info(self):
        """测试故事大纲信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/story-summary/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Story Summary Info", True, "Story summary agent info retrieved")
                else:
                    self.log_result("Story Summary Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Story Summary Info", False, str(e))

    # ==================== 大情节点 API ====================

    async def test_major_plot_points_chat(self):
        """测试大情节点分析API"""
        try:
            payload = {
                "input": "分析这个故事的主要情节点：一个失忆的侦探寻找自己的过去",
                "user_id": "test_user"
            }
            async with self.session.post(
                f"{self.base_url}/juben/major-plot-points/chat",
                json=payload
            ) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    self.log_result("Major Plot Points Chat", True, f"Response length: {len(content)} chars")
                else:
                    self.log_result("Major Plot Points Chat", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Major Plot Points Chat", False, str(e))

    async def test_major_plot_points_info(self):
        """测试大情节点信息API"""
        try:
            async with self.session.get(f"{self.base_url}/juben/major-plot-points/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result("Major Plot Points Info", True, "Major plot points agent info retrieved")
                else:
                    self.log_result("Major Plot Points Info", False, f"Status Code: {resp.status}")
        except Exception as e:
            self.log_result("Major Plot Points Info", False, str(e))

    # ==================== 运行所有测试 ====================

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("剧本创作 Agent 平台 - 完整后端API测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试目标: {self.base_url}")
        print("=" * 70)
        print()

        # 1. 基础API测试
        print("【1. 基础API测试】")
        await self.test_health_check()
        await self.test_juben_health()
        await self.test_config()
        print()

        # 2. 模型API测试
        print("【2. 模型API测试】")
        await self.test_models_list()
        await self.test_models_by_type()
        await self.test_recommended_model()
        print()

        # 3. Agents API测试
        print("【3. Agents API测试】")
        await self.test_agents_list()
        await self.test_agents_categories()
        await self.test_agents_search()

        test_agents = ["short_drama_planner", "short_drama_creator", "short_drama_evaluation",
                       "story_five_elements", "plot_points_workflow"]
        for agent_id in test_agents:
            await self.test_agent_info(agent_id)
        print()

        # 4. 聊天API测试
        print("【4. 聊天API测试】")
        await self.test_chat_api("glm-4-flash")
        await self.test_intent_analyze()
        print()

        # 5. 创作助手API测试
        print("【5. 创作助手API测试】")
        await self.test_creator_info()
        await self.test_creator_chat()
        print()

        # 6. 评估助手API测试
        print("【6. 评估助手API测试】")
        await self.test_evaluation_info()
        await self.test_evaluation_score()
        await self.test_evaluation_chat()
        print()

        # 7. 网络搜索API测试
        print("【7. 网络搜索API测试】")
        await self.test_websearch_info()
        await self.test_search_web()
        await self.test_websearch_chat()
        print()

        # 8. 知识库API测试
        print("【8. 知识库API测试】")
        await self.test_knowledge_info()
        await self.test_knowledge_collections()
        await self.test_knowledge_search()
        await self.test_knowledge_chat()
        print()

        # 9. 文件引用API测试
        print("【9. 文件引用API测试】")
        await self.test_file_reference_info()
        await self.test_file_reference_chat()
        print()

        # 10. 故事分析API测试
        print("【10. 故事分析API测试】")
        await self.test_story_analysis_info()
        await self.test_story_analysis_analyze()
        print()

        # 11. 剧集分析API测试
        print("【11. 剧集分析API测试】")
        await self.test_series_analysis_info()
        await self.test_series_analysis_analyze()
        print()

        # 12. 情节点工作流API测试
        print("【12. 情节点工作流API测试】")
        await self.test_plot_points_workflow_info()
        await self.test_plot_points_workflow_execute()
        print()

        # 13. 故事大纲API测试
        print("【13. 故事大纲API测试】")
        await self.test_story_summary_info()
        await self.test_story_summary_chat()
        print()

        # 14. 大情节点API测试
        print("【14. 大情节点API测试】")
        await self.test_major_plot_points_info()
        await self.test_major_plot_points_chat()
        print()

        # 打印测试摘要
        self.print_summary()

    def print_summary(self):
        """打印测试摘要"""
        print("=" * 70)
        print("【测试摘要】")
        print("=" * 70)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"通过率: {(passed_tests/total_tests*100):.1f}%")
        print()

        if failed_tests > 0:
            print("【失败的测试】")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['details']}")
        print()

        # 保存测试结果到JSON文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_full_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"测试结果已保存到: {filename}")


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
    print("检查后端服务状态...")
    if not await check_server_running(base_url):
        print(f"❌ 后端服务未运行！")
        print(f"请先启动后端服务: python main.py")
        print(f"或使用: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    print(f"✅ 后端服务正在运行: {base_url}")
    print()

    # 运行测试
    async with BackendTester(base_url) as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

"""
Agent注册表
负责管理和调度所有专业Agent
"""
import logging
from typing import Dict, Any, Optional, List
import importlib

logger = logging.getLogger(__name__)

try:
    from ..agents.base_juben_agent import BaseJubenAgent
    from ..utils.agent_naming import canonical_agent_id
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent
    from utils.agent_naming import canonical_agent_id


class AgentRegistry:
    """Agent注册表"""

    def __init__(self):
        """初始化Agent注册表"""
        self.agents = {}
        # 按类别组织的Agent配置
        self.agent_configs = {
            # === 核心编排类 ===
            "juben_orchestrator": {
                "class_name": "JubenOrchestrator",
                "module_path": "agents.juben_orchestrator",
                "description": "剧本编排器 - 核心协调Agent",
                "category": "orchestration",
                "enabled": True
            },
            "juben_concierge": {
                "class_name": "JubenConcierge",
                "module_path": "agents.juben_concierge",
                "description": "剧本礼宾服务 - 意图识别与分发",
                "category": "orchestration",
                "enabled": True
            },
            "series_analysis_orchestrator": {
                "class_name": "SeriesAnalysisOrchestrator",
                "module_path": "agents.series_analysis_orchestrator",
                "description": "剧集分析编排器",
                "category": "orchestration",
                "enabled": True
            },

            # === 故事分析类 ===
            "story_evaluation_agent": {
                "class_name": "StoryEvaluationAgent",
                "module_path": "agents.story_evaluation_agent",
                "description": "故事质量评估Agent",
                "category": "story_analysis",
                "enabled": True
            },
            "story_summary_generator_agent": {
                "class_name": "StorySummaryGeneratorAgent",
                "module_path": "agents.story_summary_generator_agent",
                "description": "故事摘要生成Agent",
                "category": "story_analysis",
                "enabled": True
            },
            "story_five_elements_agent": {
                "class_name": "StoryFiveElementsAgent",
                "module_path": "agents.story_five_elements_agent",
                "description": "故事五元素分析Agent",
                "category": "story_analysis",
                "enabled": True
            },
            "story_outline_evaluation_agent": {
                "class_name": "StoryOutlineEvaluationAgent",
                "module_path": "agents.story_outline_evaluation_agent",
                "description": "故事大纲评估Agent",
                "category": "story_analysis",
                "enabled": True
            },
            "story_type_analyzer_agent": {
                "class_name": "StoryTypeAnalyzerAgent",
                "module_path": "agents.story_type_analyzer_agent",
                "description": "故事类型分析Agent",
                "category": "story_analysis",
                "enabled": True
            },

            # === 角色开发类 ===
            "character_profile_generator_agent": {
                "class_name": "CharacterProfileGeneratorAgent",
                "module_path": "agents.character_profile_generator_agent",
                "description": "角色档案生成Agent",
                "category": "character",
                "enabled": True
            },
            "character_relationship_analyzer_agent": {
                "class_name": "CharacterRelationshipAnalyzerAgent",
                "module_path": "agents.character_relationship_analyzer_agent",
                "description": "角色关系分析Agent",
                "category": "character",
                "enabled": True
            },

            # === 情节开发类 ===
            "major_plot_points_agent": {
                "class_name": "MajorPlotPointsAgent",
                "module_path": "agents.major_plot_points_agent",
                "description": "主要情节点Agent",
                "category": "plot",
                "enabled": True
            },
            "detailed_plot_points_agent": {
                "class_name": "DetailedPlotPointsAgent",
                "module_path": "agents.detailed_plot_points_agent",
                "description": "详细情节点Agent",
                "category": "plot",
                "enabled": True
            },
            "plot_points_analyzer_agent": {
                "class_name": "PlotPointsAnalyzerAgent",
                "module_path": "agents.plot_points_analyzer_agent",
                "description": "情节点分析Agent",
                "category": "plot",
                "enabled": True
            },
            "plot_points_workflow_agent": {
                "class_name": "PlotPointsWorkflowAgent",
                "module_path": "agents.plot_points_workflow_agent",
                "description": "情节点工作流Agent",
                "category": "plot",
                "enabled": True
            },

            # === 短剧创作类 ===
            "short_drama_planner_agent": {
                "class_name": "ShortDramaPlannerAgent",
                "module_path": "agents.short_drama_planner_agent",
                "description": "短剧策划Agent",
                "category": "creation",
                "enabled": True
            },
            "short_drama_creator_agent": {
                "class_name": "ShortDramaCreatorAgent",
                "module_path": "agents.short_drama_creator_agent",
                "description": "短剧创作Agent",
                "category": "creation",
                "enabled": True
            },
            "drama_workflow_agent": {
                "class_name": "DramaWorkflowAgent",
                "module_path": "agents.drama_workflow_agent",
                "description": "剧本创作工作流Agent",
                "category": "creation",
                "enabled": True
            },

            # === 评估类 ===
            "short_drama_evaluation_agent": {
                "class_name": "ShortDramaEvaluationAgent",
                "module_path": "agents.short_drama_evaluation_agent",
                "description": "短剧评估Agent",
                "category": "evaluation",
                "enabled": True
            },
            "script_evaluation_agent": {
                "class_name": "ScriptEvaluationAgent",
                "module_path": "agents.script_evaluation_agent",
                "description": "剧本评估Agent",
                "category": "evaluation",
                "enabled": True
            },
            "ip_evaluation_agent": {
                "class_name": "IPEvaluationAgent",
                "module_path": "agents.ip_evaluation_agent",
                "description": "IP价值评估Agent",
                "category": "evaluation",
                "enabled": True
            },
            "novel_screening_evaluation_agent": {
                "class_name": "NovelScreeningEvaluationAgent",
                "module_path": "agents.novel_screening_evaluation_agent",
                "description": "小说初筛评估Agent",
                "category": "evaluation",
                "enabled": True
            },
            "text_processor_evaluation_agent": {
                "class_name": "TextProcessorEvaluationAgent",
                "module_path": "agents.text_processor_evaluation_agent",
                "description": "文本处理器评估Agent",
                "category": "evaluation",
                "enabled": True
            },
            "result_analyzer_evaluation_agent": {
                "class_name": "ResultAnalyzerEvaluationAgent",
                "module_path": "agents.result_analyzer_evaluation_agent",
                "description": "结果分析评估Agent",
                "category": "evaluation",
                "enabled": True
            },
            "score_analyzer_agent": {
                "class_name": "ScoreAnalyzerAgent",
                "module_path": "agents.score_analyzer_agent",
                "description": "评分分析Agent",
                "category": "evaluation",
                "enabled": True
            },
            "drama_analysis_agent": {
                "class_name": "DramaAnalysisAgent",
                "module_path": "agents.drama_analysis_agent",
                "description": "剧本分析Agent",
                "category": "evaluation",
                "enabled": True
            },

            # === 剧集分析类 ===
            "series_analysis_agent": {
                "class_name": "SeriesAnalysisAgent",
                "module_path": "agents.series_analysis_agent",
                "description": "剧集分析Agent",
                "category": "series",
                "enabled": True
            },
            "series_info_agent": {
                "class_name": "SeriesInfoAgent",
                "module_path": "agents.series_info_agent",
                "description": "剧集信息Agent",
                "category": "series",
                "enabled": True
            },
            "series_name_extractor_agent": {
                "class_name": "SeriesNameExtractorAgent",
                "module_path": "agents.series_name_extractor_agent",
                "description": "剧集名称提取Agent",
                "category": "series",
                "enabled": True
            },

            # === 工具类 ===
            "mind_map_agent": {
                "class_name": "MindMapAgent",
                "module_path": "agents.mind_map_agent",
                "description": "思维导图Agent",
                "category": "tool",
                "enabled": True
            },
            "websearch_agent": {
                "class_name": "WebsearchAgent",
                "module_path": "agents.websearch_agent",
                "description": "网络搜索Agent",
                "category": "tool",
                "enabled": True
            },
            "knowledge_agent": {
                "class_name": "KnowledgeAgent",
                "module_path": "agents.knowledge_agent",
                "description": "知识库查询Agent",
                "category": "tool",
                "enabled": True
            },
            "file_reference_agent": {
                "class_name": "FileReferenceAgent",
                "module_path": "agents.file_reference_agent",
                "description": "文件引用解析Agent",
                "category": "tool",
                "enabled": True
            },
            "ocr_agent": {
                "class_name": "OCRAgent",
                "module_path": "agents.ocr_agent",
                "description": "OCR识别Agent",
                "category": "tool",
                "enabled": True
            },
            "document_generator_agent": {
                "class_name": "DocumentGeneratorAgent",
                "module_path": "agents.document_generator_agent",
                "description": "文档生成Agent",
                "category": "tool",
                "enabled": True
            },
            "output_formatter_agent": {
                "class_name": "OutputFormatterAgent",
                "module_path": "agents.output_formatter_agent",
                "description": "输出格式化Agent",
                "category": "tool",
                "enabled": True
            },
            "text_splitter_agent": {
                "class_name": "TextSplitterAgent",
                "module_path": "agents.text_splitter_agent",
                "description": "文本分割Agent",
                "category": "tool",
                "enabled": True
            },
            "text_truncator_agent": {
                "class_name": "TextTruncatorAgent",
                "module_path": "agents.text_truncator_agent",
                "description": "文本截断Agent",
                "category": "tool",
                "enabled": True
            },

            # === 高级功能类 ===
            "logic_consistency_agent": {
                "class_name": "LogicConsistencyAgent",
                "module_path": "agents.logic_consistency_agent",
                "description": "逻辑一致性检查Agent",
                "category": "advanced",
                "enabled": True
            },
            "graph_rag_agent": {
                "class_name": "GraphRAGAgent",
                "module_path": "agents.graph_rag_agent",
                "description": "图RAG检索Agent",
                "category": "advanced",
                "enabled": True
            },
            "meta_optimizer_agent": {
                "class_name": "MetaOptimizerAgent",
                "module_path": "agents.meta_optimizer_agent",
                "description": "元优化器Agent",
                "category": "advanced",
                "enabled": True
            },
            "result_integrator_agent": {
                "class_name": "ResultIntegratorAgent",
                "module_path": "agents.result_integrator_agent",
                "description": "结果集成Agent",
                "category": "advanced",
                "enabled": True
            }
        }

        # 类别映射（用于前端分类显示）
        self.category_mapping = {
            "orchestration": {
                "name": "核心编排",
                "description": "系统核心协调和分发Agent",
                "icon": "🎯"
            },
            "story_analysis": {
                "name": "故事分析",
                "description": "故事内容和质量分析",
                "icon": "📖"
            },
            "character": {
                "name": "角色开发",
                "description": "角色创建和关系分析",
                "icon": "👤"
            },
            "plot": {
                "name": "情节开发",
                "description": "情节规划和工作流",
                "icon": "🎬"
            },
            "creation": {
                "name": "短剧创作",
                "description": "短剧策划和创作",
                "icon": "✍️"
            },
            "evaluation": {
                "name": "评估分析",
                "description": "各类评估和分析Agent",
                "icon": "📊"
            },
            "series": {
                "name": "剧集分析",
                "description": "剧集内容分析",
                "icon": "📺"
            },
            "tool": {
                "name": "工具",
                "description": "辅助工具Agent",
                "icon": "🔧"
            },
            "advanced": {
                "name": "高级功能",
                "description": "高级分析和优化Agent",
                "icon": "🚀"
            }
        }

        # 别名映射（支持多种Agent名称格式）
        self.alias_mapping = {
            # 短剧策划相关
            "short_drama_planner": "juben_orchestrator",
            "short_drama_planner_agent": "short_drama_planner_agent",
            "planner": "short_drama_planner_agent",

            # 短剧创作相关
            "short_drama_creator": "short_drama_creator_agent",
            "creator": "short_drama_creator_agent",
            "drama_creator": "short_drama_creator_agent",

            # 故事分析相关
            "story_analysis": "story_evaluation_agent",
            "story_evaluation": "story_evaluation_agent",
            "story_summary": "story_summary_generator_agent",
            "story_five_elements": "story_five_elements_agent",
            "five_elements": "story_five_elements_agent",

            # 角色相关
            "character_profile": "character_profile_generator_agent",
            "character_relationship": "character_relationship_analyzer_agent",

            # 情节相关
            "plot_points": "major_plot_points_agent",
            "detailed_plot_points": "detailed_plot_points_agent",
            "plot_workflow": "plot_points_workflow_agent",

            # 评估相关
            "short_drama_evaluation": "short_drama_evaluation_agent",
            "script_evaluation": "script_evaluation_agent",
            "ip_evaluation": "ip_evaluation_agent",
            "drama_evaluation": "drama_analysis_agent",

            # 工具相关
            "mindmap": "mind_map_agent",
            "web_search": "websearch_agent",
            "knowledge": "knowledge_agent",
            "file_ref": "file_reference_agent",

            # 剧集相关
            "series": "series_analysis_agent",
            "series_info": "series_info_agent"
        }

    def _resolve_agent_type(self, agent_type: str) -> Optional[str]:
        """
        解析Agent类型，支持别名

        Args:
            agent_type: Agent类型或别名

        Returns:
            规范化的Agent类型，如果不存在返回None
        """
        # 先尝试直接匹配
        if agent_type in self.agent_configs:
            return agent_type

        # 尝试别名映射
        canonical_id = canonical_agent_id(agent_type)
        if canonical_id in self.agent_configs:
            return canonical_id

        # 尝试别名表
        if agent_type in self.alias_mapping:
            return self.alias_mapping[agent_type]

        # 尝试规范化后的别名
        if canonical_id in self.alias_mapping:
            return self.alias_mapping[canonical_id]

        return None

    async def get_agent(self, agent_type: str) -> Optional[BaseJubenAgent]:
        """
        获取Agent实例

        Args:
            agent_type: Agent类型（支持别名）

        Returns:
            BaseJubenAgent: Agent实例
        """
        # 解析Agent类型
        resolved_type = self._resolve_agent_type(agent_type)
        if resolved_type is None:
            return None

        # 检查是否启用
        config = self.agent_configs.get(resolved_type)
        if not config or not config.get("enabled", True):
            return None

        # 如果已经创建过，直接返回
        if resolved_type in self.agents:
            return self.agents[resolved_type]

        try:
            # 动态导入Agent类
            module_path = config["module_path"]
            class_name = config["class_name"]

            # 导入模块
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)

            # 创建Agent实例
            agent_instance = agent_class()

            # 缓存Agent实例
            self.agents[resolved_type] = agent_instance

            return agent_instance

        except Exception as e:
            logger.error(f"❌ 创建Agent失败: {resolved_type}, 错误: {e}")
            return None

    def get_available_agents(self, category: Optional[str] = None) -> List[str]:
        """
        获取可用的Agent类型列表

        Args:
            category: 可选，按类别过滤

        Returns:
            Agent类型列表
        """
        if category:
            return [
                agent_type for agent_type, config in self.agent_configs.items()
                if config.get("category") == category and config.get("enabled", True)
            ]
        return [
            agent_type for agent_type, config in self.agent_configs.items()
            if config.get("enabled", True)
        ]

    def get_agent_info(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent信息

        Args:
            agent_type: Agent类型（支持别名）

        Returns:
            Agent信息字典
        """
        resolved_type = self._resolve_agent_type(agent_type)
        if resolved_type is None:
            return None

        config = self.agent_configs[resolved_type]
        category = config.get("category", "")

        return {
            "agent_type": resolved_type,
            "class_name": config["class_name"],
            "module_path": config["module_path"],
            "description": config["description"],
            "category": category,
            "enabled": config.get("enabled", True),
            "is_loaded": resolved_type in self.agents,
            "category_info": self.category_mapping.get(category, {})
        }

    def get_all_agents_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有Agent信息
        Returns:
            按类别组织的Agent信息
        """
        result = {}
        for agent_type, config in self.agent_configs.items():
            if not config.get("enabled", True):
                continue
            category = config.get("category", "uncategorized")
            if category not in result:
                result[category] = {
                    "category_info": self.category_mapping.get(category, {"name": category, "icon": "📦"}),
                    "agents": []
                }
            result[category]["agents"].append(self.get_agent_info(agent_type))
        return result

    def get_agents_by_category(self) -> Dict[str, Dict[str, Any]]:
        """
        按类别获取Agent信息
        Returns:
            按类别组织的Agent信息
        """
        return self.get_all_agents_info()

    def clear_agent_cache(self, agent_type: Optional[str] = None):
        """
        清除Agent缓存

        Args:
            agent_type: 指定Agent类型（支持别名），None表示清除所有
        """
        if agent_type:
            resolved_type = self._resolve_agent_type(agent_type)
            if resolved_type and resolved_type in self.agents:
                del self.agents[resolved_type]
        else:
            self.agents.clear()

    def register_agent(
        self,
        agent_type: str,
        agent_class,
        module_path: str,
        description: str = "",
        category: str = "custom",
        enabled: bool = True
    ):
        """
        注册新的Agent类型

        Args:
            agent_type: Agent类型
            agent_class: Agent类
            module_path: 模块路径
            description: 描述
            category: 类别
            enabled: 是否启用
        """
        self.agent_configs[agent_type] = {
            "class_name": agent_class.__name__,
            "module_path": module_path,
            "description": description,
            "category": category,
            "enabled": enabled
        }

    def get_agent_statistics(self) -> Dict[str, Any]:
        """
        获取Agent统计信息
        Returns:
            统计信息字典
        """
        total_agents = len(self.agent_configs)
        loaded_agents = len(self.agents)
        enabled_agents = sum(1 for c in self.agent_configs.values() if c.get("enabled", True))

        # 按类别统计
        category_stats = {}
        for config in self.agent_configs.values():
            if not config.get("enabled", True):
                continue
            category = config.get("category", "uncategorized")
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1

        return {
            "total_agents": total_agents,
            "enabled_agents": enabled_agents,
            "loaded_agents": loaded_agents,
            "load_rate": loaded_agents / enabled_agents if enabled_agents > 0 else 0,
            "category_stats": category_stats,
            "categories": list(self.category_mapping.keys()),
            "available_agents": self.get_available_agents()
        }

    def get_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有类别信息
        Returns:
            类别信息字典
        """
        return self.category_mapping.copy()

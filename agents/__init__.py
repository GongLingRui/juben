"""
竖屏短剧策划助手 - Agents模块
 提供专业的短剧策划服务
"""

from .base_juben_agent import BaseJubenAgent
from .short_drama_planner_agent import ShortDramaPlannerAgent
from .short_drama_creator_agent import ShortDramaCreatorAgent
from .short_drama_evaluation_agent import ShortDramaEvaluationAgent
from .websearch_agent import WebSearchAgent
from .knowledge_agent import KnowledgeAgent

# 大情节点与详细情节点工作流智能体
from .plot_points_workflow_agent import PlotPointsWorkflowAgent
# from .story_summary_agent import StorySummaryAgent  # 文件不存在
# from .major_plot_points_agent import MajorPlotPointsAgent  # 文件不存在
from .mind_map_agent import MindMapAgent
from .detailed_plot_points_agent import DetailedPlotPointsAgent
from .output_formatter_agent import OutputFormatterAgent
from .story_summary_generator_agent import StorySummaryGeneratorAgent

# 小说初筛评估和分析智能体
from .novel_screening_evaluation_agent import NovelScreeningEvaluationAgent
from .text_truncator_agent import TextTruncatorAgent
from .story_evaluation_agent import StoryEvaluationAgent
from .score_analyzer_agent import ScoreAnalyzerAgent

# IP初筛评估和剧本评估智能体
from .ip_evaluation_agent import IPEvaluationAgent
from .script_evaluation_agent import ScriptEvaluationAgent
from .text_processor_evaluation_agent import TextProcessorEvaluationAgent
from .result_analyzer_evaluation_agent import ResultAnalyzerEvaluationAgent
# from .ip_evaluation_orchestrator import IPEvaluationOrchestrator  # 文件不存在
# from .script_evaluation_orchestrator import ScriptEvaluationOrchestrator  # 文件不存在

# 已播剧集分析与拉工作流智能体
from .series_name_extractor_agent import SeriesNameExtractorAgent
from .series_info_agent import SeriesInfoAgent
from .drama_analysis_agent import DramaAnalysisAgent
from .series_analysis_orchestrator import SeriesAnalysisOrchestrator
from .series_analysis_agent import SeriesAnalysisAgent

# 故事五元素工作流智能体
from .story_type_analyzer_agent import StoryTypeAnalyzerAgent
# from .story_synopsis_agent import StorySynopsisAgent  # 文件不存在
# from .character_profile_agent import CharacterProfileAgent  # 文件不存在
from .character_profile_generator_agent import CharacterProfileGeneratorAgent
# from .character_relationship_agent import CharacterRelationshipAgent  # 文件不存在
from .character_relationship_analyzer_agent import CharacterRelationshipAnalyzerAgent
# from .story_five_elements_orchestrator import StoryFiveElementsOrchestrator  # 文件不存在
from .story_five_elements_agent import StoryFiveElementsAgent

# 情节点戏剧功能分析智能体
# from .plot_points_drama_analysis_agent import PlotPointsDramaAnalysisAgent  # 文件不存在
from .plot_points_analyzer_agent import PlotPointsAnalyzerAgent

__all__ = [
    "BaseJubenAgent",
    "ShortDramaPlannerAgent",
    "ShortDramaCreatorAgent",
    "ShortDramaEvaluationAgent",
    "WebSearchAgent",
    "KnowledgeAgent",
    # 大情节点与详细情节点工作流智能体
    "PlotPointsWorkflowAgent",
    # "StorySummaryAgent",  # 文件不存在
    # "MajorPlotPointsAgent",  # 文件不存在
    "MindMapAgent",
    "DetailedPlotPointsAgent",
    "OutputFormatterAgent",
    "StorySummaryGeneratorAgent",
    # 小说初筛评估和分析智能体
    "NovelScreeningEvaluationAgent",
    "TextTruncatorAgent",
    "StoryEvaluationAgent",
    "ScoreAnalyzerAgent",
    # IP初筛评估和剧本评估智能体
    "IPEvaluationAgent",
    "ScriptEvaluationAgent",
    "TextProcessorEvaluationAgent",
    "ResultAnalyzerEvaluationAgent",
    # "IPEvaluationOrchestrator",  # 文件不存在
    # "ScriptEvaluationOrchestrator",  # 文件不存在
    # 已播剧集分析与拉工作流智能体
    "SeriesNameExtractorAgent",
    "SeriesInfoAgent",
    "DramaAnalysisAgent",
    "SeriesAnalysisOrchestrator",
    "SeriesAnalysisAgent",
    # 故事五元素工作流智能体
    "StoryTypeAnalyzerAgent",
    # "StorySynopsisAgent",  # 文件不存在
    # "CharacterProfileAgent",  # 文件不存在
    "CharacterProfileGeneratorAgent",
    # "CharacterRelationshipAgent",  # 文件不存在
    "CharacterRelationshipAnalyzerAgent",
    # "StoryFiveElementsOrchestrator",  # 文件不存在
    "StoryFiveElementsAgent",
    # 情节点戏剧功能分析智能体
    # "PlotPointsDramaAnalysisAgent",  # 文件不存在
    "PlotPointsAnalyzerAgent"
]

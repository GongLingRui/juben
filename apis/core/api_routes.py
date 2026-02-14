"""
竖屏短剧策划助手 - API路由
 项目的优秀设计，提供统一的API接口
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 🆕 【新增】导入分布式锁相关模块
from utils.distributed_lock import (
    SessionLockContext,
    LockAcquisitionError,
    with_session_lock
)
from apis.core.distributed_lock_dependencies import lock_acquisition_exception_handler

# 🆕 【新增】导入流式响应管理器
from utils.stream_manager import (
    StreamResponseGenerator,
    StreamSessionManager,
    get_stream_response_generator,
    get_stream_session_manager
)

from agents.short_drama_planner_agent import ShortDramaPlannerAgent
from agents.short_drama_creator_agent import ShortDramaCreatorAgent
from agents.short_drama_evaluation_agent import ShortDramaEvaluationAgent
from agents.websearch_agent import WebSearchAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.file_reference_agent import FileReferenceAgent
from agents.story_five_elements_agent import StoryFiveElementsAgent
from agents.series_analysis_agent import SeriesAnalysisAgent

# 大情节点与详细情节点工作流智能体
from agents.plot_points_workflow_agent import PlotPointsWorkflowAgent
from agents.story_summary_generator_agent import StorySummaryGeneratorAgent
from agents.major_plot_points_agent import MajorPlotPointsAgent
from agents.mind_map_agent import MindMapAgent
from agents.detailed_plot_points_agent import DetailedPlotPointsAgent

# 其他智能体
from agents.character_profile_generator_agent import CharacterProfileGeneratorAgent
from agents.character_relationship_analyzer_agent import CharacterRelationshipAnalyzerAgent
from agents.script_evaluation_agent import ScriptEvaluationAgent
from agents.ip_evaluation_agent import IPEvaluationAgent
from agents.story_type_analyzer_agent import StoryTypeAnalyzerAgent
from agents.story_evaluation_agent import StoryEvaluationAgent
from agents.story_outline_evaluation_agent import StoryOutlineEvaluationAgent
from agents.novel_screening_evaluation_agent import NovelScreeningEvaluationAgent
from agents.document_generator_agent import DocumentGeneratorAgent
from agents.output_formatter_agent import OutputFormatterAgent
from agents.score_analyzer_agent import ScoreAnalyzerAgent
from agents.text_processor_evaluation_agent import TextProcessorEvaluationAgent
from agents.result_analyzer_evaluation_agent import ResultAnalyzerEvaluationAgent
from agents.series_info_agent import SeriesInfoAgent
from agents.series_name_extractor_agent import SeriesNameExtractorAgent
from agents.drama_workflow_agent import DramaWorkflowAgent

from workflows.plot_points_workflow import PlotPointsWorkflowOrchestrator
from config.settings import juben_settings
from utils.logger import get_logger
from utils.error_handler import get_error_handler, handle_error
from utils.storage_manager import get_storage
from utils.agent_dispatch import build_agent_generator
from .schemas import (
    BaseResponse, ErrorResponse, ChatRequest, ChatResponse, ResumeRequest, StreamEvent, EventType, StreamContentType, ContentTypeConfig,
    AgentInfo, AgentListResponse, HealthResponse, StatsResponse,
    # Notes相关模型
    NoteCreateRequest, NoteUpdateRequest, NoteListResponse, NoteSelectRequest,
    NoteExportRequest, NoteExportResponse, UserSelections, InteractionType, NoteContentType
)

# 设置日志
logger = get_logger("API", level=juben_settings.log_level)

# 创建路由器
router = APIRouter(prefix="/juben", tags=["竖屏短剧策划助手"])


async def _resolve_input_with_references(request: ChatRequest) -> Dict[str, Any]:
    """
    解析@引用并返回解析结果与追踪信息
    """
    resolved_input = request.input
    reference_trace: List[Dict[str, Any]] = []
    try:
        from utils.reference_resolver import get_juben_reference_resolver
        resolver = get_juben_reference_resolver()
        resolved_input = await resolver.resolve_references(
            text=request.input,
            user_id=request.user_id or "unknown",
            session_id=request.session_id or f"session_{hash(request.input) % 10000}",
            query=request.input,
            project_id=request.project_id
        )
        reference_trace = resolver.get_reference_trace()
    except Exception as e:
        logger.warning(f"⚠️ 引用解析失败，使用原文: {e}")

    return {
        "resolved_input": resolved_input,
        "reference_trace": reference_trace
    }


def _ingest_rag_trace(agent: Any, request_data: Dict[str, Any]) -> None:
    try:
        if not request_data:
            return
        trace = request_data.get("rag_trace")
        if trace and hasattr(agent, "ingest_external_rag_trace"):
            agent.ingest_external_rag_trace(trace)
    except Exception:
        pass

# ==================== Agents 列表相关端点 ====================

# 所有可用的Agents配置（与前端保持一致）
AGENTS_LIST_CONFIG = [
    {
        "id": "short_drama_planner",
        "name": "ShortDramaPlannerAgent",
        "display_name": "短剧策划助手",
        "description": "专业的短剧策划和创作建议助手，提供剧本结构、情节设计、人物塑造等全方位策划支持",
        "category": "planning",
        "icon": "📋",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/chat",
        "features": ["剧本策划", "情节设计建议", "结构优化", "创作指导"],
        "capabilities": ["分析剧本需求并提供专业策划建议", "设计合理的情节结构和故事节奏", "提供人物塑造和对话写作指导", "优化剧本的商业价值和观赏性"],
        "status": "active"
    },
    {
        "id": "short_drama_creator",
        "name": "ShortDramaCreatorAgent",
        "display_name": "短剧创作助手",
        "description": "专业短剧内容创作助手，帮助生成高质量剧本内容",
        "category": "creation",
        "icon": "✍️",
        "model": "glm-4.7-flash",
        "api_endpoint": "/juben/creator/chat",
        "features": ["剧本创作", "场景描写", "对话生成", "情节展开"],
        "status": "active"
    },
    {
        "id": "short_drama_evaluation",
        "name": "ShortDramaEvaluationAgent",
        "display_name": "短剧评估助手",
        "description": "专业的短剧质量评估助手，从多维度评估剧本质量并提供改进建议",
        "category": "evaluation",
        "icon": "📊",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/evaluation/chat",
        "features": ["质量评估", "多维度打分", "改进建议", "市场分析"],
        "status": "active"
    },
    {
        "id": "script_evaluation",
        "name": "ScriptEvaluationAgent",
        "display_name": "剧本评估专家",
        "description": "深度剧本分析评估，提供专业的质量诊断和优化方案",
        "category": "evaluation",
        "icon": "🎯",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/script/evaluation",
        "features": ["剧本诊断", "质量评分", "问题定位", "优化方案"],
        "status": "active"
    },
    {
        "id": "ip_evaluation",
        "name": "IPEvaluationAgent",
        "display_name": "IP价值评估",
        "description": "评估IP的商业价值和开发潜力",
        "category": "evaluation",
        "icon": "💎",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/ip/evaluation",
        "features": ["IP价值评估", "市场潜力分析", "商业化建议", "竞品对比"],
        "status": "beta"
    },
    {
        "id": "story_five_elements",
        "name": "StoryFiveElementsAgent",
        "display_name": "故事五元素分析",
        "description": "分析故事的核心五元素：人物、情节、环境、主题、风格",
        "category": "analysis",
        "icon": "🔍",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/story-analysis/analyze",
        "features": ["五元素分析", "结构梳理", "主题提炼", "风格识别"],
        "status": "active"
    },
    {
        "id": "series_analysis",
        "name": "SeriesAnalysisAgent",
        "display_name": "已播剧集分析",
        "description": "分析已播剧集的数据和表现，提取成功经验",
        "category": "analysis",
        "icon": "📺",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/series-analysis/analyze",
        "features": ["剧集数据分析", "成功要素提取", "趋势总结", "经验归纳"],
        "status": "active"
    },
    {
        "id": "drama_analysis",
        "name": "DramaAnalysisAgent",
        "display_name": "剧本深度分析",
        "description": "对剧本进行深度专业分析，挖掘潜在价值",
        "category": "analysis",
        "icon": "🔬",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/drama/analysis",
        "features": ["剧本结构分析", "人物关系梳理", "情节节奏分析", "价值挖掘"],
        "status": "active"
    },
    {
        "id": "story_type_analyzer",
        "name": "StoryTypeAnalyzerAgent",
        "display_name": "故事类型分析",
        "description": "识别和分析故事类型，提供类型化创作建议",
        "category": "analysis",
        "icon": "📚",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/story-type/analyze",
        "features": ["类型识别", "类型特征分析", "创作规范建议", "市场定位"],
        "status": "active"
    },
    {
        "id": "plot_points_workflow",
        "name": "PlotPointsWorkflowAgent",
        "display_name": "情节点工作流",
        "description": "完整的大情节点与详细情节点生成工作流",
        "category": "workflow",
        "icon": "🔄",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/plot-points-workflow/execute",
        "features": ["大情节点生成", "详细情节点展开", "结构化输出", "可视化展示"],
        "status": "active"
    },
    {
        "id": "drama_workflow",
        "name": "DramaWorkflowAgent",
        "display_name": "剧本创作工作流",
        "description": "端到端的剧本创作工作流，从创意到成品",
        "category": "workflow",
        "icon": "🎬",
        "model": "glm-4.7-flash",
        "api_endpoint": "/juben/drama-workflow/execute",
        "features": ["创意开发", "大纲生成", "剧本创作", "质量检验"],
        "status": "beta"
    },
    {
        "id": "character_profile_generator",
        "name": "CharacterProfileGeneratorAgent",
        "display_name": "人物小传生成",
        "description": "为故事中的主要人物生成详细的人物小传",
        "category": "character",
        "icon": "👤",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/character/profile",
        "features": ["人物识别", "小传生成", "性格分析", "背景构建"],
        "status": "active"
    },
    {
        "id": "character_relationship_analyzer",
        "name": "CharacterRelationshipAnalyzerAgent",
        "display_name": "人物关系分析",
        "description": "分析故事中人物之间的复杂关系网络",
        "category": "character",
        "icon": "👥",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/character/relationship",
        "features": ["关系识别", "关系类型分析", "关系网络构建", "关系演变追踪"],
        "status": "active"
    },
    {
        "id": "story_summary_generator",
        "name": "StorySummaryGeneratorAgent",
        "display_name": "故事大纲生成",
        "description": "为长篇故事生成精炼的故事大纲",
        "category": "story",
        "icon": "📝",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/story/summary",
        "features": ["内容提取", "要点总结", "结构梳理", "精炼表达"],
        "status": "active"
    },
    {
        "id": "detailed_plot_points",
        "name": "DetailedPlotPointsAgent",
        "display_name": "详细情节点",
        "description": "展开详细的情节点内容，丰富故事细节",
        "category": "story",
        "icon": "📍",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/plot-points/detailed",
        "features": ["情节点展开", "细节补充", "场景描写", "情节衔接"],
        "status": "active"
    },
    {
        "id": "plot_points_analyzer",
        "name": "PlotPointsAnalyzerAgent",
        "display_name": "情节点分析",
        "description": "分析和优化故事情节点的设计",
        "category": "story",
        "icon": "📌",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/plot-points/analyze",
        "features": ["情节点识别", "结构分析", "节奏评估", "优化建议"],
        "status": "active"
    },
    {
        "id": "mind_map",
        "name": "MindMapAgent",
        "display_name": "思维导图",
        "description": "生成故事结构可视化思维导图",
        "category": "story",
        "icon": "🧠",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/mind-map/generate",
        "features": ["结构提取", "导图生成", "可视化展示", "编辑导出"],
        "status": "active"
    },
    {
        "id": "major_plot_points",
        "name": "MajorPlotPointsAgent",
        "display_name": "大情节点分析",
        "description": "分析并提取故事的主要情节点",
        "category": "story",
        "icon": "🎬",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/major-plot-points/chat",
        "features": ["大情节点提取", "情节点描述", "时间线构建", "结构优化"],
        "status": "active"
    },
    {
        "id": "websearch",
        "name": "WebSearchAgent",
        "display_name": "网络搜索",
        "description": "实时搜索网络信息，获取最新资料",
        "category": "utility",
        "icon": "🌐",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/websearch/chat",
        "features": ["实时搜索", "信息聚合", "来源标注", "智能摘要"],
        "status": "active"
    },
    {
        "id": "knowledge",
        "name": "KnowledgeAgent",
        "display_name": "知识库查询",
        "description": "查询剧本创作知识库，获取专业资料",
        "category": "utility",
        "icon": "📚",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/knowledge/chat",
        "features": ["知识检索", "相似度匹配", "专业资料", "桥段参考"],
        "status": "active"
    },
    {
        "id": "file_reference",
        "name": "FileReferenceAgent",
        "display_name": "文件引用解析",
        "description": "解析和引用外部文件内容",
        "category": "utility",
        "icon": "📄",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/file-reference/chat",
        "features": ["文件解析", "内容提取", "智能引用", "格式兼容"],
        "status": "active"
    },
    {
        "id": "document_generator",
        "name": "DocumentGeneratorAgent",
        "display_name": "文档生成器",
        "description": "生成标准化的剧本文档",
        "category": "utility",
        "icon": "📃",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/document/generate",
        "features": ["格式转换", "标准排版", "批量生成", "导出功能"],
        "status": "beta"
    },
    {
        "id": "output_formatter",
        "name": "OutputFormatterAgent",
        "display_name": "输出格式化",
        "description": "格式化AI输出，确保符合规范",
        "category": "utility",
        "icon": "✨",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/output/format",
        "features": ["格式规范", "样式统一", "错误修正", "质量提升"],
        "status": "active"
    },
    {
        "id": "story_evaluation",
        "name": "StoryEvaluationAgent",
        "display_name": "故事质量评估",
        "description": "评估故事的整体质量和吸引力",
        "category": "evaluation",
        "icon": "⭐",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/story/evaluation",
        "features": ["质量打分", "吸引力分析", "改进建议", "对比评估"],
        "status": "active"
    },
    {
        "id": "story_outline_evaluation",
        "name": "StoryOutlineEvaluationAgent",
        "display_name": "大纲评估",
        "description": "评估故事大纲的完整性和可行性",
        "category": "evaluation",
        "icon": "📋",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/outline/evaluation",
        "features": ["完整性检查", "可行性评估", "结构调整", "补充建议"],
        "status": "active"
    },
    {
        "id": "novel_screening_evaluation",
        "name": "NovelScreeningEvaluationAgent",
        "display_name": "小说筛选评估",
        "description": "评估小说是否适合改编为短剧",
        "category": "evaluation",
        "icon": "📖",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/novel/screening",
        "features": ["改编可行性", "IP价值评估", "改编建议", "版权分析"],
        "status": "active"
    },
    {
        "id": "text_splitter",
        "name": "TextSplitterAgent",
        "display_name": "文本分割",
        "description": "智能分割长文本为合适的段落",
        "category": "utility",
        "icon": "✂️",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/text/split",
        "features": ["智能分割", "长度控制", "语义完整", "边界识别"],
        "status": "active"
    },
    {
        "id": "text_truncator",
        "name": "TextTruncatorAgent",
        "display_name": "文本截断",
        "description": "按要求截断文本并保持完整性",
        "category": "utility",
        "icon": "✂️",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/text/truncate",
        "features": ["长度截断", "完整性保证", "摘要保留", "边界优化"],
        "status": "active"
    },
    {
        "id": "result_integrator",
        "name": "ResultIntegratorAgent",
        "display_name": "结果集成器",
        "description": "集成多个Agent的结果",
        "category": "workflow",
        "icon": "🔗",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/result/integrate",
        "features": ["结果聚合", "格式统一", "去重合并", "优先级排序"],
        "status": "active"
    },
    {
        "id": "score_analyzer",
        "name": "ScoreAnalyzerAgent",
        "display_name": "评分分析器",
        "description": "分析评分数据，提供解读",
        "category": "evaluation",
        "icon": "📈",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/score/analyze",
        "features": ["评分统计", "分布分析", "趋势解读", "对比分析"],
        "status": "active"
    },
    {
        "id": "text_processor_evaluation",
        "name": "TextProcessorEvaluationAgent",
        "display_name": "文本处理评估",
        "description": "评估文本处理的质量和效果",
        "category": "evaluation",
        "icon": "📝",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/text/evaluate",
        "features": ["质量评估", "效果分析", "问题识别", "改进建议"],
        "status": "active"
    },
    {
        "id": "result_analyzer_evaluation",
        "name": "ResultAnalyzerEvaluationAgent",
        "display_name": "结果分析评估",
        "description": "分析评估结果，提供洞察",
        "category": "evaluation",
        "icon": "📊",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/result/analyze",
        "features": ["结果分析", "数据洞察", "趋势发现", "建议生成"],
        "status": "active"
    },
    {
        "id": "series_info",
        "name": "SeriesInfoAgent",
        "display_name": "剧集信息提取",
        "description": "从文本中提取剧集相关信息",
        "category": "utility",
        "icon": "📺",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/series/info",
        "features": ["信息提取", "数据整理", "格式规范", "批量处理"],
        "status": "active"
    },
    {
        "id": "series_name_extractor",
        "name": "SeriesNameExtractorAgent",
        "display_name": "剧名提取",
        "description": "智能识别和提取短剧名称",
        "category": "utility",
        "icon": "🏷️",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/series/name",
        "features": ["名称识别", "别名提取", "规范化处理", "去重过滤"],
        "status": "active"
    }
]

# Agent分类配置
AGENT_CATEGORIES_CONFIG = {
    "planning": {"name": "策划类", "icon": "📋"},
    "creation": {"name": "创作类", "icon": "✍️"},
    "evaluation": {"name": "评估类", "icon": "📊"},
    "analysis": {"name": "分析类", "icon": "🔍"},
    "workflow": {"name": "工作流", "icon": "🔄"},
    "character": {"name": "人物类", "icon": "👤"},
    "story": {"name": "故事类", "icon": "📖"},
    "utility": {"name": "工具类", "icon": "🛠️"},
}


@router.get("/agents-legacy/list")
async def get_agents_list(category: Optional[str] = None):
    """
    获取所有可用的Agents列表

    Args:
        category: 可选，按分类筛选

    Returns:
        Dict: 包含agents列表和统计信息
    """
    try:
        agents = AGENTS_LIST_CONFIG

        # 按分类筛选
        if category:
            agents = [a for a in agents if a.get("category") == category]

        # 统计各分类数量
        category_counts = {}
        for agent in AGENTS_LIST_CONFIG:
            cat = agent.get("category", "other")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "success": True,
            "agents": agents,
            "total": len(agents),
            "category_counts": category_counts
        }
    except Exception as e:
        logger.error(f"获取Agents列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents-legacy/{agent_id}")
async def get_agent_detail(agent_id: str):
    """
    获取指定Agent的详细信息

    Args:
        agent_id: Agent ID

    Returns:
        Dict: Agent详细信息
    """
    try:
        agent = next((a for a in AGENTS_LIST_CONFIG if a.get("id") == agent_id), None)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "success": True,
            "agent": agent
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents-legacy/categories")
async def get_agent_categories():
    """
    获取所有Agent分类

    Returns:
        Dict: 分类信息
    """
    try:
        # 统计各分类数量
        category_counts = {}
        for agent in AGENTS_LIST_CONFIG:
            cat = agent.get("category", "other")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "success": True,
            "categories": AGENT_CATEGORIES_CONFIG,
            "counts": category_counts,
            "total": len(AGENTS_LIST_CONFIG)
        }
    except Exception as e:
        logger.error(f"获取Agent分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents-legacy/search")
async def search_agents(query: str = ""):
    """
    搜索Agents

    Args:
        query: 搜索关键词

    Returns:
        Dict: 搜索结果
    """
    try:
        if not query:
            return {
                "success": True,
                "results": [],
                "total": 0
            }

        query_lower = query.lower()
        results = []

        for agent in AGENTS_LIST_CONFIG:
            # 搜索id、name、display_name、description
            if (query_lower in agent.get("id", "").lower() or
                query_lower in agent.get("name", "").lower() or
                query_lower in agent.get("display_name", "").lower() or
                query_lower in agent.get("description", "").lower()):
                results.append(agent)
                continue

            # 搜索features
            for feature in agent.get("features", []):
                if query_lower in feature.lower():
                    results.append(agent)
                    break

        return {
            "success": True,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"搜索Agents失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 全局异常处理
async def handle_exception(request: Request, exc: Exception):
    """统一异常处理"""
    logger.error(f"API异常: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="服务器内部错误",
            error_code="INTERNAL_ERROR",
            detail=str(exc) if juben_settings.debug else "请联系管理员"
        ).dict()
    )

# 全局Agent实例
planner_agent = None
creator_agent = None
evaluation_agent = None
websearch_agent = None
knowledge_agent = None
file_reference_agent = None
story_five_elements_agent = None
series_analysis_agent = None


def get_planner_agent() -> ShortDramaPlannerAgent:
    """获取策划Agent实例"""
    global planner_agent
    if planner_agent is None:
        # 使用 OpenAI 的 gpt-3.5-turbo（最便宜的模型）
        planner_agent = ShortDramaPlannerAgent(model_provider="openai")
    return planner_agent


def get_creator_agent() -> ShortDramaCreatorAgent:
    """获取创作Agent实例"""
    global creator_agent
    if creator_agent is None:
        creator_agent = ShortDramaCreatorAgent()
    return creator_agent


def get_evaluation_agent() -> ShortDramaEvaluationAgent:
    """获取评估Agent实例"""
    global evaluation_agent
    if evaluation_agent is None:
        evaluation_agent = ShortDramaEvaluationAgent()
    return evaluation_agent


def get_websearch_agent() -> WebSearchAgent:
    """获取网络搜索Agent实例"""
    global websearch_agent
    if websearch_agent is None:
        websearch_agent = WebSearchAgent()
    return websearch_agent


def get_knowledge_agent() -> KnowledgeAgent:
    """获取知识库查询Agent实例"""
    global knowledge_agent
    if knowledge_agent is None:
        knowledge_agent = KnowledgeAgent()
    return knowledge_agent


def get_file_reference_agent() -> FileReferenceAgent:
    """获取文件引用Agent实例"""
    global file_reference_agent
    if file_reference_agent is None:
        file_reference_agent = FileReferenceAgent()
    return file_reference_agent


def get_story_five_elements_agent() -> StoryFiveElementsAgent:
    """获取故事五元素分析Agent实例"""
    global story_five_elements_agent
    if story_five_elements_agent is None:
        story_five_elements_agent = StoryFiveElementsAgent()
    return story_five_elements_agent


def get_series_analysis_agent() -> SeriesAnalysisAgent:
    """获取已播剧集分析Agent实例"""
    global series_analysis_agent
    if series_analysis_agent is None:
        series_analysis_agent = SeriesAnalysisAgent()
    return series_analysis_agent


# 请求模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    input: str
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    file: Optional[str] = None
    file_ids: Optional[List[str]] = None  # 支持多个文件ID
    model: Optional[str] = None  # 模型名称，如 glm-4-flash
    model_provider: Optional[str] = None
    enable_web_search: Optional[bool] = True
    enable_knowledge_base: Optional[bool] = True


class StoryAnalysisRequest(BaseModel):
    """故事五元素分析请求模型"""
    input: str
    file: Optional[str] = None
    chunk_size: Optional[int] = 10000
    length_size: Optional[int] = 50000
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    model_provider: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# 流式响应生成器（重构版：使用 StreamResponseGenerator）
async def generate_stream_response(
    request_data: Dict[str, Any],
    context: Dict[str, Any],
    message_id: str = None
):
    """
    生成流式响应（重构版）

    特性：
    1. Redis 缓存最后 50 个 token
    2. 自动异常处理和 SSE 错误事件
    3. 支持 message_id 追踪
    4. 心跳机制防止连接超时

    Args:
        request_data: 请求数据
        context: 上下文信息（必须包含 session_id 和 user_id）
        message_id: 消息 ID（可选，自动生成）

    Yields:
        str: SSE 格式的事件
    """
    try:
        agent = get_planner_agent()
        _ingest_rag_trace(agent, request_data)

        # 获取流式响应生成器
        stream_generator = get_stream_response_generator()

        # 提取 session_id 和 user_id
        session_id = context.get("session_id", "unknown")
        user_id = context.get("user_id", "unknown")

        # 生成流式响应
        async for sse_event in stream_generator.generate(
            build_agent_generator(agent, request_data, context),
            session_id=session_id,
            user_id=user_id,
            message_id=message_id
        ):
            yield sse_event

    except Exception as e:
        logger.error(f"流式响应生成失败: {e}")
        # 发送错误事件（SSE 格式）
        error_sse = {
            "event": "error",
            "data": {
                "content": f"处理失败: {str(e)}",
                "metadata": {
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
        }
        yield f"data: {json.dumps(error_sse, ensure_ascii=False)}\n\n"


async def generate_file_reference_stream_response(request_data: Dict[str, Any], context: Dict[str, Any]):
    """生成文件引用流式响应"""
    try:
        agent = get_file_reference_agent()
        _ingest_rag_trace(agent, request_data)
        
        async for event in build_agent_generator(agent, request_data, context):
            # 转换为SSE格式
            event_data = {
                "event": event.get("event_type", "message"),
                "data": {
                    "content": event.get("data", ""),
                    "metadata": event.get("metadata", {}),
                    "timestamp": event.get("timestamp", "")
                }
            }
            
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        logger.error(f"文件引用流式响应生成失败: {e}")
        error_event = {
            "event": "error",
            "data": {
                "content": f"文件引用处理失败: {str(e)}",
                "metadata": {},
                "timestamp": ""
            }
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


async def generate_story_analysis_stream_response(request_data: Dict[str, Any], context: Dict[str, Any]):
    """生成故事五元素分析流式响应"""
    try:
        agent = get_story_five_elements_agent()
        _ingest_rag_trace(agent, request_data)
        
        async for event in build_agent_generator(agent, request_data, context):
            # 转换为SSE格式
            event_data = {
                "event": event.get("event_type", "message"),
                "data": {
                    "content": event.get("data", ""),
                    "metadata": event.get("metadata", {}),
                    "timestamp": event.get("timestamp", "")
                }
            }
            
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        logger.error(f"故事五元素分析流式响应生成失败: {e}")
        error_event = {
            "event": "error",
            "data": {
                "content": f"处理失败: {str(e)}",
                "metadata": {},
                "timestamp": ""
            }
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


async def generate_series_analysis_stream_response(request_data: Dict[str, Any], context: Dict[str, Any]):
    """生成已播剧集分析流式响应"""
    try:
        agent = get_series_analysis_agent()
        _ingest_rag_trace(agent, request_data)
        
        async for event in build_agent_generator(agent, request_data, context):
            # 转换为SSE格式
            event_data = {
                "event": event.get("event_type", "message"),
                "data": {
                    "content": event.get("data", ""),
                    "metadata": event.get("metadata", {}),
                    "timestamp": event.get("timestamp", "")
                }
            }
            
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        logger.error(f"已播剧集分析流式响应生成失败: {e}")
        error_event = {
            "event": "error",
            "data": {
                "content": f"处理失败: {str(e)}",
                "metadata": {},
                "timestamp": ""
            }
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    聊天接口（带分布式锁和流式缓存）

    特性：
    1. 🆕 API限流保护
    2. 分布式锁确保同一 session 串行处理
    3. Redis 缓存最后 50 个 token，支持断点续传
    4. 返回 message_id 用于断点续传
    5. 自动异常处理和 SSE 错误事件
    6. 🆕 访问统计

    Args:
        request: 聊天请求

    Returns:
        StreamingResponse: 流式响应（响应头包含 X-Message-ID）

    Raises:
        HTTPException: 429 - 当 session 正在被处理时或超过限流
    """
    # 提取 session_id 和 user_id
    session_id = request.session_id or f"session_{hash(request.input)}"
    user_id = request.user_id or "unknown"

    # 🆕 【新增】记录访问统计（后台执行，不阻塞主流程）
    try:
        from utils.access_counter import increment_access
        asyncio.create_task(increment_access(user_id))
    except Exception:
        pass  # 访问统计失败不影响主流程

    # 🆕 【新增】API限流检查
    try:
        from utils.rate_limiter import check_rate_limit
        is_allowed, rate_limit_info = await check_rate_limit(
            identifier=f"{user_id}:{session_id}",
            limit=60,  # 每分钟60次请求
            window_seconds=60
        )

        if not is_allowed:
            logger.warning(f"⚠️ 触发限流: user={user_id}, session={session_id}, info={rate_limit_info}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "请求过于频繁，请稍后再试",
                    "rate_limit_info": rate_limit_info
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"⚠️ 限流检查失败，继续处理请求: {e}")

    # 🆕 【新增】生成 message_id
    stream_manager = get_stream_session_manager()
    message_id = stream_manager.generate_message_id(session_id, user_id)

    # 🆕 【新增】使用分布式锁确保同一 session 串行处理
    async with SessionLockContext(
        session_id=session_id,
        user_id=user_id,
        lock_timeout=300,  # 5分钟超时
        blocking=False     # 不阻塞，直接返回 429
    ) as lock:
        try:
            logger.info(f"收到聊天请求: {request.input}, model: {request.model}, session: {session_id}, message_id: {message_id}")

            # 🆕 【新增】解析用户输入中的@引用
            resolved_input = request.input
            reference_trace = []
            try:
                from utils.reference_resolver import get_juben_reference_resolver
                resolver = get_juben_reference_resolver()
                resolved_input = await resolver.resolve_references(
                    text=request.input,
                    user_id=user_id,
                    session_id=session_id,
                    query=request.input,
                    project_id=request.project_id
                )
                reference_trace = resolver.get_reference_trace()
                if resolved_input != request.input:
                    logger.info(f"✅ 解析到@引用，原文长度: {len(request.input)}, 解析后长度: {len(resolved_input)}")
            except Exception as e:
                logger.warning(f"⚠️ 引用解析失败，使用原文: {e}")

            # 构建请求数据
            request_data = {
                "input": resolved_input,  # 🆕 使用解析后的文本
                "original_input": request.input,  # 🆕 保留原文用于日志
                "enable_web_search": request.enable_web_search,
                "enable_knowledge_base": request.enable_knowledge_base,
                "rag_trace": reference_trace
            }

            # 构建上下文
            context = {
                "user_id": user_id,
                "session_id": session_id,
                "project_id": request.project_id,
                "model_provider": request.model_provider or juben_settings.default_provider,
                "model": request.model  # 传递模型名称
            }

            # 🆕 【新增】返回流式响应（带 message_id 响应头）
            return StreamingResponse(
                generate_stream_response(request_data, context, message_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "X-Message-ID": message_id,  # 🆕 返回 message_id 供断点续传使用
                    "X-Session-ID": session_id
                }
            )

        except LockAcquisitionError as e:
            # 获取锁失败 - 返回 429
            logger.warning(f"⚠️ Session 锁获取失败: {session_id}, {str(e)}")
            raise HTTPException(
                status_code=429,
                detail="AI 正在思考中，请稍后再试"
            )

        except Exception as e:
            logger.error(f"聊天接口处理失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/resume")
async def resume_chat(request: ResumeRequest):
    """
    断点续传接口

    当网络断开后，通过 message_id 恢复流式传输。

    响应流程：
    1. 从 Redis 获取缓存的事件
    2. 发送从 from_sequence 之后的所有事件
    3. 如果消息已完成，发送完成事件
    4. 如果消息未完成，提示前端重新发起请求

    Args:
        request: 断点续传请求（包含 message_id 和 from_sequence）

    Returns:
        StreamingResponse: 缓存的事件流
    """
    try:
        logger.info(f"断点续传请求: message_id={request.message_id}, from_sequence={request.from_sequence}")

        # 获取流式响应生成器
        stream_generator = get_stream_response_generator()

        # 返回缓存的事件流
        return StreamingResponse(
            stream_generator.resume(request.message_id, request.from_sequence),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "X-Message-ID": request.message_id
            }
        )

    except Exception as e:
        logger.error(f"断点续传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/message/{message_id}")
async def get_message_info(message_id: str):
    """
    获取消息信息

    返回指定 message_id 的元数据和缓存状态。

    Args:
        message_id: 消息 ID

    Returns:
        Dict: 消息信息
    """
    try:
        stream_manager = get_stream_session_manager()

        # 获取消息元数据
        meta = await stream_manager.get_message_meta(message_id)

        if not meta:
            raise HTTPException(status_code=404, detail="消息不存在或已过期")

        # 获取缓存的事件数量
        redis = await stream_manager._get_redis()
        if redis:
            cache_key = f"{stream_manager.STREAM_CACHE_PREFIX}{message_id}"
            cache_size = await redis.llen(cache_key)
        else:
            cache_size = 0

        return {
            "success": True,
            "message_id": message_id,
            "meta": meta,
            "cache_size": cache_size,
            "cache_available": cache_size > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_models(provider: str = "zhipu"):
    """
    获取可用模型列表

    Args:
        provider: 模型提供商 (zhipu/openrouter/openai)

    Returns:
        Dict: 模型列表
    """
    try:
        from utils.llm_client import list_available_models, get_model_for_purpose

        models = list_available_models(provider)

        # 获取当前默认模型
        default_model = get_model_for_purpose("default")

        # 获取各场景推荐模型
        purpose_models = {
            "default": get_model_for_purpose("default"),
            "reasoning": get_model_for_purpose("reasoning"),
            "vision": get_model_for_purpose("vision"),
            "image_gen": get_model_for_purpose("image_gen"),
            "video_gen": get_model_for_purpose("video_gen"),
            "latest": get_model_for_purpose("latest")
        }

        return {
            "success": True,
            "provider": provider,
            "models": models,
            "default_model": default_model,
            "purpose_models": purpose_models,
            "total_count": len(models)
        }

    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/recommend")
async def get_recommended_model(purpose: str = "default"):
    """
    获取指定用途的推荐模型

    Args:
        purpose: 用途 (default/reasoning/vision/image_gen/video_gen/latest)

    Returns:
        Dict: 推荐模型信息
    """
    try:
        from utils.llm_client import get_model_for_purpose, ZhipuModel, ModelType

        model_name = get_model_for_purpose(purpose)
        model_config = ZhipuModel.get_model(model_name)

        if not model_config:
            raise HTTPException(status_code=404, detail=f"未找到推荐模型: {purpose}")

        return {
            "success": True,
            "purpose": purpose,
            "recommended_model": {
                "name": model_name,
                "display_name": model_config.get("display_name", model_name),
                "description": model_config.get("description", ""),
                "max_tokens": model_config.get("max_tokens", 0),
                "thinking_enabled": model_config.get("thinking_enabled", False)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推荐模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/types")
async def get_models_by_type():
    """
    按类型获取模型列表

    Returns:
        Dict: 按类型分类的模型列表
    """
    try:
        from utils.llm_client import ZhipuModel, ModelType

        result = {
            "success": True,
            "models": {
                "text": [],
                "vision": [],
                "image_generation": [],
                "video_generation": []
            }
        }

        # 文本模型
        for name, config in ZhipuModel.get_models_by_type(ModelType.TEXT).items():
            result["models"]["text"].append({
                "name": name,
                "display_name": config.get("display_name", name),
                "description": config.get("description", ""),
                "max_tokens": config.get("max_tokens", 0)
            })

        # 视觉模型
        for name, config in ZhipuModel.get_models_by_type(ModelType.VISION).items():
            result["models"]["vision"].append({
                "name": name,
                "display_name": config.get("display_name", name),
                "description": config.get("description", ""),
                "max_tokens": config.get("max_tokens", 0)
            })

        # 图像生成模型
        for name, config in ZhipuModel.get_models_by_type(ModelType.IMAGE_GENERATION).items():
            result["models"]["image_generation"].append({
                "name": name,
                "display_name": config.get("display_name", name),
                "description": config.get("description", "")
            })

        # 视频生成模型
        for name, config in ZhipuModel.get_models_by_type(ModelType.VIDEO_GENERATION).items():
            result["models"]["video_generation"].append({
                "name": name,
                "display_name": config.get("display_name", name),
                "description": config.get("description", "")
            })

        return result

    except Exception as e:
        logger.error(f"获取模型类型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """
    获取系统配置
    
    Returns:
        Dict: 系统配置
    """
    try:
        return {
            "success": True,
            "config": juben_settings.to_dict()
        }
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    try:
        # 检查依赖服务状态
        dependencies = {
            "database": True,  # 这里可以添加实际的数据库连接检查
            "redis": True,     # 这里可以添加实际的Redis连接检查
            "milvus": True,    # 这里可以添加实际的Milvus连接检查
            "zhipu_api": bool(os.getenv("ZHIPU_API_KEY")),
        }
        
        # 检查Agent状态
        agent_status = {
            "planner": get_planner_agent() is not None,
            "creator": get_creator_agent() is not None,
            "evaluator": get_evaluation_agent() is not None,
            "websearch": get_websearch_agent() is not None,
            "knowledge": get_knowledge_agent() is not None,
        }
        
        # 计算系统运行时间
        uptime = "unknown"  # 这里可以添加实际的运行时间计算
        
        return HealthResponse(
            message="服务运行正常",
            status="healthy",
            version=juben_settings.app_version,
            uptime=uptime,
            dependencies=dependencies
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            message="服务异常",
            status="unhealthy",
            version=juben_settings.app_version,
            uptime="unknown",
            dependencies={}
        )


@router.post("/intent/analyze")
async def analyze_intent(request: Dict[str, Any]):
    """
    意图分析接口
    
    Args:
        request: 包含input字段的请求
        
    Returns:
        Dict: 意图分析结果
    """
    try:
        user_input = request.get("input", "")
        if not user_input:
            raise HTTPException(status_code=400, detail="缺少input字段")
        
        agent = get_planner_agent()
        intent_result = await agent.intent_recognizer.analyze(user_input)
        
        return {
            "success": True,
            "intent_result": intent_result
        }
        
    except Exception as e:
        logger.error(f"意图分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/collections")
async def get_knowledge_collections():
    """
    获取知识库集合列表
    
    Returns:
        Dict: 知识库集合列表
    """
    try:
        agent = get_planner_agent()
        collections = agent.knowledge_client.list_collections()
        
        collection_info = []
        for collection in collections:
            info = agent.knowledge_client.get_collection_info(collection)
            collection_info.append({
                "name": collection,
                "info": info
            })
        
        return {
            "success": True,
            "collections": collection_info
        }
        
    except Exception as e:
        logger.error(f"获取知识库集合失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/search")
async def search_knowledge(request: Dict[str, Any]):
    """
    知识库搜索接口
    
    Args:
        request: 包含query和collection字段的请求
        
    Returns:
        Dict: 搜索结果
    """
    try:
        query = request.get("query", "")
        collection = request.get("collection", "script_segments")
        
        if not query:
            raise HTTPException(status_code=400, detail="缺少query字段")
        
        agent = get_planner_agent()
        result = await agent.knowledge_client.search(query, collection=collection)
        
        return {
            "success": True,
            "search_result": result
        }
        
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/web")
async def search_web(request: Dict[str, Any]):
    """
    网络搜索接口
    
    Args:
        request: 包含query字段的请求
        
    Returns:
        Dict: 搜索结果
    """
    try:
        query = request.get("query", "")
        count = request.get("count", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="缺少query字段")
        
        agent = get_planner_agent()
        result = agent.search_client.search_web(query, count=count)
        
        return {
            "success": True,
            "search_result": result
        }
        
    except Exception as e:
        logger.error(f"网络搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 竖屏短剧创作助手端点 ====================

@router.post("/creator/chat")
async def creator_chat(request: ChatRequest):
    """
    创作助手聊天接口
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        # 获取创作Agent
        agent = get_creator_agent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{hash(request.input) % 10000}",
            "project_id": request.project_id,
            "history": []  # 可以扩展历史记录功能
        }
        
        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "model_provider": request.model_provider,
            "enable_web_search": request.enable_web_search,
            "enable_knowledge_base": request.enable_knowledge_base,
            "rag_trace": resolved["reference_trace"]
        }
        _ingest_rag_trace(agent, request_data)
        _ingest_rag_trace(agent, request_data)
        _ingest_rag_trace(agent, request_data)
        _ingest_rag_trace(agent, request_data)
        _ingest_rag_trace(agent, request_data)
        
        async def generate_response():
            """生成响应流"""
            try:
                async for event in build_agent_generator(agent, request_data, context):
                    # 转换为统一的SSE格式
                    event_data = {
                        "event": event.get("event_type", "message"),
                        "data": {
                            "content": event.get("data", ""),
                            "metadata": event.get("metadata", {}),
                            "timestamp": event.get("timestamp", "")
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"创作助手响应生成失败: {e}")
                error_event = {
                    "event_type": "error",
                    "data": f"创作助手响应生成失败: {str(e)}",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"创作助手聊天接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/creator/info")
async def get_creator_info():
    """
    获取创作助手信息
    
    Returns:
        Dict: 创作助手信息
    """
    try:
        agent = get_creator_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取创作助手信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 竖屏短剧评估助手端点 ====================

@router.post("/evaluation/chat")
async def evaluation_chat(request: ChatRequest):
    """
    评估助手聊天接口
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        # 获取评估Agent
        agent = get_evaluation_agent()

        resolved = await _resolve_input_with_references(request)

        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{hash(request.input) % 10000}",
            "project_id": request.project_id,
            "history": []  # 可以扩展历史记录功能
        }

        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "model_provider": request.model_provider,
            "enable_web_search": request.enable_web_search,
            "enable_knowledge_base": request.enable_knowledge_base,
            "rag_trace": resolved["reference_trace"]
        }
        _ingest_rag_trace(agent, request_data)
        
        async def generate_response():
            """生成响应流"""
            try:
                async for event in build_agent_generator(agent, request_data, context):
                    # 转换为统一的SSE格式
                    event_data = {
                        "event": event.get("event_type", "message"),
                        "data": {
                            "content": event.get("data", ""),
                            "metadata": event.get("metadata", {}),
                            "timestamp": event.get("timestamp", "")
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"评估助手响应生成失败: {e}")
                error_event = {
                    "event_type": "error",
                    "data": f"评估助手响应生成失败: {str(e)}",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"评估助手聊天接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation/info")
async def get_evaluation_info():
    """
    获取评估助手信息
    
    Returns:
        Dict: 评估助手信息
    """
    try:
        agent = get_evaluation_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取评估助手信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluation/score")
async def calculate_score(request: Dict[str, Any]):
    """
    计算评估分数接口
    
    Args:
        request: 包含评分数据的请求
        
    Returns:
        Dict: 评分结果
    """
    try:
        agent = get_evaluation_agent()
        
        # 从请求中提取评分
        scores = request.get("scores", {})
        
        # 计算综合评分
        overall_score = agent.calculate_overall_score(scores)
        score_level = agent.get_score_level(overall_score)
        
        return {
            "success": True,
            "scores": scores,
            "overall_score": overall_score,
            "score_level": score_level,
            "level_description": agent.scoring_criteria[score_level]["description"]
        }
    except Exception as e:
        logger.error(f"计算评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 网络搜索Agent端点 ====================

@router.post("/websearch/chat")
async def websearch_chat(request: ChatRequest):
    """
    网络搜索助手聊天接口
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        agent = get_websearch_agent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "query": resolved["resolved_input"],
            "instruction": resolved["resolved_input"],
            "count": getattr(request, 'count', 5),
            "rag_trace": resolved["reference_trace"]
        }
        _ingest_rag_trace(agent, request_data)
        
        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "history": getattr(request, 'history', []),
            "project_id": request.project_id
        }
        _ingest_rag_trace(agent, request_data)

        async def generate_response():
            """
            将 Agent 事件转换为前端 extendedApi.streamWebSearchChat 期望的 SSE 格式：
            {
              "event_type": "message" | "llm_chunk" | "system" | ...,
              "data": "<字符串内容或对象>",
              "timestamp": "..."
            }
            """
            async for event in build_agent_generator(agent, request_data, context):
                # 兼容 emit_juben_event / 其他Agent事件结构
                event_type = event.get("event_type") or event.get("type") or "message"
                payload = {
                    "event_type": event_type,
                    "data": event.get("data", event.get("content", "")),
                    "timestamp": event.get("timestamp", "")
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )

    except Exception as e:
        logger.error(f"网络搜索助手聊天接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/websearch/info")
async def get_websearch_info():
    """
    获取网络搜索助手信息
    
    Returns:
        Dict: 网络搜索助手信息
    """
    try:
        agent = get_websearch_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取网络搜索助手信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 知识库查询Agent端点 ====================

@router.post("/knowledge/chat")
async def knowledge_chat(request: ChatRequest):
    """
    知识库查询助手聊天接口
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        agent = get_knowledge_agent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "query": resolved["resolved_input"],
            "instruction": resolved["resolved_input"],
            "collection": getattr(request, 'collection', 'script_segments'),
            "top_k": getattr(request, 'top_k', 5),
            "rag_trace": resolved["reference_trace"]
        }
        _ingest_rag_trace(agent, request_data)
        
        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id,
            "history": getattr(request, 'history', []),
            "project_id": request.project_id
        }
        _ingest_rag_trace(agent, request_data)

        async def generate_response():
            async for event in build_agent_generator(agent, request_data, context):
                # 转换为统一的SSE格式
                event_data = {
                    "event": event.get("event_type", "message"),
                    "data": {
                        "content": event.get("data", ""),
                        "metadata": event.get("metadata", {}),
                        "timestamp": event.get("timestamp", "")
                    }
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )

    except Exception as e:
        logger.error(f"知识库查询助手聊天接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/info")
async def get_knowledge_info():
    """
    获取知识库查询助手信息
    
    Returns:
        Dict: 知识库查询助手信息
    """
    try:
        agent = get_knowledge_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取知识库查询助手信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/collections")
async def get_knowledge_collections():
    """
    获取可用的知识库集合
    
    Returns:
        Dict: 知识库集合列表
    """
    try:
        agent = get_knowledge_agent()
        collections = agent.get_available_collections()
        return {
            "success": True,
            "collections": collections
        }
    except Exception as e:
        logger.error(f"获取知识库集合失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file-reference/chat")
async def file_reference_chat(request: ChatRequest):
    """
    文件引用解析聊天接口
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        logger.info(f"收到文件引用解析请求: {request.input}")
        agent = get_file_reference_agent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "rag_trace": resolved["reference_trace"]
        }
        
        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{hash(request.input)}",
            "project_id": request.project_id
        }
        _ingest_rag_trace(agent, request_data)
        
        # 返回流式响应
        return StreamingResponse(
            generate_file_reference_stream_response(request_data, context),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"文件引用解析接口处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-reference/info")
async def get_file_reference_info():
    """
    获取文件引用智能体信息
    
    Returns:
        Dict: 智能体信息
    """
    try:
        agent = get_file_reference_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取文件引用智能体信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story-analysis/analyze")
async def story_analysis(request: StoryAnalysisRequest):
    """
    故事五元素分析接口
    
    Args:
        request: 故事分析请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        logger.info(f"收到故事五元素分析请求: {request.input[:100]}...")
        resolved_input = request.input
        reference_trace = []
        try:
            from utils.reference_resolver import get_juben_reference_resolver
            resolver = get_juben_reference_resolver()
            resolved_input = await resolver.resolve_references(
                text=request.input,
                user_id=request.user_id or "unknown",
                session_id=request.session_id or f"session_{hash(request.input)}",
                query=request.input,
                project_id=request.project_id
            )
            reference_trace = resolver.get_reference_trace()
        except Exception as e:
            logger.warning(f"⚠️ 故事分析引用解析失败: {e}")
        
        # 构建请求数据
        request_data = {
            "input": resolved_input,
            "file": request.file,
            "chunk_size": request.chunk_size,
            "length_size": request.length_size,
            "rag_trace": reference_trace
        }
        
        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{hash(request.input)}",
            "project_id": request.project_id
        }
        
        # 返回流式响应
        return StreamingResponse(
            generate_story_analysis_stream_response(request_data, context),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"故事五元素分析接口处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story-analysis/info")
async def get_story_analysis_info():
    """
    获取故事五元素分析Agent信息
    
    Returns:
        Dict: Agent信息
    """
    try:
        agent = get_story_five_elements_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取故事五元素分析Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/series-analysis/analyze")
async def series_analysis(request: ChatRequest):
    """
    已播剧集分析接口
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        logger.info(f"收到已播剧集分析请求: {request.input[:100]}...")
        agent = get_series_analysis_agent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "rag_trace": resolved["reference_trace"]
        }
        
        # 构建上下文
        context = {
            "user_id": request.user_id,
            "session_id": request.session_id or f"session_{hash(request.input)}",
            "project_id": request.project_id
        }
        _ingest_rag_trace(agent, request_data)
        
        # 返回流式响应
        return StreamingResponse(
            generate_series_analysis_stream_response(request_data, context),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"已播剧集分析接口处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series-analysis/info")
async def get_series_analysis_info():
    """
    获取已播剧集分析Agent信息
    
    Returns:
        Dict: Agent信息
    """
    try:
        agent = get_series_analysis_agent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取已播剧集分析Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 大情节点与详细情节点工作流API ====================

# 全局工作流编排器实例
_workflow_orchestrator = None

def get_workflow_orchestrator():
    """获取工作流编排器实例"""
    global _workflow_orchestrator
    if _workflow_orchestrator is None:
        _workflow_orchestrator = PlotPointsWorkflowOrchestrator()
    return _workflow_orchestrator


@router.post("/plot-points-workflow/execute")
async def execute_plot_points_workflow(request: ChatRequest):
    """
    执行大情节点与详细情节点生成工作流
    
    Args:
        request: 工作流请求数据
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        orchestrator = get_workflow_orchestrator()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "chunk_size": request.chunk_size if hasattr(request, 'chunk_size') else 10000,
            "length_size": request.length_size if hasattr(request, 'length_size') else 50000,
            "format": request.format if hasattr(request, 'format') else "markdown",
            "rag_trace": resolved["reference_trace"]
        }
        _ingest_rag_trace(orchestrator, request_data)
        
        # 构建上下文
        context = {
            "user_id": request.user_id if hasattr(request, 'user_id') else "anonymous",
            "session_id": request.session_id if hasattr(request, 'session_id') else "default",
            "project_id": request.project_id
        }
        
        async def generate_response():
            """生成流式响应"""
            try:
                async for event in orchestrator.execute_workflow(request_data, context):
                    # 转换为统一的SSE格式
                    event_data = {
                        "event": event.get("event_type", "message"),
                        "data": {
                            "content": event.get("data", ""),
                            "metadata": event.get("metadata", {}),
                            "timestamp": event.get("timestamp", "")
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_event = {
                    "type": "workflow_error",
                    "message": f"工作流执行失败: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"执行大情节点工作流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plot-points-workflow/info")
async def get_plot_points_workflow_info():
    """
    获取大情节点工作流信息
    
    Returns:
        Dict: 工作流信息
    """
    try:
        orchestrator = get_workflow_orchestrator()
        info = orchestrator.get_workflow_info()
        return {
            "success": True,
            "workflow_info": info
        }
    except Exception as e:
        logger.error(f"获取大情节点工作流信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/story-summary/chat")
async def story_summary_chat(request: ChatRequest):
    """
    故事大纲生成聊天接口
    
    Args:
        request: 聊天请求数据
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        agent = StorySummaryGeneratorAgent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "rag_trace": resolved["reference_trace"]
        }
        
        # 构建上下文
        context = {
            "user_id": request.user_id if hasattr(request, 'user_id') else "anonymous",
            "session_id": request.session_id if hasattr(request, 'session_id') else "default",
            "project_id": request.project_id
        }
        _ingest_rag_trace(agent, request_data)
        
        async def generate_response():
            """生成流式响应"""
            try:
                async for event in build_agent_generator(agent, request_data, context):
                    # 转换为统一的SSE格式
                    event_data = {
                        "event": event.get("event_type", "message"),
                        "data": {
                            "content": event.get("data", ""),
                            "metadata": event.get("metadata", {}),
                            "timestamp": event.get("timestamp", "")
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_event = {
                    "type": "error",
                    "message": f"故事大纲生成失败: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"故事大纲生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story-summary/info")
async def get_story_summary_info():
    """
    获取故事大纲Agent信息
    
    Returns:
        Dict: Agent信息
    """
    try:
        agent = StorySummaryGeneratorAgent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取故事大纲Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/major-plot-points/chat")
async def major_plot_points_chat(request: ChatRequest):
    """
    大情节点分析聊天接口
    
    Args:
        request: 聊天请求数据
        
    Returns:
        StreamingResponse: 流式响应
    """
    try:
        agent = MajorPlotPointsAgent()
        resolved = await _resolve_input_with_references(request)
        
        # 构建请求数据
        request_data = {
            "input": resolved["resolved_input"],
            "rag_trace": resolved["reference_trace"]
        }
        
        # 构建上下文
        context = {
            "user_id": request.user_id if hasattr(request, 'user_id') else "anonymous",
            "session_id": request.session_id if hasattr(request, 'session_id') else "default",
            "project_id": request.project_id
        }
        _ingest_rag_trace(agent, request_data)
        
        async def generate_response():
            """生成流式响应"""
            try:
                async for event in build_agent_generator(agent, request_data, context):
                    # 转换为统一的SSE格式
                    event_data = {
                        "event": event.get("event_type", "message"),
                        "data": {
                            "content": event.get("data", ""),
                            "metadata": event.get("metadata", {}),
                            "timestamp": event.get("timestamp", "")
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_event = {
                    "type": "error",
                    "message": f"大情节点分析失败: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"大情节点分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/major-plot-points/info")
async def get_major_plot_points_info():
    """
    获取大情节点Agent信息
    
    Returns:
        Dict: Agent信息
    """
    try:
        agent = MajorPlotPointsAgent()
        info = agent.get_agent_info()
        return {
            "success": True,
            "agent_info": info
        }
    except Exception as e:
        logger.error(f"获取大情节点Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 人物关系分析 ====================
_character_relationship_analyzer_agent = None

def get_character_relationship_analyzer_agent():
    """获取人物关系分析Agent实例"""
    global _character_relationship_analyzer_agent
    if _character_relationship_analyzer_agent is None:
        from agents.character_relationship_analyzer_agent import CharacterRelationshipAnalyzerAgent
        _character_relationship_analyzer_agent = CharacterRelationshipAnalyzerAgent()
    return _character_relationship_analyzer_agent


@router.post("/character/relationship")
async def character_relationship_analyze(request: ChatRequest):
    """
    人物关系分析接口

    Args:
        request: 包含input文本的请求

    Returns:
        StreamingResponse: 流式响应
    """
    try:
        agent = get_character_relationship_analyzer_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            """事件生成器"""
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id or f"sess_{id(request)}",
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"人物关系分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/character/relationship/info")
async def get_character_relationship_analyzer_info():
    """获取人物关系分析Agent信息"""
    try:
        agent = get_character_relationship_analyzer_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取人物关系分析Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 情节点分析 ====================
_plot_points_analyzer_agent = None

def get_plot_points_analyzer_agent():
    """获取情节点分析Agent实例"""
    global _plot_points_analyzer_agent
    if _plot_points_analyzer_agent is None:
        from agents.plot_points_analyzer_agent import PlotPointsAnalyzerAgent
        _plot_points_analyzer_agent = PlotPointsAnalyzerAgent()
    return _plot_points_analyzer_agent


@router.post("/plot-points/analyze")
async def plot_points_analyze(request: ChatRequest):
    """情节点分析接口"""
    try:
        agent = get_plot_points_analyzer_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id or f"sess_{id(request)}",
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"情节点分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plot-points/analyze/info")
async def get_plot_points_analyzer_info():
    """获取情节点分析Agent信息"""
    try:
        agent = get_plot_points_analyzer_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取情节点分析Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文本处理工具 ====================
_text_splitter_agent = None
_text_truncator_agent = None


def get_text_splitter_agent():
    """获取文本分割Agent实例"""
    global _text_splitter_agent
    if _text_splitter_agent is None:
        from agents.text_splitter_agent import TextSplitterAgent
        _text_splitter_agent = TextSplitterAgent()
    return _text_splitter_agent


def get_text_truncator_agent():
    """获取文本截断Agent实例"""
    global _text_truncator_agent
    if _text_truncator_agent is None:
        from agents.text_truncator_agent import TextTruncatorAgent
        _text_truncator_agent = TextTruncatorAgent()
    return _text_truncator_agent


@router.post("/text/split")
async def text_split(request: Dict[str, Any]):
    """文本分割接口"""
    try:
        agent = get_text_splitter_agent()

        async def event_generator():
            context = {
                "user_id": request.get("user_id", "unknown"),
                "session_id": request.get("session_id", "unknown")
            }
            async for event in build_agent_generator(agent, request, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"文本分割失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text/truncate")
async def text_truncate(request: Dict[str, Any]):
    """文本截断接口"""
    try:
        agent = get_text_truncator_agent()

        async def event_generator():
            context = {
                "user_id": request.get("user_id", "unknown"),
                "session_id": request.get("session_id", "unknown")
            }
            async for event in build_agent_generator(agent, request, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"文本截断失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 剧本深度分析 ====================
_drama_analysis_agent = None


def get_drama_analysis_agent():
    """获取剧本深度分析Agent实例"""
    global _drama_analysis_agent
    if _drama_analysis_agent is None:
        from agents.drama_analysis_agent import DramaAnalysisAgent
        _drama_analysis_agent = DramaAnalysisAgent()
    return _drama_analysis_agent


@router.post("/drama/analysis")
async def drama_analysis(request: ChatRequest):
    """剧本深度分析接口"""
    try:
        agent = get_drama_analysis_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id or f"sess_{id(request)}",
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"剧本深度分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drama/analysis/info")
async def get_drama_analysis_info():
    """获取剧本深度分析Agent信息"""
    try:
        agent = get_drama_analysis_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取剧本深度分析Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 结果集成器 ====================
_result_integrator_agent = None


def get_result_integrator_agent():
    """获取结果集成器Agent实例"""
    global _result_integrator_agent
    if _result_integrator_agent is None:
        from agents.result_integrator_agent import ResultIntegratorAgent
        _result_integrator_agent = ResultIntegratorAgent()
    return _result_integrator_agent


@router.post("/result/integrate")
async def result_integrate(request: Dict[str, Any]):
    """结果集成接口"""
    try:
        agent = get_result_integrator_agent()

        async def event_generator():
            context = {
                "user_id": request.get("user_id", "unknown"),
                "session_id": request.get("session_id", "unknown")
            }
            async for event in build_agent_generator(agent, request, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"结果集成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/integrate/info")
async def get_result_integrator_info():
    """获取结果集成器Agent信息"""
    try:
        agent = get_result_integrator_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取结果集成器Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 人物小传生成 ====================
_character_profile_generator_agent = None


def get_character_profile_generator_agent():
    """获取人物小传生成Agent实例"""
    global _character_profile_generator_agent
    if _character_profile_generator_agent is None:
        _character_profile_generator_agent = CharacterProfileGeneratorAgent()
    return _character_profile_generator_agent


@router.post("/character/profile")
async def character_profile_generate(request: ChatRequest):
    """
    人物小传生成接口

    为故事中的主要人物生成详细的人物小传
    """
    try:
        agent = get_character_profile_generator_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"人物小传生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/character/profile/info")
async def get_character_profile_generator_info():
    """获取人物小传生成Agent信息"""
    try:
        agent = get_character_profile_generator_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取人物小传生成Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 剧本评估专家 ====================
_script_evaluation_agent = None


def get_script_evaluation_agent():
    """获取剧本评估专家Agent实例"""
    global _script_evaluation_agent
    if _script_evaluation_agent is None:
        _script_evaluation_agent = ScriptEvaluationAgent()
    return _script_evaluation_agent


@router.post("/script/evaluation")
async def script_evaluation(request: ChatRequest):
    """
    剧本评估专家接口

    深度剧本分析评估，提供专业的质量诊断和优化方案
    """
    try:
        agent = get_script_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"剧本评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/script/evaluation/info")
async def get_script_evaluation_info():
    """获取剧本评估专家Agent信息"""
    try:
        agent = get_script_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取剧本评估专家Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== IP价值评估 ====================
_ip_evaluation_agent = None


def get_ip_evaluation_agent():
    """获取IP价值评估Agent实例"""
    global _ip_evaluation_agent
    if _ip_evaluation_agent is None:
        _ip_evaluation_agent = IPEvaluationAgent()
    return _ip_evaluation_agent


@router.post("/ip/evaluation")
async def ip_evaluation(request: ChatRequest):
    """
    IP价值评估接口

    评估IP的商业价值和开发潜力
    """
    try:
        agent = get_ip_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"IP价值评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ip/evaluation/info")
async def get_ip_evaluation_info():
    """获取IP价值评估Agent信息"""
    try:
        agent = get_ip_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取IP价值评估Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 故事类型分析 ====================
_story_type_analyzer_agent = None


def get_story_type_analyzer_agent():
    """获取故事类型分析Agent实例"""
    global _story_type_analyzer_agent
    if _story_type_analyzer_agent is None:
        _story_type_analyzer_agent = StoryTypeAnalyzerAgent()
    return _story_type_analyzer_agent


@router.post("/story-type/analyze")
async def story_type_analyze(request: ChatRequest):
    """
    故事类型分析接口

    识别和分析故事类型，提供类型化创作建议
    """
    try:
        agent = get_story_type_analyzer_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"故事类型分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story-type/analyze/info")
async def get_story_type_analyzer_info():
    """获取故事类型分析Agent信息"""
    try:
        agent = get_story_type_analyzer_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取故事类型分析Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 故事大纲生成 ====================
# 注意：前端配置的是 /juben/story/summary，需要添加这个路由
@router.post("/story/summary")
async def story_summary(request: ChatRequest):
    """
    故事大纲生成接口（兼容前端路径）
    """
    try:
        agent = StorySummaryGeneratorAgent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"故事大纲生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 详细情节点 ====================
_detailed_plot_points_agent = None


def get_detailed_plot_points_agent():
    """获取详细情节点Agent实例"""
    global _detailed_plot_points_agent
    if _detailed_plot_points_agent is None:
        _detailed_plot_points_agent = DetailedPlotPointsAgent()
    return _detailed_plot_points_agent


@router.post("/plot-points/detailed")
async def detailed_plot_points(request: ChatRequest):
    """
    详细情节点接口

    展开详细的情节点内容，丰富故事细节
    """
    try:
        agent = get_detailed_plot_points_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"详细情节点生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plot-points/detailed/info")
async def get_detailed_plot_points_info():
    """获取详细情节点Agent信息"""
    try:
        agent = get_detailed_plot_points_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取详细情节点Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 思维导图 ====================
_mind_map_agent = None


def get_mind_map_agent():
    """获取思维导图Agent实例"""
    global _mind_map_agent
    if _mind_map_agent is None:
        _mind_map_agent = MindMapAgent()
    return _mind_map_agent


@router.post("/mind-map/generate")
async def mind_map_generate(request: ChatRequest):
    """
    思维导图生成接口

    生成故事结构可视化思维导图
    """
    try:
        agent = get_mind_map_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"思维导图生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mind-map/generate/info")
async def get_mind_map_info():
    """获取思维导图Agent信息"""
    try:
        agent = get_mind_map_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取思维导图Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 故事质量评估 ====================
_story_evaluation_agent = None


def get_story_evaluation_agent():
    """获取故事质量评估Agent实例"""
    global _story_evaluation_agent
    if _story_evaluation_agent is None:
        _story_evaluation_agent = StoryEvaluationAgent()
    return _story_evaluation_agent


@router.post("/story/evaluation")
async def story_evaluation(request: ChatRequest):
    """
    故事质量评估接口

    评估故事的整体质量和吸引力
    """
    try:
        agent = get_story_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"故事质量评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story/evaluation/info")
async def get_story_evaluation_info():
    """获取故事质量评估Agent信息"""
    try:
        agent = get_story_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取故事质量评估Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 大纲评估 ====================
_story_outline_evaluation_agent = None


def get_story_outline_evaluation_agent():
    """获取大纲评估Agent实例"""
    global _story_outline_evaluation_agent
    if _story_outline_evaluation_agent is None:
        _story_outline_evaluation_agent = StoryOutlineEvaluationAgent()
    return _story_outline_evaluation_agent


@router.post("/outline/evaluation")
async def story_outline_evaluation(request: ChatRequest):
    """
    大纲评估接口

    评估故事大纲的完整性和可行性
    """
    try:
        agent = get_story_outline_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"大纲评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outline/evaluation/info")
async def get_story_outline_evaluation_info():
    """获取大纲评估Agent信息"""
    try:
        agent = get_story_outline_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取大纲评估Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 小说筛选评估 ====================
_novel_screening_evaluation_agent = None


def get_novel_screening_evaluation_agent():
    """获取小说筛选评估Agent实例"""
    global _novel_screening_evaluation_agent
    if _novel_screening_evaluation_agent is None:
        _novel_screening_evaluation_agent = NovelScreeningEvaluationAgent()
    return _novel_screening_evaluation_agent


@router.post("/novel/screening")
async def novel_screening_evaluation(request: ChatRequest):
    """
    小说筛选评估接口

    评估小说是否适合改编为短剧
    """
    try:
        agent = get_novel_screening_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"小说筛选评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/novel/screening/info")
async def get_novel_screening_evaluation_info():
    """获取小说筛选评估Agent信息"""
    try:
        agent = get_novel_screening_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取小说筛选评估Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文档生成器 ====================
_document_generator_agent = None


def get_document_generator_agent():
    """获取文档生成器Agent实例"""
    global _document_generator_agent
    if _document_generator_agent is None:
        _document_generator_agent = DocumentGeneratorAgent()
    return _document_generator_agent


@router.post("/document/generate")
async def document_generate(request: ChatRequest):
    """
    文档生成器接口

    生成标准化的剧本文档
    """
    try:
        agent = get_document_generator_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"文档生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/generate/info")
async def get_document_generator_info():
    """获取文档生成器Agent信息"""
    try:
        agent = get_document_generator_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取文档生成器Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 输出格式化 ====================
_output_formatter_agent = None


def get_output_formatter_agent():
    """获取输出格式化Agent实例"""
    global _output_formatter_agent
    if _output_formatter_agent is None:
        _output_formatter_agent = OutputFormatterAgent()
    return _output_formatter_agent


@router.post("/output/format")
async def output_format(request: ChatRequest):
    """
    输出格式化接口

    格式化AI输出，确保符合规范
    """
    try:
        agent = get_output_formatter_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"输出格式化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/output/format/info")
async def get_output_formatter_info():
    """获取输出格式化Agent信息"""
    try:
        agent = get_output_formatter_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取输出格式化Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 评分分析器 ====================
_score_analyzer_agent = None


def get_score_analyzer_agent():
    """获取评分分析器Agent实例"""
    global _score_analyzer_agent
    if _score_analyzer_agent is None:
        _score_analyzer_agent = ScoreAnalyzerAgent()
    return _score_analyzer_agent


@router.post("/score/analyze")
async def score_analyze(request: ChatRequest):
    """
    评分分析器接口

    分析评分数据，提供解读
    """
    try:
        agent = get_score_analyzer_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"评分分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/score/analyze/info")
async def get_score_analyzer_info():
    """获取评分分析器Agent信息"""
    try:
        agent = get_score_analyzer_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取评分分析器Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文本处理评估 ====================
_text_processor_evaluation_agent = None


def get_text_processor_evaluation_agent():
    """获取文本处理评估Agent实例"""
    global _text_processor_evaluation_agent
    if _text_processor_evaluation_agent is None:
        _text_processor_evaluation_agent = TextProcessorEvaluationAgent()
    return _text_processor_evaluation_agent


@router.post("/text/evaluate")
async def text_evaluate(request: ChatRequest):
    """
    文本处理评估接口

    评估文本处理的质量和效果
    """
    try:
        agent = get_text_processor_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"文本处理评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/text/evaluate/info")
async def get_text_processor_evaluation_info():
    """获取文本处理评估Agent信息"""
    try:
        agent = get_text_processor_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取文本处理评估Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 结果分析评估 ====================
_result_analyzer_evaluation_agent = None


def get_result_analyzer_evaluation_agent():
    """获取结果分析评估Agent实例"""
    global _result_analyzer_evaluation_agent
    if _result_analyzer_evaluation_agent is None:
        _result_analyzer_evaluation_agent = ResultAnalyzerEvaluationAgent()
    return _result_analyzer_evaluation_agent


@router.post("/result/analyze")
async def result_analyze(request: ChatRequest):
    """
    结果分析评估接口

    分析评估结果，提供洞察
    """
    try:
        agent = get_result_analyzer_evaluation_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"结果分析评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/analyze/info")
async def get_result_analyzer_evaluation_info():
    """获取结果分析评估Agent信息"""
    try:
        agent = get_result_analyzer_evaluation_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取结果分析评估Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 剧集信息提取 ====================
_series_info_agent = None


def get_series_info_agent():
    """获取剧集信息提取Agent实例"""
    global _series_info_agent
    if _series_info_agent is None:
        _series_info_agent = SeriesInfoAgent()
    return _series_info_agent


@router.post("/series/info")
async def series_info(request: ChatRequest):
    """
    剧集信息提取接口

    从文本中提取剧集相关信息
    """
    try:
        agent = get_series_info_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"剧集信息提取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/info/info")
async def get_series_info_info():
    """获取剧集信息提取Agent信息"""
    try:
        agent = get_series_info_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取剧集信息提取Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 剧名提取 ====================
_series_name_extractor_agent = None


def get_series_name_extractor_agent():
    """获取剧名提取Agent实例"""
    global _series_name_extractor_agent
    if _series_name_extractor_agent is None:
        _series_name_extractor_agent = SeriesNameExtractorAgent()
    return _series_name_extractor_agent


@router.post("/series/name")
async def series_name(request: ChatRequest):
    """
    剧名提取接口

    智能识别和提取短剧名称
    """
    try:
        agent = get_series_name_extractor_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"剧名提取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/name/info")
async def get_series_name_extractor_info():
    """获取剧名提取Agent信息"""
    try:
        agent = get_series_name_extractor_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取剧名提取Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 剧本创作工作流 ====================
_drama_workflow_agent = None


def get_drama_workflow_agent():
    """获取剧本创作工作流Agent实例"""
    global _drama_workflow_agent
    if _drama_workflow_agent is None:
        _drama_workflow_agent = DramaWorkflowAgent()
    return _drama_workflow_agent


@router.post("/drama-workflow/execute")
async def drama_workflow_execute(request: ChatRequest):
    """
    剧本创作工作流接口

    端到端的剧本创作工作流，从创意到成品
    """
    try:
        agent = get_drama_workflow_agent()
        resolved = await _resolve_input_with_references(request)

        async def event_generator():
            context = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "project_id": request.project_id
            }
            request_data = {
                "input": resolved["resolved_input"],
                "rag_trace": resolved["reference_trace"]
            }
            _ingest_rag_trace(agent, request_data)

            async for event in build_agent_generator(agent, request_data, context):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        logger.error(f"剧本创作工作流执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drama-workflow/execute/info")
async def get_drama_workflow_info():
    """获取剧本创作工作流Agent信息"""
    try:
        agent = get_drama_workflow_agent()
        info = agent.get_agent_info()
        return {"success": True, "agent_info": info}
    except Exception as e:
        logger.error(f"获取剧本创作工作流Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Notes系统API（）====================

@router.post("/notes/create", response_model=BaseResponse)
async def create_note(request: NoteCreateRequest):
    """
    创建Agent输出Note

    Agent生成内容后自动调用此接口保存到Notes系统，
    供用户选择并在后续对话中引用
    """
    try:
        storage = await get_storage()
        note_id = await storage.save_agent_output_note(
            user_id=request.user_id,
            session_id=request.session_id,
            action=request.action,
            name=request.name,
            context=request.context,
            title=request.title,
            cover_title=request.cover_title,
            select_status=0,
            metadata=request.metadata or {}
        )

        if note_id:
            return BaseResponse(
                success=True,
                message="Note创建成功",
                data={"note_id": note_id, "action": request.action, "name": request.name}
            )
        else:
            raise HTTPException(status_code=500, detail="Note创建失败")
    except Exception as e:
        logger.error(f"创建Note失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/list", response_model=NoteListResponse)
async def get_notes_list(
    user_id: str,
    session_id: str,
    action: Optional[str] = None
):
    """
    获取Notes列表

    返回指定会话的所有Notes，可按action类型过滤
    """
    try:
        storage = await get_storage()
        notes = await storage.get_notes(user_id, session_id, action)

        # 按action分组
        grouped_by_action = {}
        for note in notes:
            note_action = note.get('action', 'unknown')
            if note_action not in grouped_by_action:
                grouped_by_action[note_action] = []
            grouped_by_action[note_action].append(note)

        return NoteListResponse(
            success=True,
            message="获取Notes列表成功",
            notes=notes,
            total_count=len(notes),
            grouped_by_action=grouped_by_action
        )
    except Exception as e:
        logger.error(f"获取Notes列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/select", response_model=BaseResponse)
async def update_note_selection(request: NoteSelectRequest):
    """
    批量更新Note选择状态

    用户在前端选择Note后调用此接口更新选择状态
    """
    try:
        storage = await get_storage()
        success = await storage.batch_update_note_selection(
            user_id=request.user_id,
            session_id=request.session_id,
            selections=request.selections
        )

        if success:
            return BaseResponse(
                success=True,
                message="Note选择状态更新成功",
                data={"updated_count": len(request.selections)}
            )
        else:
            raise HTTPException(status_code=500, detail="Note选择状态更新失败")
    except Exception as e:
        logger.error(f"更新Note选择状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/selected", response_model=NoteListResponse)
async def get_selected_notes(user_id: str, session_id: str):
    """
    获取已选择的Notes

    返回用户选择的所有Notes，用于后续对话引用
    """
    try:
        storage = await get_storage()
        notes = await storage.get_selected_notes(user_id, session_id)

        # 按action分组
        grouped_by_action = {}
        for note in notes:
            note_action = note.get('action', 'unknown')
            if note_action not in grouped_by_action:
                grouped_by_action[note_action] = []
            grouped_by_action[note_action].append(note)

        return NoteListResponse(
            success=True,
            message="获取已选择Notes成功",
            notes=notes,
            total_count=len(notes),
            grouped_by_action=grouped_by_action
        )
    except Exception as e:
        logger.error(f"获取已选择Notes失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/export", response_model=NoteExportResponse)
async def export_notes(request: NoteExportRequest):
    """
    导出Notes

    将Notes导出为指定格式（txt, json, md）
    """
    try:
        storage = await get_storage()
        result = await storage.export_notes(
            user_id=request.user_id,
            session_id=request.session_id,
            export_format=request.export_format.value,
            content_types=[ct.value for ct in request.content_types] if request.content_types else None,
            include_user_comments=request.include_user_comments
        )

        filename = f"juben_notes_{request.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{request.export_format.value}"

        return NoteExportResponse(
            success=True,
            message="Notes导出成功",
            export_format=request.export_format,
            total_items=result['total_items'],
            content_summary=result['content_summary'],
            exported_data=result['exported_data'],
            filename=filename
        )
    except Exception as e:
        logger.error(f"导出Notes失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 启动事件
@router.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("竖屏短剧策划助手API启动")

    # 初始化Agent
    try:
        planner = get_planner_agent()
        logger.info("策划Agent初始化成功")

        creator = get_creator_agent()
        logger.info("创作Agent初始化成功")

        evaluation = get_evaluation_agent()
        logger.info("评估Agent初始化成功")

        websearch = get_websearch_agent()
        logger.info("网络搜索Agent初始化成功")

        knowledge = get_knowledge_agent()
        logger.info("知识库查询Agent初始化成功")

        file_reference = get_file_reference_agent()
        logger.info("文件引用Agent初始化成功")

        story_five_elements = get_story_five_elements_agent()
        logger.info("故事五元素分析Agent初始化成功")

        series_analysis = get_series_analysis_agent()
        logger.info("已播剧集分析Agent初始化成功")
    except Exception as e:
        logger.error(f"Agent初始化失败: {e}")


# ==================== 🆕 限流管理API ====================

@router.get("/rate-limit/info")
async def get_rate_limit_info(
    user_id: str,
    session_id: Optional[str] = None
):
    """
    获取用户限流信息

    Args:
        user_id: 用户ID
        session_id: 会话ID（可选）

    Returns:
        Dict: 限流信息
    """
    try:
        from utils.rate_limiter import get_user_rate_limit_info

        identifier = f"{user_id}:{session_id or 'default'}"
        info = await get_user_rate_limit_info(identifier)

        return {
            "success": True,
            "user_id": user_id,
            "session_id": session_id,
            "rate_limit_info": info
        }
    except Exception as e:
        logger.error(f"获取限流信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-limit/config")
async def set_rate_limit_config(request: Dict[str, Any]):
    """
    设置限流配置

    Args:
        request: 配置请求
            - limit: 限制次数
            - window_seconds: 时间窗口（秒）
            - enabled: 是否启用

    Returns:
        Dict: 设置结果
    """
    try:
        from utils.rate_limiter import get_rate_limiter

        limit = request.get("limit", 60)
        window_seconds = request.get("window_seconds", 60)
        enabled = request.get("enabled", True)

        limiter = get_rate_limiter()
        success = await limiter.set_rate_limit_config(
            limit=limit,
            window_seconds=window_seconds,
            enabled=enabled
        )

        return {
            "success": success,
            "message": "限流配置已更新" if success else "限流配置更新失败"
        }
    except Exception as e:
        logger.error(f"设置限流配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-limit/reset")
async def reset_user_rate_limit(request: Dict[str, Any]):
    """
    重置用户限流记录

    Args:
        request: 请求
            - user_id: 用户ID
            - session_id: 会话ID（可选）

    Returns:
        Dict: 重置结果
    """
    try:
        from utils.rate_limiter import get_rate_limiter

        user_id = request.get("user_id")
        session_id = request.get("session_id", "default")

        if not user_id:
            raise HTTPException(status_code=400, detail="缺少user_id字段")

        identifier = f"{user_id}:{session_id}"
        limiter = get_rate_limiter()
        success = await limiter.reset_user_limit(identifier)

        return {
            "success": success,
            "message": "限流记录已重置" if success else "限流记录重置失败"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置限流记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 连接池管理API ====================

@router.get("/system/connection-pool/health")
async def get_connection_pool_health():
    """
    获取连接池健康状态

    Returns:
        Dict: 连接池健康信息
    """
    try:
        from utils.connection_pool_manager import get_connection_pool_manager

        pool_manager = await get_connection_pool_manager()
        health_status = await pool_manager.health_check()
        stats = pool_manager.get_stats()

        return {
            "success": True,
            "health_status": health_status,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取连接池健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/connection-pool/warmup")
async def warmup_connection_pools(request: Dict[str, Any] = None):
    """
    预热连接池

    Args:
        request: 请求（可选）
            - pool_types: 要预热的连接池类型列表

    Returns:
        Dict: 预热结果
    """
    try:
        from utils.connection_pool_manager import get_connection_pool_manager

        pool_types = request.get("pool_types") if request else None

        pool_manager = await get_connection_pool_manager()
        await pool_manager.warmup_pools(pool_types)

        return {
            "success": True,
            "message": "连接池预热完成"
        }
    except Exception as e:
        logger.error(f"预热连接池失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 访问统计API ====================

@router.get("/system/access-stats")
async def get_access_statistics():
    """
    获取访问统计信息

    Returns:
        Dict: 访问统计信息
    """
    try:
        from utils.access_counter import get_access_counter

        counter = get_access_counter()
        stats = await counter.get_stats()

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取访问统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/access-stats/daily")
async def get_daily_access_stats(days: int = 7):
    """
    获取最近几天的访问统计

    Args:
        days: 获取最近多少天的数据（默认7天）

    Returns:
        Dict: 每日访问统计
    """
    try:
        from utils.access_counter import get_access_counter

        counter = get_access_counter()
        stats = await counter.get_recent_daily_stats(days)

        return {
            "success": True,
            "data": {
                "days": days,
                "daily_stats": stats
            }
        }
    except Exception as e:
        logger.error(f"获取每日访问统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/access-stats/user/{user_id}")
async def get_user_access_stats(user_id: str):
    """
    获取指定用户的访问统计

    Args:
        user_id: 用户ID

    Returns:
        Dict: 用户访问统计
    """
    try:
        from utils.access_counter import get_access_counter

        counter = get_access_counter()
        access_count = await counter.get_user_access(user_id)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "access_count": access_count
            }
        }
    except Exception as e:
        logger.error(f"获取用户访问统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 Token统计API ====================

@router.get("/system/token-dashboard")
async def get_token_dashboard():
    """
    获取Token统计仪表盘数据

    Returns:
        Dict: Token仪表盘数据
    """
    try:
        from utils.token_accumulator import get_token_dashboard

        dashboard = await get_token_dashboard()

        return {
            "success": True,
            "data": dashboard
        }
    except Exception as e:
        logger.error(f"获取Token仪表盘失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/token-ranking")
async def get_token_ranking(top_n: int = 10, date: str = None):
    """
    获取用户Token消耗排行榜

    Args:
        top_n: 返回前N名用户，默认10名
        date: 目标日期（YYYY-MM-DD），默认今天

    Returns:
        Dict: 用户Token排行榜
    """
    try:
        from utils.token_accumulator import get_daily_token_ranking

        ranking = await get_daily_token_ranking(top_n=top_n)

        return {
            "success": True,
            "data": {
                "date": date or "today",
                "top_n": top_n,
                "ranking": ranking
            }
        }
    except Exception as e:
        logger.error(f"获取Token排行榜失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/token-stats")
async def get_token_stats(days: int = 7):
    """
    获取Token统计数据

    Args:
        days: 获取最近多少天的数据，默认7天

    Returns:
        Dict: Token统计数据
    """
    try:
        from utils.token_accumulator import get_token_stats

        stats = await get_token_stats(days=days)

        return {
            "success": True,
            "data": {
                "days": days,
                "stats": stats
            }
        }
    except Exception as e:
        logger.error(f"获取Token统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 端口监控API ====================

@router.get("/system/port-monitor/status")
async def get_port_monitor_status():
    """
    获取端口监控状态

    Returns:
        Dict: 端口监控状态
    """
    try:
        from utils.port_monitor_service import get_port_monitor_status

        status = get_port_monitor_status()

        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取端口监控状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/port-monitor/health")
async def get_port_monitor_health():
    """
    获取端口健康状态摘要

    Returns:
        Dict: 端口健康状态
    """
    try:
        from utils.port_monitor_service import get_port_monitor_service

        service = get_port_monitor_service()
        health = await service.get_health_summary()

        return {
            "success": True,
            "data": health
        }
    except Exception as e:
        logger.error(f"获取端口健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/port-monitor/start")
async def start_port_monitoring(interval: int = 300):
    """
    启动端口监控

    Args:
        interval: 监控间隔（秒），默认300秒

    Returns:
        Dict: 启动结果
    """
    try:
        from utils.port_monitor_service import start_port_monitoring

        await start_port_monitoring(monitor_interval=interval)

        return {
            "success": True,
            "message": f"端口监控已启动，监控间隔: {interval}秒"
        }
    except Exception as e:
        logger.error(f"启动端口监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/port-monitor/stop")
async def stop_port_monitoring():
    """
    停止端口监控

    Returns:
        Dict: 停止结果
    """
    try:
        from utils.port_monitor_service import stop_port_monitoring

        await stop_port_monitoring()

        return {
            "success": True,
            "message": "端口监控已停止"
        }
    except Exception as e:
        logger.error(f"停止端口监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 告警系统API ====================

@router.get("/system/alert/status")
async def get_alert_status():
    """
    获取告警系统状态

    Returns:
        Dict: 告警系统状态
    """
    try:
        from utils.alert_manager import get_alert_manager

        manager = get_alert_manager()
        status = manager.get_status()

        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取告警系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/alert/test")
async def test_alert():
    """
    测试告警系统

    Returns:
        Dict: 测试结果
    """
    try:
        from utils.alert_manager import send_alert
        from utils.alert_manager import AlertType, AlertLevel

        success = await send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            title="告警系统测试",
            message="这是一条测试告警消息",
            level=AlertLevel.INFO,
            extra_data={"test": True, "timestamp": "now"}
        )

        return {
            "success": success,
            "message": "告警测试完成" if success else "告警测试失败"
        }
    except Exception as e:
        logger.error(f"测试告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 流式事件回放API ====================

@router.post("/stream/heartbeat")
async def stream_heartbeat(request: HeartbeatRequest):
    """
    流式事件心跳接口
    - 前端每5秒调用一次
    - 后端记录用户最后活跃时间
    - 用于判断用户何时断网
    """
    try:
        from utils.stream_replay_manager import get_stream_replay_manager

        replay_manager = get_stream_replay_manager()
        success = await replay_manager.update_user_heartbeat(
            user_id=request.user_id,
            session_id=request.session_id
        )

        return {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "message": "心跳更新成功" if success else "心跳更新失败"
        }
    except Exception as e:
        logger.error(f"心跳处理失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/stream/check-replay/{session_id}")
async def check_stream_replay(session_id: str, user_id: str):
    """
    检查是否需要回放流式事件

    Args:
        session_id: 会话ID
        user_id: 用户ID

    Returns:
        Dict: 回放信息
    """
    try:
        from utils.stream_replay_manager import get_stream_replay_manager

        replay_manager = get_stream_replay_manager()
        replay_info = await replay_manager.check_need_replay(session_id, user_id)

        return {
            "success": True,
            "data": replay_info
        }
    except Exception as e:
        logger.error(f"检查回放失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/task-status/{session_id}")
async def get_stream_task_status(session_id: str):
    """
    获取流式任务状态

    Args:
        session_id: 会话ID

    Returns:
        Dict: 任务状态
    """
    try:
        from utils.stream_replay_manager import get_stream_replay_manager

        replay_manager = get_stream_replay_manager()
        task_status = await replay_manager.check_task_status(session_id)

        return {
            "success": True,
            "data": task_status
        }
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 🆕 停止控制API ====================

class StopRequest(BaseModel):
    """停止请求"""
    user_id: str
    session_id: str
    reason: str = "user_request"  # user_request, error, timeout
    message: str = ""
    agent_name: Optional[str] = None


class HeartbeatRequest(BaseModel):
    """心跳请求"""
    user_id: str
    session_id: str


@router.post("/stop/request")
async def request_stop(request: StopRequest):
    """
    请求停止当前执行

    Args:
        request: 停止请求

    Returns:
        Dict: 停止结果
    """
    try:
        from utils.stop_manager import get_stop_manager, StopReason

        stop_manager = get_stop_manager()

        # 转换停止原因
        try:
            reason_enum = StopReason(request.reason)
        except ValueError:
            reason_enum = StopReason.USER_REQUEST

        success = await stop_manager.request_stop(
            user_id=request.user_id,
            session_id=request.session_id,
            reason=reason_enum,
            message=request.message,
            agent_name=request.agent_name
        )

        return {
            "success": success,
            "message": "停止请求已设置" if success else "停止请求设置失败"
        }
    except Exception as e:
        logger.error(f"请求停止失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stop/status/{user_id}/{session_id}")
async def get_stop_status(user_id: str, session_id: str):
    """
    获取停止状态

    Args:
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        Dict: 停止状态
    """
    try:
        from utils.stop_manager import get_stop_manager

        stop_manager = get_stop_manager()
        is_stopped = await stop_manager.is_stopped(user_id, session_id)

        return {
            "success": True,
            "data": {
                "is_stopped": is_stopped,
                "user_id": user_id,
                "session_id": session_id
            }
        }
    except Exception as e:
        logger.error(f"获取停止状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/clear/{user_id}/{session_id}")
async def clear_stop_status(user_id: str, session_id: str):
    """
    清除停止状态

    Args:
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        Dict: 清除结果
    """
    try:
        from utils.stop_manager import get_stop_manager

        stop_manager = get_stop_manager()
        success = await stop_manager.clear_stop_status(user_id, session_id)

        return {
            "success": success,
            "message": "停止状态已清除" if success else "清除失败"
        }
    except Exception as e:
        logger.error(f"清除停止状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stop/history/{user_id}")
async def get_stop_history(user_id: str, limit: int = 10):
    """
    获取用户的停止历史

    Args:
        user_id: 用户ID
        limit: 返回历史记录数量

    Returns:
        Dict: 停止历史
    """
    try:
        from utils.stop_manager import get_stop_manager

        stop_manager = get_stop_manager()
        history = await stop_manager.get_stop_history(user_id, limit)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "history": history
            }
        }
    except Exception as e:
        logger.error(f"获取停止历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 关闭事件
@router.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("竖屏短剧策划助手API关闭")

# ==================== 项目管理端点 ====================
_project_manager: Optional[ProjectManager] = None

def get_project_manager() -> ProjectManager:
    """获取项目管理器实例"""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager

@router.get("/projects/list")
async def get_projects_list(request: Request):
    """获取项目列表"""
    try:
        pm = get_project_manager()
        
        form = await request.form()
        user_id = form.get("user_id", "default_user")
        status = form.get("status")  # active, archived, deleted, completed
        tags = form.get("tags", "").split(",") if form.get("tags") else []
        page = int(form.get("page", 1))
        page_size = int(form.get("page_size", 20))
        
        projects = pm.list_projects(
            user_id=user_id,
            status=status,
            tags=tags,
            page=page,
            page_size=page_size
        )
        
        total = len(projects) if status else len(pm.list_projects(user_id=user_id))
        
        from .schemas import BaseResponse
        response_data = {
            "success": True,
            "projects": projects,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
        async def event_generator():
            yield {
                "event": "projects",
                "data": response_data
            }
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

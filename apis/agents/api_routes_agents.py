"""
Agents 管理相关的 API 路由
提供 Agent 列表、详情、分类等功能
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from utils.llm_client import (
    ZhipuModel,
    ModelType,
    list_available_models,
    get_model_for_purpose,
)
from utils.logger import get_logger

logger = get_logger("AgentsAPI")

router = APIRouter(prefix="/juben/agents", tags=["Agents管理"])


class AgentInfo(BaseModel):
    """Agent 基础信息"""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    icon: str
    model: str
    api_endpoint: str
    status: str


class AgentDetail(AgentInfo):
    """Agent 详细信息"""
    features: List[str]
    capabilities: List[str]
    input_example: str
    output_example: str


class AgentListResponse(BaseModel):
    """Agent 列表响应"""
    success: bool
    agents: List[AgentInfo]
    total: int
    categories: Dict[str, List[AgentInfo]]


# 配置所有可用的 Agents
AGENTS_CONFIG = {
    # 策划类
    "short_drama_planner": {
        "id": "short_drama_planner",
        "name": "ShortDramaPlannerAgent",
        "display_name": "短剧策划助手",
        "description": "专业的短剧策划和创作建议助手，提供剧本结构、情节设计、人物塑造等全方位策划支持",
        "category": "planning",
        "icon": "📋",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/chat",
        "features": ["剧本策划", "情节设计建议", "结构优化", "创作指导"],
        "capabilities": [
            "分析剧本需求并提供专业策划建议",
            "设计合理的情节结构和故事节奏",
            "提供人物塑造和对话写作指导",
            "优化剧本的商业价值和观赏性",
        ],
        "input_example": "帮我策划一个关于都市爱情的短剧剧本",
        "output_example": "根据您的需求，我为您策划了以下短剧方案...",
        "status": "active",
    },
    # 创作类
    "short_drama_creator": {
        "id": "short_drama_creator",
        "name": "ShortDramaCreatorAgent",
        "display_name": "短剧创作助手",
        "description": "专业短剧内容创作助手，帮助生成高质量剧本内容",
        "category": "creation",
        "icon": "✍️",
        "model": "glm-4.7-flash",
        "api_endpoint": "/juben/creator/chat",
        "features": ["剧本创作", "场景描写", "对话生成", "情节展开"],
        "capabilities": [
            "创作完整的短剧剧本",
            "生成生动的场景描写",
            "编写符合人物性格的对话",
            "展开引人入胜的故事情节",
        ],
        "input_example": "创作一个悬疑短剧的第一场戏",
        "output_example": "【第一场】\n场景：废弃工厂 - 夜",
        "status": "active",
    },
    # 评估类
    "short_drama_evaluation": {
        "id": "short_drama_evaluation",
        "name": "ShortDramaEvaluationAgent",
        "display_name": "短剧评估助手",
        "description": "专业的短剧质量评估助手，从多维度评估剧本质量并提供改进建议",
        "category": "evaluation",
        "icon": "📊",
        "model": "glm-4.1v-thinking-flash",
        "api_endpoint": "/juben/evaluation/chat",
        "features": ["质量评估", "多维度打分", "改进建议", "市场分析"],
        "capabilities": [
            "从情节、人物、对话等维度评估剧本",
            "提供详细的评分和改进建议",
            "分析剧本的市场潜力",
            "对比同类优秀作品",
        ],
        "input_example": "请评估我的短剧剧本质量",
        "output_example": "【评估报告】\n综合评分：85/100",
        "status": "active",
    },
    # 分析类
    "story_five_elements": {
        "id": "story_five_elements",
        "name": "StoryFiveElementsAgent",
        "display_name": "故事五元素分析",
        "description": "分析故事的核心五元素：人物、情节、环境、主题、风格",
        "category": "analysis",
        "icon": "🔍",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/story-analysis/analyze",
        "features": ["五元素分析", "结构梳理", "主题提炼", "风格识别"],
        "capabilities": [
            "深度分析故事五要素",
            "梳理故事结构和脉络",
            "提炼核心主题思想",
            "识别故事风格特征",
        ],
        "input_example": "分析这个故事的核心元素",
        "output_example": "【五元素分析】\n一、人物分析...",
        "status": "active",
    },
    # 工作流类
    "plot_points_workflow": {
        "id": "plot_points_workflow",
        "name": "PlotPointsWorkflowAgent",
        "display_name": "情节点工作流",
        "description": "完整的大情节点与详细情节点生成工作流",
        "category": "workflow",
        "icon": "🔄",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/plot-points-workflow/execute",
        "features": ["大情节点生成", "详细情节点展开", "结构化输出", "可视化展示"],
        "capabilities": [
            "生成完整的大情节点框架",
            "展开详细的情节点内容",
            "提供结构化输出格式",
            "支持可视化展示",
        ],
        "input_example": "生成这个故事的完整情节点",
        "output_example": "【情节点工作流】\n一、大情节点...",
        "status": "active",
    },
    # 人物类
    "character_profile_generator": {
        "id": "character_profile_generator",
        "name": "CharacterProfileGeneratorAgent",
        "display_name": "人物小传生成",
        "description": "为故事中的主要人物生成详细的人物小传",
        "category": "character",
        "icon": "👤",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/character/profile",
        "features": ["人物识别", "小传生成", "性格分析", "背景构建"],
        "capabilities": [
            "识别故事中的主要人物",
            "生成300-500字的详细小传",
            "分析人物性格特征",
            "构建完整的背景故事",
        ],
        "input_example": "为这个故事生成人物小传",
        "output_example": "【人物小传】\n1. 张三（主角）...",
        "status": "active",
    },
    "character_relationship_analyzer": {
        "id": "character_relationship_analyzer",
        "name": "CharacterRelationshipAnalyzerAgent",
        "display_name": "人物关系分析",
        "description": "分析故事中人物之间的复杂关系网络",
        "category": "character",
        "icon": "👥",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/character/relationship",
        "features": ["关系识别", "关系类型分析", "关系网络构建", "关系演变追踪"],
        "capabilities": [
            "识别各种类型的人物关系",
            "分析关系的性质和强度",
            "构建完整的关系网络",
            "追踪关系的演变过程",
        ],
        "input_example": "分析这个故事中的人物关系",
        "output_example": "【人物关系分析】\n1. 张三 ↔ 李四：恋人关系...",
        "status": "active",
    },
    # 故事类
    "mind_map": {
        "id": "mind_map",
        "name": "MindMapAgent",
        "display_name": "思维导图",
        "description": "生成故事结构可视化思维导图",
        "category": "story",
        "icon": "🧠",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/mind-map/generate",
        "features": ["结构提取", "导图生成", "可视化展示", "编辑导出"],
        "capabilities": [
            "提取故事结构层次",
            "生成可视化思维导图",
            "支持在线编辑",
            "可导出多种格式",
        ],
        "input_example": "为这个故事生成思维导图",
        "output_example": "【思维导图】\n已生成，点击查看",
        "status": "active",
    },
    # 工具类
    "websearch": {
        "id": "websearch",
        "name": "WebSearchAgent",
        "display_name": "网络搜索",
        "description": "实时搜索网络信息，获取最新资料",
        "category": "utility",
        "icon": "🌐",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/websearch/chat",
        "features": ["实时搜索", "信息聚合", "来源标注", "智能摘要"],
        "capabilities": [
            "实时搜索最新信息",
            "聚合多个来源结果",
            "标注信息来源",
            "生成智能摘要",
        ],
        "input_example": "搜索2025年短剧市场趋势",
        "output_example": "【搜索结果】\n找到5条相关信息...",
        "status": "active",
    },
    "knowledge": {
        "id": "knowledge",
        "name": "KnowledgeAgent",
        "display_name": "知识库查询",
        "description": "查询剧本创作知识库，获取专业资料",
        "category": "utility",
        "icon": "📚",
        "model": "glm-4-flash",
        "api_endpoint": "/juben/knowledge/chat",
        "features": ["知识检索", "相似度匹配", "专业资料", "桥段参考"],
        "capabilities": [
            "检索剧本创作专业知识",
            "基于相似度匹配结果",
            "提供权威专业资料",
            "参考优秀作品桥段",
        ],
        "input_example": "查询短剧反转技巧",
        "output_example": "【知识库结果】\n找到相关资料...",
        "status": "active",
    },
}


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    category: Optional[str] = None,
    status: Optional[str] = None
) -> AgentListResponse:
    """
    获取所有可用的 Agents 列表

    Args:
        category: 按分类筛选 (planning/creation/evaluation/analysis/workflow/character/story/utility)
        status: 按状态筛选 (active/beta/experimental)

    Returns:
        AgentListResponse: Agent 列表
    """
    try:
        agents = []

        for agent_id, config in AGENTS_CONFIG.items():
            # 筛选条件
            if category and config.get("category") != category:
                continue
            if status and config.get("status") != status:
                continue

            agents.append(AgentInfo(**config))

        # 按分类组织
        categories = {}
        for agent in agents:
            cat = agent.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(agent)

        logger.info(f"返回 {len(agents)} 个 Agents")

        return AgentListResponse(
            success=True,
            agents=agents,
            total=len(agents),
            categories=categories
        )
    except Exception as e:
        logger.error(f"获取 Agent 列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_agent_categories() -> Dict[str, Any]:
    """
    获取所有 Agent 分类

    Returns:
        Dict: 分类列表和每个分类的数量
    """
    try:
        categories = {
            "planning": {"name": "策划类", "icon": "📋", "description": "剧本策划和规划相关"},
            "creation": {"name": "创作类", "icon": "✍️", "description": "内容创作和生成"},
            "evaluation": {"name": "评估类", "icon": "📊", "description": "质量评估和分析"},
            "analysis": {"name": "分析类", "icon": "🔍", "description": "深度分析和洞察"},
            "workflow": {"name": "工作流", "icon": "🔄", "description": "多步骤工作流程"},
            "character": {"name": "人物类", "icon": "👤", "description": "人物相关功能"},
            "story": {"name": "故事类", "icon": "📖", "description": "故事处理功能"},
            "utility": {"name": "工具类", "icon": "🛠️", "description": "辅助工具功能"},
        }

        # 统计每个分类的 Agent 数量
        category_counts = {}
        for config in AGENTS_CONFIG.values():
            cat = config.get("category", "utility")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "success": True,
            "categories": categories,
            "counts": category_counts,
            "total": len(AGENTS_CONFIG)
        }
    except Exception as e:
        logger.error(f"获取分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_agents(
    query: str,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    搜索 Agents

    Args:
        query: 搜索关键词
        category: 分类筛选

    Returns:
        Dict: 搜索结果
    """
    try:
        query_lower = query.lower()
        results = []

        for agent_id, config in AGENTS_CONFIG.items():
            # 筛选分类
            if category and config.get("category") != category:
                continue

            # 搜索匹配
            searchable_text = (
                config.get("name", "") + " " +
                config.get("display_name", "") + " " +
                config.get("description", "") + " " +
                " ".join(config.get("features", []))
            ).lower()

            if query_lower in searchable_text:
                results.append(AgentInfo(**config))

        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"搜索 Agents 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent_detail(agent_id: str) -> AgentDetail:
    """
    获取指定 Agent 的详细信息

    Args:
        agent_id: Agent ID

    Returns:
        AgentDetail: Agent 详细信息
    """
    try:
        if agent_id not in AGENTS_CONFIG:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

        config = AGENTS_CONFIG[agent_id]
        return AgentDetail(**config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Agent 详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

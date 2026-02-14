"""
统一 Agent 命名与分类映射
"""
from typing import Dict

# 规范化别名（旧名称 -> 规范ID）
AGENT_ALIASES: Dict[str, str] = {
    "short_drama_planner_agent": "short_drama_planner",
    "short_drama_creator_agent": "short_drama_creator",
    "short_drama_evaluation_agent": "short_drama_evaluation",
    "plot_points_workflow_agent": "plot_points_workflow",
    "ip_evaluation_agent": "ip_evaluation",
    "story_five_elements_agent": "story_five_elements",
}


def canonical_agent_id(agent_name: str) -> str:
    return AGENT_ALIASES.get(agent_name, agent_name)


AGENT_CATEGORY_MAPPING: Dict[str, str] = {
    "short_drama_planner": "planning",
    "short_drama_creator": "creation",
    "short_drama_evaluation": "evaluation",
    "script_evaluation": "evaluation",
    "ip_evaluation": "evaluation",
    "novel_screening_evaluation": "evaluation",
    "story_five_elements": "analysis",
    "story_evaluation": "analysis",
    "story_summary_generator": "analysis",
    "character_profile_generator": "character",
    "character_profile_agent": "character",
    "character_relationship_analyzer": "character",
    "character_relationship_agent": "character",
    "plot_points_analyzer": "story",
    "major_plot_points_agent": "story",
    "detailed_plot_points_agent": "story",
    "plot_points_workflow": "workflow",
    "mind_map_agent": "utility",
    "juben_orchestrator": "workflow",
    "juben_concierge": "workflow",
}

OUTPUT_TAG_PHASE_MAPPING: Dict[str, str] = {
    "drama_planning": "planning",
    "drama_creation": "creation",
    "drama_evaluation": "evaluation",
    "novel_screening": "evaluation",
    "story_analysis": "analysis",
    "character_development": "character",
    "plot_development": "story",
    "series_analysis": "analysis",
}

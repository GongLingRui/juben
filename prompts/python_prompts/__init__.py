"""
系统提示词模块索引
自动生成的文件，包含所有转换后的系统提示词
"""

from .plot_points_workflow_system_system import *
from .story_summary_generator_system_system import *
from .story_five_elements_system_system import *
from .major_plot_points_system_system import *
from .story_type_analyzer_system_system import *
from .story_summary_system_system import *
from .websearch_system_system import *
from .character_relationship_analyzer_system_system import *
from .short_drama_creater_system_system import *
from .detailed_plot_points_system_system import *
from .drama_analysis_system_system import *
from .short_drama_planner_system_system import *
from .mind_map_system_system import *
from .series_analysis_system_system import *
from .character_profile_generator_system_system import *
from .drama_workflow_system_system import *
from .file_reference_system_system import *
from .text_truncator_system_system import *
from .output_formatter_system_system import *
from .text_splitter_system_system import *
from .ip_evaluation_agent_system_system import *
from .result_integrator_system_system import *
from .short_drama_evaluation_system_system import *
from .plot_points_analyzer_system_system import *
from .script_evaluation_agent_system_system import *
from .knowledge_system_system import *

# 所有可用的系统提示词
AVAILABLE_PROMPTS = ['plot_points_workflow_system_system', 'story_summary_generator_system_system', 'story_five_elements_system_system', 'major_plot_points_system_system', 'story_type_analyzer_system_system', 'story_summary_system_system', 'websearch_system_system', 'character_relationship_analyzer_system_system', 'short_drama_creater_system_system', 'detailed_plot_points_system_system', 'drama_analysis_system_system', 'short_drama_planner_system_system', 'mind_map_system_system', 'series_analysis_system_system', 'character_profile_generator_system_system', 'drama_workflow_system_system', 'file_reference_system_system', 'text_truncator_system_system', 'output_formatter_system_system', 'text_splitter_system_system', 'ip_evaluation_agent_system_system', 'result_integrator_system_system', 'short_drama_evaluation_system_system', 'plot_points_analyzer_system_system', 'script_evaluation_agent_system_system', 'knowledge_system_system']

def get_all_prompts():
    """获取所有可用的提示词模块"""
    return AVAILABLE_PROMPTS

__all__ = ["get_all_prompts", "AVAILABLE_PROMPTS"] + AVAILABLE_PROMPTS

#!/usr/bin/env python3
"""
检查Agent输出保存状态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

agents_with_saving = [
    "juben_orchestrator",
    "juben_concierge",
    "text_splitter_agent",
    "short_drama_creator_agent",
    "text_truncator_agent",
    "character_relationship_analyzer_agent",
    "plot_points_analyzer_agent"
]

all_agents = [
    "character_profile_generator_agent",
    "character_relationship_analyzer_agent",
    "detailed_plot_points_agent",
    "document_generator_agent",
    "drama_analysis_agent",
    "drama_workflow_agent",
    "file_reference_agent",
    "ip_evaluation_agent",
    "knowledge_agent",
    "major_plot_points_agent",
    "mind_map_agent",
    "novel_screening_evaluation_agent",
    "output_formatter_agent",
    "plot_points_analyzer_agent",
    "plot_points_workflow_agent",
    "result_analyzer_evaluation_agent",
    "result_integrator_agent",
    "score_analyzer_agent",
    "script_evaluation_agent",
    "series_analysis_agent",
    "series_info_agent",
    "series_name_extractor_agent",
    "short_drama_creator_agent",
    "short_drama_evaluation_agent",
    "short_drama_planner_agent",
    "story_evaluation_agent",
    "story_five_elements_agent",
    "story_outline_evaluation_agent",
    "story_summary_generator_agent",
    "story_type_analyzer_agent",
    "text_processor_evaluation_agent",
    "text_splitter_agent",
    "text_truncator_agent",
    "websearch_agent"
]

agents_without_saving = [a for a in all_agents if a not in agents_with_saving]

print("=" * 80)
print("Agent输出保存状态检查")
print("=" * 80)
print(f"\n✅ 已实现输出保存的Agent ({len(agents_with_saving)}个):")
for agent in agents_with_saving:
    print(f"  - {agent}")

print(f"\n❌ 未实现输出保存的Agent ({len(agents_without_saving)}个):")
for agent in agents_without_saving:
    print(f"  - {agent}")

print(f"\n📊 统计:")
print(f"  总Agent数: {len(all_agents)}")
print(f"  已保存: {len(agents_with_saving)} ({len(agents_with_saving)/len(all_agents)*100:.1f}%)")
print(f"  未保存: {len(agents_without_saving)} ({len(agents_without_saving)/len(all_agents)*100:.1f}%)")

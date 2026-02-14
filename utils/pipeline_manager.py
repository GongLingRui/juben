"""
创作管线管理器
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.agent_registry import AgentRegistry
from utils.agent_dispatch import build_agent_generator


DEFAULT_TEMPLATES = [
    {
        "id": "script_creation_pipeline",
        "name": "剧本创作流水线",
        "description": "从策划到创作再到评估的基础流水线",
        "steps": [
            {
                "id": "plan",
                "name": "策划",
                "agent_id": "short_drama_planner_agent",
                "input_template": "请为以下需求完成短剧策划：\n{user_input}"
            },
            {
                "id": "create",
                "name": "创作",
                "agent_id": "short_drama_creator_agent",
                "input_template": "基于策划结果创作完整内容：\n{steps.plan.output}\n\n用户需求：{user_input}"
            },
            {
                "id": "evaluate",
                "name": "评估",
                "agent_id": "short_drama_evaluation_agent",
                "input_template": "请对以下内容进行评估：\n{steps.create.output}"
            }
        ]
    },
    {
        "id": "creative_pipeline_full",
        "name": "创意到分镜全链路",
        "description": "从创意 → 大纲 → 分集 → 分场 → 分镜的自动化管线",
        "steps": [
            {
                "id": "idea",
                "name": "创意",
                "agent_id": "short_drama_planner_agent",
                "input_template": "基于以下需求生成创意方向与核心卖点：\n{user_input}"
            },
            {
                "id": "outline",
                "name": "大纲",
                "agent_id": "story_summary_generator_agent",
                "input_template": "基于创意生成完整故事大纲：\n{steps.idea.output}"
            },
            {
                "id": "episodes",
                "name": "分集",
                "agent_id": "major_plot_points_agent",
                "input_template": "基于大纲拆分分集大纲（含集标题与集目标）：\n{steps.outline.output}"
            },
            {
                "id": "scenes",
                "name": "分场",
                "agent_id": "detailed_plot_points_agent",
                "input_template": "基于分集大纲拆分分场（含场景目标/冲突/情绪）：\n{steps.episodes.output}"
            },
            {
                "id": "storyboard",
                "name": "分镜",
                "agent_id": "mind_map_agent",
                "input_template": "基于分场生成可执行分镜/镜头设计要点：\n{steps.scenes.output}"
            }
        ]
    }
]


class PipelineManager:
    def __init__(self, base_dir: str = "data/pipelines"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.templates_file = self.base_dir / "templates.json"
        self.runs_dir = self.base_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.registry = AgentRegistry()
        self._ensure_templates()

    def _ensure_templates(self):
        if not self.templates_file.exists():
            self.templates_file.write_text(json.dumps(DEFAULT_TEMPLATES, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_templates(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.templates_file.read_text(encoding="utf-8"))
        except Exception:
            return DEFAULT_TEMPLATES

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        for item in self.list_templates():
            if item.get("id") == template_id:
                return item
        return None

    def _render(self, template: str, context: Dict[str, Any]) -> str:
        result = template
        for key, value in context.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    async def run_pipeline(
        self,
        template_id: str,
        user_input: str,
        user_id: str,
        session_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        template = self.get_template(template_id)
        if not template:
            raise ValueError("未找到管线模板")

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        run = {
            "id": run_id,
            "template_id": template_id,
            "name": template.get("name"),
            "project_id": project_id,
            "user_id": user_id,
            "session_id": session_id,
            "input": user_input,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "steps": []
        }

        step_outputs: Dict[str, Any] = {}

        for step in template.get("steps", []):
            step_id = step.get("id")
            agent_id = step.get("agent_id")
            agent = await self.registry.get_agent(agent_id)
            if not agent:
                run["steps"].append({
                    "id": step_id,
                    "name": step.get("name"),
                    "status": "failed",
                    "error": f"Agent不存在: {agent_id}"
                })
                run["status"] = "failed"
                break

            ctx = {
                "user_input": user_input,
            }
            for prev_id, prev_data in step_outputs.items():
                ctx[f"steps.{prev_id}.output"] = prev_data.get("output", "")

            input_text = self._render(step.get("input_template", "{user_input}"), ctx)
            request_data = {"input": input_text, "project_id": project_id}
            context = {"user_id": user_id, "session_id": session_id, "project_id": project_id}

            step_record = {
                "id": step_id,
                "name": step.get("name"),
                "agent_id": agent_id,
                "input": input_text,
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "output": "",
                "events": []
            }

            output_buffer: List[str] = []
            async for event in build_agent_generator(agent, request_data, context):
                step_record["events"].append(event)
                if event.get("event_type") in ("content", "message", "tool_complete"):
                    data = event.get("data")
                    if isinstance(data, dict) and "result" in data:
                        output_buffer.append(str(data.get("result")))
                    elif isinstance(data, str):
                        output_buffer.append(data)
                if event.get("event_type") == "error":
                    step_record["status"] = "failed"
                    step_record["error"] = event.get("data")
                    break

            step_record["output"] = "".join(output_buffer).strip()
            step_record["rag_trace"] = getattr(agent, "get_rag_trace", lambda: [])()
            step_record["status"] = step_record.get("status") if step_record.get("status") != "running" else "completed"
            step_record["completed_at"] = datetime.now().isoformat()
            run["steps"].append(step_record)

            step_outputs[step_id] = {
                "output": step_record["output"]
            }

            if step_record["status"] == "failed":
                run["status"] = "failed"
                break

        if run["status"] != "failed":
            run["status"] = "completed"
        run["completed_at"] = datetime.now().isoformat()
        self._save_run(run)
        return run

    def _save_run(self, run: Dict[str, Any]):
        path = self.runs_dir / f"{run['id']}.json"
        path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_runs(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        runs = []
        for file in self.runs_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if project_id and data.get("project_id") != project_id:
                    continue
                runs.append(data)
            except Exception:
                continue
        return sorted(runs, key=lambda r: r.get("created_at", ""), reverse=True)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None


def get_pipeline_manager() -> PipelineManager:
    return PipelineManager()

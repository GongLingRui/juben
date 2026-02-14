"""
质量与稳定性评估 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher
import json
from datetime import datetime

from utils.agent_registry import AgentRegistry
from utils.agent_dispatch import build_agent_generator
from utils.graph_consistency import validate_graph, check_character_consistency, check_character_motivation_consistency
from utils.project_manager import get_project_manager
from apis.core.schemas import FileType

router = APIRouter(prefix="/juben/quality", tags=["质量评估"])


class StabilityRequest(BaseModel):
    agent_id: str = Field(..., description="Agent ID")
    input: str = Field(..., description="输入内容")
    runs: int = Field(3, ge=2, le=5, description="重复次数")
    user_id: str = Field(default="default-user", description="用户ID")
    session_id: str = Field(default="stability_session", description="会话ID")
    project_id: Optional[str] = Field(default=None, description="项目ID")


def _collect_text(events: List[Dict[str, Any]]) -> str:
    buffer: List[str] = []
    for event in events:
        if event.get("event_type") in ("content", "message", "tool_complete"):
            data = event.get("data")
            if isinstance(data, dict) and "result" in data:
                buffer.append(str(data.get("result")))
            elif isinstance(data, str):
                buffer.append(data)
    return "".join(buffer).strip()


@router.post("/stability")
async def evaluate_stability(request: StabilityRequest):
    registry = AgentRegistry()
    agent = await registry.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    outputs: List[str] = []
    for i in range(request.runs):
        events: List[Dict[str, Any]] = []
        async for event in build_agent_generator(
            agent,
            {"input": request.input, "project_id": request.project_id},
            {"user_id": request.user_id, "session_id": f"{request.session_id}_{i}", "project_id": request.project_id},
        ):
            events.append(event)
        outputs.append(_collect_text(events))

    if len(outputs) < 2:
        return {"success": True, "data": {"score": 0, "outputs": outputs}}

    ratios: List[float] = []
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            ratios.append(SequenceMatcher(None, outputs[i], outputs[j]).ratio())
    score = round(sum(ratios) / len(ratios), 4) if ratios else 0.0

    return {
        "success": True,
        "data": {
            "score": score,
            "stable": score >= 0.85,
            "outputs": outputs
        }
    }


class GraphValidateRequest(BaseModel):
    story_id: str = Field(..., description="故事ID")


@router.post("/graph-validate")
async def graph_validate(request: GraphValidateRequest):
    try:
        result = await validate_graph(request.story_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CharacterConsistencyRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    script_text: Optional[str] = Field(default=None, description="剧本原文（可选）")
    llm_check: bool = Field(default=False, description="是否启用LLM动机一致性检测")


@router.post("/character-consistency")
async def character_consistency(request: CharacterConsistencyRequest):
    try:
        text = request.script_text or ""
        if not text:
            manager = get_project_manager()
            files = await manager.get_project_files(request.project_id)
            script_files = [f for f in files if str(f.file_type) == "script" or str(f.file_type) == "SCRIPT"]
            if script_files:
                # 使用最新脚本
                latest = sorted(script_files, key=lambda f: f.updated_at, reverse=True)[0]
                text = latest.content if isinstance(latest.content, str) else json.dumps(latest.content, ensure_ascii=False)
        if not text:
            return {"success": True, "data": {"status": "empty", "issues": [], "details": []}}
        result = check_character_consistency(text)
        if request.llm_check:
            llm_result = await check_character_motivation_consistency(text)
            result["llm_motivation"] = llm_result

        # 保存评估报告到项目文件（可追溯）
        try:
            manager = get_project_manager()
            await manager.add_file_to_project(
                project_id=request.project_id,
                filename=f"人物一致性报告_{request.project_id}_{int(datetime.now().timestamp())}.json",
                file_type=FileType.EVALUATION,
                content=result,
                agent_source="consistency_validator",
                tags=["consistency", "character", "llm_motivation" if request.llm_check else "rule_based"],
            )
        except Exception:
            pass
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

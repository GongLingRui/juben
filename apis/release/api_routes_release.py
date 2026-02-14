"""
制作流通闭环 API
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

router = APIRouter(prefix="/juben/release", tags=["制作流通"])

PLATFORM_TEMPLATES = {
    "douyin": {
        "name": "抖音",
        "episode_length_sec": 60,
        "hook_window_sec": 5,
        "episodes": 40,
        "tags": ["短剧", "情感", "高能"],
        "description": "强钩子+快节奏，前3秒必须抛矛盾"
    },
    "kuaishou": {
        "name": "快手",
        "episode_length_sec": 90,
        "hook_window_sec": 8,
        "episodes": 30,
        "tags": ["短剧", "情感", "下沉"],
        "description": "情绪密度高，强调人物关系" 
    },
    "bilibili": {
        "name": "B站",
        "episode_length_sec": 180,
        "hook_window_sec": 10,
        "episodes": 20,
        "tags": ["剧情", "成长", "强设定"],
        "description": "世界观设定清晰，角色弧线完整"
    }
}


class RoiRequest(BaseModel):
    views: int = Field(..., description="曝光量")
    ctr: float = Field(..., description="点击率(0-1)")
    cvr: float = Field(..., description="转化率(0-1)")
    arpu: float = Field(..., description="单用户收入")
    cost: float = Field(..., description="投放成本")


class ChecklistRequest(BaseModel):
    platform: str = Field(..., description="平台ID")
    title: str = Field(..., description="作品名")
    episodes: int = Field(..., description="集数")


@router.get("/templates")
async def list_templates():
    return {"success": True, "data": PLATFORM_TEMPLATES}


@router.post("/roi")
async def calculate_roi(request: RoiRequest):
    clicks = request.views * request.ctr
    conversions = clicks * request.cvr
    revenue = conversions * request.arpu
    roi = (revenue - request.cost) / request.cost if request.cost > 0 else 0
    return {
        "success": True,
        "data": {
            "clicks": int(clicks),
            "conversions": int(conversions),
            "revenue": round(revenue, 2),
            "roi": round(roi, 4)
        }
    }


@router.post("/checklist")
async def generate_checklist(request: ChecklistRequest):
    template = PLATFORM_TEMPLATES.get(request.platform)
    checklist = [
        f"确认《{request.title}》集数为 {request.episodes}",
        "完成首集5秒强钩子设计",
        "准备至少3条投放标题与封面",
        "确保角色关系图与时间线一致",
        "制作投放素材（竖版/横版）",
    ]
    if template:
        checklist.append(f"满足 {template['name']} 平台时长/节奏要求")
    return {"success": True, "data": {"platform": request.platform, "checklist": checklist}}

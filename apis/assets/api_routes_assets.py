"""
资产库 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from utils.asset_library import get_asset_library

router = APIRouter(prefix="/juben/assets", tags=["资产库"])


class AssetCreateRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    artifact_id: Optional[str] = Field(None, description="关联的Artifact ID")
    name: str = Field(..., description="资产名称")
    asset_type: str = Field(default="generic", description="资产类型")
    tags: List[str] = Field(default_factory=list, description="标签")
    collection: str = Field(default="default", description="所属集合")
    source: str = Field(default="manual", description="来源")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetUpdateRequest(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    tags: Optional[List[str]] = None
    collection: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("")
async def list_assets(project_id: str = Query(..., description="项目ID")):
    library = get_asset_library()
    return {"success": True, "data": library.list_assets(project_id)}


@router.post("")
async def create_asset(request: AssetCreateRequest):
    library = get_asset_library()
    asset = library.create_asset(request.project_id, request.dict())
    return {"success": True, "data": asset}


@router.put("/{asset_id}")
async def update_asset(asset_id: str, request: AssetUpdateRequest, project_id: str = Query(...)):
    library = get_asset_library()
    updated = library.update_asset(project_id, asset_id, request.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="资产不存在")
    return {"success": True, "data": updated}


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str, project_id: str = Query(...)):
    library = get_asset_library()
    ok = library.delete_asset(project_id, asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="资产不存在")
    return {"success": True}


@router.get("/collections")
async def list_collections(project_id: str = Query(..., description="项目ID")):
    library = get_asset_library()
    return {"success": True, "data": library.list_collections(project_id)}

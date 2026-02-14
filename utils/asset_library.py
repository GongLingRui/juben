"""
资产库管理
用于管理项目内的素材资产（基于 artifact 索引）
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class AssetLibrary:
    def __init__(self, base_dir: str = "projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def _asset_file(self, project_id: str) -> Path:
        return self.base_dir / project_id / "resources" / "assets.json"

    def _load_assets(self, project_id: str) -> List[Dict[str, Any]]:
        path = self._asset_file(project_id)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_assets(self, project_id: str, items: List[Dict[str, Any]]):
        path = self._asset_file(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_assets(self, project_id: str) -> List[Dict[str, Any]]:
        return self._load_assets(project_id)

    def create_asset(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        items = self._load_assets(project_id)
        asset = {
            "id": data.get("id") or f"asset_{uuid.uuid4().hex[:8]}",
            "project_id": project_id,
            "artifact_id": data.get("artifact_id"),
            "name": data.get("name") or "未命名资产",
            "asset_type": data.get("asset_type") or "generic",
            "tags": data.get("tags") or [],
            "collection": data.get("collection") or "default",
            "source": data.get("source") or "manual",
            "created_at": datetime.now().isoformat(),
            "metadata": data.get("metadata") or {},
        }
        items.insert(0, asset)
        self._save_assets(project_id, items)
        return asset

    def update_asset(self, project_id: str, asset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        items = self._load_assets(project_id)
        updated = None
        for item in items:
            if item.get("id") == asset_id:
                item.update({k: v for k, v in updates.items() if v is not None})
                item["updated_at"] = datetime.now().isoformat()
                updated = item
                break
        if updated:
            self._save_assets(project_id, items)
        return updated

    def delete_asset(self, project_id: str, asset_id: str) -> bool:
        items = self._load_assets(project_id)
        new_items = [item for item in items if item.get("id") != asset_id]
        if len(new_items) == len(items):
            return False
        self._save_assets(project_id, new_items)
        return True

    def list_collections(self, project_id: str) -> Dict[str, List[Dict[str, Any]]]:
        items = self._load_assets(project_id)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            key = item.get("collection") or "default"
            grouped.setdefault(key, []).append(item)
        return grouped


def get_asset_library() -> AssetLibrary:
    return AssetLibrary()

"""
记忆开关设置管理
支持用户级与项目级的记忆开关
"""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MemorySettings:
    user_enabled: bool = True
    project_enabled: bool = True
    effective_enabled: bool = True
    updated_at: str = ""


class MemorySettingsManager:
    def __init__(self, path: str = "data/memory_settings.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._cache = {"users": {}, "projects": {}}
            return
        try:
            self._cache = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._cache = {"users": {}, "projects": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_user(self, user_id: str) -> Dict[str, Any]:
        return self._cache.setdefault("users", {}).get(user_id, {})

    def _get_project(self, project_id: str) -> Dict[str, Any]:
        return self._cache.setdefault("projects", {}).get(project_id, {})

    def get_settings(self, user_id: str, project_id: Optional[str] = None) -> MemorySettings:
        user_cfg = self._get_user(user_id)
        project_cfg = self._get_project(project_id) if project_id else {}

        user_enabled = user_cfg.get("enabled", True)
        project_enabled = project_cfg.get("enabled", True) if project_id else True
        effective = bool(user_enabled and project_enabled)
        updated_at = project_cfg.get("updated_at") or user_cfg.get("updated_at") or ""

        return MemorySettings(
            user_enabled=user_enabled,
            project_enabled=project_enabled,
            effective_enabled=effective,
            updated_at=updated_at,
        )

    def set_user_enabled(self, user_id: str, enabled: bool) -> MemorySettings:
        self._cache.setdefault("users", {})[user_id] = {
            "enabled": enabled,
            "updated_at": datetime.now().isoformat()
        }
        self._save()
        return self.get_settings(user_id)

    def set_project_enabled(self, project_id: str, enabled: bool, user_id: Optional[str] = None) -> MemorySettings:
        self._cache.setdefault("projects", {})[project_id] = {
            "enabled": enabled,
            "updated_at": datetime.now().isoformat(),
            "updated_by": user_id
        }
        self._save()
        return self.get_settings(user_id or "", project_id)


_memory_settings_manager: Optional[MemorySettingsManager] = None


def get_memory_settings_manager() -> MemorySettingsManager:
    global _memory_settings_manager
    if _memory_settings_manager is None:
        _memory_settings_manager = MemorySettingsManager()
    return _memory_settings_manager


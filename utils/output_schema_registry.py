"""
输出 JSON Schema 注册表
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional, List


DEFAULT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "generic_result_v1": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "details": {"type": "string"},
            "score": {"type": "number"},
            "issues": {"type": "array"},
        },
        "required": ["summary"]
    }
}


class OutputSchemaRegistry:
    def __init__(self, path: str = "data/output_schemas.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._cache = dict(DEFAULT_SCHEMAS)
            self._save()
            return
        try:
            self._cache = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self._cache, dict):
                self._cache = dict(DEFAULT_SCHEMAS)
        except Exception:
            self._cache = dict(DEFAULT_SCHEMAS)

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_schemas(self) -> List[Dict[str, Any]]:
        return [{"id": k, "schema": v} for k, v in self._cache.items()]

    def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(schema_id)

    def register_schema(self, schema_id: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        self._cache[schema_id] = schema
        self._save()
        return {"id": schema_id, "schema": schema}


_registry: Optional[OutputSchemaRegistry] = None


def get_output_schema_registry() -> OutputSchemaRegistry:
    global _registry
    if _registry is None:
        _registry = OutputSchemaRegistry()
    return _registry


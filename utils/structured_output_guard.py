"""
结构化输出守卫
用于约束模型输出为 JSON，并进行基础 Schema/类型校验与修复
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple, Type, Union, List

from pydantic import BaseModel, ValidationError


JSON_INTENT_PATTERNS = [
    r"JSON Schema",
    r"json schema",
    r"仅输出JSON",
    r"只输出JSON",
    r"输出JSON",
    r"JSON格式",
    r"返回JSON",
]


def _extract_json(text: str) -> Optional[str]:
    if not text:
        return None
    fenced = re.search(r"```json\\s*(\\{.*?\\})\\s*```", text, flags=re.S)
    if fenced:
        return fenced.group(1)
    brace = re.search(r"(\\{.*\\})", text, flags=re.S)
    if brace:
        return brace.group(1)
    return None


def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    payload = _extract_json(text) or text
    try:
        return json.loads(payload)
    except Exception:
        return None


def _simple_schema_validate(schema: Dict[str, Any], data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for key in required:
        if key not in data:
            errors.append(f"missing:{key}")
    for key, rule in properties.items():
        if key not in data:
            continue
        expected = rule.get("type")
        if not expected:
            continue
        if expected == "array" and not isinstance(data[key], list):
            errors.append(f"type:{key}:array")
        if expected == "object" and not isinstance(data[key], dict):
            errors.append(f"type:{key}:object")
        if expected == "string" and not isinstance(data[key], str):
            errors.append(f"type:{key}:string")
        if expected == "number" and not isinstance(data[key], (int, float)):
            errors.append(f"type:{key}:number")
        if expected == "integer" and not isinstance(data[key], int):
            errors.append(f"type:{key}:integer")
        if expected == "boolean" and not isinstance(data[key], bool):
            errors.append(f"type:{key}:boolean")
    return len(errors) == 0, errors


class StructuredOutputGuard:
    """结构化输出校验与修复"""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def detect_json_intent(self, messages: List[Dict[str, str]]) -> bool:
        content = "\\n".join([m.get("content", "") for m in messages if m])
        return any(re.search(p, content) for p in JSON_INTENT_PATTERNS)

    def extract_inline_schema(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        content = "\\n".join([m.get("content", "") for m in messages if m])
        match = re.search(r"JSON Schema\\s*:\\s*(\\{.*?\\})\\s*(?:\\n\\n|$)", content, flags=re.S)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                return None
        return None

    def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Union[Type[BaseModel], BaseModel, Dict[str, Any]]] = None,
    ) -> Tuple[bool, List[str]]:
        if schema is None:
            return True, []
        if isinstance(schema, dict):
            return _simple_schema_validate(schema, data)
        try:
            model = schema if isinstance(schema, BaseModel) else schema.parse_obj(data)  # type: ignore
            if isinstance(model, BaseModel):
                model.dict()
            return True, []
        except ValidationError as e:
            return False, [str(err) for err in e.errors()]
        except Exception as e:
            return False, [str(e)]

    async def enforce_json_string(
        self,
        llm_client,
        messages: List[Dict[str, str]],
        raw_output: str,
        schema: Optional[Union[Type[BaseModel], BaseModel, Dict[str, Any]]] = None,
        constraint_template: Optional[str] = None,
    ) -> str:
        data = _parse_json(raw_output)
        if data is not None:
            ok, _ = self.validate(data, schema)
            if ok:
                return json.dumps(data, ensure_ascii=False)

        last_output = raw_output
        for _ in range(self.max_retries):
            constraint_note = f"\\n\\n请遵守以下输出约束：\\n{constraint_template}" if constraint_template else ""
            repair_prompt = (
                "请将下面内容修复为严格的JSON，仅输出JSON对象，不要多余文本。"
                "如果有Schema约束，请严格遵循。\\n\\n"
                f"原始输出：\\n{last_output}"
                f"{constraint_note}"
            )
            repair_messages = messages + [{"role": "user", "content": repair_prompt}]
            last_output = await llm_client.chat(repair_messages, temperature=0.1, max_tokens=2000)
            data = _parse_json(last_output)
            if data is None:
                continue
            ok, _ = self.validate(data, schema)
            if ok:
                return json.dumps(data, ensure_ascii=False)

        # 最终回退：返回原始输出
        return raw_output

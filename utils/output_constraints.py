"""
统一输出约束模板
"""
from typing import Dict


STANDARD_TEMPLATE_ID = "standard_v1"

TEMPLATES: Dict[str, str] = {
    STANDARD_TEMPLATE_ID: (
        "【输出约束模板】\n"
        "1) 输出结构清晰，优先给出结论/结果，再给理由/细节。\n"
        "2) 避免重复与冗长铺垫。\n"
        "3) 如存在 JSON Schema 约束，请只输出 JSON 对象，不要额外文本。\n"
        "4) 不输出与任务无关的免责声明或客套。\n"
    )
}


def get_output_constraint_template(template_id: str = STANDARD_TEMPLATE_ID) -> str:
    return TEMPLATES.get(template_id, TEMPLATES[STANDARD_TEMPLATE_ID])


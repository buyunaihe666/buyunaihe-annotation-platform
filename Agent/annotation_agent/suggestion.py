import json
from typing import Any, Dict, List, Optional

from .llm import call_llm, call_llm_openai_fallback, has_llm, parse_json_lenient
from .config import config


def _materials(template_schema: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not template_schema:
        return []
    mats = template_schema.get("materials") or []
    if isinstance(mats, list):
        return [m for m in mats if isinstance(m, dict)]
    return []


def _first_text_field_from_raw(raw_data: Optional[Dict[str, Any]]) -> str:
    if not isinstance(raw_data, dict):
        return ""
    for v in raw_data.values():
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def heuristic_suggestion(template_schema: Optional[Dict[str, Any]], raw_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    materials = _materials(template_schema)
    first_text = _first_text_field_from_raw(raw_data)
    result: Dict[str, Any] = {}
    for m in sorted(materials, key=lambda x: x.get("sortOrder", 0)):
        key = m.get("fieldKey")
        if not key:
            continue
        mtype = (m.get("type") or "text").lower()
        opts = m.get("options") or []
        if mtype in ("text", "textarea"):
            result[key] = first_text if mtype == "text" and first_text else ""
        elif mtype in ("radio", "select"):
            result[key] = opts[0] if opts else ""
        elif mtype == "checkbox":
            result[key] = []
        elif mtype == "number":
            result[key] = 0
        elif mtype == "json":
            result[key] = {}
        elif mtype in ("file", "image"):
            result[key] = None
        elif mtype == "llm_prompt":
            result[key] = ""
        else:
            result[key] = "" if not opts else opts[0]
    return result


def build_prompt(template_schema: Optional[Dict[str, Any]], raw_data: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    schema_desc = json.dumps(template_schema or {}, ensure_ascii=False)
    raw_desc = json.dumps(raw_data or {}, ensure_ascii=False)
    system = (
        "你是一个AI数据标注助手。根据标注模板的 schema 和原始数据，自动生成标注结果 JSON。"
        "只返回 JSON 对象，键为 fieldKey，值为该字段的标注值。不要输出任何额外说明。"
    )
    user = (
        f"标注模板 schema：\n{schema_desc}\n\n"
        f"原始数据：\n{raw_desc}\n\n"
        "请严格按照 schema.materials 中的 fieldKey 和 type 生成标注结果 JSON。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_suggestion(template_schema: Optional[Dict[str, Any]], raw_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not has_llm():
        return {"suggestion": heuristic_suggestion(template_schema, raw_data), "model": "heuristic", "error": None}

    messages = build_prompt(template_schema, raw_data)
    text = call_llm(messages)
    if text is None:
        text = call_llm_openai_fallback(messages)
    if text is None:
        return {
            "suggestion": heuristic_suggestion(template_schema, raw_data),
            "model": "heuristic",
            "error": "LLM call failed, fell back to heuristic",
        }
    parsed = parse_json_lenient(text)
    if not isinstance(parsed, dict):
        return {
            "suggestion": heuristic_suggestion(template_schema, raw_data),
            "model": config.AI_AUDIT_MODEL,
            "error": "LLM returned non-JSON, fell back to heuristic",
        }
    return {"suggestion": parsed, "model": config.AI_AUDIT_MODEL, "error": None}
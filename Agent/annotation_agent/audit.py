import json
from typing import Any, Dict, List, Optional, Tuple

from .config import config
from .llm import call_llm, call_llm_openai_fallback, has_llm, parse_json_lenient


def _materials(template_schema: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not template_schema:
        return []
    mats = template_schema.get("materials") or []
    if isinstance(mats, list):
        return [m for m in mats if isinstance(m, dict)]
    return []


def _check_type(mtype: str, value: Any) -> bool:
    if mtype in ("text", "textarea", "llm_prompt"):
        return isinstance(value, str)
    if mtype == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if mtype == "json":
        return isinstance(value, (dict, list))
    if mtype in ("radio", "select"):
        return isinstance(value, str)
    if mtype == "checkbox":
        return isinstance(value, list)
    if mtype in ("file", "image"):
        return value is None or isinstance(value, (str, dict, list))
    return True


def validate_rules(
    template_schema: Optional[Dict[str, Any]],
    annotation_result: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    materials = _materials(template_schema)
    result = annotation_result or {}
    issues: List[Dict[str, Any]] = []
    passed: List[Dict[str, Any]] = []
    for m in sorted(materials, key=lambda x: x.get("sortOrder", 0)):
        key = m.get("fieldKey")
        if not key:
            continue
        label = m.get("label", key)
        mtype = (m.get("type") or "text").lower()
        required = bool(m.get("required"))
        options = m.get("options") or []
        value = result.get(key)

        if required and (value is None or (isinstance(value, str) and value == "")
                         or (isinstance(value, (list, dict)) and len(value) == 0)):
            issues.append({"fieldKey": key, "label": label, "rule": "required", "message": f"字段「{label}」必填但为空"})
            continue

        if value is None and not required:
            passed.append({"fieldKey": key, "label": label, "rule": "required", "message": "可选字段，未填写"})
            continue

        if not _check_type(mtype, value):
            issues.append({"fieldKey": key, "label": label, "rule": "type", "message": f"字段「{label}」类型与期望 {mtype} 不符"})
            continue

        if mtype in ("radio", "select", "checkbox") and options:
            if mtype == "checkbox":
                if not isinstance(value, list):
                    issues.append({"fieldKey": key, "label": label, "rule": "options", "message": f"字段「{label}」应为选项数组"})
                    continue
                bad = [v for v in value if v not in options]
                if bad:
                    issues.append({"fieldKey": key, "label": label, "rule": "options",
                                   "message": f"字段「{label}」包含非法选项 {bad}"})
                    continue
            else:
                if value not in options:
                    issues.append({"fieldKey": key, "label": label, "rule": "options",
                                   "message": f"字段「{label}」值 {value!r} 不在选项列表中"})
                    continue

        passed.append({"fieldKey": key, "label": label, "rule": "all", "message": f"字段「{label}」校验通过"})
    return issues, passed


def rule_based_scoring(issues: List[Dict[str, Any]], passed: List[Dict[str, Any]],
                       raw_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    score = max(0, 100 - 15 * len(issues))
    score = min(100, score)
    if issues:
        issue_lines = "; ".join(f"{it['label']}: {it['message']}" for it in issues)
        reasoning = f"规则校验未通过 {len(issues)} 项。具体：{issue_lines}"
        suggestion = "请修正以下字段：" + ", ".join(it["label"] for it in issues)
    else:
        reasoning = "所有标注字段均通过模板规则校验（必填/类型/选项）。"
        suggestion = "标注符合模板规则。"
    evidence = {
        "rules": {
            "passed": passed,
            "failed": issues,
        },
        "raw_data_snapshot": raw_data,
    }
    return {
        "score": float(score),
        "issues": issues,
        "reasoning": reasoning,
        "suggestion": suggestion,
        "evidence": evidence,
        "model": "rule-based",
    }


def build_audit_prompt(
    template_schema: Optional[Dict[str, Any]],
    annotation_result: Optional[Dict[str, Any]],
    raw_data: Optional[Dict[str, Any]],
    rule_issues: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    schema_desc = json.dumps(template_schema or {}, ensure_ascii=False)
    result_desc = json.dumps(annotation_result or {}, ensure_ascii=False)
    raw_desc = json.dumps(raw_data or {}, ensure_ascii=False)
    issues_desc = json.dumps(rule_issues, ensure_ascii=False)
    system = (
        "你是AI标注审核助手。根据标注模板 schema、原始数据和标注人员的标注结果，"
        "对标注质量进行评分并指出问题。评分范围 0-100。"
        "只返回 JSON：{\"score\": number, \"issues\": [{\"fieldKey\": string, \"label\": string, \"message\": string}], "
        "\"reasoning\": string, \"suggestion\": string}。不要输出额外说明。"
    )
    user = (
        f"标注模板 schema：\n{schema_desc}\n\n"
        f"原始数据：\n{raw_desc}\n\n"
        f"标注结果：\n{result_desc}\n\n"
        f"规则校验发现的初步问题：\n{issues_desc}\n\n"
        "请综合评估标注质量，输出 JSON。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def run_audit(
    template_schema: Optional[Dict[str, Any]],
    annotation_result: Optional[Dict[str, Any]],
    raw_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    issues, passed = validate_rules(template_schema, annotation_result)

    if not has_llm():
        return rule_based_scoring(issues, passed, raw_data)

    messages = build_audit_prompt(template_schema, annotation_result, raw_data, issues)
    text = call_llm(messages)
    if text is None:
        text = call_llm_openai_fallback(messages)
    if text is None:
        result = rule_based_scoring(issues, passed, raw_data)
        result["error"] = "LLM call failed, fell back to rule-based"
        result["model"] = "rule-based"
        return result

    parsed = parse_json_lenient(text)
    if not isinstance(parsed, dict):
        result = rule_based_scoring(issues, passed, raw_data)
        result["error"] = "LLM returned non-JSON, fell back to rule-based"
        result["model"] = config.AI_AUDIT_MODEL
        return result

    score = parsed.get("score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    llm_issues = parsed.get("issues") if isinstance(parsed.get("issues"), list) else issues
    reasoning = parsed.get("reasoning") or ""
    suggestion = parsed.get("suggestion") or ""
    evidence = {
        "rules": {
            "passed": passed,
            "failed": issues,
            "llm_issues": llm_issues,
        },
        "raw_data_snapshot": raw_data,
    }
    if not reasoning:
        resp = rule_based_scoring(issues, passed, raw_data)
        reasoning = resp["reasoning"]
        if not suggestion:
            suggestion = resp["suggestion"]
    if score is None:
        score = max(0, 100 - 15 * len(issues))
    score = min(100.0, max(0.0, float(score)))
    return {
        "score": score,
        "issues": llm_issues,
        "reasoning": reasoning,
        "suggestion": suggestion,
        "evidence": evidence,
        "model": config.AI_AUDIT_MODEL,
        "error": None,
    }
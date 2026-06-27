import json
import re
from typing import List, Dict, Any, Optional

from .config import config


_llm = None
_llm_lock_init = False


def has_llm() -> bool:
    return config.has_llm


def _get_llm():
    global _llm, _llm_lock_init
    if _llm_lock_init:
        return _llm
    _llm_lock_init = True
    if not config.has_llm:
        _llm = None
        return _llm
    try:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(
            base_url=config.AI_AUDIT_BASE_URL,
            api_key=config.AI_AUDIT_API_KEY,
            model=config.AI_AUDIT_MODEL,
            temperature=0.2,
        )
    except Exception:
        _llm = None
    return _llm


def call_llm(messages: List[Dict[str, Any]]) -> Optional[str]:
    llm = _get_llm()
    if llm is None:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        lc_messages: List[Any] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        resp = llm.invoke(lc_messages)
        content = resp.content if hasattr(resp, "content") else str(resp)
        if isinstance(content, list):
            content = "".join(str(part) for part in content)
        return str(content)
    except Exception:
        return None


def call_llm_openai_fallback(messages: List[Dict[str, Any]]) -> Optional[str]:
    if not config.has_llm:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=config.AI_AUDIT_BASE_URL,
            api_key=config.AI_AUDIT_API_KEY,
        )
        resp = client.chat.completions.create(
            model=config.AI_AUDIT_MODEL,
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def parse_json_lenient(text: Optional[str]) -> Optional[Any]:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None
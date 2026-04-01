from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from ....infrastructure.ai.openai_compat import AIRequestError, OpenAICompatGateway
from ....infrastructure.demo.dynamic_sources import get_dynamic_options
from ....infrastructure.settings.system_settings import build_completion_provider_config


class ParamExtractionError(Exception):
    pass


def normalize_parameters(raw_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in raw_params or []:
        if not isinstance(item, dict):
            continue
        param_id = str(item.get("id") or item.get("name") or "").strip()
        if not param_id:
            continue
        interaction_mode = str(item.get("interaction_mode") or "form")
        if interaction_mode not in {"form", "chat"}:
            interaction_mode = "form"
        normalized.append(
            {
                "id": param_id,
                "label": str(item.get("label") or param_id),
                "required": bool(item.get("required")),
                "input_type": str(item.get("input_type") or item.get("type") or "free_text"),
                "interaction_mode": interaction_mode,
                "multi": bool(item.get("multi")),
                "options": list(item.get("options") or []),
                "source": str(item.get("source") or ""),
            }
        )
        if normalized[-1]["input_type"] == "dynamic" and not normalized[-1]["options"]:
            normalized[-1]["options"] = get_dynamic_options(normalized[-1]["source"])
    return normalized


def extract_params_from_message(
    *,
    db,
    gateway: OpenAICompatGateway,
    template_params: List[Dict[str, Any]],
    message: str,
) -> Dict[str, Any]:
    if not template_params:
        return {}
    config = build_completion_provider_config(db)
    param_lines = [
        {
            "id": p["id"],
            "label": p["label"],
            "required": p["required"],
            "input_type": p["input_type"],
            "multi": p["multi"],
            "options": p["options"],
            "source": p["source"],
        }
        for p in template_params
    ]
    prompt = "\n".join(
        [
            "你是参数抽取助手。根据用户输入提取出能确定的模板参数。",
            "只返回 JSON 对象，键为参数 id，值为参数值。",
            "未提及的参数不要输出。",
            "多值参数请输出数组。",
            "不要输出解释或 Markdown。",
            "模板参数定义(JSON):",
            json.dumps(param_lines, ensure_ascii=False, indent=2),
            f"用户输入: {message}",
        ]
    )
    try:
        response = gateway.chat_completion(
            config,
            [
                {"role": "system", "content": "你只输出 JSON，不要输出多余内容。"},
                {"role": "user", "content": prompt},
            ],
            temperature=min(config.temperature, 0.2),
            max_tokens=400,
        )
    except AIRequestError as exc:
        raise ParamExtractionError(str(exc)) from exc

    content = str(response.get("content") or "").strip()
    parsed = _extract_json_obj(content)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def validate_and_merge_params(
    *,
    template_params: List[Dict[str, Any]],
    collected: Dict[str, Any],
    updates: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    warnings: List[str] = []
    merged = dict(collected or {})
    for key, value in (updates or {}).items():
        if key not in {p["id"] for p in template_params}:
            continue
        normalized, warning = _normalize_param_value(template_params, key, value)
        if warning:
            warnings.append(warning)
            continue
        merged[key] = normalized
    return merged, warnings


def build_missing_required(
    template_params: List[Dict[str, Any]],
    collected: Dict[str, Any],
) -> List[str]:
    missing: List[str] = []
    for param in template_params:
        if not param.get("required"):
            continue
        pid = param["id"]
        val = collected.get(pid)
        if val is None or val == "" or (isinstance(val, list) and not val):
            missing.append(pid)
    return missing


def build_param_prompt(param: Dict[str, Any]) -> str:
    label = param.get("label") or param.get("id")
    input_type = param.get("input_type") or "free_text"
    options = _resolve_options(param)
    if input_type in {"enum", "dynamic"} and options:
        return f"请提供参数「{label}」的取值，可选：{', '.join(options)}。"
    return f"请提供参数「{label}」的取值。"


def _resolve_options(param: Dict[str, Any]) -> List[str]:
    input_type = param.get("input_type")
    if input_type == "enum":
        return [str(item) for item in param.get("options") or [] if str(item).strip()]
    if input_type == "dynamic":
        return get_dynamic_options(param.get("source") or "")
    return []


def _normalize_param_value(
    template_params: List[Dict[str, Any]],
    param_id: str,
    value: Any,
) -> Tuple[Any, str]:
    param = next((p for p in template_params if p["id"] == param_id), None)
    if not param:
        return value, ""

    input_type = param.get("input_type") or "free_text"
    multi = bool(param.get("multi"))
    options = _resolve_options(param)

    normalized = value
    if multi:
        normalized = _coerce_list(value)
    if input_type in {"enum", "dynamic"} and options:
        allowed = _match_options(normalized, options)
        if multi:
            if not allowed:
                return None, f"参数 {param_id} 的取值不在可选范围内。"
            return allowed, ""
        if isinstance(allowed, list):
            if not allowed:
                return None, f"参数 {param_id} 的取值不在可选范围内。"
            return allowed[0], ""
    return normalized, ""


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,\n，、/]+", value)
        return [part.strip() for part in parts if part.strip()]
    return [str(value)]


def _match_options(value: Any, options: List[str]) -> List[str]:
    if isinstance(value, list):
        return [match for v in value for match in _match_options(v, options)]
    val = str(value or "").strip()
    if not val:
        return []
    for option in options:
        if val == option:
            return [option]
    for option in options:
        if val.lower() == option.lower():
            return [option]
    return []


def _extract_json_obj(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

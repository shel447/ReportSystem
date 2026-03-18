from __future__ import annotations

from typing import Any, Dict, List


def apply_template_selection(
    state: Dict[str, Any],
    template: Dict[str, Any],
    *,
    confidence: float,
    locked: bool,
) -> Dict[str, Any]:
    report = state.get("report") or {}
    report["template_id"] = template.get("template_id") or ""
    report["template_name"] = template.get("name") or template.get("template_name") or ""
    report["template_confidence"] = float(confidence or 0)
    report["template_locked"] = bool(locked)
    state["report"] = report

    state["slots"] = {}
    missing = state.get("missing") or {}
    missing["required"] = []
    missing["optional"] = missing.get("optional") or []
    missing["pending_confirmation"] = []
    state["missing"] = missing

    flow = state.get("flow") or {}
    flow["in_report_flow"] = True
    flow["stage"] = "required_collection" if locked else "template_matching"
    state["flow"] = flow
    return state


def upsert_slots_from_params(
    state: Dict[str, Any],
    values: Dict[str, Any],
    param_defs: List[Dict[str, Any]],
    *,
    source: str,
    turn_index: int,
) -> Dict[str, Any]:
    slots = dict(state.get("slots") or {})
    valid_ids = {str(item.get("id")) for item in param_defs if isinstance(item, dict)}
    for key, value in (values or {}).items():
        if key not in valid_ids:
            continue
        slots[key] = {
            "value": value,
            "status": "confirmed" if source == "user" else "inferred",
            "source": source,
            "confidence": 1.0 if source == "user" else 0.8,
            "updated_turn": turn_index,
            "depends_on": [],
        }
    state["slots"] = slots
    return state


def build_ask_param_action(state: Dict[str, Any], params: List[Dict[str, Any]]) -> Dict[str, Any]:
    missing_required = list(state.get("missing", {}).get("required") or [])
    if not missing_required:
        return {}
    required_count = len([p for p in params if p.get("required")])
    collected_count = 0
    slots = state.get("slots") or {}
    for p in params:
        if not p.get("required"):
            continue
        if p.get("id") in slots:
            collected_count += 1

    target_id = missing_required[0]
    param = next((p for p in params if p.get("id") == target_id), {"id": target_id, "label": target_id})
    slot = slots.get(target_id) or {}
    return {
        "type": "ask_param",
        "template_name": state.get("report", {}).get("template_name", ""),
        "param": {
            "id": param.get("id"),
            "label": param.get("label") or param.get("id"),
            "input_type": param.get("input_type") or "free_text",
            "multi": bool(param.get("multi")),
            "options": list(param.get("options") or []),
        },
        "widget": _build_param_widget(param),
        "selected_values": _selected_values(slot.get("value")),
        "progress": {
            "collected": collected_count,
            "required": required_count,
        },
    }


def build_review_params_action(state: Dict[str, Any], params: List[Dict[str, Any]]) -> Dict[str, Any]:
    slots = state.get("slots") or {}
    collected = []
    for param in params:
        param_id = str(param.get("id") or "")
        if param_id not in slots:
            continue
        collected.append(
            {
                "id": param_id,
                "label": param.get("label") or param_id,
                "value": slots[param_id].get("value"),
                "required": bool(param.get("required")),
            }
        )
    return {
        "type": "review_params",
        "template_id": state.get("report", {}).get("template_id", ""),
        "template_name": state.get("report", {}).get("template_name", ""),
        "params": collected,
        "missing_required": list(state.get("missing", {}).get("required") or []),
    }


def rewind_slots_for_param(state: Dict[str, Any], params: List[Dict[str, Any]], target_param_id: str) -> Dict[str, Any]:
    slots = dict(state.get("slots") or {})
    ordered_ids = [str(item.get("id") or "") for item in params if str(item.get("id") or "")]
    if target_param_id not in ordered_ids:
        return state
    start = ordered_ids.index(target_param_id)
    for param_id in ordered_ids[start:]:
        slots.pop(param_id, None)
    state["slots"] = slots
    state["missing"] = state.get("missing") or {}
    state["missing"]["required"] = [
        param_id
        for param_id in ordered_ids[start:]
        if next((item for item in params if item.get("id") == param_id and item.get("required")), None)
    ]
    return state


def reset_slots(state: Dict[str, Any]) -> Dict[str, Any]:
    state["slots"] = {}
    missing = state.get("missing") or {}
    missing["required"] = []
    state["missing"] = missing
    return state


def _build_param_widget(param: Dict[str, Any]) -> Dict[str, Any]:
    input_type = str(param.get("input_type") or "free_text")
    multi = bool(param.get("multi"))
    if input_type in {"enum", "dynamic"}:
        return {"kind": "multi_select" if multi else "single_select"}
    if input_type == "date":
        return {"kind": "date"}
    return {"kind": "text"}


def _selected_values(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

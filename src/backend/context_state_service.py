from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from .chat_capability_service import ensure_task_state

CONTEXT_SCHEMA_VERSION = "ctx.v2"


def new_context_state(session_id: str, locale: str = "zh-CN") -> Dict[str, Any]:
    state = {
        "session": {
            "session_id": session_id,
            "locale": locale,
        },
        "active_task": {
            "task_id": "",
            "capability": "report_generation",
            "stage": "idle",
            "progress_state": {"has_progress": False},
            "context_payload": {},
        },
        "pending_switch": None,
        "flow": {
            "in_report_flow": False,
            "stage": "idle",
            "turn_index": 0,
            "last_action": None,
        },
        "report": {
            "template_id": "",
            "template_name": "",
            "template_confidence": 0.0,
            "template_locked": False,
        },
        "slots": {},
        "missing": {
            "required": [],
            "optional": [],
            "pending_confirmation": [],
        },
        "summary": {
            "facts": [],
            "open_question": "",
            "recent_turns": {},
        },
        "meta": {
            "session_id": session_id,
            "locale": locale,
            "updated_at": "",
            "schema_version": CONTEXT_SCHEMA_VERSION,
        },
    }
    return ensure_task_state(state, session_id=session_id, locale=locale)


def restore_state_from_history(history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for item in reversed(history or []):
        meta = item.get("meta") or {}
        if meta.get("type") != "context_state":
            continue
        if meta.get("schema_version") not in {"ctx.v1", CONTEXT_SCHEMA_VERSION}:
            continue
        state = meta.get("state")
        if isinstance(state, dict):
            copied = copy.deepcopy(state)
            session_id = str((copied.get("meta") or {}).get("session_id") or "")
            locale = str((copied.get("meta") or {}).get("locale") or "zh-CN")
            upgraded = ensure_task_state(copied, session_id=session_id, locale=locale)
            upgraded.setdefault("meta", {})["schema_version"] = CONTEXT_SCHEMA_VERSION
            return upgraded
    return None


def should_persist_state(
    previous_state: Optional[Dict[str, Any]],
    state: Dict[str, Any],
    *,
    turns_since_last: int,
    min_turns: int = 3,
) -> bool:
    if previous_state is None:
        return True
    if _value(previous_state, "active_task", "capability") != _value(state, "active_task", "capability"):
        return True
    if _value(previous_state, "active_task", "stage") != _value(state, "active_task", "stage"):
        return True
    if previous_state.get("pending_switch") != state.get("pending_switch"):
        return True
    if _value(previous_state, "flow", "stage") != _value(state, "flow", "stage"):
        return True
    if _value(previous_state, "report", "template_id") != _value(state, "report", "template_id"):
        return True
    if _sorted_list(previous_state, "missing", "required") != _sorted_list(state, "missing", "required"):
        return True
    if previous_state.get("slots") != state.get("slots"):
        return True
    return turns_since_last >= min_turns


def persist_state_to_history(
    history: List[Dict[str, Any]],
    state: Dict[str, Any],
    *,
    previous_state: Optional[Dict[str, Any]] = None,
    min_turns: int = 3,
) -> List[Dict[str, Any]]:
    snapshot = _latest_snapshot(history or [])
    turns_since_last = _turns_since(snapshot, state)
    if not should_persist_state(previous_state, state, turns_since_last=turns_since_last, min_turns=min_turns):
        return list(history or [])

    state_copy = copy.deepcopy(state)
    state_copy.setdefault("meta", {})["updated_at"] = _now_iso()
    message = {
        "role": "assistant",
        "content": "",
        "meta": {
            "type": "context_state",
            "schema_version": CONTEXT_SCHEMA_VERSION,
            "state": state_copy,
            "updated_at": state_copy.get("meta", {}).get("updated_at"),
        },
    }
    return list(history or []) + [message]


def compress_state(state: Dict[str, Any], *, max_facts: int = 6) -> Dict[str, Any]:
    summary = state.get("summary") or {}
    facts = list(summary.get("facts") or [])
    if len(facts) > max_facts:
        summary["facts"] = facts[:max_facts]
    state["summary"] = summary
    return state


def _latest_snapshot(history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for item in reversed(history or []):
        meta = item.get("meta") or {}
        if meta.get("type") != "context_state":
            continue
        state = meta.get("state")
        if isinstance(state, dict):
            return state
    return None


def _turns_since(snapshot: Optional[Dict[str, Any]], state: Dict[str, Any]) -> int:
    if not snapshot:
        return 999
    try:
        return int(_value(state, "flow", "turn_index")) - int(_value(snapshot, "flow", "turn_index"))
    except (TypeError, ValueError):
        return 999


def _value(state: Dict[str, Any], *path: str):
    current: Any = state
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _sorted_list(state: Dict[str, Any], *path: str) -> List[Any]:
    value = _value(state, *path)
    if isinstance(value, list):
        return sorted(value)
    return []


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

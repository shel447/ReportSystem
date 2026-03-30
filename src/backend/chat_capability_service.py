from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from .ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from .query_engine import QueryRequest, run_query
from .system_settings_service import build_completion_provider_config

CAPABILITY_REPORT = "report_generation"
CAPABILITY_SMART_QUERY = "smart_query"
CAPABILITY_FAULT_DIAGNOSIS = "fault_diagnosis"
VALID_CAPABILITIES = {CAPABILITY_REPORT, CAPABILITY_SMART_QUERY, CAPABILITY_FAULT_DIAGNOSIS}

_REPORT_KEYWORDS = ("报告", "报表", "模板", "生成报告", "制作")
_QUERY_KEYWORDS = ("查询", "统计", "多少", "top", "排行", "排名", "趋势", "kpi", "资产", "清单", "告警top")
_FAULT_KEYWORDS = ("故障", "异常", "定位", "根因", "排障", "掉站", "中断", "恢复")


def ensure_task_state(state: Dict[str, Any], *, session_id: str, locale: str = "zh-CN") -> Dict[str, Any]:
    state.setdefault("session", {"session_id": session_id, "locale": locale})
    session = state.get("session") or {}
    session["session_id"] = session_id
    session["locale"] = session.get("locale") or locale
    state["session"] = session

    flow = state.get("flow") or {}
    report = state.get("report") or {}
    active_task = state.get("active_task")
    if not isinstance(active_task, dict):
        active_task = {
            "task_id": "",
            "capability": _infer_legacy_capability(state),
            "stage": flow.get("stage") or "idle",
            "progress_state": {"has_progress": _has_report_progress(state)},
            "context_payload": {},
        }
    else:
        active_task["capability"] = str(active_task.get("capability") or _infer_legacy_capability(state))
        active_task["stage"] = str(active_task.get("stage") or flow.get("stage") or "idle")
        progress_state = active_task.get("progress_state")
        if not isinstance(progress_state, dict):
            progress_state = {"has_progress": False}
        progress_state["has_progress"] = bool(progress_state.get("has_progress") or _has_report_progress(state))
        active_task["progress_state"] = progress_state
        active_task["context_payload"] = active_task.get("context_payload") or {}
    state["active_task"] = active_task
    state["pending_switch"] = state.get("pending_switch") if isinstance(state.get("pending_switch"), dict) else None
    state.setdefault("report", report)
    state.setdefault("slots", {})
    state.setdefault("missing", {"required": [], "optional": [], "pending_confirmation": []})
    state.setdefault("summary", {"facts": [], "open_question": "", "recent_turns": {}})
    state.setdefault("meta", {})
    state["meta"]["session_id"] = session_id
    state["meta"]["locale"] = state["meta"].get("locale") or locale
    return state


def detect_capability(
    *,
    message: str,
    preferred_capability: Optional[str],
    current_capability: str,
    current_stage: str,
    has_report_commands: bool,
) -> str:
    if preferred_capability in VALID_CAPABILITIES:
        return preferred_capability
    if has_report_commands:
        return CAPABILITY_REPORT

    normalized = str(message or "").strip().lower()
    if not normalized:
        return current_capability or CAPABILITY_REPORT

    report_hits = _keyword_hits(normalized, _REPORT_KEYWORDS)
    query_hits = _keyword_hits(normalized, _QUERY_KEYWORDS)
    fault_hits = _keyword_hits(normalized, _FAULT_KEYWORDS)

    if current_capability == CAPABILITY_REPORT and current_stage in {"required_collection", "review_ready", "outline_review"}:
        if max(query_hits, fault_hits) == 0:
            return CAPABILITY_REPORT

    if fault_hits > max(query_hits, report_hits):
        return CAPABILITY_FAULT_DIAGNOSIS
    if query_hits > max(fault_hits, report_hits):
        return CAPABILITY_SMART_QUERY
    if report_hits > 0:
        return CAPABILITY_REPORT
    return current_capability or CAPABILITY_REPORT


def has_substantial_progress(state: Dict[str, Any]) -> bool:
    active_task = state.get("active_task") or {}
    capability = str(active_task.get("capability") or CAPABILITY_REPORT)
    stage = str(active_task.get("stage") or "idle")
    if capability == CAPABILITY_REPORT:
        return _has_report_progress(state)
    if stage not in {"", "idle"}:
        return True
    payload = active_task.get("context_payload") or {}
    return bool(payload.get("last_user_message") or payload.get("clarification_question") or payload.get("result_summary"))


def build_confirm_task_switch_action(state: Dict[str, Any]) -> Dict[str, Any]:
    pending = state.get("pending_switch") or {}
    return {
        "type": "confirm_task_switch",
        "from_capability": pending.get("from_capability") or CAPABILITY_REPORT,
        "to_capability": pending.get("to_capability") or CAPABILITY_SMART_QUERY,
        "reason": pending.get("reason") or "检测到新的任务意图，这会结束当前任务。",
    }


def clear_current_task_state(state: Dict[str, Any]) -> Dict[str, Any]:
    state["flow"] = {
        "in_report_flow": False,
        "stage": "idle",
        "turn_index": int((state.get("flow") or {}).get("turn_index") or 0),
        "last_action": None,
    }
    state["report"] = {
        "template_id": "",
        "template_name": "",
        "template_confidence": 0.0,
        "template_locked": False,
        "pending_outline_review": [],
        "outline_review_warnings": [],
    }
    state["slots"] = {}
    state["missing"] = {
        "required": [],
        "optional": [],
        "pending_confirmation": [],
    }
    state["summary"] = {
        "facts": [],
        "open_question": "",
        "recent_turns": {},
    }
    state["pending_switch"] = None
    return state


def set_active_task(
    state: Dict[str, Any],
    *,
    capability: str,
    stage: str,
    progress_state: Optional[Dict[str, Any]] = None,
    context_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    active_task = state.get("active_task") or {}
    active_task["capability"] = capability
    active_task["stage"] = stage
    active_task["progress_state"] = progress_state or {"has_progress": stage not in {"", "idle"}}
    active_task["context_payload"] = context_payload or {}
    state["active_task"] = active_task
    return state


def sync_report_task_state(state: Dict[str, Any]) -> Dict[str, Any]:
    flow = state.get("flow") or {}
    report = state.get("report") or {}
    context_payload = {
        "template_id": report.get("template_id") or "",
        "template_name": report.get("template_name") or "",
        "slot_ids": sorted((state.get("slots") or {}).keys()),
        "missing_required": list((state.get("missing") or {}).get("required") or []),
    }
    return set_active_task(
        state,
        capability=CAPABILITY_REPORT,
        stage=str(flow.get("stage") or "idle"),
        progress_state={"has_progress": _has_report_progress(state)},
        context_payload=context_payload,
    )


def handle_smart_query_turn(
    *,
    db: Session,
    gateway: OpenAICompatGateway,
    message: str,
    state: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]], Dict[str, Any]]:
    text = str(message or "").strip()
    if len(text) < 6:
        return (
            "请说明想查询的指标、对象和时间范围，例如“查询昨天华东区域告警 TOP10 站点”。",
            None,
            {
                "stage": "clarifying",
                "progress_state": {"has_progress": True},
                "context_payload": {"clarification_question": "请说明想查询的指标、对象和时间范围。"},
            },
        )

    config = build_completion_provider_config(db)
    result = run_query(
        gateway=gateway,
        config=config,
        request=QueryRequest(
            nl_request=text,
            template_context={"name": "智能问数"},
            section={"title": "智能问数", "description": text},
            params={},
        ),
    )
    reply = _format_query_reply(result.row_count, result.sample_rows)
    return (
        reply,
        None,
        {
            "stage": "answered",
            "progress_state": {"has_progress": True},
            "context_payload": {
                "last_user_message": text,
                "row_count": result.row_count,
                "sample_rows": deepcopy(result.sample_rows),
                "compiled_sql": result.compiled_sql,
                "result_summary": reply,
            },
        },
    )


def handle_fault_diagnosis_turn(
    *,
    db: Session,
    gateway: OpenAICompatGateway,
    message: str,
    state: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]], Dict[str, Any]]:
    text = str(message or "").strip()
    if len(text) < 6:
        reply = "请补充故障对象、现象和时间范围，例如“华东区域 1 号站点 10:30 开始掉站”。"
        return (
            reply,
            None,
            {
                "stage": "clarifying",
                "progress_state": {"has_progress": True},
                "context_payload": {"clarification_question": reply},
            },
        )

    config = build_completion_provider_config(db)
    response = gateway.chat_completion(
        config,
        [
            {
                "role": "system",
                "content": "你是智能故障助手。请基于用户描述给出初步诊断思路、重点排查项和下一步建议，输出简洁中文。",
            },
            {"role": "user", "content": text},
        ],
        temperature=min(config.temperature, 0.2),
        max_tokens=280,
    )
    reply = response["content"]
    return (
        reply,
        None,
        {
            "stage": "answered",
            "progress_state": {"has_progress": True},
            "context_payload": {
                "last_user_message": text,
                "result_summary": reply,
            },
        },
    )


def capability_label(capability: str) -> str:
    return {
        CAPABILITY_REPORT: "制作报告",
        CAPABILITY_SMART_QUERY: "智能问数",
        CAPABILITY_FAULT_DIAGNOSIS: "智能故障",
    }.get(capability, capability or "当前任务")


def _infer_legacy_capability(state: Dict[str, Any]) -> str:
    flow = state.get("flow") or {}
    report = state.get("report") or {}
    if flow.get("in_report_flow") or report.get("template_id") or report.get("template_locked"):
        return CAPABILITY_REPORT
    return CAPABILITY_REPORT


def _has_report_progress(state: Dict[str, Any]) -> bool:
    report = state.get("report") or {}
    flow = state.get("flow") or {}
    if report.get("template_locked") or report.get("template_id"):
        return True
    if state.get("slots"):
        return True
    return str(flow.get("stage") or "idle") not in {"", "idle", "template_matching"}


def _keyword_hits(message: str, keywords: tuple[str, ...]) -> int:
    hits = 0
    for keyword in keywords:
        if keyword and keyword.lower() in message:
            hits += 1
    return hits


def _format_query_reply(row_count: int, sample_rows: list[dict[str, Any]]) -> str:
    if row_count <= 0:
        return "已完成查询，但当前条件下没有返回数据。"
    preview = sample_rows[:3]
    lines = []
    for index, row in enumerate(preview, start=1):
        fragments = [f"{key}={value}" for key, value in row.items()]
        if fragments:
            lines.append(f"{index}. " + "，".join(fragments))
    summary = f"已完成查询，共返回 {row_count} 条结果。"
    if not lines:
        return summary
    return summary + "\n" + "\n".join(lines)

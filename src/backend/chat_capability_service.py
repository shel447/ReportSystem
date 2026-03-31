from __future__ import annotations

from copy import deepcopy
import json
import re
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
_QUERY_KEYWORDS = ("查询", "统计", "多少", "top", "排行", "排名", "趋势", "kpi", "资产", "清单", "告警top", "想知道", "哪些", "哪个", "最多", "最少", "前十", "前三")
_FAULT_KEYWORDS = ("故障", "异常", "定位", "根因", "排障", "掉站", "中断", "恢复", "出问题", "有问题", "退服", "离线", "不通", "波动")
_QUERY_PATTERNS = (
    r"想知道",
    r"看下",
    r"看一下",
    r"帮我看",
    r"最多",
    r"最少",
    r"前\d+",
    r"前三",
    r"前十",
    r"top\s*\d*",
    r"哪些",
    r"哪个",
    r"多少",
)
_FAULT_PATTERNS = (
    r"出问题了?",
    r"有问题",
    r"是不是.*(异常|故障|掉站|中断|退服)",
    r"掉站",
    r"退服",
    r"离线",
    r"不通",
    r"中断",
    r"故障",
    r"异常",
    r"排查",
    r"定位",
    r"根因",
    r"恢复",
    r"波动",
)
_QUERY_DOMAIN_TERMS = ("区域", "站点", "小区", "设备", "告警", "工单", "巡检", "资产", "kpi", "流量")
_FAULT_DOMAIN_TERMS = ("站点", "小区", "设备", "链路", "传输", "电源", "告警", "退服", "掉站", "中断")
_REPORT_CANCEL_PHRASES = ("先别做报告", "先不做报告", "别做报告了", "不做报告了", "暂停报告", "先别生成报告")
_CAPABILITY_SWITCH_VERBS = ("切换到", "切到", "改成", "转到", "改为", "换成")
_CAPABILITY_SWITCH_TERMS = {
    CAPABILITY_SMART_QUERY: ("智能问数", "问数"),
    CAPABILITY_FAULT_DIAGNOSIS: ("智能故障", "故障分析", "排障", "故障诊断"),
    CAPABILITY_REPORT: ("制作报告", "报告生成", "做报告"),
}


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

    report_hits = _report_signal_score(normalized)
    query_hits = _query_signal_score(normalized)
    fault_hits = _fault_signal_score(normalized)

    if current_capability == CAPABILITY_REPORT and current_stage in {"required_collection", "review_ready", "outline_review"}:
        if max(query_hits, fault_hits) < 2:
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
    query_debug = deepcopy(result.debug or {})
    if not result.success:
        reply = _format_query_failure_reply(query_debug)
        return (
            reply,
            None,
            {
                "stage": "clarifying",
                "progress_state": {"has_progress": True},
                "context_payload": {
                    "last_user_message": text,
                    "query_debug": query_debug,
                    "compiled_sql": result.compiled_sql,
                    "clarification_question": reply,
                    "result_summary": reply,
                },
            },
        )

    reply = _format_query_reply(text, result.row_count, result.sample_rows, query_debug)
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
                "query_debug": query_debug,
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
                "content": (
                    "你是智能故障助手。请根据用户描述输出 JSON，不要输出解释、不要 Markdown。"
                    'JSON 字段固定为 symptom_summary, judgment, possible_causes, next_steps, missing_info, risk_level。'
                    "possible_causes/next_steps/missing_info 必须是字符串数组；risk_level 只能是 high/medium/low。"
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=min(config.temperature, 0.2),
        max_tokens=360,
    )
    diagnosis = _parse_fault_diagnosis_payload(response["content"])
    reply = _format_fault_diagnosis_reply(diagnosis)
    stage = "clarifying" if diagnosis["missing_info"] else "answered"
    return (
        reply,
        None,
        {
            "stage": stage,
            "progress_state": {"has_progress": True},
            "context_payload": {
                "last_user_message": text,
                "symptom_summary": diagnosis["symptom_summary"],
                "judgment": diagnosis["judgment"],
                "possible_causes": diagnosis["possible_causes"],
                "next_steps": diagnosis["next_steps"],
                "missing_info": diagnosis["missing_info"],
                "risk_level": diagnosis["risk_level"],
                "result_summary": reply,
                **({"clarification_question": reply} if diagnosis["missing_info"] else {}),
            },
        },
    )


def capability_label(capability: str) -> str:
    return {
        CAPABILITY_REPORT: "制作报告",
        CAPABILITY_SMART_QUERY: "智能问数",
        CAPABILITY_FAULT_DIAGNOSIS: "智能故障",
    }.get(capability, capability or "当前任务")


def is_explicit_capability_switch_request(message: str, target_capability: str) -> bool:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return False
    if any(phrase in normalized for phrase in _REPORT_CANCEL_PHRASES):
        return True
    terms = _CAPABILITY_SWITCH_TERMS.get(target_capability, ())
    return any(term.lower() in normalized for term in terms) and any(
        verb in normalized for verb in _CAPABILITY_SWITCH_VERBS
    )


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


def _report_signal_score(message: str) -> int:
    score = _keyword_hits(message, _REPORT_KEYWORDS)
    if any(phrase in message for phrase in _REPORT_CANCEL_PHRASES):
        score = max(0, score - 2)
    return score


def _query_signal_score(message: str) -> int:
    score = _keyword_hits(message, _QUERY_KEYWORDS)
    score += _pattern_hits(message, _QUERY_PATTERNS)
    if any(term in message for term in _QUERY_DOMAIN_TERMS) and any(
        phrase in message for phrase in ("想知道", "多少", "哪些", "哪个", "最多", "最少", "前", "top", "统计", "查询", "趋势")
    ):
        score += 1
    return score


def _fault_signal_score(message: str) -> int:
    score = _keyword_hits(message, _FAULT_KEYWORDS)
    score += _pattern_hits(message, _FAULT_PATTERNS)
    if any(term in message for term in _FAULT_DOMAIN_TERMS) and any(
        phrase in message for phrase in ("故障", "异常", "出问题", "有问题", "掉站", "退服", "中断", "不通", "排查", "定位", "根因")
    ):
        score += 1
    return score


def _pattern_hits(message: str, patterns: tuple[str, ...]) -> int:
    hits = 0
    for pattern in patterns:
        if re.search(pattern, message, flags=re.IGNORECASE):
            hits += 1
    return hits


def _format_query_reply(
    nl_request: str,
    row_count: int,
    sample_rows: list[dict[str, Any]],
    query_debug: Dict[str, Any],
) -> str:
    query_spec = query_debug.get("query_spec") if isinstance(query_debug.get("query_spec"), dict) else {}
    intent = str(query_spec.get("intent") or "").strip() or _summarize_query_request(nl_request)
    warnings = [str(item).strip() for item in (query_spec.get("warnings") or []) if str(item).strip()]
    lines = [
        "已完成智能问数。",
        f"查询口径：{intent}",
        f"结果概览：共返回 {row_count} 条结果。",
    ]
    preview_lines = _format_preview_rows(sample_rows)
    if preview_lines:
        lines.append("核心结果：")
        lines.extend(preview_lines)
    if warnings:
        lines.append("口径说明：")
        lines.extend([f"- {item}" for item in warnings[:3]])
    return "\n".join(lines)


def _format_query_failure_reply(query_debug: Dict[str, Any]) -> str:
    query_spec = query_debug.get("query_spec") if isinstance(query_debug.get("query_spec"), dict) else {}
    warnings = [str(item).strip() for item in (query_spec.get("warnings") or []) if str(item).strip()]
    error_message = str(query_debug.get("error_message") or "").strip()
    lines = [
        "这次智能问数没有成功执行。",
        "请补充更明确的查询对象、指标和时间范围后再试。",
    ]
    if warnings:
        lines.append("当前缺口：")
        lines.extend([f"- {item}" for item in warnings[:3]])
    elif error_message:
        lines.append(f"失败原因：{error_message}")
    return "\n".join(lines)


def _format_preview_rows(sample_rows: list[dict[str, Any]]) -> list[str]:
    preview = sample_rows[:3]
    lines: list[str] = []
    for index, row in enumerate(preview, start=1):
        fragments = [f"{key}={value}" for key, value in row.items()]
        if fragments:
            lines.append(f"- {index}. " + "，".join(fragments))
    return lines


def _summarize_query_request(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    if len(normalized) <= 24:
        return normalized
    return normalized[:24].rstrip() + "..."


def _parse_fault_diagnosis_payload(text: str) -> Dict[str, Any]:
    content = str(text or "").strip()
    try:
        payload = json.loads(_extract_json_block(content))
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    symptom_summary = str(payload.get("symptom_summary") or "").strip() or content
    judgment = str(payload.get("judgment") or "").strip()
    possible_causes = _ensure_text_list(payload.get("possible_causes"))
    next_steps = _ensure_text_list(payload.get("next_steps"))
    missing_info = _ensure_text_list(payload.get("missing_info"))
    risk_level = str(payload.get("risk_level") or "medium").strip().lower()
    if risk_level not in {"high", "medium", "low"}:
        risk_level = "medium"
    return {
        "symptom_summary": symptom_summary,
        "judgment": judgment,
        "possible_causes": possible_causes,
        "next_steps": next_steps,
        "missing_info": missing_info,
        "risk_level": risk_level,
    }


def _format_fault_diagnosis_reply(diagnosis: Dict[str, Any]) -> str:
    risk_label = {"high": "高", "medium": "中", "low": "低"}.get(str(diagnosis.get("risk_level") or "medium"), "中")
    lines = [
        "已进入智能故障分析。",
        f"故障现象：{diagnosis.get('symptom_summary') or '待补充'}",
        f"初步判断：{diagnosis.get('judgment') or '当前信息不足，先给出通用排查方向。'}",
        f"风险等级：{risk_label}",
    ]
    possible_causes = diagnosis.get("possible_causes") or []
    if possible_causes:
        lines.append("可能原因：")
        lines.extend([f"- {item}" for item in possible_causes[:3]])
    next_steps = diagnosis.get("next_steps") or []
    if next_steps:
        lines.append("下一步建议：")
        lines.extend([f"- {item}" for item in next_steps[:3]])
    missing_info = diagnosis.get("missing_info") or []
    if missing_info:
        lines.append("建议补充：")
        lines.extend([f"- {item}" for item in missing_info[:3]])
    return "\n".join(lines)


def _extract_json_block(text: str) -> str:
    content = str(text or "").strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced[0].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        return content[start : end + 1]
    return content


def _ensure_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .chat_flow_service import apply_template_selection, build_review_outline_action, upsert_slots_from_params
from .chat_session_service import (
    ensure_session_metadata,
    serialize_chat_session_detail,
    truncate_text,
    visible_chat_messages,
)
from .context_state_service import new_context_state, persist_state_to_history, restore_state_from_history
from .models import ChatSession, ReportTemplate, TemplateInstance, gen_id
from .outline_review_service import build_pending_outline_review, merge_outline_override
from .param_dialog_service import normalize_parameters

FORK_SUFFIX_LENGTH = 6
FORK_ASSISTANT_REPLY = "参数已确认，请检查报告大纲。"
UPDATE_ASSISTANT_REPLY = "已恢复确认大纲，请继续修改。"


def build_visible_message_payload(
    role: str,
    content: str,
    *,
    action: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    from datetime import datetime, timezone

    payload: Dict[str, Any] = {
        "role": role,
        "content": content,
        "message_id": gen_id(),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    if action:
        payload["action"] = action
    return payload


def fork_session_from_message(
    db: Session,
    *,
    source_session: ChatSession,
    source_message_id: str,
) -> Dict[str, Any]:
    ensure_session_metadata(source_session)
    flag_modified(source_session, "messages")
    db.commit()
    db.refresh(source_session)

    source_messages = list(source_session.messages or [])
    anchor_index = _find_message_index(source_messages, source_message_id)
    if anchor_index < 0:
        raise HTTPException(status_code=404, detail="Source message not found")

    anchor = source_messages[anchor_index]
    if anchor.get("role") == "user":
        copied_messages = deepcopy(source_messages[: anchor_index + 1])
        draft_message = str(anchor.get("content") or "")
    else:
        end_index = _extend_with_context_state(source_messages, anchor_index)
        copied_messages = deepcopy(source_messages[:end_index])
        draft_message = ""

    fork_session_id = gen_id()
    restored_state = restore_state_from_history(copied_messages) or new_context_state(fork_session_id)
    restored_state.setdefault("meta", {})["session_id"] = fork_session_id
    copied_messages = persist_state_to_history(copied_messages, restored_state, previous_state=None, min_turns=3)

    fork_meta = {
        "source_kind": "session_message",
        "source_session_id": source_session.session_id,
        "source_message_id": source_message_id,
        "source_title": source_session.title or "未命名会话",
        "source_preview": _message_preview(anchor),
    }
    forked = ChatSession(
        session_id=fork_session_id,
        user_id=source_session.user_id or "default",
        title=_fork_title(source_session.title or "未命名会话"),
        messages=copied_messages,
        fork_meta=fork_meta,
        matched_template_id=(restored_state.get("report") or {}).get("template_id") or None,
    )
    db.add(forked)
    db.commit()
    db.refresh(forked)

    payload = serialize_chat_session_detail(forked)
    payload["draft_message"] = draft_message
    return payload


def fork_session_from_template_instance(
    db: Session,
    *,
    template_instance: TemplateInstance,
) -> Dict[str, Any]:
    return _build_outline_review_session_from_template_instance(
        db,
        template_instance=template_instance,
        allowed_capture_stages={"outline_saved", "generation_baseline"},
        reply_text=FORK_ASSISTANT_REPLY,
        source_kind="template_instance",
        source_preview=_template_instance_preview(template_instance),
        source_report_instance_id=None,
    )


def update_session_from_template_instance(
    db: Session,
    *,
    template_instance: TemplateInstance,
) -> Dict[str, Any]:
    return _build_outline_review_session_from_template_instance(
        db,
        template_instance=template_instance,
        allowed_capture_stages={"outline_saved", "outline_confirmed", "generation_baseline"},
        reply_text=UPDATE_ASSISTANT_REPLY,
        source_kind="update_from_instance",
        source_preview=_template_instance_preview(template_instance, for_update=True),
        source_report_instance_id=template_instance.report_instance_id or None,
    )


def _build_outline_review_session_from_template_instance(
    db: Session,
    *,
    template_instance: TemplateInstance,
    allowed_capture_stages: set[str],
    reply_text: str,
    source_kind: str,
    source_preview: str,
    source_report_instance_id: str | None,
) -> Dict[str, Any]:
    capture_stage = str(template_instance.capture_stage or "")
    if capture_stage not in allowed_capture_stages:
        raise HTTPException(status_code=409, detail="Only outline review snapshots can be forked")

    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_instance.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_payload = {
        "template_id": template.template_id,
        "name": template.name,
        "scene": template.scene or template.scenario,
    }
    template_params = normalize_parameters((template.parameters or []) if template.parameters else (template.content_params or []))
    base_outline, build_warnings = build_pending_outline_review(
        _template_entity_from_model(template),
        deepcopy(template_instance.input_params_snapshot or {}),
    )
    restored_outline = merge_outline_override(base_outline, template_instance.outline_snapshot or [])
    warnings = _dedupe_strings(list(template_instance.warnings or []) + list(build_warnings or []))

    fork_session_id = gen_id()
    state = new_context_state(fork_session_id)
    state = apply_template_selection(state, template_payload, confidence=1.0, locked=True)
    state = upsert_slots_from_params(
        state,
        deepcopy(template_instance.input_params_snapshot or {}),
        template_params,
        source="user",
        turn_index=0,
    )
    state.setdefault("missing", {})["required"] = []
    state["flow"]["stage"] = "outline_review"
    state["report"]["pending_outline_review"] = restored_outline
    state["report"]["outline_review_warnings"] = warnings

    action = build_review_outline_action(state, template_params)
    messages = [build_visible_message_payload("assistant", reply_text, action=action)]
    messages = persist_state_to_history(messages, state, previous_state=None, min_turns=3)

    fork_meta = {
        "source_kind": source_kind,
        "source_template_instance_id": template_instance.template_instance_id,
        "source_report_instance_id": source_report_instance_id,
        "source_title": template_instance.template_name or template.name or "确认大纲",
        "source_preview": source_preview,
    }
    forked = ChatSession(
        session_id=fork_session_id,
        user_id="default",
        title=_fork_title(template_instance.template_name or template.name or "确认大纲"),
        messages=messages,
        fork_meta=fork_meta,
        matched_template_id=template.template_id,
    )
    db.add(forked)
    db.commit()
    db.refresh(forked)

    payload = serialize_chat_session_detail(forked)
    payload["draft_message"] = ""
    return payload


def _template_instance_preview(template_instance: TemplateInstance, *, for_update: bool = False) -> str:
    capture_stage = str(template_instance.capture_stage or "")
    if for_update:
        if capture_stage == "outline_confirmed":
            return "确认大纲"
        return "生成基线"
    return "确认大纲" if capture_stage == "generation_baseline" else "已保存大纲"


def _find_message_index(messages: List[Dict[str, Any]], message_id: str) -> int:
    for index, item in enumerate(messages or []):
        if str(item.get("message_id") or "") == message_id:
            return index
    return -1


def _extend_with_context_state(messages: List[Dict[str, Any]], anchor_index: int) -> int:
    end_index = anchor_index + 1
    while end_index < len(messages):
        meta = (messages[end_index].get("meta") or {}) if isinstance(messages[end_index], dict) else {}
        if meta.get("type") != "context_state":
            break
        end_index += 1
    return end_index


def _message_preview(message: Dict[str, Any]) -> str:
    content = str(message.get("content") or "").strip()
    if content:
        return truncate_text(content, 48)
    action = message.get("action") if isinstance(message.get("action"), dict) else {}
    action_type = str(action.get("type") or "").strip()
    if action_type:
        return action_type
    return "消息"


def _fork_title(source_title: str) -> str:
    return f"{(source_title or '未命名会话').strip()} copy_{uuid4().hex[:FORK_SUFFIX_LENGTH]}"


def _dedupe_strings(items: List[str]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


def _template_entity_from_model(template: ReportTemplate):
    from .domain.reporting.entities import ReportTemplateEntity

    return ReportTemplateEntity(
        template_id=template.template_id,
        name=template.name,
        description=template.description or "",
        report_type=template.report_type or "",
        scenario=template.scenario or "",
        template_type=template.template_type or "",
        scene=template.scene or "",
        match_keywords=template.match_keywords or [],
        content_params=template.content_params or [],
        version=template.version or "1.0",
        outline=template.outline or [],
        parameters=template.parameters or [],
        sections=template.sections or [],
        schema_version=template.schema_version or "",
    )

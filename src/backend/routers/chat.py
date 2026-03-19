"""对话交互路由"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ..chat_flow_service import (
    apply_template_selection,
    build_ask_param_action,
    build_review_outline_action,
    build_review_params_action,
    reset_slots,
    rewind_slots_for_param,
    upsert_slots_from_params,
)
from ..chat_response_service import generate_chat_reply
from ..context_state_service import compress_state, new_context_state, persist_state_to_history, restore_state_from_history
from ..database import get_db
from ..document_service import create_markdown_document, serialize_document
from ..infrastructure.dependencies import build_instance_application_service
from ..models import ChatSession, ReportTemplate, gen_id
from ..outline_review_service import build_pending_outline_review, merge_outline_override
from ..param_dialog_service import (
    build_missing_required,
    build_param_prompt,
    extract_params_from_message,
    normalize_parameters,
    ParamExtractionError,
    validate_and_merge_params,
)
from ..system_settings_service import get_settings_payload
from ..template_instance_service import capture_template_instance
from ..template_index_service import TemplateIndexUnavailableError, match_templates

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str = ""
    session_id: str = ""
    selected_template_id: Optional[str] = None
    param_id: Optional[str] = None
    param_value: Optional[Any] = None
    param_values: Optional[List[str]] = None
    command: Optional[str] = None
    target_param_id: Optional[str] = None
    outline_override: Optional[List[Dict[str, Any]]] = None


@router.post("")
def send_message(data: ChatMessage, db: Session = Depends(get_db)):
    session = None
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.session_id == data.session_id).first()
    if not session:
        session = ChatSession(session_id=gen_id(), messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    messages = list(session.messages or [])
    user_message = str(data.message or "")
    if user_message or data.param_id or data.selected_template_id or data.command:
        messages.append({"role": "user", "content": user_message})

    state = restore_state_from_history(messages) or new_context_state(session.session_id)
    state.setdefault("meta", {})["session_id"] = session.session_id
    flow = state.get("flow") or {}
    flow["turn_index"] = int(flow.get("turn_index") or 0) + 1
    state["flow"] = flow

    reply = ""
    action = None
    gateway = OpenAICompatGateway()
    templates_count = db.query(ReportTemplate).count()
    settings = get_settings_payload(db)

    previous_state = deepcopy(state)

    if templates_count == 0:
        reply = "当前还没有可用模板，请先在“报告模板”中创建报告模板。"
    elif not settings["is_ready"]:
        reply = "系统设置尚未完成，请先到“系统设置”中配置 Completion 与 Embedding 接口，再开始对话生成。"
    else:
        try:
            template: ReportTemplate | None = None
            template_locked = bool(state.get("report", {}).get("template_locked"))

            if data.selected_template_id:
                template = db.query(ReportTemplate).filter(
                    ReportTemplate.template_id == data.selected_template_id
                ).first()
                if not template:
                    raise HTTPException(status_code=404, detail="Selected template not found")
                state = apply_template_selection(
                    state,
                    {
                        "template_id": template.template_id,
                        "name": template.name,
                        "scene": template.scene or template.scenario,
                    },
                    confidence=1.0,
                    locked=True,
                )
                template_locked = True
            elif template_locked:
                template_id = state.get("report", {}).get("template_id")
                if template_id:
                    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
            else:
                matched = match_templates(db, user_message, gateway)
                if matched["auto_match"]:
                    template = db.query(ReportTemplate).filter(
                        ReportTemplate.template_id == matched["best"]["template_id"]
                    ).first()
                    if not template:
                        raise HTTPException(status_code=404, detail="Matched template not found")
                    state = apply_template_selection(
                        state,
                        {
                            "template_id": template.template_id,
                            "name": template.name,
                            "scene": template.scene or template.scenario,
                        },
                        confidence=matched["best"]["score"],
                        locked=True,
                    )
                    template_locked = True
                else:
                    reply = generate_chat_reply(db, gateway, user_message, candidates=matched["candidates"])
                    action = {
                        "type": "show_template_candidates",
                        "candidates": [
                            {
                                "template_id": item["template_id"],
                                "template_name": item["template_name"],
                                "scenario": item.get("scenario", ""),
                                "description": item.get("description", ""),
                                "report_type": item.get("report_type", ""),
                                "template_type": item.get("template_type", ""),
                                "score": item["score"],
                                "score_label": item["score_label"],
                                "match_reasons": item["match_reasons"],
                            }
                            for item in matched["candidates"]
                        ],
                    }
                    flow = state.get("flow") or {}
                    flow["stage"] = "template_matching"
                    state["flow"] = flow

            if template_locked and template is not None:
                template_params = normalize_parameters(
                    (template.parameters or []) if template.parameters else (template.content_params or [])
                )
                if data.command == "reset_params":
                    state = reset_slots(state)
                    report = state.get("report") or {}
                    report["pending_outline_review"] = []
                    report["outline_review_warnings"] = []
                    state["report"] = report
                elif data.command == "edit_param" and data.target_param_id:
                    state = rewind_slots_for_param(state, template_params, data.target_param_id)
                    report = state.get("report") or {}
                    report["pending_outline_review"] = []
                    report["outline_review_warnings"] = []
                    state["report"] = report

                collected = {key: slot.get("value") for key, slot in (state.get("slots") or {}).items()}
                updates: Dict[str, Any] = {}
                source = "llm"
                if data.param_id:
                    if data.param_values is not None:
                        updates = {data.param_id: data.param_values}
                    else:
                        updates = {data.param_id: data.param_value}
                    source = "user"
                elif user_message and not data.command:
                    updates = extract_params_from_message(
                        db=db,
                        gateway=gateway,
                        template_params=template_params,
                        message=user_message,
                    )

                merged, warnings = validate_and_merge_params(
                    template_params=template_params,
                    collected=collected,
                    updates=updates,
                )
                if updates:
                    state = upsert_slots_from_params(
                        state,
                        merged,
                        template_params,
                        source=source,
                        turn_index=state.get("flow", {}).get("turn_index", 0),
                    )

                missing_required = build_missing_required(template_params, merged)
                missing = state.get("missing") or {}
                missing["required"] = missing_required
                state["missing"] = missing

                if data.command == "edit_param" and not data.target_param_id and (state.get("flow") or {}).get("stage") == "outline_review":
                    reply = "请确认需要调整的参数。"
                    action = build_review_params_action(state, template_params)
                    report = state.get("report") or {}
                    report["pending_outline_review"] = []
                    report["outline_review_warnings"] = []
                    state["report"] = report
                    flow = state.get("flow") or {}
                    flow["stage"] = "review_ready"
                    state["flow"] = flow
                elif data.command in {"prepare_outline_review", "confirm_generation"}:
                    if missing_required:
                        action = build_ask_param_action(state, template_params)
                        target_id = action.get("param", {}).get("id") if action else None
                        prompt = ""
                        if target_id:
                            target_param = next((p for p in template_params if p.get("id") == target_id), None)
                            if target_param:
                                prompt = build_param_prompt(target_param)
                        reply = prompt or "请先补充完所有必填参数。"
                        flow = state.get("flow") or {}
                        flow["stage"] = "required_collection"
                        state["flow"] = flow
                    else:
                        outline_review, outline_warnings = build_pending_outline_review(
                            build_instance_application_service(db).template_reader.get_by_id(template.template_id),
                            merged,
                        )
                        report = state.get("report") or {}
                        report["pending_outline_review"] = outline_review
                        report["outline_review_warnings"] = outline_warnings
                        state["report"] = report
                        reply = "参数已确认，请检查报告大纲。"
                        action = build_review_outline_action(state, template_params)
                        flow = state.get("flow") or {}
                        flow["stage"] = "outline_review"
                        state["flow"] = flow
                        summary = state.get("summary") or {}
                        summary["open_question"] = reply
                        state["summary"] = summary
                elif data.command == "edit_outline":
                    report = state.get("report") or {}
                    pending_outline = report.get("pending_outline_review") or []
                    report["pending_outline_review"] = merge_outline_override(pending_outline, data.outline_override or [])
                    capture_template_instance(
                        db,
                        template=template,
                        session_id=session.session_id,
                        capture_stage="outline_saved",
                        input_params_snapshot=merged,
                        outline_snapshot=report["pending_outline_review"],
                        warnings=report.get("outline_review_warnings") or [],
                        created_by=session.user_id or "system",
                    )
                    state["report"] = report
                    reply = "报告大纲已更新，请继续确认。"
                    action = build_review_outline_action(state, template_params)
                    flow = state.get("flow") or {}
                    flow["stage"] = "outline_review"
                    state["flow"] = flow
                elif data.command == "confirm_outline_generation":
                    if missing_required:
                        action = build_ask_param_action(state, template_params)
                        target_id = action.get("param", {}).get("id") if action else None
                        prompt = ""
                        if target_id:
                            target_param = next((p for p in template_params if p.get("id") == target_id), None)
                            if target_param:
                                prompt = build_param_prompt(target_param)
                        reply = prompt or "请先补充完所有必填参数。"
                        flow = state.get("flow") or {}
                        flow["stage"] = "required_collection"
                        state["flow"] = flow
                    else:
                        report = state.get("report") or {}
                        pending_outline = report.get("pending_outline_review") or []
                        if data.outline_override:
                            pending_outline = merge_outline_override(pending_outline, data.outline_override)
                            report["pending_outline_review"] = pending_outline
                            state["report"] = report
                        app_service = build_instance_application_service(db)
                        created = app_service.create_instance(
                            template_id=template.template_id,
                            input_params=merged,
                            outline_override=pending_outline,
                        )
                        capture_template_instance(
                            db,
                            template=template,
                            session_id=session.session_id,
                            capture_stage="outline_confirmed",
                            input_params_snapshot=merged,
                            outline_snapshot=pending_outline,
                            warnings=report.get("outline_review_warnings") or [],
                            report_instance_id=created["instance_id"],
                            created_by=session.user_id or "system",
                        )
                        document = create_markdown_document(db, created["instance_id"])
                        reply = "报告已生成，可以下载 Markdown 文档。"
                        action = {
                            "type": "download_document",
                            "document": serialize_document(document),
                        }
                        flow = state.get("flow") or {}
                        flow["stage"] = "generated"
                        state["flow"] = flow
                        summary = state.get("summary") or {}
                        summary["open_question"] = ""
                        state["summary"] = summary
                        session.instance_id = created["instance_id"]
                elif missing_required:
                    action = build_ask_param_action(state, template_params)
                    target_id = action.get("param", {}).get("id") if action else None
                    prompt = ""
                    if target_id:
                        target_param = next((p for p in template_params if p.get("id") == target_id), None)
                        if target_param:
                            prompt = build_param_prompt(target_param)
                    reply = prompt or "请补充必填参数。"
                    flow = state.get("flow") or {}
                    flow["stage"] = "required_collection"
                    state["flow"] = flow
                    summary = state.get("summary") or {}
                    summary["open_question"] = reply
                    state["summary"] = summary
                else:
                    reply = "参数已收集完成，请确认后生成大纲。"
                    action = build_review_params_action(state, template_params)
                    flow = state.get("flow") or {}
                    flow["stage"] = "review_ready"
                    state["flow"] = flow
                    summary = state.get("summary") or {}
                    summary["open_question"] = reply
                    state["summary"] = summary

                state_facts = []
                if template:
                    state_facts.append(f"模板={template.name}")
                for key, slot in (state.get("slots") or {}).items():
                    value = slot.get("value")
                    if value:
                        state_facts.append(f"{key}={value}")
                summary = state.get("summary") or {}
                summary["facts"] = state_facts[:6]
                state["summary"] = summary

            if not reply:
                reply = generate_chat_reply(db, gateway, user_message)
        except AIConfigurationError as exc:
            reply = str(exc)
        except TemplateIndexUnavailableError as exc:
            reply = str(exc)
        except ParamExtractionError as exc:
            reply = str(exc)
        except AIRequestError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    messages.append({"role": "assistant", "content": reply, **({"action": action} if action else {})})
    if action:
        flow = state.get("flow") or {}
        target = ""
        if action.get("type") == "ask_param":
            target = action.get("param", {}).get("id", "")
        if action.get("type") == "download_document":
            target = action.get("document", {}).get("document_id", "")
        flow["last_action"] = {"kind": action.get("type"), "target": target}
        state["flow"] = flow
    summary = state.get("summary") or {}
    summary["recent_turns"] = {
        "system": reply,
        "user": user_message,
    }
    state["summary"] = summary
    compress_state(state)
    messages = persist_state_to_history(messages, state, previous_state=previous_state, min_turns=3)

    session.messages = messages
    template_id = state.get("report", {}).get("template_id")
    if template_id:
        session.matched_template_id = template_id
    if action and action.get("type") == "show_template_candidates":
        session.matched_template_id = None

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "messages")
    db.commit()

    return {
        "session_id": session.session_id,
        "reply": reply,
        "action": action,
        "matched_template_id": session.matched_template_id,
        "messages": messages,
    }


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "messages": session.messages,
        "matched_template_id": session.matched_template_id,
    }


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "deleted"}

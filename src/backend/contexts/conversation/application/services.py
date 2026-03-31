"""Conversation application services."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from ....ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ....chat_capability_service import (
    CAPABILITY_FAULT_DIAGNOSIS,
    CAPABILITY_REPORT,
    CAPABILITY_SMART_QUERY,
    build_confirm_task_switch_action,
    capability_label,
    clear_current_task_state,
    detect_capability,
    ensure_task_state,
    handle_fault_diagnosis_turn,
    handle_smart_query_turn,
    has_substantial_progress,
    is_explicit_capability_switch_request,
    set_active_task,
    sync_report_task_state,
)
from ....chat_flow_service import (
    apply_template_selection,
    build_ask_param_action,
    build_review_outline_action,
    build_review_params_action,
    get_next_missing_param,
    reset_slots,
    rewind_slots_for_param,
    upsert_slots_from_params,
)
from ....chat_fork_service import (
    build_visible_message_payload,
    fork_session_from_message,
    fork_session_from_template_instance,
)
from ....chat_response_service import generate_chat_reply
from ....chat_session_service import ensure_session_metadata, list_chat_sessions, serialize_chat_session_detail, visible_chat_messages
from ....context_state_service import compress_state, new_context_state, persist_state_to_history, restore_state_from_history
from ....document_service import create_markdown_document, serialize_document
from ....infrastructure.dependencies import build_instance_application_service
from ....models import ChatSession, ReportInstance, ReportTemplate, TemplateInstance, gen_id
from ....outline_review_service import (
    build_pending_outline_review,
    merge_outline_override,
    resolve_outline_execution_baseline,
)
from ....param_dialog_service import (
    build_missing_required,
    build_param_prompt,
    extract_params_from_message,
    normalize_parameters,
    ParamExtractionError,
    validate_and_merge_params,
)
from ....system_settings_service import get_settings_payload
from ....template_instance_service import capture_generation_baseline
from ....template_index_service import TemplateIndexUnavailableError, match_templates
from ....shared.kernel.errors import NotFoundError, ValidationError


def build_message_payload(
    role: str,
    content: str,
    *,
    action: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return build_visible_message_payload(role, content, action=action)


def _resume_report_action(state: Dict[str, Any], template_params: List[Dict[str, Any]]) -> tuple[str, Dict[str, Any] | None]:
    flow = state.get("flow") or {}
    stage = str(flow.get("stage") or "idle")
    if stage == "outline_review":
        return "已保留当前任务，请继续确认报告大纲。", build_review_outline_action(state, template_params)
    if (state.get("missing") or {}).get("required"):
        return _build_missing_required_response(
            state,
            template_params,
            default_reply="已保留当前任务，请继续补充参数。",
        )
    return "已保留当前任务，请继续确认参数。", build_review_params_action(state, template_params)


def _build_missing_required_response(
    state: Dict[str, Any],
    template_params: List[Dict[str, Any]],
    *,
    default_reply: str,
) -> tuple[str, Dict[str, Any] | None]:
    target_param = get_next_missing_param(state, template_params)
    if not target_param:
        return default_reply, None
    prompt = build_param_prompt(target_param)
    if str(target_param.get("interaction_mode") or "form") == "chat":
        return prompt or default_reply, None
    action = build_ask_param_action(state, template_params)
    return prompt or default_reply, action


def _handle_report_turn(
    *,
    db: Session,
    gateway: OpenAICompatGateway,
    state: Dict[str, Any],
    session: ChatSession,
    data: ChatMessage,
    user_message: str,
) -> tuple[str, Dict[str, Any] | None]:
    templates_count = db.query(ReportTemplate).count()
    if templates_count == 0:
        state = sync_report_task_state(state)
        return "当前还没有可用模板，请先在“报告模板”中创建报告模板。", None

    reply = ""
    action = None
    template: ReportTemplate | None = None
    template_locked = bool(state.get("report", {}).get("template_locked"))

    if data.selected_template_id:
        template = db.query(ReportTemplate).filter(
            ReportTemplate.template_id == data.selected_template_id
        ).first()
        if not template:
            raise NotFoundError("Selected template not found")
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
                raise NotFoundError("Matched template not found")
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
            state = sync_report_task_state(state)
            return reply, action

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

        merged, _warnings = validate_and_merge_params(
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
                reply, action = _build_missing_required_response(
                    state,
                    template_params,
                    default_reply="请先补充完所有必填参数。",
                )
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
            state["report"] = report
            reply = "报告大纲已更新，请继续确认。"
            action = build_review_outline_action(state, template_params)
            flow = state.get("flow") or {}
            flow["stage"] = "outline_review"
            state["flow"] = flow
        elif data.command == "confirm_outline_generation":
            if missing_required:
                reply, action = _build_missing_required_response(
                    state,
                    template_params,
                    default_reply="请先补充完所有必填参数。",
                )
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
                resolved_outline = resolve_outline_execution_baseline(pending_outline)
                app_service = build_instance_application_service(db)
                created = app_service.create_instance(
                    template_id=template.template_id,
                    input_params=merged,
                    outline_override=resolved_outline,
                )
                try:
                    capture_generation_baseline(
                        db,
                        template=template,
                        session_id=session.session_id,
                        report_instance_id=created["instance_id"],
                        input_params_snapshot=merged,
                        outline_snapshot=resolved_outline,
                        warnings=report.get("outline_review_warnings") or [],
                        created_by=session.user_id or "system",
                    )
                    db.commit()
                except Exception:
                    created_instance = (
                        db.query(ReportInstance)
                        .filter(ReportInstance.instance_id == created["instance_id"])
                        .first()
                    )
                    if created_instance is not None:
                        db.delete(created_instance)
                        db.commit()
                    raise
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
            reply, action = _build_missing_required_response(
                state,
                template_params,
                default_reply="请补充必填参数。",
            )
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
    state = sync_report_task_state(state)
    return reply, action


def list_sessions(*, db):
    return list_chat_sessions(db)


def send_message(*, data, db):
    user_message = str(data.message or "")
    has_request_intent = bool(
        user_message.strip()
        or data.param_id
        or data.selected_template_id
        or data.command
    )

    session = None
    if data.session_id:
        session = db.query(ChatSession).filter(ChatSession.session_id == data.session_id).first()
        if session and ensure_session_metadata(session):
            db.commit()
            db.refresh(session)
    if not session and not has_request_intent:
        return {
            "session_id": "",
            "reply": "",
            "action": None,
            "matched_template_id": None,
            "messages": [],
        }
    if not session:
        session = ChatSession(session_id=gen_id(), messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    messages = list(session.messages or [])
    should_append_user_message = bool(
        user_message
        or data.param_id
        or data.selected_template_id
        or (data.command and data.command not in {"confirm_task_switch", "cancel_task_switch"})
    )
    if should_append_user_message:
        messages.append(build_message_payload("user", user_message))

    state = restore_state_from_history(messages) or new_context_state(session.session_id)
    state = ensure_task_state(state, session_id=session.session_id)
    flow = state.get("flow") or {}
    flow["turn_index"] = int(flow.get("turn_index") or 0) + 1
    state["flow"] = flow

    reply = ""
    action = None
    effective_user_message = user_message
    gateway = OpenAICompatGateway()
    settings = get_settings_payload(db)

    previous_state = deepcopy(state)

    if not settings["is_ready"]:
        reply = "系统设置尚未完成，请先到“系统设置”中配置 Completion 与 Embedding 接口，再开始对话生成。"
    else:
        try:
            current_capability = str((state.get("active_task") or {}).get("capability") or CAPABILITY_REPORT)
            current_stage = str((state.get("active_task") or {}).get("stage") or "idle")

            if data.command == "confirm_task_switch":
                pending = state.get("pending_switch") or {}
                next_capability = str(pending.get("to_capability") or CAPABILITY_REPORT)
                captured_user_message = str(pending.get("captured_user_message") or "")
                effective_user_message = captured_user_message
                state = clear_current_task_state(state)
                state = set_active_task(state, capability=next_capability, stage="idle")
                if next_capability == CAPABILITY_REPORT:
                    reply, action = _handle_report_turn(
                        db=db,
                        gateway=gateway,
                        state=state,
                        session=session,
                        data=ChatMessage(message=captured_user_message, preferred_capability=next_capability),
                        user_message=captured_user_message,
                    )
                elif next_capability == CAPABILITY_SMART_QUERY:
                    reply, action, task_update = handle_smart_query_turn(
                        db=db,
                        gateway=gateway,
                        message=captured_user_message,
                        state=state,
                    )
                    state = set_active_task(
                        state,
                        capability=CAPABILITY_SMART_QUERY,
                        stage=str(task_update.get("stage") or "idle"),
                        progress_state=task_update.get("progress_state"),
                        context_payload=task_update.get("context_payload"),
                    )
                else:
                    reply, action, task_update = handle_fault_diagnosis_turn(
                        db=db,
                        gateway=gateway,
                        message=captured_user_message,
                        state=state,
                    )
                    state = set_active_task(
                        state,
                        capability=CAPABILITY_FAULT_DIAGNOSIS,
                        stage=str(task_update.get("stage") or "idle"),
                        progress_state=task_update.get("progress_state"),
                        context_payload=task_update.get("context_payload"),
                    )
                state["pending_switch"] = None
            elif data.command == "cancel_task_switch":
                state["pending_switch"] = None
                if current_capability == CAPABILITY_REPORT:
                    template_id = state.get("report", {}).get("template_id")
                    template = None
                    if template_id:
                        template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
                    template_params = normalize_parameters(
                        (template.parameters or []) if template and template.parameters else ((template.content_params or []) if template else [])
                    )
                    reply, action = _resume_report_action(state, template_params)
                    state = sync_report_task_state(state)
                else:
                    reply = f"已保留当前{capability_label(current_capability)}任务，请继续。"
            else:
                has_report_commands = bool(
                    data.selected_template_id
                    or data.param_id
                    or data.outline_override
                    or data.command
                )
                desired_capability = current_capability
                if (
                    current_capability == CAPABILITY_REPORT
                    and not data.preferred_capability
                    and not has_report_commands
                ):
                    template_id = state.get("report", {}).get("template_id")
                    template = None
                    if template_id:
                        template = db.query(ReportTemplate).filter(
                            ReportTemplate.template_id == template_id
                        ).first()
                    template_params = normalize_parameters(
                        (template.parameters or []) if template and template.parameters else ((template.content_params or []) if template else [])
                    )
                    target_param = get_next_missing_param(state, template_params)
                    if target_param and str(target_param.get("interaction_mode") or "form") == "chat":
                        routed_capability = detect_capability(
                            message=user_message,
                            preferred_capability=data.preferred_capability,
                            current_capability=current_capability,
                            current_stage=current_stage,
                            has_report_commands=has_report_commands,
                        )
                        if routed_capability == CAPABILITY_REPORT or not is_explicit_capability_switch_request(
                            user_message,
                            routed_capability,
                        ):
                            desired_capability = CAPABILITY_REPORT
                        else:
                            desired_capability = routed_capability
                    else:
                        desired_capability = detect_capability(
                            message=user_message,
                            preferred_capability=data.preferred_capability,
                            current_capability=current_capability,
                            current_stage=current_stage,
                            has_report_commands=has_report_commands,
                        )
                else:
                    desired_capability = detect_capability(
                        message=user_message,
                        preferred_capability=data.preferred_capability,
                        current_capability=current_capability,
                        current_stage=current_stage,
                        has_report_commands=has_report_commands,
                    )
                if desired_capability != current_capability and has_substantial_progress(state):
                    state["pending_switch"] = {
                        "from_capability": current_capability,
                        "to_capability": desired_capability,
                        "reason": f"检测到你正在发起{capability_label(desired_capability)}，这会结束当前任务。",
                        "captured_user_message": user_message,
                    }
                    reply = f"检测到你想切换到{capability_label(desired_capability)}，这将结束当前任务。"
                    action = build_confirm_task_switch_action(state)
                else:
                    if desired_capability != current_capability:
                        state = clear_current_task_state(state)
                    if desired_capability == CAPABILITY_REPORT:
                        state = set_active_task(state, capability=CAPABILITY_REPORT, stage=str((state.get("active_task") or {}).get("stage") or "idle"))
                        reply, action = _handle_report_turn(
                            db=db,
                            gateway=gateway,
                            state=state,
                            session=session,
                            data=data,
                            user_message=user_message,
                        )
                    elif desired_capability == CAPABILITY_SMART_QUERY:
                        reply, action, task_update = handle_smart_query_turn(
                            db=db,
                            gateway=gateway,
                            message=user_message,
                            state=state,
                        )
                        state = set_active_task(
                            state,
                            capability=CAPABILITY_SMART_QUERY,
                            stage=str(task_update.get("stage") or "idle"),
                            progress_state=task_update.get("progress_state"),
                            context_payload=task_update.get("context_payload"),
                        )
                    else:
                        reply, action, task_update = handle_fault_diagnosis_turn(
                            db=db,
                            gateway=gateway,
                            message=user_message,
                            state=state,
                        )
                        state = set_active_task(
                            state,
                            capability=CAPABILITY_FAULT_DIAGNOSIS,
                            stage=str(task_update.get("stage") or "idle"),
                            progress_state=task_update.get("progress_state"),
                            context_payload=task_update.get("context_payload"),
                        )
        except AIConfigurationError as exc:
            reply = str(exc)
        except TemplateIndexUnavailableError as exc:
            reply = str(exc)
        except ParamExtractionError as exc:
            reply = str(exc)
        except AIRequestError as exc:
            raise ValidationError(str(exc)) from exc

    messages.append(build_message_payload("assistant", reply, action=action))
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
        "user": effective_user_message,
    }
    state["summary"] = summary
    compress_state(state)
    messages = persist_state_to_history(messages, state, previous_state=previous_state, min_turns=3)

    session.messages = messages
    if not (session.title or "").strip() and effective_user_message.strip():
        from ....chat_session_service import derive_session_title
        session.title = derive_session_title(messages)
    template_id = state.get("report", {}).get("template_id")
    if template_id:
        session.matched_template_id = template_id
    elif action and action.get("type") == "show_template_candidates":
        session.matched_template_id = None
    elif (state.get("active_task") or {}).get("capability") != CAPABILITY_REPORT:
        session.matched_template_id = None

    db.commit()

    return {
        "session_id": session.session_id,
        "reply": reply,
        "action": action,
        "matched_template_id": session.matched_template_id,
        "messages": messages,
    }


def get_session(*, session_id: str, db):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise NotFoundError("Session not found")
    if ensure_session_metadata(session):
        db.commit()
        db.refresh(session)
    return serialize_chat_session_detail(session)


def fork_session(*, data, db):
    if data.source_kind == "session_message":
        if not data.source_session_id or not data.source_message_id:
            raise NotFoundError("Source session or message not found")
        source_session = db.query(ChatSession).filter(ChatSession.session_id == data.source_session_id).first()
        if not source_session:
            raise NotFoundError("Source session not found")
        return fork_session_from_message(
            db,
            source_session=source_session,
            source_message_id=data.source_message_id,
        )

    if data.source_kind == "template_instance":
        if not data.template_instance_id:
            raise NotFoundError("Template instance not found")
        record = db.query(TemplateInstance).filter(
            TemplateInstance.template_instance_id == data.template_instance_id
        ).first()
        if not record:
            raise NotFoundError("Template instance not found")
        return fork_session_from_template_instance(db, template_instance=record)

    raise ValidationError("Unsupported fork source")


def delete_session(*, session_id: str, db):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise NotFoundError("Session not found")
    db.delete(session)
    db.commit()
    return {"message": "deleted"}


def update_session_from_instance(*, instance_id: str, db):
    from ....chat_fork_service import update_session_from_template_instance
    from ....template_instance_service import get_generation_baseline

    baseline = get_generation_baseline(db, instance_id)
    if not baseline:
        raise NotFoundError("Generation baseline not found")
    return update_session_from_template_instance(db, template_instance=baseline)


def list_instance_fork_sources(*, instance_id: str, db):
    from ....template_instance_service import get_generation_baseline

    baseline = get_generation_baseline(db, instance_id)
    if not baseline:
        raise NotFoundError("Generation baseline not found")
    session_id = str(getattr(baseline, "session_id", "") or "").strip()
    if not session_id:
        raise NotFoundError("Source session not found")
    source_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not source_session:
        raise NotFoundError("Source session not found")
    ensure_session_metadata(source_session)
    visible = visible_chat_messages(source_session.messages or [])
    return [_serialize_fork_source_message(item) for item in visible]


def fork_instance_chat(*, instance_id: str, source_message_id: str, db):
    from ....template_instance_service import get_generation_baseline

    baseline = get_generation_baseline(db, instance_id)
    if not baseline:
        raise NotFoundError("Generation baseline not found")
    session_id = str(getattr(baseline, "session_id", "") or "").strip()
    if not session_id:
        raise NotFoundError("Source session not found")
    source_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not source_session:
        raise NotFoundError("Source session not found")
    if not source_message_id:
        raise NotFoundError("Source message not found")
    return fork_session_from_message(
        db,
        source_session=source_session,
        source_message_id=source_message_id,
    )


def _serialize_fork_source_message(message: Dict[str, Any]) -> Dict[str, Any]:
    action = message.get("action") if isinstance(message.get("action"), dict) else {}
    return {
        "message_id": message.get("message_id"),
        "role": message.get("role"),
        "content": message.get("content"),
        "created_at": message.get("created_at"),
        "preview": str(message.get("content") or action.get("type") or "").strip()[:80],
        "action_type": action.get("type") if action else None,
    }

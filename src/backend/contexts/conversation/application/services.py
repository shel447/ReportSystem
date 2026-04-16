"""Conversation application services."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from ....shared.kernel.errors import NotFoundError, ValidationError
from .errors import ConversationReplyError


def _resume_report_action(
    report_gateway,
    state: Dict[str, Any],
    template_params: list[dict[str, Any]],
) -> tuple[str, Dict[str, Any] | None]:
    flow = state.get("flow") or {}
    stage = str(flow.get("stage") or "idle")
    if stage == "outline_review":
        return "已保留当前任务，请继续确认报告诉求。", report_gateway.build_review_outline_action(state, template_params)
    if (state.get("missing") or {}).get("required"):
        return _build_missing_required_response(
            report_gateway,
            state,
            template_params,
            default_reply="已保留当前任务，请继续补充参数。",
        )
    return "已保留当前任务，请继续确认参数。", report_gateway.build_review_params_action(state, template_params)


def _build_missing_required_response(
    report_gateway,
    state: Dict[str, Any],
    template_params: list[dict[str, Any]],
    *,
    default_reply: str,
) -> tuple[str, Dict[str, Any] | None]:
    target_param = report_gateway.get_next_missing_param(state, template_params)
    if not target_param:
        return default_reply, None
    prompt = report_gateway.build_param_prompt(target_param)
    if str(target_param.get("interaction_mode") or "form") == "chat":
        return prompt or default_reply, None
    action = report_gateway.build_ask_param_action(state, template_params)
    return prompt or default_reply, action


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


class ConversationService:
    def __init__(
        self,
        *,
        persistence,
        state_gateway,
        capability_gateway,
        report_gateway,
        fork_gateway,
    ) -> None:
        self.persistence = persistence
        self.state_gateway = state_gateway
        self.capability_gateway = capability_gateway
        self.report_gateway = report_gateway
        self.fork_gateway = fork_gateway

    def list_sessions(self, *, user_id: str) -> list[dict[str, Any]]:
        return self.persistence.list_sessions(user_id=user_id)

    def send_message(self, *, data, user_id: str) -> dict[str, Any]:
        user_message = str(data.message or "")
        has_request_intent = bool(
            user_message.strip()
            or data.param_id
            or data.selected_template_id
            or data.command
        )

        session = None
        if data.session_id:
            session = self.persistence.get_session(data.session_id, user_id=user_id)
            if session and self.persistence.ensure_session_metadata(session):
                self.persistence.save_session(session)
        if not session and not has_request_intent:
            return {
                "session_id": "",
                "reply": "",
                "action": None,
                "matched_template_id": None,
                "messages": [],
            }
        if not session:
            session = self.persistence.create_session(user_id=user_id)

        messages = list(session.messages or [])
        should_append_user_message = bool(
            user_message
            or data.param_id
            or data.selected_template_id
            or (data.command and data.command not in {"confirm_task_switch", "cancel_task_switch"})
        )
        if should_append_user_message:
            messages.append(self.persistence.build_message_payload("user", user_message))

        state = self.state_gateway.restore_state_from_history(messages) or self.state_gateway.new_context_state(session.session_id)
        state = self.state_gateway.ensure_task_state(state, session_id=session.session_id)
        flow = state.get("flow") or {}
        flow["turn_index"] = int(flow.get("turn_index") or 0) + 1
        state["flow"] = flow

        reply = ""
        action = None
        effective_user_message = user_message
        previous_state = deepcopy(state)
        settings = self.capability_gateway.get_settings_payload()

        if not settings["is_ready"]:
            reply = "系统设置尚未完成，请先到“系统设置”中配置 Completion 与 Embedding 接口，再开始对话生成。"
        else:
            try:
                current_capability = str((state.get("active_task") or {}).get("capability") or "report_generation")
                current_stage = str((state.get("active_task") or {}).get("stage") or "idle")

                if data.command == "confirm_task_switch":
                    pending = state.get("pending_switch") or {}
                    next_capability = str(pending.get("to_capability") or "report_generation")
                    captured_user_message = str(pending.get("captured_user_message") or "")
                    effective_user_message = captured_user_message
                    state = self.capability_gateway.clear_current_task_state(state)
                    state = self.capability_gateway.set_active_task(
                        state,
                        capability=next_capability,
                        stage="idle",
                    )
                    if next_capability == "report_generation":
                        reply, action = self._handle_report_turn(
                            state=state,
                            session=session,
                            data=self._clone_chat_message(
                                data,
                                message=captured_user_message,
                                preferred_capability=next_capability,
                            ),
                            user_message=captured_user_message,
                        )
                    elif next_capability == "smart_query":
                        reply, action, task_update = self.capability_gateway.handle_smart_query_turn(
                            message=captured_user_message,
                            state=state,
                        )
                        state = self.capability_gateway.set_active_task(
                            state,
                            capability="smart_query",
                            stage=str(task_update.get("stage") or "idle"),
                            progress_state=task_update.get("progress_state"),
                            context_payload=task_update.get("context_payload"),
                        )
                    else:
                        reply, action, task_update = self.capability_gateway.handle_fault_diagnosis_turn(
                            message=captured_user_message,
                            state=state,
                        )
                        state = self.capability_gateway.set_active_task(
                            state,
                            capability="fault_diagnosis",
                            stage=str(task_update.get("stage") or "idle"),
                            progress_state=task_update.get("progress_state"),
                            context_payload=task_update.get("context_payload"),
                        )
                    state["pending_switch"] = None
                elif data.command == "cancel_task_switch":
                    state["pending_switch"] = None
                    if current_capability == "report_generation":
                        template_id = state.get("report", {}).get("template_id")
                        template = self.persistence.get_template(template_id) if template_id else None
                        template_params = self.report_gateway.normalize_parameters(
                            (template.parameters or []) if template and template.parameters else ((template.content_params or []) if template else [])
                        )
                        reply, action = _resume_report_action(self.report_gateway, state, template_params)
                        state = self.capability_gateway.sync_report_task_state(state)
                    else:
                        reply = f"已保留当前{self.capability_gateway.capability_label(current_capability)}任务，请继续。"
                else:
                    has_report_commands = bool(
                        data.selected_template_id
                        or data.param_id
                        or data.outline_override
                        or data.command
                    )
                    desired_capability = current_capability
                    if (
                        current_capability == "report_generation"
                        and not data.preferred_capability
                        and not has_report_commands
                    ):
                        template_id = state.get("report", {}).get("template_id")
                        template = self.persistence.get_template(template_id) if template_id else None
                        template_params = self.report_gateway.normalize_parameters(
                            (template.parameters or []) if template and template.parameters else ((template.content_params or []) if template else [])
                        )
                        target_param = self.report_gateway.get_next_missing_param(state, template_params)
                        if target_param and str(target_param.get("interaction_mode") or "form") == "chat":
                            routed_capability = self.capability_gateway.detect_capability(
                                message=user_message,
                                preferred_capability=data.preferred_capability,
                                current_capability=current_capability,
                                current_stage=current_stage,
                                has_report_commands=has_report_commands,
                            )
                            if routed_capability == "report_generation" or not self.capability_gateway.is_explicit_capability_switch_request(
                                user_message,
                                routed_capability,
                            ):
                                desired_capability = "report_generation"
                            else:
                                desired_capability = routed_capability
                        else:
                            desired_capability = self.capability_gateway.detect_capability(
                                message=user_message,
                                preferred_capability=data.preferred_capability,
                                current_capability=current_capability,
                                current_stage=current_stage,
                                has_report_commands=has_report_commands,
                            )
                    else:
                        desired_capability = self.capability_gateway.detect_capability(
                            message=user_message,
                            preferred_capability=data.preferred_capability,
                            current_capability=current_capability,
                            current_stage=current_stage,
                            has_report_commands=has_report_commands,
                        )
                    if desired_capability != current_capability and self.capability_gateway.has_substantial_progress(state):
                        state["pending_switch"] = {
                            "from_capability": current_capability,
                            "to_capability": desired_capability,
                            "reason": f"检测到你正在发起{self.capability_gateway.capability_label(desired_capability)}，这会结束当前任务。",
                            "captured_user_message": user_message,
                        }
                        reply = f"检测到你想切换到{self.capability_gateway.capability_label(desired_capability)}，这将结束当前任务。"
                        action = self.capability_gateway.build_confirm_task_switch_action(state)
                    else:
                        if desired_capability != current_capability:
                            state = self.capability_gateway.clear_current_task_state(state)
                        if desired_capability == "report_generation":
                            state = self.capability_gateway.set_active_task(
                                state,
                                capability="report_generation",
                                stage=str((state.get("active_task") or {}).get("stage") or "idle"),
                            )
                            reply, action = self._handle_report_turn(
                                state=state,
                                session=session,
                                data=data,
                                user_message=user_message,
                            )
                        elif desired_capability == "smart_query":
                            reply, action, task_update = self.capability_gateway.handle_smart_query_turn(
                                message=user_message,
                                state=state,
                            )
                            state = self.capability_gateway.set_active_task(
                                state,
                                capability="smart_query",
                                stage=str(task_update.get("stage") or "idle"),
                                progress_state=task_update.get("progress_state"),
                                context_payload=task_update.get("context_payload"),
                            )
                        else:
                            reply, action, task_update = self.capability_gateway.handle_fault_diagnosis_turn(
                                message=user_message,
                                state=state,
                            )
                            state = self.capability_gateway.set_active_task(
                                state,
                                capability="fault_diagnosis",
                                stage=str(task_update.get("stage") or "idle"),
                                progress_state=task_update.get("progress_state"),
                                context_payload=task_update.get("context_payload"),
                            )
            except ConversationReplyError as exc:
                reply = str(exc)

        messages.append(self.persistence.build_message_payload("assistant", reply, action=action))
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
        self.state_gateway.compress_state(state)
        messages = self.state_gateway.persist_state_to_history(
            messages,
            state,
            previous_state=previous_state,
            min_turns=3,
        )

        session.messages = messages
        if not (session.title or "").strip() and effective_user_message.strip():
            session.title = self.persistence.derive_session_title(messages)
        template_id = state.get("report", {}).get("template_id")
        if template_id:
            session.matched_template_id = template_id
        elif action and action.get("type") == "show_template_candidates":
            session.matched_template_id = None
        elif (state.get("active_task") or {}).get("capability") != "report_generation":
            session.matched_template_id = None

        self.persistence.save_session(session)

        return {
            "session_id": session.session_id,
            "reply": reply,
            "action": action,
            "matched_template_id": session.matched_template_id,
            "messages": messages,
        }

    def get_session(self, *, session_id: str, user_id: str) -> dict[str, Any]:
        session = self.persistence.get_session(session_id, user_id=user_id)
        if not session:
            raise NotFoundError("Session not found")
        if self.persistence.ensure_session_metadata(session):
            self.persistence.save_session(session)
        return self.persistence.serialize_session_detail(session)

    def fork_session(self, *, data, user_id: str) -> dict[str, Any]:
        if data.source_kind == "session_message":
            if not data.source_session_id or not data.source_message_id:
                raise NotFoundError("Source session or message not found")
            source_session = self.persistence.get_session(data.source_session_id, user_id=user_id)
            if not source_session:
                raise NotFoundError("Source session not found")
            return self.fork_gateway.fork_session_from_message(
                source_session=source_session,
                source_message_id=data.source_message_id,
            )

        if data.source_kind == "template_instance":
            if not data.template_instance_id:
                raise NotFoundError("Template instance not found")
            record = self.persistence.get_template_instance(data.template_instance_id)
            if not record:
                raise NotFoundError("Template instance not found")
            return self.fork_gateway.fork_session_from_template_instance(template_instance=record)

        raise ValidationError("Unsupported fork source")

    def delete_session(self, *, session_id: str, user_id: str) -> dict[str, Any]:
        if not self.persistence.delete_session(session_id, user_id=user_id):
            raise NotFoundError("Session not found")
        return {"message": "deleted"}

    def update_session_from_instance(self, *, instance_id: str, user_id: str = "default") -> dict[str, Any]:
        template_instance = self.persistence.get_template_instance_by_instance(instance_id)
        if not template_instance:
            raise NotFoundError("Template instance not found")
        report_instance = self.persistence.get_report_instance(instance_id, user_id=user_id)
        preferred_session_id = str(getattr(report_instance, "source_session_id", "") or "").strip() if report_instance else ""
        if preferred_session_id:
            source_session = self.persistence.get_session(preferred_session_id, user_id=user_id)
            if not source_session:
                raise NotFoundError("Source session not found")
        return self.fork_gateway.update_session_from_template_instance(template_instance=template_instance)

    def list_instance_fork_sources(self, *, instance_id: str, user_id: str = "default") -> list[dict[str, Any]]:
        session_id = self._resolve_instance_source_session_id(instance_id=instance_id, user_id=user_id)
        if not session_id:
            raise NotFoundError("Source session not found")
        source_session = self.persistence.get_session(session_id, user_id=user_id)
        if not source_session:
            raise NotFoundError("Source session not found")
        if self.persistence.ensure_session_metadata(source_session):
            self.persistence.save_session(source_session)
        visible = self.persistence.visible_messages(source_session.messages or [])
        return [_serialize_fork_source_message(item) for item in visible]

    def fork_instance_chat(self, *, instance_id: str, source_message_id: str, user_id: str = "default") -> dict[str, Any]:
        session_id = self._resolve_instance_source_session_id(instance_id=instance_id, user_id=user_id)
        if not session_id:
            raise NotFoundError("Source session not found")
        source_session = self.persistence.get_session(session_id, user_id=user_id)
        if not source_session:
            raise NotFoundError("Source session not found")
        if not source_message_id:
            raise NotFoundError("Source message not found")
        return self.fork_gateway.fork_session_from_message(
            source_session=source_session,
            source_message_id=source_message_id,
        )

    def _handle_report_turn(
        self,
        *,
        state: Dict[str, Any],
        session,
        data,
        user_message: str,
    ) -> tuple[str, Dict[str, Any] | None]:
        templates_count = self.persistence.count_templates()
        if templates_count == 0:
            state = self.capability_gateway.sync_report_task_state(state)
            return "当前还没有可用模板，请先在“报告模板”中创建报告模板。", None

        reply = ""
        action = None
        template = None
        template_locked = bool(state.get("report", {}).get("template_locked"))

        if data.selected_template_id:
            template = self.persistence.get_template(data.selected_template_id)
            if not template:
                raise NotFoundError("Selected template not found")
            state = self.report_gateway.apply_template_selection(
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
                template = self.persistence.get_template(template_id)
        else:
            matched = self.report_gateway.match_templates(user_message)
            if matched["auto_match"]:
                template = self.persistence.get_template(matched["best"]["template_id"])
                if not template:
                    raise NotFoundError("Matched template not found")
                state = self.report_gateway.apply_template_selection(
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
                reply = self.capability_gateway.generate_chat_reply(user_message, candidates=matched["candidates"])
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
                state = self.capability_gateway.sync_report_task_state(state)
                return reply, action

        if template_locked and template is not None:
            template_params = self.report_gateway.normalize_parameters(
                (template.parameters or []) if template.parameters else (template.content_params or [])
            )
            if data.command == "reset_params":
                state = self.report_gateway.reset_slots(state)
                report = state.get("report") or {}
                report["pending_outline_review"] = []
                report["outline_review_warnings"] = []
                state["report"] = report
            elif data.command == "edit_param" and data.target_param_id:
                state = self.report_gateway.rewind_slots_for_param(state, template_params, data.target_param_id)
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
                updates = self.report_gateway.extract_params_from_message(
                    template_params=template_params,
                    message=user_message,
                )

            merged, _warnings = self.report_gateway.validate_and_merge_params(
                template_params=template_params,
                collected=collected,
                updates=updates,
            )
            if updates:
                state = self.report_gateway.upsert_slots_from_params(
                    state,
                    merged,
                    template_params,
                    source=source,
                    turn_index=state.get("flow", {}).get("turn_index", 0),
                )

            missing_required = self.report_gateway.build_missing_required(template_params, merged)
            missing = state.get("missing") or {}
            missing["required"] = missing_required
            state["missing"] = missing

            if data.command == "edit_param" and not data.target_param_id and (state.get("flow") or {}).get("stage") == "outline_review":
                reply = "请确认需要调整的参数。"
                action = self.report_gateway.build_review_params_action(state, template_params)
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
                        self.report_gateway,
                        state,
                        template_params,
                        default_reply="请先补充完所有必填参数。",
                    )
                    flow = state.get("flow") or {}
                    flow["stage"] = "required_collection"
                    state["flow"] = flow
                else:
                    outline_review, outline_warnings = self.report_gateway.build_pending_outline_review(template, merged)
                    report = state.get("report") or {}
                    report["pending_outline_review"] = outline_review
                    report["outline_review_warnings"] = outline_warnings
                    state["report"] = report
                    self.report_gateway.capture_template_instance_state(
                        template=template,
                        session_id=session.session_id,
                        capture_stage="outline_confirmed",
                        input_params_snapshot=merged,
                        outline_snapshot=outline_review,
                        warnings=outline_warnings,
                        report_instance_id=None,
                        created_by=session.user_id or "system",
                    )
                    reply = "参数已确认，请检查报告诉求。"
                    action = self.report_gateway.build_review_outline_action(state, template_params)
                    flow = state.get("flow") or {}
                    flow["stage"] = "outline_review"
                    state["flow"] = flow
                    summary = state.get("summary") or {}
                    summary["open_question"] = reply
                    state["summary"] = summary
            elif data.command == "edit_outline":
                report = state.get("report") or {}
                pending_outline = report.get("pending_outline_review") or []
                report["pending_outline_review"] = self.report_gateway.merge_outline_override(pending_outline, data.outline_override or [])
                state["report"] = report
                self.report_gateway.capture_template_instance_state(
                    template=template,
                    session_id=session.session_id,
                    capture_stage="outline_confirmed",
                    input_params_snapshot=merged,
                    outline_snapshot=report.get("pending_outline_review") or [],
                    warnings=report.get("outline_review_warnings") or [],
                    report_instance_id=None,
                    created_by=session.user_id or "system",
                )
                reply = "报告诉求已更新，请继续确认。"
                action = self.report_gateway.build_review_outline_action(state, template_params)
                flow = state.get("flow") or {}
                flow["stage"] = "outline_review"
                state["flow"] = flow
            elif data.command == "confirm_outline_generation":
                if missing_required:
                    reply, action = _build_missing_required_response(
                        self.report_gateway,
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
                        pending_outline = self.report_gateway.merge_outline_override(pending_outline, data.outline_override)
                        report["pending_outline_review"] = pending_outline
                        state["report"] = report
                    resolved_outline = self.report_gateway.resolve_outline_execution_baseline(pending_outline)
                    created = self.report_gateway.create_instance(
                        template_id=template.template_id,
                        input_params=merged,
                        outline_override=resolved_outline,
                        user_id=session.user_id or "default",
                        source_session_id=session.session_id,
                        source_message_id=None,
                    )
                    try:
                        self.report_gateway.capture_template_instance_for_generation(
                            template=template,
                            session_id=session.session_id,
                            report_instance_id=created["instance_id"],
                            input_params_snapshot=merged,
                            outline_snapshot=resolved_outline,
                            warnings=report.get("outline_review_warnings") or [],
                            created_by=session.user_id or "system",
                        )
                    except Exception:
                        self.persistence.delete_report_instance(created["instance_id"])
                        raise
                    document = self.report_gateway.create_markdown_document(created["instance_id"])
                    reply = "报告已生成，可以下载 Markdown 文档。"
                    action = {
                        "type": "download_document",
                        "document": self.report_gateway.serialize_document(document),
                    }
                    flow = state.get("flow") or {}
                    flow["stage"] = "generated"
                    state["flow"] = flow
                    summary = state.get("summary") or {}
                    summary["open_question"] = ""
                    state["summary"] = summary
            elif missing_required:
                reply, action = _build_missing_required_response(
                    self.report_gateway,
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
                reply = "参数已收集完成，请确认后生成诉求。"
                action = self.report_gateway.build_review_params_action(state, template_params)
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
            reply = self.capability_gateway.generate_chat_reply(user_message)
        state = self.capability_gateway.sync_report_task_state(state)
        return reply, action

    def _resolve_instance_source_session_id(self, *, instance_id: str, user_id: str) -> str:
        report_instance = self.persistence.get_report_instance(instance_id, user_id=user_id)
        if not report_instance:
            raise NotFoundError("Instance not found")
        preferred = str(getattr(report_instance, "source_session_id", "") or "").strip()
        if preferred:
            return preferred
        template_instance = self.persistence.get_template_instance_by_instance(instance_id)
        if not template_instance:
            raise NotFoundError("Template instance not found")
        return str(getattr(template_instance, "session_id", "") or "").strip()

    @staticmethod
    def _clone_chat_message(source, **overrides):
        payload = {
            "message": getattr(source, "message", ""),
            "session_id": getattr(source, "session_id", ""),
            "preferred_capability": getattr(source, "preferred_capability", None),
            "selected_template_id": getattr(source, "selected_template_id", None),
            "param_id": getattr(source, "param_id", None),
            "param_value": getattr(source, "param_value", None),
            "param_values": getattr(source, "param_values", None),
            "command": getattr(source, "command", None),
            "target_param_id": getattr(source, "target_param_id", None),
            "outline_override": getattr(source, "outline_override", None),
        }
        payload.update(overrides)
        return type("ConversationChatMessage", (), payload)()

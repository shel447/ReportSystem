from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

from ....ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ....chat_capability_service import (
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
    update_session_from_template_instance,
)
from ....chat_response_service import generate_chat_reply
from ....chat_session_service import (
    derive_session_title,
    ensure_session_metadata,
    list_chat_sessions,
    serialize_chat_session_detail,
    visible_chat_messages,
)
from ....context_state_service import (
    compress_state,
    new_context_state,
    persist_state_to_history,
    restore_state_from_history,
)
from ....document_service import create_markdown_document, serialize_document
from ....models import ChatSession, ReportInstance, ReportTemplate, TemplateInstance, gen_id
from ....outline_review_service import (
    build_pending_outline_review,
    merge_outline_override,
    resolve_outline_execution_baseline,
)
from ....param_dialog_service import (
    ParamExtractionError,
    build_missing_required,
    build_param_prompt,
    extract_params_from_message,
    normalize_parameters,
    validate_and_merge_params,
)
from ....shared.kernel.errors import ConflictError, NotFoundError, ValidationError
from ....system_settings_service import get_settings_payload
from ....template_instance_service import capture_generation_baseline, get_generation_baseline
from ....contexts.template_catalog.infrastructure.indexing import TemplateIndexUnavailableError, match_templates
from ..application.errors import ConversationReplyError


def build_instance_application_service(db):
    from ....contexts.report_runtime.infrastructure.gateways import (
        build_legacy_instance_application_service as _build_instance_application_service,
    )

    return _build_instance_application_service(db)


class ConversationPersistenceGateway:
    def __init__(self, db) -> None:
        self.db = db

    def list_sessions(self) -> list[dict[str, Any]]:
        return list_chat_sessions(self.db)

    def get_session(self, session_id: str):
        return self.db.query(ChatSession).filter(ChatSession.session_id == session_id).first()

    def create_session(self):
        session = ChatSession(session_id=gen_id(), messages=[])
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def save_session(self, session) -> None:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

    def commit(self) -> None:
        self.db.commit()

    def ensure_session_metadata(self, session) -> bool:
        return ensure_session_metadata(session)

    def serialize_session_detail(self, session) -> dict[str, Any]:
        return serialize_chat_session_detail(session)

    def derive_session_title(self, messages: list[dict[str, Any]]) -> str:
        return derive_session_title(messages)

    def delete_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    def build_message_payload(
        self,
        role: str,
        content: str,
        *,
        action: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return build_visible_message_payload(role, content, action=action)

    def visible_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return visible_chat_messages(messages)

    def count_templates(self) -> int:
        return self.db.query(ReportTemplate).count()

    def get_template(self, template_id: str):
        return self.db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()

    def get_template_instance(self, template_instance_id: str):
        return (
            self.db.query(TemplateInstance)
            .filter(TemplateInstance.template_instance_id == template_instance_id)
            .first()
        )

    def get_generation_baseline(self, instance_id: str):
        return get_generation_baseline(self.db, instance_id)

    def delete_report_instance(self, instance_id: str) -> None:
        record = self.db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
        if record is not None:
            self.db.delete(record)
            self.db.commit()


class ConversationStateGateway:
    def ensure_task_state(self, state: Dict[str, Any], *, session_id: str) -> Dict[str, Any]:
        return ensure_task_state(state, session_id=session_id)

    def new_context_state(self, session_id: str) -> Dict[str, Any]:
        return new_context_state(session_id)

    def restore_state_from_history(self, history: list[dict[str, Any]]) -> Dict[str, Any] | None:
        return restore_state_from_history(history)

    def compress_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return compress_state(state)

    def persist_state_to_history(
        self,
        history: list[dict[str, Any]],
        state: dict[str, Any],
        *,
        previous_state: dict[str, Any] | None,
        min_turns: int,
    ) -> list[dict[str, Any]]:
        return persist_state_to_history(
            history,
            state,
            previous_state=previous_state,
            min_turns=min_turns,
        )


class ConversationCapabilityGateway:
    def __init__(self, db) -> None:
        self.db = db
        self.gateway = OpenAICompatGateway()

    def get_settings_payload(self) -> dict[str, Any]:
        return get_settings_payload(self.db)

    def detect_capability(
        self,
        *,
        message: str,
        preferred_capability: Optional[str],
        current_capability: str,
        current_stage: str,
        has_report_commands: bool,
    ) -> str:
        return detect_capability(
            message=message,
            preferred_capability=preferred_capability,
            current_capability=current_capability,
            current_stage=current_stage,
            has_report_commands=has_report_commands,
        )

    def build_confirm_task_switch_action(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return build_confirm_task_switch_action(state)

    def capability_label(self, capability: str) -> str:
        return capability_label(capability)

    def clear_current_task_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return clear_current_task_state(state)

    def has_substantial_progress(self, state: Dict[str, Any]) -> bool:
        return has_substantial_progress(state)

    def is_explicit_capability_switch_request(self, message: str, target_capability: str) -> bool:
        return is_explicit_capability_switch_request(message, target_capability)

    def set_active_task(
        self,
        state: Dict[str, Any],
        *,
        capability: str,
        stage: str,
        progress_state: Optional[Dict[str, Any]] = None,
        context_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return set_active_task(
            state,
            capability=capability,
            stage=stage,
            progress_state=progress_state,
            context_payload=context_payload,
        )

    def sync_report_task_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return sync_report_task_state(state)

    def generate_chat_reply(self, message: str, *, candidates: Optional[list[dict[str, Any]]] = None) -> str:
        try:
            return generate_chat_reply(self.db, self.gateway, message, candidates=candidates)
        except AIConfigurationError as exc:
            raise ConversationReplyError(str(exc)) from exc
        except AIRequestError as exc:
            raise ValidationError(str(exc)) from exc

    def handle_smart_query_turn(
        self,
        *,
        message: str,
        state: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any] | None, Dict[str, Any]]:
        try:
            return handle_smart_query_turn(
                db=self.db,
                gateway=self.gateway,
                message=message,
                state=state,
            )
        except AIConfigurationError as exc:
            raise ConversationReplyError(str(exc)) from exc
        except AIRequestError as exc:
            raise ValidationError(str(exc)) from exc

    def handle_fault_diagnosis_turn(
        self,
        *,
        message: str,
        state: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any] | None, Dict[str, Any]]:
        try:
            return handle_fault_diagnosis_turn(
                db=self.db,
                gateway=self.gateway,
                message=message,
                state=state,
            )
        except AIConfigurationError as exc:
            raise ConversationReplyError(str(exc)) from exc
        except AIRequestError as exc:
            raise ValidationError(str(exc)) from exc


class ConversationReportGateway:
    def __init__(self, db) -> None:
        self.db = db
        self.gateway = OpenAICompatGateway()

    def match_templates(self, message: str) -> dict[str, Any]:
        try:
            return match_templates(self.db, message, self.gateway)
        except TemplateIndexUnavailableError as exc:
            raise ConversationReplyError(str(exc)) from exc

    def normalize_parameters(self, raw_params: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return normalize_parameters(raw_params)

    def extract_params_from_message(
        self,
        *,
        template_params: list[dict[str, Any]],
        message: str,
    ) -> dict[str, Any]:
        try:
            return extract_params_from_message(
                db=self.db,
                gateway=self.gateway,
                template_params=template_params,
                message=message,
            )
        except ParamExtractionError as exc:
            raise ConversationReplyError(str(exc)) from exc

    def validate_and_merge_params(
        self,
        *,
        template_params: list[dict[str, Any]],
        collected: dict[str, Any],
        updates: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        return validate_and_merge_params(
            template_params=template_params,
            collected=collected,
            updates=updates,
        )

    def build_missing_required(
        self,
        template_params: list[dict[str, Any]],
        collected: dict[str, Any],
    ) -> list[str]:
        return build_missing_required(template_params, collected)

    def build_param_prompt(self, param: dict[str, Any]) -> str:
        return build_param_prompt(param)

    def apply_template_selection(
        self,
        state: Dict[str, Any],
        template: Dict[str, Any],
        *,
        confidence: float,
        locked: bool,
    ) -> Dict[str, Any]:
        return apply_template_selection(state, template, confidence=confidence, locked=locked)

    def build_ask_param_action(self, state: Dict[str, Any], params: list[dict[str, Any]]) -> Dict[str, Any]:
        return build_ask_param_action(state, params)

    def build_review_outline_action(self, state: Dict[str, Any], params: list[dict[str, Any]]) -> Dict[str, Any]:
        return build_review_outline_action(state, params)

    def build_review_params_action(self, state: Dict[str, Any], params: list[dict[str, Any]]) -> Dict[str, Any]:
        return build_review_params_action(state, params)

    def get_next_missing_param(self, state: Dict[str, Any], params: list[dict[str, Any]]) -> Dict[str, Any] | None:
        return get_next_missing_param(state, params)

    def reset_slots(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return reset_slots(state)

    def rewind_slots_for_param(
        self,
        state: Dict[str, Any],
        params: list[dict[str, Any]],
        target_param_id: str,
    ) -> Dict[str, Any]:
        return rewind_slots_for_param(state, params, target_param_id)

    def upsert_slots_from_params(
        self,
        state: Dict[str, Any],
        values: Dict[str, Any],
        param_defs: list[dict[str, Any]],
        *,
        source: str,
        turn_index: int,
    ) -> Dict[str, Any]:
        return upsert_slots_from_params(
            state,
            values,
            param_defs,
            source=source,
            turn_index=turn_index,
        )

    def build_pending_outline_review(self, template, input_params: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        instance_service = build_instance_application_service(self.db)
        template_entity = instance_service.template_reader.get_by_id(template.template_id)
        return build_pending_outline_review(template_entity, input_params)

    def merge_outline_override(
        self,
        current_outline: list[dict[str, Any]],
        override_outline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return merge_outline_override(current_outline, override_outline)

    def resolve_outline_execution_baseline(self, outline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return resolve_outline_execution_baseline(outline)

    def create_instance(
        self,
        *,
        template_id: str,
        input_params: dict[str, Any],
        outline_override: Optional[list[Any]],
    ) -> dict[str, Any]:
        service = build_instance_application_service(self.db)
        try:
            return service.create_instance(
                template_id=template_id,
                input_params=input_params,
                outline_override=outline_override,
            )
        except AIConfigurationError as exc:
            raise ConversationReplyError(str(exc)) from exc
        except AIRequestError as exc:
            raise ValidationError(str(exc)) from exc

    def create_markdown_document(self, instance_id: str):
        return create_markdown_document(self.db, instance_id)

    def serialize_document(self, document) -> dict[str, Any]:
        return serialize_document(document)

    def capture_generation_baseline(
        self,
        *,
        template,
        session_id: str,
        report_instance_id: str,
        input_params_snapshot: dict[str, Any],
        outline_snapshot: list[dict[str, Any]],
        warnings: list[str] | None,
        created_by: str,
    ) -> None:
        capture_generation_baseline(
            self.db,
            template=template,
            session_id=session_id,
            report_instance_id=report_instance_id,
            input_params_snapshot=input_params_snapshot,
            outline_snapshot=outline_snapshot,
            warnings=warnings,
            created_by=created_by,
        )
        self.db.commit()


class ConversationForkGateway:
    def __init__(self, db) -> None:
        self.db = db

    def fork_session_from_message(self, *, source_session, source_message_id: str) -> dict[str, Any]:
        try:
            return fork_session_from_message(
                self.db,
                source_session=source_session,
                source_message_id=source_message_id,
            )
        except HTTPException as exc:
            if exc.status_code == 404:
                raise NotFoundError(str(exc.detail)) from exc
            if exc.status_code == 409:
                raise ConflictError(str(exc.detail)) from exc
            raise ValidationError(str(exc.detail)) from exc

    def fork_session_from_template_instance(self, *, template_instance) -> dict[str, Any]:
        try:
            return fork_session_from_template_instance(self.db, template_instance=template_instance)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise NotFoundError(str(exc.detail)) from exc
            if exc.status_code == 409:
                raise ConflictError(str(exc.detail)) from exc
            raise ValidationError(str(exc.detail)) from exc

    def update_session_from_generation_baseline(self, *, template_instance) -> dict[str, Any]:
        try:
            return update_session_from_template_instance(self.db, template_instance=template_instance)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise NotFoundError(str(exc.detail)) from exc
            if exc.status_code == 409:
                raise ConflictError(str(exc.detail)) from exc
            raise ValidationError(str(exc.detail)) from exc

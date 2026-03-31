"""对话交互路由"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..contexts.conversation.application import services as conversation_services
from ..contexts.conversation.application.services import (
    delete_session as delete_session_service,
    fork_session as fork_session_service,
    get_session as get_session_service,
    list_sessions as list_sessions_service,
    send_message as send_message_service,
)
from ..shared.kernel.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/chat", tags=["chat"])

# Compatibility shim for existing tests and call sites that patch router-level
# collaborators. The real orchestration lives in conversation application.
get_settings_payload = conversation_services.get_settings_payload
match_templates = conversation_services.match_templates
extract_params_from_message = conversation_services.extract_params_from_message
build_instance_application_service = conversation_services.build_instance_application_service
create_markdown_document = conversation_services.create_markdown_document
serialize_document = conversation_services.serialize_document
handle_smart_query_turn = conversation_services.handle_smart_query_turn
handle_fault_diagnosis_turn = conversation_services.handle_fault_diagnosis_turn


def _sync_conversation_compatibility_overrides() -> None:
    conversation_services.get_settings_payload = get_settings_payload
    conversation_services.match_templates = match_templates
    conversation_services.extract_params_from_message = extract_params_from_message
    conversation_services.build_instance_application_service = build_instance_application_service
    conversation_services.create_markdown_document = create_markdown_document
    conversation_services.serialize_document = serialize_document
    conversation_services.handle_smart_query_turn = handle_smart_query_turn
    conversation_services.handle_fault_diagnosis_turn = handle_fault_diagnosis_turn


class ChatMessage(BaseModel):
    message: str = ""
    session_id: str = ""
    preferred_capability: Optional[str] = None
    selected_template_id: Optional[str] = None
    param_id: Optional[str] = None
    param_value: Optional[Any] = None
    param_values: Optional[List[str]] = None
    command: Optional[str] = None
    target_param_id: Optional[str] = None
    outline_override: Optional[List[Dict[str, Any]]] = None


class ChatForkRequest(BaseModel):
    source_kind: str
    source_session_id: Optional[str] = None
    source_message_id: Optional[str] = None
    template_instance_id: Optional[str] = None


@router.get("")
def list_sessions(db: Session = Depends(get_db)):
    return list_sessions_service(db=db)


@router.post("")
def send_message(data: ChatMessage, db: Session = Depends(get_db)):
    _sync_conversation_compatibility_overrides()
    try:
        return send_message_service(data=data, db=db)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        detail = str(exc)
        status_code = 502 if detail.startswith("request to") or detail.startswith("[WinError") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    try:
        return get_session_service(session_id=session_id, db=db)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/forks")
def fork_session(data: ChatForkRequest, db: Session = Depends(get_db)):
    _sync_conversation_compatibility_overrides()
    try:
        return fork_session_service(data=data, db=db)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Unsupported fork source" else 400, detail=str(exc)) from exc


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    try:
        return delete_session_service(session_id=session_id, db=db)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

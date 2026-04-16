"""对话交互路由"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.persistence.database import get_db
from ..infrastructure.dependencies import build_conversation_service
from ..shared.kernel.http import resolve_user_id
from ..shared.kernel.errors import ConflictError, NotFoundError, ValidationError

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatReplyPayload(BaseModel):
    type: str = ""
    parameters: Dict[str, Any] = {}


class ChatCommandPayload(BaseModel):
    name: str = ""


class ChatMessage(BaseModel):
    message: str = ""
    session_id: str = ""
    preferred_capability: Optional[str] = None
    selected_template_id: Optional[str] = None
    param_id: Optional[str] = None
    param_value: Optional[Any] = None
    param_values: Optional[List[str]] = None
    command: Optional[Union[str, ChatCommandPayload]] = None
    target_param_id: Optional[str] = None
    outline_override: Optional[List[Dict[str, Any]]] = None
    parameter_updates: Optional[Dict[str, Any]] = None
    conversationId: Optional[str] = None
    chatId: Optional[str] = None
    instruction: Optional[str] = None
    question: Optional[str] = None
    reply: Optional[ChatReplyPayload] = None


class ChatForkRequest(BaseModel):
    source_kind: str
    source_session_id: Optional[str] = None
    source_message_id: Optional[str] = None


@router.get("")
def list_sessions(db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    return build_conversation_service(db).list_sessions(user_id=resolve_user_id(user_id))


@router.post("")
def send_message(
    data: ChatMessage,
    request: Request = None,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    request_data = _map_contract_request(data)
    try:
        response = build_conversation_service(db).send_message(data=request_data, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        detail = str(exc)
        status_code = 502 if detail.startswith("request to") or detail.startswith("[WinError") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    if _is_contract_request(data):
        payload = _build_contract_response(original=data, internal=response)
        if _wants_sse(request):
            return StreamingResponse(
                _single_event_stream(payload),
                media_type="text/event-stream",
            )
        return payload
    return response


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_conversation_service(db).get_session(session_id=session_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/forks")
def fork_session(data: ChatForkRequest, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_conversation_service(db).fork_session(data=data, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Unsupported fork source" else 400, detail=str(exc)) from exc


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_conversation_service(db).delete_session(session_id=session_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _is_contract_request(data: ChatMessage) -> bool:
    return bool(
        (data.conversationId or "").strip()
        or (data.chatId or "").strip()
        or (data.instruction or "").strip()
        or (data.question or "").strip()
        or data.reply is not None
        or isinstance(data.command, ChatCommandPayload)
    )


def _map_contract_request(data: ChatMessage) -> ChatMessage:
    if not _is_contract_request(data):
        return data

    command_name = _command_name(data.command)
    reply_type = str((data.reply.type if data.reply else "") or "").strip()
    if not command_name and reply_type == "final_confirm":
        command_name = "confirm_generate_report"
    parameter_updates = dict((data.reply.parameters if data.reply else data.parameter_updates) or {})
    preferred_capability = _map_instruction_to_capability(data.instruction or data.preferred_capability)
    return ChatMessage(
        message=str(data.question or data.message or ""),
        session_id=str(data.conversationId or data.session_id or ""),
        preferred_capability=preferred_capability,
        selected_template_id=data.selected_template_id,
        command=_map_contract_command(command_name),
        target_param_id=data.target_param_id,
        outline_override=data.outline_override,
        parameter_updates=parameter_updates or None,
    )


def _command_name(command: Optional[Union[str, ChatCommandPayload]]) -> str:
    if isinstance(command, ChatCommandPayload):
        return str(command.name or "").strip()
    return str(command or "").strip()


def _map_instruction_to_capability(instruction: Optional[str]) -> Optional[str]:
    normalized = str(instruction or "").strip()
    if not normalized:
        return None
    if normalized == "generate_report":
        return "report_generation"
    if normalized in {"smart_query", "fault_diagnosis"}:
        return normalized
    return None


def _map_contract_command(command_name: str) -> Optional[str]:
    if not command_name:
        return None
    mapping = {
        "confirm_generate_report": "confirm_outline_generation",
        "reset_params": "reset_params",
        "confirm_task_switch": "confirm_task_switch",
        "cancel_task_switch": "cancel_task_switch",
    }
    return mapping.get(command_name, command_name)


def _build_contract_response(*, original: ChatMessage, internal: Dict[str, Any]) -> Dict[str, Any]:
    ask = _map_contract_ask(internal)
    answer = _map_contract_answer(internal)
    return {
        "conversationId": str(internal.get("session_id") or original.conversationId or ""),
        "chatId": str(original.chatId or ""),
        "status": _derive_contract_status(ask=ask, answer=answer),
        "steps": [],
        "delta": [],
        "ask": ask,
        "answer": answer,
    }


def _map_contract_ask(internal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    action = internal.get("action") if isinstance(internal.get("action"), dict) else None
    reply = str(internal.get("reply") or "")
    if not action:
        if reply.startswith("请提供参数"):
            return {
                "mode": "chat",
                "type": "fill_params",
                "title": "请补充参数",
                "question": reply,
            }
        return None

    action_type = str(action.get("type") or "")
    if action_type == "ask_param":
        param = action.get("param") if isinstance(action.get("param"), dict) else {}
        return {
            "mode": "form",
            "type": "fill_params",
            "title": "请填写参数",
            "parameters": [
                {
                    "id": param.get("id"),
                    "label": param.get("label") or param.get("id"),
                    "inputType": param.get("input_type") or "free_text",
                    "required": True,
                    "multi": bool(param.get("multi")),
                    "options": _map_param_options(param.get("options") or []),
                }
            ],
        }
    if action_type == "review_params":
        parameters: List[Dict[str, Any]] = []
        for item in action.get("params") or []:
            if not isinstance(item, dict):
                continue
            parameters.append(
                {
                    "id": item.get("id"),
                    "label": item.get("label") or item.get("id"),
                    "inputType": "free_text",
                    "required": bool(item.get("required")),
                    "value": item.get("value"),
                }
            )
        return {
            "mode": "form",
            "type": "confirm",
            "parameters": parameters,
        }
    if action_type == "review_outline":
        return {
            "mode": "form",
            "type": "confirm_outline",
            "outline": list(action.get("outline") or []),
            "warnings": list(action.get("warnings") or []),
            "paramsSnapshot": list(action.get("params_snapshot") or []),
        }
    if action_type == "show_template_candidates":
        return {
            "mode": "form",
            "type": "select_template",
            "candidates": list(action.get("candidates") or []),
        }
    if action_type == "confirm_task_switch":
        return {
            "mode": "form",
            "type": "confirm_task_switch",
            "reason": action.get("reason") or "",
            "fromCapability": action.get("from_capability") or "",
            "toCapability": action.get("to_capability") or "",
        }
    return None


def _map_contract_answer(internal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    action = internal.get("action") if isinstance(internal.get("action"), dict) else None
    if action and str(action.get("type") or "") == "download_document":
        document = action.get("document") if isinstance(action.get("document"), dict) else {}
        report_id = str(action.get("report_id") or document.get("instance_id") or "")
        template_instance_id = str(action.get("template_instance_id") or "")
        return {
            "answerType": "report_ready",
            "reportId": report_id,
            "templateInstanceId": template_instance_id,
            "summary": str(internal.get("reply") or "报告已生成。"),
            "document": document,
        }
    return None


def _derive_contract_status(*, ask: Optional[Dict[str, Any]], answer: Optional[Dict[str, Any]]) -> str:
    if answer:
        return "finished"
    if ask:
        return "waiting_user"
    return "finished"


def _wants_sse(request: Request | None) -> bool:
    if request is None:
        return False
    return "text/event-stream" in str(request.headers.get("accept") or "").lower()


def _single_event_stream(payload: Dict[str, Any]):
    chunk = json.dumps(payload, ensure_ascii=False)
    yield f"event: message\ndata: {chunk}\n\n"


def _map_param_options(options: List[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in options:
        if isinstance(item, dict):
            label = item.get("label") or item.get("key")
            value = item.get("key") or item.get("value") or item.get("label")
            if label is None or value is None:
                continue
            normalized.append({"label": label, "value": value})
            continue
        normalized.append({"label": item, "value": item})
    return normalized

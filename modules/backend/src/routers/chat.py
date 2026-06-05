from __future__ import annotations

import json
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..contexts.conversation.application.models import (
    chat_command_from_payload,
    chat_response_to_dict,
    delete_result_to_dict,
    fork_session_command_from_payload,
    fork_session_result_to_dict,
    session_detail_to_dict,
    session_summary_to_dict,
)
from ..shared.agentflow import FlowEvent
from ..infrastructure.dependencies import build_conversation_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import ApplicationError, ErrorCode, NotFoundError, error_response_payload
from ..shared.kernel.http import get_current_user_id

router = APIRouter(prefix="/chat", tags=["chat"])


class ReplyPayload(BaseModel):
    type: str
    sourceChatId: str
    parameters: Optional[dict[str, list[Any]]] = None
    reportContext: Optional[dict[str, Any]] = None


class ChatRequestPayload(BaseModel):
    conversationId: Optional[str] = None
    chatId: Optional[str] = None
    question: Optional[str] = None
    instruction: Optional[str] = None
    reply: Optional[ReplyPayload] = None
    report: Optional[dict[str, Any]] = None
    template: Optional[dict[str, Any]] = None
    attachments: list[dict[str, Any]] = []
    histories: list[dict[str, Any]] = []


class ChatForkRequest(BaseModel):
    source_kind: str
    source_conversation_id: Optional[str] = None
    source_chat_id: Optional[str] = None


@router.get("")
def list_sessions(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return [session_summary_to_dict(item) for item in build_conversation_service(db).list_sessions(user_id=user_id)]


@router.post("")
def chat(
    data: ChatRequestPayload,
    request: Request = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    command = chat_command_from_payload(data.model_dump(exclude_none=True))
    service = build_conversation_service(db)
    if _wants_sse(request):
        return StreamingResponse(
            _flow_event_stream(
                lambda: service.chat_stream(data=command, user_id=user_id),
                conversation_id=command.conversation_id or "",
                chat_id=command.chat_id or "",
                request_id=request.headers.get("X-Request-Id") if request is not None else None,
            ),
            media_type="text/event-stream",
        )
    payload = service.chat(data=command, user_id=user_id)

    return chat_response_to_dict(payload)


@router.post("/{chat_id}/stop")
def stop_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    ok = build_conversation_service(db).stop_chat(chat_id=chat_id, user_id=user_id)
    if not ok:
        raise NotFoundError(
            "当前没有正在运行的对话。",
            error_code=ErrorCode.CONVERSATION_CANCEL_NOT_RUNNING,
        )
    return {"chatId": chat_id, "status": "stop_requested"}


@router.get("/{conversation_id}")
def get_session(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return session_detail_to_dict(build_conversation_service(db).get_session(conversation_id=conversation_id, user_id=user_id))


@router.delete("/{conversation_id}")
def delete_session(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return delete_result_to_dict(
        build_conversation_service(db).delete_session(conversation_id=conversation_id, user_id=user_id)
    )


@router.post("/forks")
def fork_session(
    data: ChatForkRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return fork_session_result_to_dict(
        build_conversation_service(db).fork_session(
            data=fork_session_command_from_payload(data.model_dump(exclude_none=True)),
            user_id=user_id,
        )
    )


def _wants_sse(request: Request | None) -> bool:
    if request is None:
        return False
    return "text/event-stream" in str(request.headers.get("accept") or "").lower()


def _flow_event_stream(events_factory, *, conversation_id: str = "", chat_id: str = "", request_id: str | None = None):
    sequence = 1
    current_conversation_id = conversation_id
    current_chat_id = chat_id
    try:
        events = events_factory()
        for event in events:
            current_conversation_id = event.conversation_id or current_conversation_id
            current_chat_id = event.chat_id or current_chat_id
            sequence = max(sequence, int(event.sequence or sequence))
            chunk = json.dumps(_flow_event_to_chat_stream_event(event), ensure_ascii=False)
            yield f"event: message\ndata: {chunk}\n\n"
            sequence += 1
    except ApplicationError as exc:
        yield _sse_chunk(
            _stream_error_event(
                conversation_id=current_conversation_id,
                chat_id=current_chat_id,
                sequence=sequence,
                error=error_response_payload(exc, request_id=request_id),
            )
        )
        yield _sse_chunk(
            _stream_done_event(
                conversation_id=current_conversation_id,
                chat_id=current_chat_id,
                sequence=sequence + 1,
                status="failed",
            )
        )
    except Exception as exc:
        yield _sse_chunk(
            _stream_error_event(
                conversation_id=current_conversation_id,
                chat_id=current_chat_id,
                sequence=sequence,
                error=error_response_payload(exc, request_id=request_id, fallback_message="系统处理失败，请稍后重试。"),
            )
        )
        yield _sse_chunk(
            _stream_done_event(
                conversation_id=current_conversation_id,
                chat_id=current_chat_id,
                sequence=sequence + 1,
                status="failed",
            )
        )


def _sse_chunk(payload: dict[str, Any]) -> str:
    chunk = json.dumps(payload, ensure_ascii=False)
    return f"event: message\ndata: {chunk}\n\n"


def _stream_error_event(*, conversation_id: str, chat_id: str, sequence: int, error: dict[str, Any]) -> dict[str, Any]:
    return {
        "conversationId": conversation_id,
        "chatId": chat_id,
        "eventType": "error",
        "sequence": sequence,
        "timestamp": int(time.time() * 1000),
        "status": "failed",
        "error": error,
    }


def _stream_done_event(*, conversation_id: str, chat_id: str, sequence: int, status: str) -> dict[str, Any]:
    return {
        "conversationId": conversation_id,
        "chatId": chat_id,
        "eventType": "done",
        "sequence": sequence,
        "timestamp": int(time.time() * 1000),
        "status": status,
    }


def _legacy_event_stream(payload: dict[str, Any]):
    for event in _build_stream_events(payload):
        chunk = json.dumps(event, ensure_ascii=False)
        yield f"event: message\ndata: {chunk}\n\n"


def _flow_event_to_chat_stream_event(event: FlowEvent) -> dict[str, Any]:
    public_event_type = event.event_type
    if event.event_type == "delta":
        public_event_type = "answer"
    if event.event_type in {"tool_call", "tool_result", "checkpoint"}:
        public_event_type = "step_delta"
    payload: dict[str, Any] = {
        "conversationId": event.conversation_id or "",
        "chatId": event.chat_id or "",
        "eventType": public_event_type,
        "sequence": event.sequence,
        "timestamp": int(time.time() * 1000),
        "status": event.status,
    }
    if event.step is not None:
        payload["step"] = {
            "code": event.step.code,
            "stepId": event.step.code,
            "title": event.step.title,
            "status": event.step.status,
            "detail": event.step.detail,
            "parentStepId": event.step.parent_step_id,
            "stepPath": list(event.step.step_path),
        }
    if event.delta:
        payload["delta"] = list(event.delta)
    if event.answer is not None:
        payload["answer"] = event.answer
    if event.ask is not None:
        payload["ask"] = event.ask
    if event.error is not None:
        payload["error"] = event.error
    if event.tool_call is not None:
        payload["toolCall"] = event.tool_call
    if event.tool_result is not None:
        payload["toolResult"] = event.tool_result
    if event.refusal is not None:
        payload["refusal"] = event.refusal
    if event.checkpoint is not None:
        payload["checkpoint"] = {key: value for key, value in event.checkpoint.items() if key != "runId"}
    if event.source_subflow is not None:
        payload["sourceSubflow"] = event.source_subflow
    return payload


def _build_stream_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    conversation_id = str(payload.get("conversationId") or "")
    chat_id = str(payload.get("chatId") or "")
    response_status = str(payload.get("status") or "finished")
    sequence = 1
    events: list[dict[str, Any]] = []

    def append_event(*, event_type: str, status: str, ask: dict[str, Any] | None = None, answer: dict[str, Any] | None = None, delta: list[dict[str, Any]] | None = None):
        nonlocal sequence
        event = {
            "conversationId": conversation_id,
            "chatId": chat_id,
            "eventType": event_type,
            "sequence": sequence,
            "timestamp": int(time.time() * 1000),
            "status": status,
        }
        if ask is not None:
            event["ask"] = ask
        if answer is not None:
            event["answer"] = answer
        if delta is not None:
            event["delta"] = delta
        events.append(event)
        sequence += 1

    answer = payload.get("answer") if isinstance(payload.get("answer"), dict) else None
    ask = payload.get("ask") if isinstance(payload.get("ask"), dict) else None

    append_event(event_type="status", status=response_status)
    if ask is not None:
        append_event(event_type="ask", status=response_status, ask=ask)
    if answer is not None:
        append_event(event_type="answer", status=response_status, answer=answer)
    if payload.get("errors"):
        append_event(event_type="error", status="failed")
    append_event(event_type="done", status=response_status)
    return events

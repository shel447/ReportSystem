from __future__ import annotations

import json
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
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
from ..shared.kernel.errors import ConflictError, NotFoundError, UnsupportedCapabilityError, ValidationError
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
    requestId: Optional[str] = None
    apiVersion: Optional[str] = None


class ChatForkRequest(BaseModel):
    source_kind: str
    source_conversation_id: Optional[str] = None
    source_chat_id: Optional[str] = None


class RunInputRequest(BaseModel):
    text: Optional[str] = None
    payload: dict[str, Any] = {}


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
    try:
        command = chat_command_from_payload(data.model_dump(exclude_none=True))
        service = build_conversation_service(db)
        if _wants_sse(request):
            if hasattr(service, "chat_stream"):
                return StreamingResponse(_flow_event_stream(service.chat_stream(data=command, user_id=user_id)), media_type="text/event-stream")
            payload = service.chat(data=command, user_id=user_id)
            return StreamingResponse(_legacy_event_stream(chat_response_to_dict(payload)), media_type="text/event-stream")
        payload = service.chat(data=command, user_id=user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return chat_response_to_dict(payload)


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    _ = user_id
    ok = build_conversation_service(db).cancel_run(run_id=run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Flow run not found")
    return {"runId": run_id, "status": "cancel_requested"}


@router.post("/runs/{run_id}/input")
def send_run_input(
    run_id: str,
    data: RunInputRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    _ = user_id
    payload = dict(data.payload or {})
    if data.text is not None:
        payload["text"] = data.text
    ok = build_conversation_service(db).send_run_input(run_id=run_id, payload=payload)
    if not ok:
        raise HTTPException(status_code=404, detail="Flow run not found")
    return {"runId": run_id, "status": "input_accepted"}


@router.get("/{conversation_id}")
def get_session(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return session_detail_to_dict(build_conversation_service(db).get_session(conversation_id=conversation_id, user_id=user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}")
def delete_session(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return delete_result_to_dict(
            build_conversation_service(db).delete_session(conversation_id=conversation_id, user_id=user_id)
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedCapabilityError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/forks")
def fork_session(
    data: ChatForkRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return fork_session_result_to_dict(
            build_conversation_service(db).fork_session(
                data=fork_session_command_from_payload(data.model_dump(exclude_none=True)),
                user_id=user_id,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedCapabilityError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


def _wants_sse(request: Request | None) -> bool:
    if request is None:
        return False
    return "text/event-stream" in str(request.headers.get("accept") or "").lower()


def _flow_event_stream(events):
    for event in events:
        chunk = json.dumps(_flow_event_to_chat_stream_event(event), ensure_ascii=False)
        yield f"event: message\ndata: {chunk}\n\n"


def _legacy_event_stream(payload: dict[str, Any]):
    for event in _build_stream_events(payload):
        chunk = json.dumps(event, ensure_ascii=False)
        yield f"event: message\ndata: {chunk}\n\n"


def _flow_event_to_chat_stream_event(event: FlowEvent) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "conversationId": event.conversation_id or "",
        "chatId": event.chat_id or "",
        "runId": event.run_id,
        "eventType": event.event_type,
        "sequence": event.sequence,
        "timestamp": int(time.time() * 1000),
        "status": event.status,
    }
    if event.step is not None:
        payload["step"] = {
            "code": event.step.code,
            "title": event.step.title,
            "status": event.step.status,
            "detail": event.step.detail,
        }
    if event.delta:
        payload["delta"] = list(event.delta)
    if event.answer is not None:
        payload["answer"] = event.answer
    if event.ask is not None:
        payload["ask"] = event.ask
    if event.error is not None:
        payload["error"] = event.error
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

    if answer and answer.get("answerType") == "REPORT":
        append_event(event_type="status", status="running")
        for delta in _report_delta_events(answer):
            append_event(event_type="answer", status="running", delta=[delta])
        append_event(event_type="answer", status=response_status, answer=answer)
        append_event(event_type="done", status=response_status)
        return events

    if answer and answer.get("answerType") == "REPORT_SEGMENT":
        append_event(event_type="status", status="running")
        append_event(event_type="answer", status="running", delta=[_report_segment_delta_event(answer)])
        append_event(event_type="answer", status=response_status, answer=answer)
        append_event(event_type="done", status=response_status)
        return events

    append_event(event_type="status", status=response_status)
    if ask is not None:
        append_event(event_type="ask", status=response_status, ask=ask)
    if answer is not None:
        append_event(event_type="answer", status=response_status, answer=answer)
    if payload.get("errors"):
        append_event(event_type="error", status="failed")
    append_event(event_type="done", status=response_status)
    return events


def _report_delta_events(answer: dict[str, Any]) -> list[dict[str, Any]]:
    report_answer = answer.get("answer") if isinstance(answer.get("answer"), dict) else {}
    report = report_answer.get("report") if isinstance(report_answer.get("report"), dict) else {}
    deltas: list[dict[str, Any]] = []
    report_id = str(report_answer.get("reportId") or "")
    report_title = str(((report.get("basicInfo") or {}).get("name")) or report_id)
    structure_type = str(report.get("structureType") or "flow")
    deltas.append({"action": "init_report", "report": {"reportId": report_id, "title": report_title, "structureType": structure_type}})
    deltas.extend(_catalog_delta_events(list(report.get("catalogs") or []), parent_catalog_id=None, parent_catalog_path=None))
    return deltas


def _report_segment_delta_event(answer: dict[str, Any]) -> dict[str, Any]:
    segment = answer.get("answer") if isinstance(answer.get("answer"), dict) else {}
    section = segment.get("section") if isinstance(segment.get("section"), dict) else {}
    return {
        "action": "add_section",
        "structureType": "flow",
        "sections": [
            {
                "sectionId": str(segment.get("sectionId") or section.get("id") or ""),
                "status": str(segment.get("status") or "available"),
                "requirement": str(((segment.get("outline") or {}).get("renderedRequirement")) or ((segment.get("outline") or {}).get("requirement")) or ""),
                "components": list(section.get("components") or []),
            }
        ],
    }


def _catalog_delta_events(
    catalogs: list[dict[str, Any]],
    *,
    parent_catalog_id: str | None,
    parent_catalog_path: list[int] | None,
) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    if catalogs:
        deltas.append(
            {
                "action": "add_catalog",
                "structureType": "flow",
                "parentCatalogId": parent_catalog_id,
                "parentCatalog": parent_catalog_path,
                "catalogs": [
                    {
                        "catalogId": str(catalog.get("id") or ""),
                        "title": str(catalog.get("name") or catalog.get("title") or catalog.get("id") or ""),
                    }
                    for catalog in catalogs
                ],
            }
        )

    for index, catalog in enumerate(catalogs):
        catalog_path = [*parent_catalog_path, index] if parent_catalog_path is not None else [index]
        sections = list(catalog.get("sections") or [])
        if sections:
            deltas.append(
                {
                    "action": "add_section",
                    "structureType": "flow",
                    "parentCatalogId": str(catalog.get("id") or ""),
                    "parentCatalog": catalog_path,
                    "sections": [
                        {
                            "sectionId": str(section.get("id") or ""),
                            "status": "finished",
                            "requirement": str(section.get("title") or section.get("requirement") or section.get("id") or ""),
                            "components": list(section.get("components") or []),
                        }
                        for section in sections
                    ],
                }
            )
        deltas.extend(
            _catalog_delta_events(
                list(catalog.get("subCatalogs") or []),
                parent_catalog_id=str(catalog.get("id") or ""),
                parent_catalog_path=catalog_path,
            )
        )
    return deltas

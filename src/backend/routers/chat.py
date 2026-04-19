from __future__ import annotations

import json
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.dependencies import build_conversation_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import ConflictError, NotFoundError, ValidationError
from ..shared.kernel.http import resolve_user_id

router = APIRouter(prefix="/chat", tags=["chat"])


class ReplyPayload(BaseModel):
    type: str
    parameters: Optional[list[dict[str, Any]]] = None
    reportContext: Optional[dict[str, Any]] = None


class ChatRequestPayload(BaseModel):
    conversationId: Optional[str] = None
    chatId: Optional[str] = None
    question: Optional[str] = None
    instruction: Optional[str] = None
    reply: Optional[ReplyPayload] = None
    attachments: list[dict[str, Any]] = []
    histories: list[dict[str, Any]] = []
    requestId: Optional[str] = None
    apiVersion: Optional[str] = None


class ChatForkRequest(BaseModel):
    source_kind: str
    source_conversation_id: Optional[str] = None
    source_chat_id: Optional[str] = None


@router.get("")
def list_sessions(db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    return build_conversation_service(db).list_sessions(user_id=resolve_user_id(user_id))


@router.post("")
def send_message(
    data: ChatRequestPayload,
    request: Request = None,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        payload = build_conversation_service(db).send_message(data=data.model_dump(exclude_none=True), user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if _wants_sse(request):
        return StreamingResponse(_single_event_stream(payload), media_type="text/event-stream")
    return payload


@router.get("/{conversation_id}")
def get_session(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return build_conversation_service(db).get_session(conversation_id=conversation_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{conversation_id}")
def delete_session(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return build_conversation_service(db).delete_session(conversation_id=conversation_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/forks")
def fork_session(
    data: ChatForkRequest,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return build_conversation_service(db).fork_session(data=data.model_dump(exclude_none=True), user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _wants_sse(request: Request | None) -> bool:
    if request is None:
        return False
    return "text/event-stream" in str(request.headers.get("accept") or "").lower()


def _single_event_stream(payload: dict[str, Any]):
    for event in _build_stream_events(payload):
        chunk = json.dumps(event, ensure_ascii=False)
        yield f"event: message\ndata: {chunk}\n\n"


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
    deltas.append({"action": "init_report", "report": {"reportId": report_id, "title": report_title}})
    deltas.extend(_catalog_delta_events(list(report.get("catalogs") or []), parent_catalog_id=None, parent_catalog_path=None))
    return deltas


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

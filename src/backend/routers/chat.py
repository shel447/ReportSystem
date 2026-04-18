from __future__ import annotations

import json
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
    chunk = json.dumps(payload, ensure_ascii=False)
    yield f"event: message\ndata: {chunk}\n\n"

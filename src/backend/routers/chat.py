"""对话交互路由"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..infrastructure.dependencies import build_conversation_service
from ..shared.kernel.errors import ConflictError, NotFoundError, ValidationError

router = APIRouter(prefix="/chat", tags=["chat"])


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
    return build_conversation_service(db).list_sessions()


@router.post("")
def send_message(data: ChatMessage, db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).send_message(data=data)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        detail = str(exc)
        status_code = 502 if detail.startswith("request to") or detail.startswith("[WinError") else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).get_session(session_id=session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/forks")
def fork_session(data: ChatForkRequest, db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).fork_session(data=data)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Unsupported fork source" else 400, detail=str(exc)) from exc


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).delete_session(session_id=session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

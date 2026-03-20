from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .models import ChatSession

MAX_SESSION_TITLE_LENGTH = 28
MAX_SESSION_PREVIEW_LENGTH = 48


def list_chat_sessions(db: Session, *, user_id: str = "default") -> List[Dict[str, Any]]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc(), ChatSession.session_id.desc())
        .all()
    )
    return [serialize_chat_session_summary(session) for session in sessions]


def serialize_chat_session_summary(session: ChatSession) -> Dict[str, Any]:
    visible = visible_chat_messages(session.messages or [])
    return {
        "session_id": session.session_id,
        "title": derive_session_title(session.messages or []),
        "matched_template_id": session.matched_template_id,
        "instance_id": session.instance_id,
        "message_count": len(visible),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "last_message_preview": build_last_message_preview(visible),
    }


def visible_chat_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    visible: List[Dict[str, Any]] = []
    for item in messages or []:
        role = item.get("role")
        if role not in {"user", "assistant"}:
            continue
        meta = item.get("meta") or {}
        if meta.get("type") == "context_state":
            continue
        content = str(item.get("content") or "").strip()
        if not content and not item.get("action"):
            continue
        visible.append(item)
    return visible


def derive_session_title(messages: List[Dict[str, Any]]) -> str:
    for item in visible_chat_messages(messages):
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content:
            return truncate_text(content, MAX_SESSION_TITLE_LENGTH)
    return "未命名会话"


def build_last_message_preview(messages: List[Dict[str, Any]]) -> str:
    for item in reversed(messages):
        content = str(item.get("content") or "").strip()
        if content:
            return truncate_text(content, MAX_SESSION_PREVIEW_LENGTH)
    return ""


def truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


"""统一对话上下文的会话与消息流持久化适配器。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ....infrastructure.persistence.models import Chat as ChatRow
from ....infrastructure.persistence.models import Conversation as ConversationRow
from ....infrastructure.persistence.models import gen_id, utc_now


class SqlAlchemyConversationRepository:
    """会话容器的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, conversation_id: str, *, user_id: str):
        row = self.db.get(ConversationRow, conversation_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    def create(self, *, conversation_id: str | None, user_id: str) -> ConversationRow:
        row = ConversationRow(
            id=conversation_id or gen_id(),
            user_id=user_id,
            title="",
            fork_meta={},
            status="active",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_all(self, *, user_id: str) -> list[ConversationRow]:
        return (
            self.db.query(ConversationRow)
            .filter(ConversationRow.user_id == user_id)
            .order_by(ConversationRow.updated_at.desc())
            .all()
        )

    def delete(self, conversation_id: str, *, user_id: str) -> bool:
        row = self.get(conversation_id, user_id=user_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def save(self, row: ConversationRow) -> ConversationRow:
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row


class SqlAlchemyChatRepository:
    """有序聊天消息流的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def append_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: str,
        content: dict[str, Any],
        action: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
        chat_id: str | None = None,
    ) -> ChatRow:
        # 序号字段是单条会话消息流的权威排序键。
        seq_no = self.next_seq_no(conversation_id)
        row = ChatRow(
            id=chat_id or gen_id(),
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            action=action,
            meta=meta or {},
            seq_no=seq_no,
            created_at=utc_now(),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_conversation(self, conversation_id: str, *, user_id: str) -> list[ChatRow]:
        return (
            self.db.query(ChatRow)
            .filter(ChatRow.conversation_id == conversation_id, ChatRow.user_id == user_id)
            .order_by(ChatRow.seq_no.asc())
            .all()
        )

    def mark_ask_replied(self, *, conversation_id: str, user_id: str, source_chat_id: str) -> bool:
        """按 reply.sourceChatId 精确回写被消费的追问消息。"""
        row = (
            self.db.query(ChatRow)
            .filter(
                ChatRow.id == source_chat_id,
                ChatRow.conversation_id == conversation_id,
                ChatRow.user_id == user_id,
                ChatRow.role == "assistant",
            )
            .one_or_none()
        )
        if row is None:
            return False

        content = row.content if isinstance(row.content, dict) else {}
        response = content.get("response") if isinstance(content.get("response"), dict) else None
        ask = response.get("ask") if isinstance(response, dict) else None
        if not isinstance(ask, dict) or ask.get("status") != "pending":
            return False

        updated = dict(content)
        updated_response = dict(response)
        updated_ask = dict(ask)
        updated_ask["status"] = "replied"
        updated_response["ask"] = updated_ask
        updated["response"] = updated_response
        row.content = updated
        self.db.add(row)
        self.db.commit()
        return True

    def next_seq_no(self, conversation_id: str) -> int:
        last = (
            self.db.query(ChatRow)
            .filter(ChatRow.conversation_id == conversation_id)
            .order_by(ChatRow.seq_no.desc())
            .first()
        )
        return int(last.seq_no or 0) + 1 if last else 1

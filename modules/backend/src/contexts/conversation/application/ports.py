"""Application ports for platform-hosted conversation and safety services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class GuardrailResult:
    passed: bool
    reason: str = ""


class GuardrailGateway(Protocol):
    def check_question(self, question: str, *, user_id: str) -> GuardrailResult: ...
    def check_answer(self, answer: str, *, user_id: str) -> GuardrailResult: ...
    def check_application_security(self, *, kind: str, content: str, user_id: str) -> GuardrailResult: ...


@dataclass(slots=True)
class HostedConversation:
    conversation_id: str
    title: str = ""
    status: str = "active"
    updated_at: str | None = None
    last_message_preview: str = ""


@dataclass(slots=True)
class HostedChat:
    chat_id: str
    conversation_id: str
    question: str = ""
    request_payload: dict[str, Any] = field(default_factory=dict)
    response_payload: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


class ConversationHistoryGateway(Protocol):
    def create_conversation(self, *, title: str, description: str | None, user_id: str) -> HostedConversation: ...
    def create_chat(self, *, conversation_id: str, question: str, user_id: str) -> HostedChat: ...
    def import_chat(self, *, chat: HostedChat, user_id: str) -> None: ...
    def query_chat_history(self, *, conversation_id: str, page_num: int, page_size: int, user_id: str) -> list[HostedChat]: ...
    def get_chat_detail(self, *, chat_id: str, user_id: str) -> HostedChat | None: ...
    def list_conversations(self, *, page_num: int, page_size: int, user_id: str) -> list[HostedConversation]: ...

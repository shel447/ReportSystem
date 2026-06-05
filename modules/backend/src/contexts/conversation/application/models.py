"""统一对话应用层的正式输入输出模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..domain.models import (
    ChatContext,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    ForkSource,
    ScenarioTrace,
    conversation_message_action_to_dict,
    conversation_message_content_to_dict,
    conversation_message_meta_to_dict,
)
from ....shared.kernel.errors import error_response_payload

Scalar = str | int | float | bool


@dataclass(slots=True)
class ChatReply:
    """通用答复外壳；业务字段只在场景 handler 边界解释。"""

    type: str
    source_chat_id: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChatCommand:
    """聊天入口命令；raw_payload 仅短暂保留 HTTP 边界原始字段。"""

    conversation_id: str | None = None
    chat_id: str | None = None
    question: str | None = None
    instruction: str | None = None
    reply: ChatReply | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeleteResult:
    """删除会话结果。"""

    message: str


@dataclass(slots=True)
class ForkSessionCommand:
    """派生会话命令。"""

    source_kind: str
    source_conversation_id: str | None = None
    source_chat_id: str | None = None


@dataclass(slots=True)
class ForkSessionResult:
    """派生会话结果。"""

    conversation_id: str


@dataclass(slots=True)
class ChatAsk:
    """通用追问外壳；具体追问内容由业务场景扩展定义。"""

    status: str
    mode: str
    type: str
    title: str
    text: str
    fields: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ChatAnswerEnvelope:
    """聊天最终答案包络。"""

    answer_type: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ChatStep:
    """聊天执行步骤。"""

    code: str
    status: str
    title: str | None = None
    detail: str | None = None
    parent_step_id: str | None = None
    step_path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChatResponse:
    """统一聊天响应。"""

    conversation_id: str
    chat_id: str
    status: str
    steps: list[ChatStep] = field(default_factory=list)
    ask: ChatAsk | None = None
    answer: ChatAnswerEnvelope | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    timestamp: int | None = None


@dataclass(slots=True)
class SessionSummary:
    """会话列表项。"""

    conversation_id: str
    title: str
    status: str
    updated_at: str | None
    last_message_preview: str


@dataclass(slots=True)
class ConversationAnswer:
    """一轮对话中的一条系统回答。"""

    type: str
    content: str
    answer_time: int | str | None = None


@dataclass(slots=True)
class ConversationRecord:
    """会话历史中的一轮问答。"""

    chat_id: str
    question: str
    ask_time: int | str | None = None
    answers: list[ConversationAnswer] = field(default_factory=list)


@dataclass(slots=True)
class SessionMessage:
    """会话消息视图。"""

    chat_id: str
    role: str
    content: "ConversationMessageContent"
    action: "ConversationMessageAction | None"
    meta: "ConversationMessageMeta | None"
    created_at: str | None


@dataclass(slots=True)
class SessionDetail:
    """会话详情视图。"""

    conversation_id: str
    title: str
    status: str
    records: list[ConversationRecord] = field(default_factory=list)
    messages: list[SessionMessage] = field(default_factory=list)


def chat_command_from_payload(payload: dict[str, Any]) -> ChatCommand:
    reply_payload = payload.get("reply") if isinstance(payload.get("reply"), dict) else None
    reply = None
    if reply_payload is not None:
        reply = ChatReply(
            type=str(reply_payload.get("type") or ""),
            source_chat_id=str(reply_payload.get("sourceChatId") or ""),
            raw_payload=dict(reply_payload),
        )
    return ChatCommand(
        conversation_id=str(payload.get("conversationId") or "").strip() or None,
        chat_id=str(payload.get("chatId") or "").strip() or None,
        question=str(payload.get("question") or "").strip() or None,
        instruction=str(payload.get("instruction") or "").strip() or None,
        reply=reply,
        raw_payload=dict(payload),
    )


def fork_session_command_from_payload(payload: dict[str, Any]) -> ForkSessionCommand:
    return ForkSessionCommand(
        source_kind=str(payload.get("source_kind") or ""),
        source_conversation_id=str(payload.get("source_conversation_id") or "").strip() or None,
        source_chat_id=str(payload.get("source_chat_id") or "").strip() or None,
    )


def chat_ask_to_dict(ask: ChatAsk) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": ask.status,
        "mode": ask.mode,
        "type": ask.type,
        "title": ask.title,
        "text": ask.text,
    }
    payload.update(ask.fields)
    return payload


def chat_answer_to_dict(answer: ChatAnswerEnvelope) -> dict[str, object]:
    return {"answerType": answer.answer_type, "answer": dict(answer.payload)}


def chat_response_to_dict(response: ChatResponse) -> dict[str, object]:
    return {
        "conversationId": response.conversation_id,
        "chatId": response.chat_id,
        "status": response.status,
        "steps": [
            {
                "code": item.code,
                "stepId": item.code,
                "status": item.status,
                "title": item.title,
                "detail": item.detail,
                "parentStepId": item.parent_step_id,
                "stepPath": list(item.step_path),
            }
            for item in response.steps
        ],
        "ask": chat_ask_to_dict(response.ask) if response.ask is not None else None,
        "answer": chat_answer_to_dict(response.answer) if response.answer is not None else None,
        "errors": [_normalize_error(item) for item in response.errors],
        "timestamp": response.timestamp,
    }


def session_summary_to_dict(summary: SessionSummary) -> dict[str, object]:
    return {
        "conversationId": summary.conversation_id,
        "title": summary.title,
        "status": summary.status,
        "updatedAt": summary.updated_at,
        "lastMessagePreview": summary.last_message_preview,
    }


def session_message_to_dict(message: SessionMessage) -> dict[str, object]:
    return {
        "chatId": message.chat_id,
        "role": message.role,
        "content": conversation_message_content_to_dict(message.content),
        "action": conversation_message_action_to_dict(message.action),
        "meta": conversation_message_meta_to_dict(message.meta),
        "createdAt": message.created_at,
    }


def conversation_answer_to_dict(answer: ConversationAnswer) -> dict[str, object]:
    return {
        "type": answer.type,
        "content": answer.content,
        "answerTime": answer.answer_time,
    }


def conversation_record_to_dict(record: ConversationRecord) -> dict[str, object]:
    return {
        "chatId": record.chat_id,
        "question": record.question,
        "askTime": record.ask_time,
        "answers": [conversation_answer_to_dict(item) for item in record.answers],
    }


def session_detail_to_dict(detail: SessionDetail) -> dict[str, object]:
    return {
        "conversationId": detail.conversation_id,
        "title": detail.title,
        "status": detail.status,
        "records": [conversation_record_to_dict(item) for item in detail.records],
    }


def delete_result_to_dict(result: DeleteResult) -> dict[str, object]:
    return {"message": result.message}


def fork_session_result_to_dict(result: ForkSessionResult) -> dict[str, object]:
    return {"conversationId": result.conversation_id}


def _normalize_error(error: object) -> dict[str, Any]:
    if isinstance(error, dict):
        return dict(error)
    return error_response_payload(str(error or "系统处理失败，请稍后重试。"))

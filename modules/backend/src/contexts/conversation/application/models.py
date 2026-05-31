"""统一对话应用层的正式输入输出模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...report.application.generation_models import ReportAnswerView, report_answer_view_to_dict
from ...report.application.scenario_models import (
    ReportAskPayload,
    ReportReplyPayload,
    ReportSegmentAnswer,
    ReportSegmentRequest,
    report_ask_payload_from_dict,
    report_ask_payload_to_dict,
    report_reply_payload_from_dict,
    report_segment_answer_to_dict,
    report_segment_request_from_dict,
)
from ...report.application.template_models import TemplateImportPreview, template_import_preview_to_dict

Scalar = str | int | float | bool


@dataclass(slots=True)
class ChatReply:
    """通用答复外壳；报告参数和报告上下文属于报告场景扩展。"""

    type: str
    source_chat_id: str
    report_payload: ReportReplyPayload | None = None


@dataclass(slots=True)
class ChatCommand:
    """聊天入口命令。"""

    conversation_id: str | None = None
    chat_id: str | None = None
    question: str | None = None
    instruction: str | None = None
    reply: ChatReply | None = None
    report_segment: ReportSegmentRequest | None = None
    request_id: str | None = None
    api_version: str | None = None


@dataclass(slots=True)
class ChatContext:
    """通用对话上下文，不承载任何具体业务场景的领域对象。"""

    conversation_id: str
    chat_id: str
    user_id: str
    instruction: str
    question: str | None = None
    reply_type: str | None = None
    source_chat_id: str | None = None
    request_id: str | None = None
    api_version: str = "v1"


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
    report_payload: ReportAskPayload | None = None


@dataclass(slots=True)
class ChatAnswerEnvelope:
    """聊天最终答案包络。"""

    answer_type: str
    report: ReportAnswerView | None = None
    report_template_preview: TemplateImportPreview | None = None
    report_segment: ReportSegmentAnswer | None = None


@dataclass(slots=True)
class ChatStep:
    """聊天执行步骤。"""

    code: str
    status: str


@dataclass(slots=True)
class ChatResponse:
    """统一聊天响应。"""

    conversation_id: str
    chat_id: str
    status: str
    steps: list[ChatStep] = field(default_factory=list)
    ask: ChatAsk | None = None
    answer: ChatAnswerEnvelope | None = None
    errors: list[str] = field(default_factory=list)
    request_id: str | None = None
    timestamp: int | None = None
    api_version: str = "v1"


@dataclass(slots=True)
class SessionSummary:
    """会话列表项。"""

    conversation_id: str
    title: str
    status: str
    updated_at: str | None
    last_message_preview: str


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
    messages: list[SessionMessage] = field(default_factory=list)


@dataclass(slots=True)
class ConversationMessageContent:
    """聊天消息内容。"""

    question: str | None = None
    response: ChatResponse | None = None


@dataclass(slots=True)
class ConversationMessageAction:
    """聊天消息动作元信息。"""

    type: str


@dataclass(slots=True)
class ConversationMessageMeta:
    """聊天消息附加元信息。"""

    status: str | None = None
    forked_from: dict[str, str] | None = None


def chat_command_from_payload(payload: dict[str, Any]) -> ChatCommand:
    reply_payload = payload.get("reply") if isinstance(payload.get("reply"), dict) else None
    reply = None
    if reply_payload is not None:
        reply = ChatReply(
            type=str(reply_payload.get("type") or ""),
            source_chat_id=str(reply_payload.get("sourceChatId") or ""),
            report_payload=report_reply_payload_from_dict(reply_payload),
        )
    return ChatCommand(
        conversation_id=str(payload.get("conversationId") or "").strip() or None,
        chat_id=str(payload.get("chatId") or "").strip() or None,
        question=str(payload.get("question") or "").strip() or None,
        instruction=str(payload.get("instruction") or "").strip() or None,
        reply=reply,
        report_segment=report_segment_request_from_dict(payload.get("template")),
        request_id=str(payload.get("requestId") or "").strip() or None,
        api_version=str(payload.get("apiVersion") or "").strip() or None,
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
    payload.update(report_ask_payload_to_dict(ask.report_payload))
    return payload


def chat_answer_to_dict(answer: ChatAnswerEnvelope) -> dict[str, object]:
    payload: dict[str, object] = {"answerType": answer.answer_type}
    if answer.report is not None:
        payload["answer"] = report_answer_view_to_dict(answer.report)
    elif answer.report_template_preview is not None:
        payload["answer"] = template_import_preview_to_dict(answer.report_template_preview)
    elif answer.report_segment is not None:
        payload["answer"] = report_segment_answer_to_dict(answer.report_segment)
    else:
        payload["answer"] = {}
    return payload


def chat_response_to_dict(response: ChatResponse) -> dict[str, object]:
    return {
        "conversationId": response.conversation_id,
        "chatId": response.chat_id,
        "status": response.status,
        "steps": [{"code": item.code, "status": item.status} for item in response.steps],
        "ask": chat_ask_to_dict(response.ask) if response.ask is not None else None,
        "answer": chat_answer_to_dict(response.answer) if response.answer is not None else None,
        "errors": list(response.errors),
        "requestId": response.request_id,
        "timestamp": response.timestamp,
        "apiVersion": response.api_version,
    }


def session_summary_to_dict(summary: SessionSummary) -> dict[str, object]:
    return {
        "conversationId": summary.conversation_id,
        "title": summary.title,
        "status": summary.status,
        "updatedAt": summary.updated_at,
        "lastMessagePreview": summary.last_message_preview,
    }


def conversation_message_content_to_dict(content: ConversationMessageContent) -> dict[str, object]:
    payload: dict[str, object] = {}
    if content.question is not None:
        payload["question"] = content.question
    if content.response is not None:
        payload["response"] = chat_response_to_dict(content.response)
    return payload


def conversation_message_action_to_dict(action: ConversationMessageAction | None) -> dict[str, object] | None:
    if action is None:
        return None
    return {"type": action.type}


def conversation_message_meta_to_dict(meta: ConversationMessageMeta | None) -> dict[str, object] | None:
    if meta is None:
        return None
    payload: dict[str, object] = {}
    if meta.status is not None:
        payload["status"] = meta.status
    if meta.forked_from is not None:
        payload["forkedFrom"] = dict(meta.forked_from)
    return payload


def session_message_to_dict(message: SessionMessage) -> dict[str, object]:
    return {
        "chatId": message.chat_id,
        "role": message.role,
        "content": conversation_message_content_to_dict(message.content),
        "action": conversation_message_action_to_dict(message.action),
        "meta": conversation_message_meta_to_dict(message.meta),
        "createdAt": message.created_at,
    }


def session_detail_to_dict(detail: SessionDetail) -> dict[str, object]:
    return {
        "conversationId": detail.conversation_id,
        "title": detail.title,
        "status": detail.status,
        "messages": [session_message_to_dict(item) for item in detail.messages],
    }


def delete_result_to_dict(result: DeleteResult) -> dict[str, object]:
    return {"message": result.message}


def fork_session_result_to_dict(result: ForkSessionResult) -> dict[str, object]:
    return {"conversationId": result.conversation_id}

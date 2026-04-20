"""统一对话应用层的正式输入输出模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...report_runtime.application.models import ReportAnswerView, report_answer_view_to_dict
from ...report_runtime.domain.models import TemplateInstance, template_instance_from_dict, template_instance_to_dict
from ...template_catalog.domain.models import Parameter, parameter_to_dict
from ...template_catalog.application.models import TemplateImportPreview, template_import_preview_to_dict

Scalar = str | int | float | bool


@dataclass(slots=True)
class ChatReply:
    """结构化回复命令。"""

    type: str
    source_chat_id: str
    parameters: dict[str, list[Scalar]] = field(default_factory=dict)
    template_instance: TemplateInstance | None = None


@dataclass(slots=True)
class ChatCommand:
    """聊天入口命令。"""

    conversation_id: str | None = None
    chat_id: str | None = None
    question: str | None = None
    instruction: str | None = None
    reply: ChatReply | None = None
    request_id: str | None = None
    api_version: str | None = None


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
    """结构化追问载荷。"""

    status: str
    mode: str
    type: str
    title: str
    text: str
    parameters: list[Parameter] = field(default_factory=list)
    template_instance: TemplateInstance | None = None


@dataclass(slots=True)
class ChatAnswerEnvelope:
    """聊天最终答案包络。"""

    answer_type: str
    report: ReportAnswerView | None = None
    report_template_preview: TemplateImportPreview | None = None


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
    template_instance_payload = ((reply_payload.get("reportContext") or {}).get("templateInstance")) if isinstance(reply_payload, dict) and isinstance(reply_payload.get("reportContext"), dict) else None
    reply = None
    if reply_payload is not None:
        reply = ChatReply(
            type=str(reply_payload.get("type") or ""),
            source_chat_id=str(reply_payload.get("sourceChatId") or ""),
            parameters={
                str(key): list(value or [])
                for key, value in dict(reply_payload.get("parameters") or {}).items()
                if isinstance(value, list)
            },
            template_instance=template_instance_from_dict(template_instance_payload) if isinstance(template_instance_payload, dict) else None,
        )
    return ChatCommand(
        conversation_id=str(payload.get("conversationId") or "").strip() or None,
        chat_id=str(payload.get("chatId") or "").strip() or None,
        question=str(payload.get("question") or "").strip() or None,
        instruction=str(payload.get("instruction") or "").strip() or None,
        reply=reply,
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
        "parameters": [parameter_to_dict(item) for item in ask.parameters],
    }
    if ask.template_instance is not None:
        payload["reportContext"] = {"templateInstance": template_instance_to_dict(ask.template_instance)}
    return payload


def chat_answer_to_dict(answer: ChatAnswerEnvelope) -> dict[str, object]:
    payload: dict[str, object] = {"answerType": answer.answer_type}
    if answer.report is not None:
        payload["answer"] = report_answer_view_to_dict(answer.report)
    elif answer.report_template_preview is not None:
        payload["answer"] = template_import_preview_to_dict(answer.report_template_preview)
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

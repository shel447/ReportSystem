"""通用对话应用服务，负责会话、多轮澄清和业务场景分发。"""

from __future__ import annotations

from typing import Any

from ....shared.kernel.errors import NotFoundError, ValidationError
from ...report.application.scenario_models import (
    ReportScenarioCommand,
    report_ask_payload_from_dict,
    report_scenario_answer_from_dict,
)
from .models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatContext,
    ChatResponse,
    DeleteResult,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    ForkSessionCommand,
    ForkSessionResult,
    SessionDetail,
    SessionMessage,
    SessionSummary,
)


class ConversationService:
    """拥有聊天协议、消息流水和通用追问生命周期的应用服务。"""

    def __init__(self, *, conversation_repository, chat_repository, report_service) -> None:
        self.conversation_repository = conversation_repository
        self.chat_repository = chat_repository
        self.report_service = report_service

    def list_sessions(self, *, user_id: str) -> list[SessionSummary]:
        """返回会话列表视图，仅包含最后一条消息预览。"""
        result = []
        for conversation in self.conversation_repository.list_all(user_id=user_id):
            messages = self.chat_repository.list_by_conversation(conversation.id, user_id=user_id)
            latest = messages[-1] if messages else None
            result.append(
                SessionSummary(
                    conversation_id=conversation.id,
                    title=conversation.title or "未命名会话",
                    status=conversation.status,
                    updated_at=conversation.updated_at.isoformat().replace("+00:00", "Z") if conversation.updated_at else None,
                    last_message_preview=_message_preview(_message_content_from_row(latest) if latest else ConversationMessageContent()),
                )
            )
        return result

    def get_session(self, *, conversation_id: str, user_id: str) -> SessionDetail:
        """加载单个会话，并按顺序组装聊天消息流。"""
        conversation = self.conversation_repository.get(conversation_id, user_id=user_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        messages = self.chat_repository.list_by_conversation(conversation_id, user_id=user_id)
        return SessionDetail(
            conversation_id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            messages=[
                SessionMessage(
                    chat_id=row.id,
                    role=row.role,
                    content=_message_content_from_row(row),
                    action=_message_action_from_row(row),
                    meta=_message_meta_from_row(row),
                    created_at=row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
                )
                for row in messages
            ],
        )

    def delete_session(self, *, conversation_id: str, user_id: str) -> DeleteResult:
        if not self.conversation_repository.delete(conversation_id, user_id=user_id):
            raise NotFoundError("Conversation not found")
        return DeleteResult(message="deleted")

    def fork_session(self, *, data: ForkSessionCommand, user_id: str) -> ForkSessionResult:
        """从历史聊天节点派生出一个新会话。"""
        source_conversation_id = str(data.source_conversation_id or "").strip()
        source_chat_id = str(data.source_chat_id or "").strip()
        source = self.conversation_repository.get(source_conversation_id, user_id=user_id)
        if source is None:
            raise NotFoundError("Source conversation not found")
        messages = self.chat_repository.list_by_conversation(source_conversation_id, user_id=user_id)
        target = next((row for row in messages if row.id == source_chat_id), None)
        if target is None:
            raise NotFoundError("Source chat not found")
        new_conversation = self.conversation_repository.create(conversation_id=None, user_id=user_id)
        self.chat_repository.append_message(
            conversation_id=new_conversation.id,
            user_id=user_id,
            role=target.role,
            content=_message_content_from_row(target),
            action=_message_action_from_row(target),
            meta=ConversationMessageMeta(status=None, forked_from={"conversationId": source_conversation_id, "chatId": source_chat_id}),
        )
        new_conversation.title = source.title or _message_preview(_message_content_from_row(target))
        self.conversation_repository.save(new_conversation)
        return ForkSessionResult(conversation_id=new_conversation.id)

    def chat(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
        """通过通用聊天通道推进一次业务场景交互。"""
        instruction = str(data.instruction or "generate_report").strip() or "generate_report"
        if instruction == "extract_report_template":
            result = self.report_service.chat(
                command=ReportScenarioCommand(
                    conversation_id=data.conversation_id or "",
                    chat_id=data.chat_id or "",
                    user_id=user_id,
                    instruction=instruction,
                    question=data.question,
                )
            )
            return _response_from_scenario_result(data=data, conversation_id=data.conversation_id or "", chat_id=data.chat_id or "", result=result)

        conversation = self._ensure_conversation(data=data, user_id=user_id)
        user_chat = self.chat_repository.append_message(
            conversation_id=conversation.id,
            user_id=user_id,
            role="user",
            content=ConversationMessageContent(question=str(data.question or "")),
            chat_id=data.chat_id,
        )
        context = ChatContext(
            conversation_id=conversation.id,
            chat_id=user_chat.id,
            user_id=user_id,
            instruction=instruction,
            question=data.question,
            reply_type=data.reply.type if data.reply else None,
            source_chat_id=data.reply.source_chat_id if data.reply else None,
            request_id=data.request_id,
            api_version=data.api_version or "v1",
        )
        self._consume_reply(context=context)
        result = self.report_service.chat(
            command=ReportScenarioCommand(
                conversation_id=context.conversation_id,
                chat_id=context.chat_id,
                user_id=context.user_id,
                instruction=context.instruction,
                question=context.question,
                reply_type=context.reply_type,
                reply=data.reply.report_payload if data.reply else None,
                segment=data.report_segment,
            )
        )
        if result.conversation_title and not conversation.title:
            conversation.title = result.conversation_title
            self.conversation_repository.save(conversation)
        response = _response_from_scenario_result(
            data=data,
            conversation_id=context.conversation_id,
            chat_id=_random_id("chat"),
            result=result,
        )
        self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=response.chat_id, response=response)
        return response

    def _consume_reply(self, *, context: ChatContext) -> None:
        """消费任意业务场景的结构化答复，不解释其业务字段。"""
        if context.reply_type is None:
            return
        source_chat_id = str(context.source_chat_id or "").strip()
        if not source_chat_id:
            raise ValidationError("reply.sourceChatId is required")
        if not self.chat_repository.mark_ask_replied(
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            source_chat_id=source_chat_id,
        ):
            raise ValidationError("reply.sourceChatId must reference a pending ask in the same conversation")

    def _ensure_conversation(self, *, data: ChatCommand, user_id: str):
        conversation_id = str(data.conversation_id or "").strip()
        if conversation_id:
            existing = self.conversation_repository.get(conversation_id, user_id=user_id)
            if existing is None:
                raise NotFoundError("Conversation not found")
            return existing
        return self.conversation_repository.create(conversation_id=None, user_id=user_id)

    def _append_assistant_message(self, *, conversation_id: str, user_id: str, chat_id: str, response: ChatResponse) -> None:
        self.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=ConversationMessageContent(response=response),
            action=ConversationMessageAction(type="chat_response"),
            meta=ConversationMessageMeta(status=response.status),
            chat_id=chat_id,
        )


def _response_from_scenario_result(*, data: ChatCommand, conversation_id: str, chat_id: str, result) -> ChatResponse:
    ask = None
    if result.ask is not None:
        ask = ChatAsk(
            status="pending",
            mode=result.ask.mode,
            type=result.ask.type,
            title=result.ask.title,
            text=result.ask.text,
            report_payload=result.ask.payload,
        )
    answer = None
    if result.answer is not None:
        answer = ChatAnswerEnvelope(
            answer_type=result.answer.answer_type,
            report=result.answer.report,
            report_template_preview=result.answer.report_template_preview,
            report_segment=result.answer.report_segment,
        )
    return ChatResponse(
        conversation_id=conversation_id,
        chat_id=chat_id,
        status=result.status,
        ask=ask,
        answer=answer,
        errors=[],
        request_id=data.request_id,
        timestamp=_epoch_ms(),
        api_version=data.api_version or "v1",
    )


def _message_preview(content: ConversationMessageContent) -> str:
    if content.question:
        return str(content.question)[:80]
    response = content.response
    if response is not None and response.ask is not None:
        return str(response.ask.title or response.ask.text or "")[:80]
    return ""


def _message_content_from_row(row) -> ConversationMessageContent:
    content = row.content if isinstance(row.content, dict) else {}
    response_payload = content.get("response") if isinstance(content.get("response"), dict) else None
    response = _chat_response_from_payload(response_payload) if response_payload is not None else None
    return ConversationMessageContent(question=content.get("question"), response=response)


def _message_action_from_row(row) -> ConversationMessageAction | None:
    if not isinstance(row.action, dict):
        return None
    action_type = str(row.action.get("type") or "").strip()
    return ConversationMessageAction(type=action_type) if action_type else None


def _message_meta_from_row(row) -> ConversationMessageMeta | None:
    if not isinstance(row.meta, dict):
        return None
    forked_from = row.meta.get("forkedFrom") if isinstance(row.meta.get("forkedFrom"), dict) else None
    status = str(row.meta.get("status") or "").strip() or None
    return ConversationMessageMeta(status=status, forked_from=dict(forked_from) if forked_from else None)


def _chat_response_from_payload(payload: dict[str, Any]) -> ChatResponse:
    ask_payload = payload.get("ask") if isinstance(payload.get("ask"), dict) else None
    answer_payload = payload.get("answer") if isinstance(payload.get("answer"), dict) else None
    ask = (
        ChatAsk(
            status=str(ask_payload.get("status") or ""),
            mode=str(ask_payload.get("mode") or ""),
            type=str(ask_payload.get("type") or ""),
            title=str(ask_payload.get("title") or ""),
            text=str(ask_payload.get("text") or ""),
            report_payload=report_ask_payload_from_dict(ask_payload),
        )
        if ask_payload is not None
        else None
    )
    answer = None
    if answer_payload is not None:
        answer_type = str(answer_payload.get("answerType") or "")
        restored = report_scenario_answer_from_dict(
            answer_type,
            answer_payload.get("answer") if isinstance(answer_payload.get("answer"), dict) else {},
        )
        answer = ChatAnswerEnvelope(
            answer_type=restored.answer_type,
            report=restored.report,
            report_template_preview=restored.report_template_preview,
            report_segment=restored.report_segment,
        )
    return ChatResponse(
        conversation_id=str(payload.get("conversationId") or ""),
        chat_id=str(payload.get("chatId") or ""),
        status=str(payload.get("status") or ""),
        ask=ask,
        answer=answer,
        errors=[str(item) for item in list(payload.get("errors") or [])],
        request_id=str(payload.get("requestId") or "") or None,
        timestamp=int(payload.get("timestamp") or 0) or None,
        api_version=str(payload.get("apiVersion") or "v1"),
    )


def _random_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _epoch_ms() -> int:
    import time

    return int(time.time() * 1000)

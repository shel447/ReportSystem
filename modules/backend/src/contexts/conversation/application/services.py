"""通用对话应用服务，负责会话、多轮澄清和业务场景分发。"""

from __future__ import annotations

from typing import Any

from ....shared.kernel.errors import NotFoundError, ValidationError
from ..domain.models import (
    ChatContext,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    ForkSource,
    ScenarioTrace,
    scenario_trace_from_dict,
)
from .models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatResponse,
    DeleteResult,
    ForkSessionCommand,
    ForkSessionResult,
    SessionDetail,
    SessionMessage,
    SessionSummary,
    chat_response_to_dict,
)
from .scenarios import ScenarioDispatchService, ScenarioResult


class ConversationService:
    """拥有聊天协议、消息流水和通用追问生命周期的应用服务。"""

    def __init__(self, *, conversation_repository, chat_repository, scenario_dispatcher: ScenarioDispatchService) -> None:
        self.conversation_repository = conversation_repository
        self.chat_repository = chat_repository
        self.scenario_dispatcher = scenario_dispatcher

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
        target = self.chat_repository.get_for_conversation(source_conversation_id, source_chat_id, user_id=user_id)
        if target is None:
            raise NotFoundError("Source chat not found")
        new_conversation = self.conversation_repository.create(conversation_id=None, user_id=user_id)
        source_trace = _scenario_trace_from_row(target)
        self.chat_repository.append_message(
            conversation_id=new_conversation.id,
            user_id=user_id,
            role=target.role,
            content=_message_content_from_row(target),
            action=_message_action_from_row(target),
            meta=ConversationMessageMeta(
                forked_from=ForkSource(conversation_id=source_conversation_id, chat_id=source_chat_id),
                scenario=source_trace,
            ),
            scenario_key=source_trace.key if source_trace else None,
        )
        new_conversation.title = source.title or _message_preview(_message_content_from_row(target))
        self.conversation_repository.save(new_conversation)
        return ForkSessionResult(conversation_id=new_conversation.id)

    def chat(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
        """通过通用聊天通道推进一次业务场景交互。"""
        initial_resolution = self.scenario_dispatcher.resolve(
            instruction=data.instruction,
            question=data.question,
            reply_source_trace=None,
            previous_trace=None,
        )
        if self.scenario_dispatcher.is_stateless(initial_resolution):
            context = _build_context(data=data, user_id=user_id, chat_id=data.chat_id or "", resolution=initial_resolution)
            result = self.scenario_dispatcher.dispatch(resolution=initial_resolution, context=context, payload=_dispatch_payload(data))
            return _response_from_scenario_result(
                data=data,
                conversation_id=data.conversation_id or "",
                chat_id=data.chat_id or "",
                result=result,
            )

        conversation = self._ensure_conversation(data=data, user_id=user_id)
        reply_source = self._reply_source_row(data=data, conversation_id=conversation.id, user_id=user_id)
        previous = self.chat_repository.get_latest_assistant(conversation.id, user_id=user_id)
        resolution = self.scenario_dispatcher.resolve(
            instruction=data.instruction,
            question=data.question,
            reply_source_trace=_scenario_trace_from_row(reply_source),
            previous_trace=_scenario_trace_from_row(previous),
        )
        self._consume_reply(data=data, conversation_id=conversation.id, user_id=user_id)
        user_trace = resolution.to_trace()
        user_chat = self.chat_repository.append_message(
            conversation_id=conversation.id,
            user_id=user_id,
            role="user",
            content=ConversationMessageContent(question=str(data.question or "")),
            meta=ConversationMessageMeta(scenario=user_trace),
            scenario_key=resolution.key,
            chat_id=data.chat_id,
        )
        context = _build_context(
            data=data,
            user_id=user_id,
            chat_id=user_chat.id,
            resolution=resolution,
            previous_trace=_scenario_trace_from_row(previous),
            conversation_id=conversation.id,
        )
        result = self.scenario_dispatcher.dispatch(resolution=resolution, context=context, payload=_dispatch_payload(data))
        if result.conversation_title and not conversation.title:
            conversation.title = result.conversation_title
            self.conversation_repository.save(conversation)
        response = _response_from_scenario_result(
            data=data,
            conversation_id=context.conversation_id,
            chat_id=_random_id("chat"),
            result=result,
        )
        self._append_assistant_message(
            conversation_id=conversation.id,
            user_id=user_id,
            chat_id=response.chat_id,
            response=response,
            trace=resolution.to_trace(continuation_state=result.status),
        )
        return response

    def _reply_source_row(self, *, data: ChatCommand, conversation_id: str, user_id: str):
        if data.reply is None or not str(data.reply.source_chat_id or "").strip():
            return None
        return self.chat_repository.get_for_conversation(conversation_id, data.reply.source_chat_id, user_id=user_id)

    def _consume_reply(self, *, data: ChatCommand, conversation_id: str, user_id: str) -> None:
        """消费任意业务场景的结构化答复，不解释其业务字段。"""
        if data.reply is None:
            return
        source_chat_id = str(data.reply.source_chat_id or "").strip()
        if not source_chat_id:
            raise ValidationError("reply.sourceChatId is required")
        if not self.chat_repository.mark_ask_replied(
            conversation_id=conversation_id,
            user_id=user_id,
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

    def _append_assistant_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        chat_id: str,
        response: ChatResponse,
        trace: ScenarioTrace,
    ) -> None:
        self.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=ConversationMessageContent(response=chat_response_to_dict(response)),
            action=ConversationMessageAction(type="chat_response"),
            meta=ConversationMessageMeta(status=response.status, scenario=trace),
            scenario_key=trace.key,
            chat_id=chat_id,
        )


def _build_context(
    *,
    data: ChatCommand,
    user_id: str,
    chat_id: str,
    resolution,
    previous_trace: ScenarioTrace | None = None,
    conversation_id: str | None = None,
) -> ChatContext:
    return ChatContext(
        conversation_id=conversation_id if conversation_id is not None else data.conversation_id or "",
        chat_id=chat_id,
        user_id=user_id,
        instruction=resolution.instruction,
        scenario_key=resolution.key,
        previous_scenario_key=previous_trace.key if previous_trace else None,
        scenario_resolution=resolution.source,
        question=data.question,
        reply_type=data.reply.type if data.reply else None,
        source_chat_id=data.reply.source_chat_id if data.reply else None,
        request_id=data.request_id,
        api_version=data.api_version or "v1",
    )


def _dispatch_payload(data: ChatCommand) -> dict[str, Any]:
    payload = dict(data.raw_payload)
    if data.reply is not None and "reply" not in payload:
        payload["reply"] = dict(data.reply.raw_payload)
    return payload


def _response_from_scenario_result(*, data: ChatCommand, conversation_id: str, chat_id: str, result: ScenarioResult) -> ChatResponse:
    ask = None
    if result.ask is not None:
        ask = ChatAsk(
            status="pending",
            mode=result.ask.mode,
            type=result.ask.type,
            title=result.ask.title,
            text=result.ask.text,
            fields=dict(result.ask.fields),
        )
    answer = None
    if result.answer is not None:
        answer = ChatAnswerEnvelope(answer_type=result.answer.answer_type, payload=dict(result.answer.payload))
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
    response = content.response or {}
    ask = response.get("ask") if isinstance(response.get("ask"), dict) else None
    return str((ask or {}).get("title") or (ask or {}).get("text") or "")[:80]


def _message_content_from_row(row) -> ConversationMessageContent:
    content = row.content if row is not None and isinstance(row.content, dict) else {}
    response = content.get("response") if isinstance(content.get("response"), dict) else None
    return ConversationMessageContent(question=content.get("question"), response=dict(response) if response is not None else None)


def _message_action_from_row(row) -> ConversationMessageAction | None:
    if row is None or not isinstance(row.action, dict):
        return None
    action_type = str(row.action.get("type") or "").strip()
    return ConversationMessageAction(type=action_type) if action_type else None


def _message_meta_from_row(row) -> ConversationMessageMeta | None:
    if row is None or not isinstance(row.meta, dict):
        return None
    forked_from = row.meta.get("forkedFrom") if isinstance(row.meta.get("forkedFrom"), dict) else None
    status = str(row.meta.get("status") or "").strip() or None
    return ConversationMessageMeta(
        status=status,
        forked_from=ForkSource(
            conversation_id=str(forked_from.get("conversationId") or ""),
            chat_id=str(forked_from.get("chatId") or ""),
        )
        if forked_from
        else None,
        scenario=scenario_trace_from_dict(row.meta.get("scenario")),
    )


def _scenario_trace_from_row(row) -> ScenarioTrace | None:
    if row is None:
        return None
    trace = scenario_trace_from_dict((row.meta or {}).get("scenario") if isinstance(row.meta, dict) else None)
    if trace is not None:
        return trace
    key = str(getattr(row, "scenario_key", None) or "").strip()
    return ScenarioTrace(key=key, resolution="unmatched", confidence=0.0) if key else None


def _random_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _epoch_ms() -> int:
    import time

    return int(time.time() * 1000)

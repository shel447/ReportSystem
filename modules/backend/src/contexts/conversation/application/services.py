"""通用对话应用服务，负责 AgentCore 会话、多轮澄清和场景分发。"""

from __future__ import annotations

import json
from typing import Any

from ....shared.kernel.errors import NotFoundError, UnsupportedCapabilityError, ValidationError
from ....shared.kernel.audit import AuditEvent
from ..domain.models import (
    ChatContext,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    ScenarioTrace,
    scenario_trace_from_dict,
    scenario_trace_to_dict,
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
from .ports import ConversationHistoryGateway, GuardrailGateway, HostedChat
from .scenarios import ScenarioDispatchService, ScenarioResult


class ConversationService:
    """拥有聊天协议和通用追问生命周期；会话事实源由 AgentCore 托管。"""

    def __init__(
        self,
        *,
        history_gateway: ConversationHistoryGateway,
        guardrail_gateway: GuardrailGateway,
        scenario_dispatcher: ScenarioDispatchService,
        audit_dispatcher=None,
    ) -> None:
        self.history_gateway = history_gateway
        self.guardrail_gateway = guardrail_gateway
        self.scenario_dispatcher = scenario_dispatcher
        self.audit_dispatcher = audit_dispatcher

    def list_sessions(self, *, user_id: str) -> list[SessionSummary]:
        return [
            SessionSummary(
                conversation_id=item.conversation_id,
                title=item.title or "未命名会话",
                status=item.status,
                updated_at=item.updated_at,
                last_message_preview=item.last_message_preview,
            )
            for item in self.history_gateway.list_conversations(page_num=1, page_size=100, user_id=user_id)
        ]

    def get_session(self, *, conversation_id: str, user_id: str) -> SessionDetail:
        conversations = self.history_gateway.list_conversations(page_num=1, page_size=100, user_id=user_id)
        conversation = next((item for item in conversations if item.conversation_id == conversation_id), None)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        rounds = self.history_gateway.query_chat_history(conversation_id=conversation_id, page_num=1, page_size=200, user_id=user_id)
        messages: list[SessionMessage] = []
        for item in rounds:
            if item.question:
                messages.append(
                    SessionMessage(
                        chat_id=item.chat_id,
                        role="user",
                        content=ConversationMessageContent(question=item.question),
                        action=None,
                        meta=ConversationMessageMeta(scenario=_trace_from_hosted(item)),
                        created_at=item.created_at,
                    )
                )
            if item.response_payload:
                messages.append(
                    SessionMessage(
                        chat_id=item.chat_id,
                        role="assistant",
                        content=ConversationMessageContent(response=dict(item.response_payload)),
                        action=ConversationMessageAction(type="chat_response"),
                        meta=ConversationMessageMeta(
                            status=str(item.response_payload.get("status") or "") or None,
                            scenario=_trace_from_hosted(item),
                        ),
                        created_at=item.created_at,
                    )
                )
        return SessionDetail(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            status=conversation.status,
            messages=messages,
        )

    def delete_session(self, *, conversation_id: str, user_id: str) -> DeleteResult:
        raise UnsupportedCapabilityError("capability_not_available: AgentCore conversation deletion is not available")

    def fork_session(self, *, data: ForkSessionCommand, user_id: str) -> ForkSessionResult:
        raise UnsupportedCapabilityError("capability_not_available: AgentCore conversation fork is not available")

    def chat(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
        """通过通用聊天通道推进一次业务场景交互。"""
        self._ensure_question_allowed(data=data, user_id=user_id)
        initial_resolution = self.scenario_dispatcher.resolve(
            instruction=data.instruction,
            question=data.question,
            reply_source_trace=None,
            previous_trace=None,
        )
        if self.scenario_dispatcher.is_stateless(initial_resolution):
            context = _build_context(data=data, user_id=user_id, chat_id=data.chat_id or "", resolution=initial_resolution)
            result = self.scenario_dispatcher.dispatch(resolution=initial_resolution, context=context, payload=_dispatch_payload(data))
            response = _response_from_scenario_result(
                data=data,
                conversation_id=data.conversation_id or "",
                chat_id=data.chat_id or "",
                result=result,
            )
            self._ensure_answer_allowed(response=response, user_id=user_id)
            return response

        conversation_id = self._ensure_conversation(data=data, user_id=user_id)
        rounds = self.history_gateway.query_chat_history(conversation_id=conversation_id, page_num=1, page_size=200, user_id=user_id)
        reply_source = self._reply_source(data=data, rounds=rounds, user_id=user_id)
        previous = rounds[-1] if rounds else None
        resolution = self.scenario_dispatcher.resolve(
            instruction=data.instruction,
            question=data.question,
            reply_source_trace=_trace_from_hosted(reply_source),
            previous_trace=_trace_from_hosted(previous),
        )
        self._consume_reply(data=data, source=reply_source, user_id=user_id)
        hosted_chat = self._ensure_chat(data=data, conversation_id=conversation_id, user_id=user_id)
        context = _build_context(
            data=data,
            user_id=user_id,
            chat_id=hosted_chat.chat_id,
            resolution=resolution,
            previous_trace=_trace_from_hosted(previous),
            conversation_id=conversation_id,
        )
        result = self.scenario_dispatcher.dispatch(resolution=resolution, context=context, payload=_dispatch_payload(data))
        response = _response_from_scenario_result(data=data, conversation_id=conversation_id, chat_id=hosted_chat.chat_id, result=result)
        self._ensure_answer_allowed(response=response, user_id=user_id)
        self.history_gateway.import_chat(
            chat=HostedChat(
                chat_id=hosted_chat.chat_id,
                conversation_id=conversation_id,
                question=str(data.question or ""),
                request_payload=dict(data.raw_payload),
                response_payload=chat_response_to_dict(response),
                meta={"scenario": scenario_trace_to_dict(resolution.to_trace(continuation_state=result.status)) or {}},
            ),
            user_id=user_id,
        )
        self._audit(
            AuditEvent(
                operation="conversation.chat",
                detail=f"completed scenario={resolution.key or 'unmatched'} status={result.status}",
                user_id=user_id,
                target_obj=f"{conversation_id}/{hosted_chat.chat_id}",
            )
        )
        return response

    def _ensure_question_allowed(self, *, data: ChatCommand, user_id: str) -> None:
        question = str(data.question or "").strip()
        if not question:
            return
        result = self.guardrail_gateway.check_question(question, user_id=user_id)
        if not result.passed:
            self._audit(
                AuditEvent(
                    operation="conversation.guardrail.question",
                    detail=result.reason or "question blocked",
                    user_id=user_id,
                    result="FAILED",
                    level="WARNING",
                    kind="security",
                )
            )
            raise ValidationError(result.reason or "用户输入未通过安全检查")

    def _ensure_answer_allowed(self, *, response: ChatResponse, user_id: str) -> None:
        if response.answer is None:
            return
        result = self.guardrail_gateway.check_answer(json.dumps(response.answer.payload, ensure_ascii=False), user_id=user_id)
        if not result.passed:
            self._audit(
                AuditEvent(
                    operation="conversation.guardrail.answer",
                    detail=result.reason or "answer blocked",
                    user_id=user_id,
                    result="FAILED",
                    level="WARNING",
                    kind="security",
                )
            )
            raise ValidationError(result.reason or "系统回答未通过安全检查")

    def _ensure_conversation(self, *, data: ChatCommand, user_id: str) -> str:
        conversation_id = str(data.conversation_id or "").strip()
        if conversation_id:
            return conversation_id
        created = self.history_gateway.create_conversation(title=str(data.question or "新会话")[:80], description=None, user_id=user_id)
        if not created.conversation_id:
            raise ValidationError("AgentCore did not return conversationId")
        return created.conversation_id

    def _ensure_chat(self, *, data: ChatCommand, conversation_id: str, user_id: str) -> HostedChat:
        chat_id = str(data.chat_id or "").strip()
        if chat_id:
            return HostedChat(chat_id=chat_id, conversation_id=conversation_id, question=str(data.question or ""))
        created = self.history_gateway.create_chat(conversation_id=conversation_id, question=str(data.question or ""), user_id=user_id)
        if not created.chat_id:
            raise ValidationError("AgentCore did not return chatId")
        return created

    def _reply_source(self, *, data: ChatCommand, rounds: list[HostedChat], user_id: str) -> HostedChat | None:
        if data.reply is None:
            return None
        source_chat_id = str(data.reply.source_chat_id or "").strip()
        if not source_chat_id:
            raise ValidationError("reply.sourceChatId is required")
        source = next((item for item in rounds if item.chat_id == source_chat_id), None)
        return source or self.history_gateway.get_chat_detail(chat_id=source_chat_id, user_id=user_id)

    def _consume_reply(self, *, data: ChatCommand, source: HostedChat | None, user_id: str) -> None:
        if data.reply is None:
            return
        if source is None:
            raise ValidationError("reply.sourceChatId must reference a pending ask in the same conversation")
        ask = source.response_payload.get("ask") if isinstance(source.response_payload.get("ask"), dict) else None
        if not isinstance(ask, dict) or ask.get("status") != "pending":
            raise ValidationError("reply.sourceChatId must reference a pending ask in the same conversation")
        updated = dict(source.response_payload)
        updated_ask = dict(ask)
        updated_ask["status"] = "replied"
        updated["ask"] = updated_ask
        source.response_payload = updated
        self.history_gateway.import_chat(chat=source, user_id=user_id)

    def _audit(self, event: AuditEvent) -> None:
        if self.audit_dispatcher is None:
            return
        try:
            self.audit_dispatcher.submit(event)
        except Exception:
            return


def _build_context(*, data: ChatCommand, user_id: str, chat_id: str, resolution, previous_trace=None, conversation_id: str | None = None) -> ChatContext:
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
    ask = ChatAsk(status="pending", mode=result.ask.mode, type=result.ask.type, title=result.ask.title, text=result.ask.text, fields=dict(result.ask.fields)) if result.ask else None
    answer = ChatAnswerEnvelope(answer_type=result.answer.answer_type, payload=dict(result.answer.payload)) if result.answer else None
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


def _trace_from_hosted(chat: HostedChat | None) -> ScenarioTrace | None:
    return scenario_trace_from_dict((chat.meta or {}).get("scenario")) if chat is not None else None


def _epoch_ms() -> int:
    import time

    return int(time.time() * 1000)

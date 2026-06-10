from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from pydantic import BaseModel
from tornado.iostream import StreamClosedError

from ..contexts.conversation.application.models import (
    chat_command_from_payload,
    chat_response_to_dict,
    delete_result_to_dict,
    fork_session_command_from_payload,
    fork_session_result_to_dict,
    session_detail_to_dict,
    session_summary_to_dict,
)
from ..shared.agentflow import FlowEvent
from ..shared.kernel.errors import ApplicationError, ErrorCode, NotFoundError, error_response_payload
from ..shared.kernel.policy_auth import policy_auth
from ..web.base import BusinessHandler


class ReplyPayload(BaseModel):
    type: str
    sourceChatId: str
    parameters: Optional[dict[str, list[Any]]] = None
    reportContext: Optional[dict[str, Any]] = None


class ChatRequestPayload(BaseModel):
    conversationId: Optional[str] = None
    chatId: Optional[str] = None
    question: Optional[str] = None
    instruction: Optional[str] = None
    reply: Optional[ReplyPayload] = None
    report: Optional[dict[str, Any]] = None
    template: Optional[dict[str, Any]] = None
    attachments: list[dict[str, Any]] = []
    histories: list[dict[str, Any]] = []


class ChatForkRequest(BaseModel):
    source_kind: str
    source_conversation_id: Optional[str] = None
    source_chat_id: Optional[str] = None


class ChatsHandler(BusinessHandler):
    @policy_auth(resource="chat", action="list")
    async def get(self):
        def action():
            with self.container.conversation_service_scope() as service:
                return [session_summary_to_dict(item) for item in service.list_sessions(user_id=self.user_id)]
        self.write_json(await self.run_blocking(action))

    @policy_auth(resource="chat", action="create")
    async def post(self):
        data = self.parse_json(ChatRequestPayload)
        command = chat_command_from_payload(data.model_dump(exclude_none=True))
        if "text/event-stream" not in str(self.request.headers.get("Accept") or "").lower():
            def action():
                with self.container.conversation_service_scope() as service:
                    return chat_response_to_dict(service.chat(data=command, user_id=self.user_id))
            self.write_json(await self.run_blocking(action))
            return
        await self._stream(command)

    async def _stream(self, command) -> None:
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()
        end = object()
        service_scope = self.container.conversation_service_scope
        user_id = self.user_id

        def produce() -> None:
            try:
                with service_scope() as service:
                    for event in service.chat_stream(data=command, user_id=user_id):
                        loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, end)

        self.container.executor.submit(produce)
        sequence = 1
        conversation_id = command.conversation_id or ""
        chat_id = command.chat_id or ""
        try:
            while True:
                item = await queue.get()
                if item is end:
                    break
                if isinstance(item, Exception):
                    for payload in _error_and_done(item, conversation_id=conversation_id, chat_id=chat_id, sequence=sequence, request_id=self.request.headers.get("X-Request-Id")):
                        self.write(_sse_chunk(payload))
                        await self.flush()
                    return
                event: FlowEvent = item
                conversation_id = event.conversation_id or conversation_id
                chat_id = event.chat_id or chat_id
                sequence = max(sequence, int(event.sequence or sequence))
                self.write(_sse_chunk(_flow_event_to_chat_stream_event(event)))
                await self.flush()
                sequence += 1
        except StreamClosedError:
            return


class ChatStopHandler(BusinessHandler):
    @policy_auth(resource="chat", action="stop")
    async def post(self, chat_id: str):
        def action():
            with self.container.conversation_service_scope() as service:
                return service.stop_chat(chat_id=chat_id, user_id=self.user_id)
        if not await self.run_blocking(action):
            raise NotFoundError("当前没有正在运行的对话。", error_code=ErrorCode.CONVERSATION_CANCEL_NOT_RUNNING)
        self.write_json({"chatId": chat_id, "status": "stop_requested"})


class ChatDetailHandler(BusinessHandler):
    @policy_auth(resource="chat", action="read")
    async def get(self, conversation_id: str):
        def action():
            with self.container.conversation_service_scope() as service:
                return session_detail_to_dict(service.get_session(conversation_id=conversation_id, user_id=self.user_id))
        self.write_json(await self.run_blocking(action))

    @policy_auth(resource="chat", action="delete")
    async def delete(self, conversation_id: str):
        def action():
            with self.container.conversation_service_scope() as service:
                return delete_result_to_dict(service.delete_session(conversation_id=conversation_id, user_id=self.user_id))
        self.write_json(await self.run_blocking(action))


class ChatForkHandler(BusinessHandler):
    @policy_auth(resource="chat", action="fork")
    async def post(self):
        data = self.parse_json(ChatForkRequest)
        def action():
            with self.container.conversation_service_scope() as service:
                return fork_session_result_to_dict(service.fork_session(
                    data=fork_session_command_from_payload(data.model_dump(exclude_none=True)),
                    user_id=self.user_id,
                ))
        self.write_json(await self.run_blocking(action))


def _sse_chunk(payload: dict[str, Any]) -> str:
    return f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _error_and_done(exc: Exception, *, conversation_id: str, chat_id: str, sequence: int, request_id: str | None):
    error = error_response_payload(exc, request_id=request_id, fallback_message="系统处理失败，请稍后重试。")
    yield {"conversationId": conversation_id, "chatId": chat_id, "eventType": "error", "sequence": sequence, "timestamp": int(time.time() * 1000), "status": "failed", "error": error}
    yield {"conversationId": conversation_id, "chatId": chat_id, "eventType": "done", "sequence": sequence + 1, "timestamp": int(time.time() * 1000), "status": "failed"}


def _flow_event_to_chat_stream_event(event: FlowEvent) -> dict[str, Any]:
    event_type = "answer" if event.event_type == "delta" else event.event_type
    if event.event_type in {"tool_call", "tool_result", "checkpoint"}:
        event_type = "step_delta"
    payload: dict[str, Any] = {
        "conversationId": event.conversation_id or "",
        "chatId": event.chat_id or "",
        "eventType": event_type,
        "sequence": event.sequence,
        "timestamp": int(time.time() * 1000),
        "status": event.status,
    }
    if event.step is not None:
        payload["step"] = {"code": event.step.code, "stepId": event.step.code, "title": event.step.title, "status": event.step.status, "detail": event.step.detail, "parentStepId": event.step.parent_step_id, "stepPath": list(event.step.step_path)}
    if event.delta:
        payload["delta"] = list(event.delta)
    for name in ("answer", "ask", "error", "refusal"):
        value = getattr(event, name, None)
        if value is not None:
            payload[name] = value
    if event.tool_call is not None:
        payload["toolCall"] = event.tool_call
    if event.tool_result is not None:
        payload["toolResult"] = event.tool_result
    if event.checkpoint is not None:
        payload["checkpoint"] = {key: value for key, value in event.checkpoint.items() if key != "runId"}
    if event.source_subflow is not None:
        payload["sourceSubflow"] = event.source_subflow
    return payload


ROUTES = [
    (r"/rest/chatbi/v1/chat", ChatsHandler),
    (r"/rest/chatbi/v1/chat/forks", ChatForkHandler),
    (r"/rest/chatbi/v1/chat/([^/]+)/stop", ChatStopHandler),
    (r"/rest/chatbi/v1/chat/([^/]+)", ChatDetailHandler),
]

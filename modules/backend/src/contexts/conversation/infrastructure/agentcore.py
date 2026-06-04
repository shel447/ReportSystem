"""Adapter for AgentCore-hosted conversation history."""

from __future__ import annotations

import json
from typing import Any

from ....shared.kernel.errors import ErrorCode, UpstreamError
from ..application.ports import HostedChat, HostedConversation


class ExternalConversationHistoryGateway:
    def __init__(self, *, client, piu_name: str = "dtecommon-uis-uiboard", piu_version: str = "1.0.0") -> None:
        self.client = client
        self.piu_name = piu_name
        self.piu_version = piu_version

    def create_conversation(self, *, title: str, description: str | None, user_id: str) -> HostedConversation:
        try:
            payload = self.client.post_json(
                path_or_url="/rest/naie/aiagentcore/v1/conversation",
                payload={"title": title, "description": description},
                user_id=user_id,
            )
        except UpstreamError as exc:
            raise _map_agentcore_error(exc, fallback_code=ErrorCode.CONVERSATION_CREATE_FAILED) from exc
        return HostedConversation(conversation_id=str(payload.get("conversationId") or ""), title=title)

    def create_chat(self, *, conversation_id: str, question: str, user_id: str) -> HostedChat:
        try:
            payload = self.client.post_json(
                path_or_url="/rest/naie/aiagentcore/v1/chat/create",
                payload={"conversationId": conversation_id, "question": question},
                user_id=user_id,
            )
        except UpstreamError as exc:
            raise _map_agentcore_error(exc, fallback_code=ErrorCode.CONVERSATION_CHAT_CREATE_FAILED) from exc
        return HostedChat(chat_id=str(payload.get("chatId") or ""), conversation_id=conversation_id, question=question)

    def import_chat(self, *, chat: HostedChat, user_id: str) -> None:
        try:
            self.client.post_json(
                path_or_url="/rest/naie/aiagent/v1/chat/import",
                payload={
                    "conversationId": chat.conversation_id,
                    "chatId": chat.chat_id,
                    "type": "PIU",
                    "content": {
                        "piuName": self.piu_name,
                        "piuVersion": self.piu_version,
                        "answers": {
                            "request": dict(chat.request_payload),
                            "response": dict(chat.response_payload),
                            "meta": dict(chat.meta),
                        },
                    },
                },
                user_id=user_id,
            )
        except UpstreamError as exc:
            raise _map_agentcore_error(exc, fallback_code=ErrorCode.CONVERSATION_ARCHIVE_FAILED) from exc

    def query_chat_history(self, *, conversation_id: str, page_num: int, page_size: int, user_id: str) -> list[HostedChat]:
        payload = self.client.post_json(
            path_or_url="/rest/naie/aiagentcore/v2/chat/history",
            payload={"conversationId": conversation_id, "pageNum": page_num, "pageSize": page_size},
            user_id=user_id,
        )
        return [_history_record(item, conversation_id=conversation_id) for item in list(payload.get("records") or [])]

    def get_chat_detail(self, *, chat_id: str, user_id: str) -> HostedChat | None:
        payload = self.client.get_json(path_or_url=f"/rest/naie/aiagentcore/v1/chat/detail/{chat_id}", user_id=user_id)
        return _history_record(payload, conversation_id=str(payload.get("conversationId") or ""))

    def list_conversations(self, *, page_num: int, page_size: int, user_id: str) -> list[HostedConversation]:
        payload = self.client.get_json(
            path_or_url="/rest/naie/aiagentcore/v1/conversations",
            params={"pageNum": page_num, "pageSize": page_size},
            user_id=user_id,
        )
        records = payload.get("records") or payload.get("results") or payload.get("data") or []
        if isinstance(records, dict):
            records = records.get("results") or []
        return [
            HostedConversation(
                conversation_id=str(item.get("conversationId") or item.get("id") or ""),
                title=str(item.get("title") or "未命名会话"),
                status=str(item.get("status") or "active"),
                updated_at=_optional_str(item.get("updatedAt") or item.get("modifyTime")),
                last_message_preview=str(item.get("lastMessagePreview") or ""),
            )
            for item in records
            if isinstance(item, dict)
        ]


def _history_record(payload: dict[str, Any], *, conversation_id: str) -> HostedChat:
    answers = payload.get("answers")
    imported = _decode_imported_answers(answers)
    question = _decode_question(payload.get("question"))
    return HostedChat(
        chat_id=str(payload.get("chatId") or payload.get("id") or ""),
        conversation_id=str(payload.get("conversationId") or conversation_id),
        question=question or str(imported.get("request", {}).get("question") or ""),
        request_payload=dict(imported.get("request") or {}),
        response_payload=dict(imported.get("response") or {}),
        meta=dict(imported.get("meta") or {}),
        created_at=_optional_str(payload.get("askTime")),
    )


def _decode_imported_answers(raw: object) -> dict[str, Any]:
    if isinstance(raw, list):
        raw = raw[-1].get("content") if raw and isinstance(raw[-1], dict) else {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    if isinstance(raw, dict) and "content" in raw and isinstance(raw.get("content"), dict):
        raw = raw["content"].get("answers")
    if isinstance(raw, dict) and ("conversationId" in raw or "status" in raw) and "response" not in raw:
        raw = {"response": raw}
    return dict(raw) if isinstance(raw, dict) else {}


def _decode_question(raw: object) -> str:
    if isinstance(raw, list):
        return "\n".join(str(item.get("content") or "") for item in raw if isinstance(item, dict)).strip()
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return raw
        if isinstance(parsed, dict):
            return str(parsed.get("content") or "")
        return raw
    return ""


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _map_agentcore_error(exc: UpstreamError, *, fallback_code: str) -> UpstreamError:
    upstream_code = str(exc.details.get("upstreamCode") or exc.details.get("code") or "").strip()
    if upstream_code == "naie.aiagent.452":
        return UpstreamError(
            "您创建的会话已超系统上限1000个，请删除部分历史会话后再次尝试创建新会话",
            details={**dict(exc.details), "upstreamCode": upstream_code},
            error_code=ErrorCode.CONVERSATION_QUOTA_EXCEEDED,
            category="quota",
            retryable=False,
            source="agentcore",
            http_status=409,
        )
    return UpstreamError(
        str(exc),
        details={**dict(exc.details), **({"upstreamCode": upstream_code} if upstream_code else {})},
        error_code=fallback_code,
        category="upstream",
        retryable=exc.retryable,
        source="agentcore",
        http_status=exc.http_status,
    )

"""通用对话领域模型，只表达所有业务场景都能理解的信息。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ScenarioTrace:
    """记录一轮消息所属场景及其识别依据。"""

    key: str | None
    resolution: str
    confidence: float
    continuation_state: str | None = None
    instruction: str | None = None


@dataclass(slots=True)
class ChatContext:
    """通用对话上下文，不承载任何具体业务场景的领域对象。"""

    conversation_id: str
    chat_id: str
    user_id: str
    instruction: str | None
    scenario_key: str | None
    previous_scenario_key: str | None = None
    scenario_resolution: str = "unmatched"
    question: str | None = None
    reply_type: str | None = None
    source_chat_id: str | None = None


@dataclass(slots=True)
class ForkSource:
    """会话分支来源。"""

    conversation_id: str
    chat_id: str


@dataclass(slots=True)
class ConversationMessageContent:
    """持久化消息内容；response 只在数据库序列化边界保存公开快照。"""

    question: str | None = None
    response: dict[str, Any] | None = None


@dataclass(slots=True)
class ConversationMessageAction:
    """聊天消息动作元信息。"""

    type: str


@dataclass(slots=True)
class ConversationMessageMeta:
    """聊天消息附加元信息。"""

    status: str | None = None
    forked_from: ForkSource | None = None
    scenario: ScenarioTrace | None = None


def scenario_trace_to_dict(trace: ScenarioTrace | None) -> dict[str, object] | None:
    if trace is None:
        return None
    return {
        "key": trace.key,
        "resolution": trace.resolution,
        "confidence": trace.confidence,
        "continuationState": trace.continuation_state,
        "instruction": trace.instruction,
    }


def scenario_trace_from_dict(payload: object) -> ScenarioTrace | None:
    if not isinstance(payload, dict):
        return None
    return ScenarioTrace(
        key=str(payload.get("key") or "").strip() or None,
        resolution=str(payload.get("resolution") or "unmatched"),
        confidence=float(payload.get("confidence") or 0.0),
        continuation_state=str(payload.get("continuationState") or "").strip() or None,
        instruction=str(payload.get("instruction") or "").strip() or None,
    )


def conversation_message_content_to_dict(content: ConversationMessageContent) -> dict[str, object]:
    payload: dict[str, object] = {}
    if content.question is not None:
        payload["question"] = content.question
    if content.response is not None:
        payload["response"] = dict(content.response)
    return payload

def conversation_message_action_to_dict(action: ConversationMessageAction | None) -> dict[str, object] | None:
    return {"type": action.type} if action is not None else None


def conversation_message_meta_to_dict(meta: ConversationMessageMeta | None) -> dict[str, object] | None:
    if meta is None:
        return None
    payload: dict[str, object] = {}
    if meta.status is not None:
        payload["status"] = meta.status
    if meta.forked_from is not None:
        payload["forkedFrom"] = {
            "conversationId": meta.forked_from.conversation_id,
            "chatId": meta.forked_from.chat_id,
        }
    scenario = scenario_trace_to_dict(meta.scenario)
    if scenario is not None:
        payload["scenario"] = scenario
    return payload

"""对话基础设施层使用的消息对象类型。"""

from __future__ import annotations

from ..application.models import (
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    conversation_message_action_to_dict,
    conversation_message_content_to_dict,
    conversation_message_meta_to_dict,
)

__all__ = [
    "ConversationMessageAction",
    "ConversationMessageContent",
    "ConversationMessageMeta",
    "conversation_message_action_to_dict",
    "conversation_message_content_to_dict",
    "conversation_message_meta_to_dict",
]


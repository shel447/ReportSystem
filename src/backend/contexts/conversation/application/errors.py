"""统一对话应用层异常，表示应回传给用户的软失败。"""

from __future__ import annotations


class ConversationReplyError(Exception):
    """对话过程中的软失败，应以助手回复形式暴露给用户。"""

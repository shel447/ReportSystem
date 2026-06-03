"""Agent Flow 提示词组装接口。"""

from __future__ import annotations

from dataclasses import dataclass
from string import Formatter
from typing import Any


@dataclass(slots=True)
class PromptMessage:
    """LLM 对话消息。"""

    role: str
    content: str


@dataclass(slots=True)
class PromptTemplate:
    """可渲染的提示词模板。"""

    name: str
    messages: list[PromptMessage]


class PromptAssembler:
    """基于模板和变量组装 prompt。"""

    def render(self, template: PromptTemplate, variables: dict[str, Any]) -> list[PromptMessage]:
        missing: set[str] = set()
        for message in template.messages:
            for _, field_name, _, _ in Formatter().parse(message.content):
                if field_name and field_name not in variables:
                    missing.add(field_name)
        if missing:
            raise ValueError(f"Missing prompt variables: {', '.join(sorted(missing))}")
        return [PromptMessage(role=message.role, content=message.content.format(**variables)) for message in template.messages]

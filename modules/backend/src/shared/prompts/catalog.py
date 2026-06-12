"""与具体业务无关的只读提示词目录。"""

from __future__ import annotations

from dataclasses import dataclass
from string import Formatter
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class PromptEntry:
    name: str
    description: str
    template: str
    variables: frozenset[str]

    def render(self, **variables: Any) -> str:
        missing = self.variables.difference(variables)
        if missing:
            raise ValueError(f"Missing prompt variables for {self.name}: {', '.join(sorted(missing))}")
        return self.template.format(**variables)


class PromptCatalog:
    """启动时构造、运行时只读的提示词目录。"""

    def __init__(self, entries: Mapping[str, PromptEntry]) -> None:
        self._entries = MappingProxyType(dict(entries))

    def require(self, prompt_name: str) -> PromptEntry:
        try:
            return self._entries[prompt_name]
        except KeyError as exc:
            raise KeyError(f"Prompt not found: {prompt_name}") from exc

    def render(self, prompt_name: str, **variables: Any) -> str:
        return self.require(prompt_name).render(**variables)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    @staticmethod
    def variables(template: str) -> frozenset[str]:
        return frozenset(
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        )

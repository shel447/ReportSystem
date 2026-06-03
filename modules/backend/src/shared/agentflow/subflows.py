"""Agent Flow 子流程接口。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .graph import FlowGraph


@dataclass(slots=True)
class SubflowEventPolicy:
    """子流程事件汇入父流程的策略。"""

    bubble_answer: bool = False
    error_policy: str = "propagate"


@dataclass(slots=True)
class SubflowSpec:
    """可复用子流程声明。"""

    name: str
    build_graph: Callable[[dict[str, Any]], FlowGraph]
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    event_policy: SubflowEventPolicy = field(default_factory=SubflowEventPolicy)


class SubflowRegistry:
    """流程运行可用子流程注册表。"""

    def __init__(self, specs: list[SubflowSpec] | None = None) -> None:
        self._specs: dict[str, SubflowSpec] = {}
        for spec in specs or []:
            self.register(spec)

    def register(self, spec: SubflowSpec) -> None:
        if not spec.name:
            raise ValueError("Subflow name is required")
        if spec.name in self._specs:
            raise ValueError(f"Duplicate subflow: {spec.name}")
        self._specs[spec.name] = spec

    def get(self, name: str) -> SubflowSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise ValueError(f"Unknown subflow: {name}") from exc

"""Agent Flow 工具调用接口。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


ToolHandler = Callable[[dict[str, Any]], Any]


@dataclass(slots=True)
class ToolSpec:
    """可被流程节点调用的工具声明。"""

    name: str
    description: str = ""
    handler: ToolHandler | None = None
    schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolCall:
    """一次工具调用。"""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """一次工具调用结果。"""

    call_id: str
    name: str
    output: Any = None
    error: str | None = None


class ToolRegistry:
    """流程运行可用工具注册表。"""

    def __init__(self, specs: list[ToolSpec] | None = None) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs or []:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if not spec.name:
            raise ValueError("Tool name is required")
        if spec.name in self._specs:
            raise ValueError(f"Duplicate tool: {spec.name}")
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise ValueError(f"Unknown tool: {name}") from exc

    def execute(self, call: ToolCall) -> ToolResult:
        spec = self.get(call.name)
        if spec.handler is None:
            raise ValueError(f"Tool has no handler: {call.name}")
        try:
            return ToolResult(call_id=call.id, name=call.name, output=spec.handler(dict(call.arguments)))
        except Exception as exc:
            return ToolResult(call_id=call.id, name=call.name, error=str(exc))

    def list_specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

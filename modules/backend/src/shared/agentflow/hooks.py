"""Agent Flow 节点和工具 hook。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class HookDecision:
    """Hook 对流程的控制建议。"""

    action: str = "continue"
    reason: str | None = None
    answer: dict[str, Any] | None = None

    @classmethod
    def continue_(cls) -> "HookDecision":
        return cls(action="continue")

    @classmethod
    def skip(cls, reason: str | None = None) -> "HookDecision":
        return cls(action="skip", reason=reason)

    @classmethod
    def terminate(cls, reason: str) -> "HookDecision":
        return cls(action="terminate", reason=reason)

    @classmethod
    def refuse(cls, reason: str, answer: dict[str, Any] | None = None) -> "HookDecision":
        return cls(action="refuse", reason=reason, answer=answer)


@dataclass(slots=True)
class HookContext:
    """Hook 调用上下文。"""

    run_id: str
    node_id: str | None = None
    tool_name: str | None = None
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class FlowHook(Protocol):
    """可选实现部分方法的流程 hook。"""

    def before_node(self, context: HookContext) -> HookDecision | None: ...

    def after_node(self, context: HookContext) -> HookDecision | None: ...

    def on_error(self, context: HookContext, error: Exception) -> HookDecision | None: ...

    def before_tool(self, context: HookContext) -> HookDecision | None: ...

    def after_tool(self, context: HookContext) -> HookDecision | None: ...

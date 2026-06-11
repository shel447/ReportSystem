"""Agent Flow 事件和信号模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FlowStep:
    """流程步骤进展。"""

    code: str
    title: str | None = None
    status: str = "running"
    detail: str | None = None
    parent_step_id: str | None = None
    step_path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FlowEvent:
    """AgentFlow-internal event normalized before MessageCenter publication."""

    run_id: str
    sequence: int
    event_type: str
    status: str = "running"
    step: FlowStep | None = None
    delta: list[dict[str, Any]] = field(default_factory=list)
    answer: dict[str, Any] | None = None
    ask: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    tool_call: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    refusal: dict[str, Any] | None = None
    checkpoint: dict[str, Any] | None = None
    source_subflow: dict[str, Any] | None = None


@dataclass(slots=True)
class FlowSignal:
    """流程运行中的外部信号。"""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)

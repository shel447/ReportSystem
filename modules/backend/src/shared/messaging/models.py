"""Transport-neutral message contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MessageKind = Literal["event", "command"]
MessageChannel = Literal["interaction", "domain", "observability", "control"]


@dataclass(slots=True)
class MessageEnvelope:
    message_id: str
    kind: MessageKind
    channel: MessageChannel
    topic: str
    source: str
    occurred_at: float
    partition_key: str
    payload: Any
    sequence: int = 0
    source_sequence: int | None = None
    correlation_id: str | None = None
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class CommandReceipt:
    command_id: str
    status: Literal["queued"] = "queued"


@dataclass(frozen=True, slots=True)
class FlowControlCommand:
    run_id: str
    reason: str = ""


@dataclass(slots=True)
class InteractionStep:
    step_id: str
    title: str | None = None
    status: str = "running"
    detail: str | None = None
    parent_step_id: str | None = None
    step_path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InteractionEvent:
    """Standard interaction payload that any module may publish."""

    event_type: str
    status: str = "running"
    sequence: int = 0
    step: InteractionStep | None = None
    delta: list[dict[str, Any]] = field(default_factory=list)
    answer: dict[str, Any] | None = None
    ask: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    tool_call: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    refusal: dict[str, Any] | None = None
    checkpoint: dict[str, Any] | None = None
    source_subflow: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ConsumerFailure:
    consumer_name: str
    message_id: str
    topic: str
    error: str


@dataclass(frozen=True, slots=True)
class CommandFailure:
    command_id: str
    target: str
    topic: str
    reason: str


@dataclass(frozen=True, slots=True)
class DomainEvent:
    context: str
    fact: str
    data: Any = None

"""Agent Flow metrics collection and publishing."""

from __future__ import annotations

import contextlib
import contextvars
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol


@dataclass(slots=True)
class FlowMetricRecord:
    """A custom metric recorded by a flow node or infrastructure adapter."""

    name: str
    value: int | float | str | bool
    tags: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class FlowMetrics:
    """Terminal resource usage notification for a flow run."""

    run_id: str
    status: str
    duration_ms: int
    conversation_id: str | None = None
    chat_id: str | None = None
    user_id: str | None = None
    scenario_key: str | None = None
    logical_entity_count: int = 0
    llm_output_tokens: int = 0
    node_count: int = 0
    failed_node_count: int = 0
    custom: list[FlowMetricRecord] = field(default_factory=list)


class MetricsSink(Protocol):
    """Transport-neutral metrics sink.

    Kafka, HTTP or database implementations can be added by implementing this
    protocol. AgentFlow itself only depends on this abstraction.
    """

    def publish(self, metrics: FlowMetrics) -> None: ...


class NoopMetricsSink:
    """Default sink used when metrics publishing is not configured."""

    def publish(self, metrics: FlowMetrics) -> None:  # pragma: no cover - intentionally empty
        return None


class InMemoryMetricsSink:
    """Test and local-debug sink."""

    def __init__(self) -> None:
        self.items: list[FlowMetrics] = []
        self._lock = threading.RLock()

    def publish(self, metrics: FlowMetrics) -> None:
        with self._lock:
            self.items.append(metrics)


class MetricsCenter:
    """Publishes terminal flow metrics to configured sinks."""

    def __init__(self, sinks: Iterable[MetricsSink] | None = None) -> None:
        self.sinks = list(sinks or [NoopMetricsSink()])

    def publish(self, metrics: FlowMetrics) -> None:
        for sink in self.sinks:
            try:
                sink.publish(metrics)
            except Exception:
                # Metrics publishing must never change the business outcome.
                continue


class FlowMetricsCollector:
    """Thread-safe collector scoped to one flow run."""

    def __init__(self) -> None:
        self.started_at = time.perf_counter()
        self._lock = threading.RLock()
        self._logical_entities: set[str] = set()
        self._llm_output_tokens = 0
        self._node_count = 0
        self._failed_nodes: set[str] = set()
        self._custom: list[FlowMetricRecord] = []

    def record_node_started(self, node_id: str) -> None:
        with self._lock:
            self._node_count += 1

    def record_node_failed(self, node_id: str) -> None:
        with self._lock:
            self._failed_nodes.add(node_id)

    def record_logical_resource(self, *, kind: str, name: str | None) -> None:
        value = str(name or "").strip()
        if not value:
            return
        with self._lock:
            if kind == "logical_entity":
                self._logical_entities.add(value)
            self._custom.append(FlowMetricRecord(name="resource.usage", value=1, tags={"kind": kind, "name": value}))

    def record_datacatalog_logical_entity(self, entity: str | None) -> None:
        self.record_logical_resource(kind="logical_entity", name=entity)

    def record_llm_output_tokens(self, tokens: int | None) -> None:
        if tokens is None or tokens <= 0:
            return
        with self._lock:
            self._llm_output_tokens += int(tokens)

    def record(self, name: str, value: int | float | str | bool, tags: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._custom.append(FlowMetricRecord(name=name, value=value, tags=dict(tags or {})))

    def snapshot(
        self,
        *,
        run_id: str,
        status: str,
        conversation_id: str | None = None,
        chat_id: str | None = None,
        user_id: str | None = None,
        scenario_key: str | None = None,
    ) -> FlowMetrics:
        with self._lock:
            return FlowMetrics(
                run_id=run_id,
                status=status,
                duration_ms=max(0, int((time.perf_counter() - self.started_at) * 1000)),
                conversation_id=conversation_id,
                chat_id=chat_id,
                user_id=user_id,
                scenario_key=scenario_key,
                logical_entity_count=len(self._logical_entities),
                llm_output_tokens=self._llm_output_tokens,
                node_count=self._node_count,
                failed_node_count=len(self._failed_nodes),
                custom=list(self._custom),
            )


_current_collector: contextvars.ContextVar[FlowMetricsCollector | None] = contextvars.ContextVar(
    "agentflow_metrics_collector",
    default=None,
)


@contextlib.contextmanager
def use_metrics_collector(collector: FlowMetricsCollector):
    token = _current_collector.set(collector)
    try:
        yield
    finally:
        _current_collector.reset(token)


def current_metrics_collector() -> FlowMetricsCollector | None:
    return _current_collector.get()


def record_datacatalog_logical_entity(entity: str | None) -> None:
    record_logical_resource(kind="logical_entity", name=entity)


def record_logical_resource(*, kind: str, name: str | None) -> None:
    collector = current_metrics_collector()
    if collector is not None:
        collector.record_logical_resource(kind=kind, name=name)


def record_llm_usage(raw_response: dict[str, Any] | None) -> None:
    collector = current_metrics_collector()
    if collector is None or not isinstance(raw_response, dict):
        return
    usage = raw_response.get("usage")
    if not isinstance(usage, dict):
        return
    token_value = (
        usage.get("completion_tokens")
        or usage.get("output_tokens")
        or usage.get("generated_tokens")
        or usage.get("completionTokens")
        or usage.get("outputTokens")
    )
    try:
        tokens = int(token_value)
    except (TypeError, ValueError):
        return
    collector.record_llm_output_tokens(tokens)

"""Agent Flow metrics collection and publishing."""

from __future__ import annotations

import contextlib
import contextvars
import threading
import time
from dataclasses import dataclass, field
from typing import Any


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
    llm_output_tokens: int = 0
    node_count: int = 0
    failed_node_count: int = 0
    custom: list[FlowMetricRecord] = field(default_factory=list)
    unique_counts: dict[str, int] = field(default_factory=dict)


class FlowMetricsCollector:
    """Thread-safe collector scoped to one flow run."""

    def __init__(self) -> None:
        self.started_at = time.perf_counter()
        self._lock = threading.RLock()
        self._llm_output_tokens = 0
        self._node_count = 0
        self._failed_nodes: set[str] = set()
        self._custom: list[FlowMetricRecord] = []
        self._unique_metrics: dict[str, set[str]] = {}

    def record_node_started(self, node_id: str) -> None:
        with self._lock:
            self._node_count += 1

    def record_node_failed(self, node_id: str) -> None:
        with self._lock:
            self._failed_nodes.add(node_id)

    def record_unique_metric(self, name: str, key: str | int | float | bool | None, tags: dict[str, Any] | None = None) -> None:
        metric_name = str(name or "").strip()
        metric_key = str(key or "").strip()
        if not metric_name or not metric_key:
            return
        with self._lock:
            values = self._unique_metrics.setdefault(metric_name, set())
            if metric_key in values:
                return
            values.add(metric_key)
            self._custom.append(FlowMetricRecord(name=metric_name, value=metric_key, tags=dict(tags or {})))

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
    ) -> FlowMetrics:
        with self._lock:
            return FlowMetrics(
                run_id=run_id,
                status=status,
                duration_ms=max(0, int((time.perf_counter() - self.started_at) * 1000)),
                llm_output_tokens=self._llm_output_tokens,
                node_count=self._node_count,
                failed_node_count=len(self._failed_nodes),
                custom=list(self._custom),
                unique_counts={name: len(values) for name, values in self._unique_metrics.items()},
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


def record_unique_metric(name: str, key: str | int | float | bool | None, tags: dict[str, Any] | None = None) -> None:
    collector = current_metrics_collector()
    if collector is not None:
        collector.record_unique_metric(name=name, key=key, tags=tags)


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

"""内存态 Agent Flow 运行器。"""

from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable

from .events import FlowEvent, FlowSignal, FlowStep
from .graph import FlowGraph


class FlowCancelled(Exception):
    """流程被协作式取消。"""


@dataclass(slots=True)
class FlowRun:
    """一次流程运行。"""

    run_id: str
    graph: FlowGraph
    events: "queue.Queue[FlowEvent]" = field(default_factory=queue.Queue)
    inputs: "queue.Queue[FlowSignal]" = field(default_factory=queue.Queue)
    cancel_requested: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    sequence: int = 0
    final_event: FlowEvent | None = None
    thread: threading.Thread | None = None
    state: dict[str, Any] = field(default_factory=dict)


class FlowContext:
    """节点运行上下文。"""

    def __init__(self, *, run: FlowRun, runtime: "InMemoryFlowRuntime", state: dict[str, Any] | None = None) -> None:
        self.run = run
        self.runtime = runtime
        self.state = state if state is not None else {}

    @property
    def run_id(self) -> str:
        return self.run.run_id

    def check_cancelled(self) -> None:
        if self.run.cancel_requested.is_set():
            raise FlowCancelled("flow run was cancelled")

    def emit_status(self, *, status: str = "running") -> FlowEvent:
        return self.runtime.emit(self.run, event_type="status", status=status)

    def emit_step(self, *, code: str, title: str | None = None, status: str = "running", detail: str | None = None) -> FlowEvent:
        return self.runtime.emit(
            self.run,
            event_type="step_delta",
            status=status,
            step=FlowStep(code=code, title=title, status=status, detail=detail),
        )

    def emit_delta(self, delta: dict[str, Any] | list[dict[str, Any]], *, status: str = "running") -> FlowEvent:
        return self.runtime.emit(
            self.run,
            event_type="delta",
            status=status,
            delta=[delta] if isinstance(delta, dict) else list(delta),
        )

    def emit_answer(self, answer: dict[str, Any], *, status: str = "finished") -> FlowEvent:
        return self.runtime.emit(self.run, event_type="answer", status=status, answer=answer)

    def emit_ask(self, ask: dict[str, Any], *, status: str = "waiting_user") -> FlowEvent:
        return self.runtime.emit(self.run, event_type="ask", status=status, ask=ask)

    def emit_error(self, error: str, *, status: str = "failed") -> FlowEvent:
        return self.runtime.emit(self.run, event_type="error", status=status, error=error)

    def wait_for_input(self, ask: dict[str, Any] | None = None) -> FlowSignal:
        if ask is not None:
            self.emit_ask(ask)
        while True:
            self.check_cancelled()
            try:
                signal = self.run.inputs.get(timeout=0.1)
            except queue.Empty:
                continue
            if signal.type == "cancel":
                self.run.cancel_requested.set()
                self.check_cancelled()
            if signal.type == "input":
                return signal


class InMemoryFlowRuntime:
    """单进程内存流程运行器。"""

    def __init__(self) -> None:
        self._runs: dict[str, FlowRun] = {}
        self._lock = threading.RLock()

    def start(self, graph: FlowGraph, *, state: dict[str, Any] | None = None) -> FlowRun:
        run = FlowRun(run_id=f"run_{uuid.uuid4().hex[:16]}", graph=graph, state=dict(state or {}))
        context = FlowContext(run=run, runtime=self, state=run.state)
        thread = threading.Thread(target=self._execute, args=(run, context), name=f"agentflow-{run.run_id}", daemon=True)
        run.thread = thread
        with self._lock:
            self._runs[run.run_id] = run
        thread.start()
        return run

    def run_sync(self, graph: FlowGraph, *, state: dict[str, Any] | None = None) -> list[FlowEvent]:
        run = self.start(graph, state=state)
        return list(self.iter_events(run.run_id))

    def get(self, run_id: str) -> FlowRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def cancel(self, run_id: str) -> bool:
        run = self.get(run_id)
        if run is None:
            return False
        run.cancel_requested.set()
        run.inputs.put(FlowSignal(type="cancel"))
        return True

    def send_input(self, run_id: str, payload: dict[str, Any]) -> bool:
        run = self.get(run_id)
        if run is None:
            return False
        run.inputs.put(FlowSignal(type="input", payload=dict(payload)))
        return True

    def iter_events(self, run_id: str) -> Iterable[FlowEvent]:
        run = self.get(run_id)
        if run is None:
            return
        while True:
            try:
                yield run.events.get(timeout=0.1)
            except queue.Empty:
                if run.done.is_set():
                    break

    def emit(
        self,
        run: FlowRun,
        *,
        event_type: str,
        status: str = "running",
        step: FlowStep | None = None,
        delta: list[dict[str, Any]] | None = None,
        answer: dict[str, Any] | None = None,
        ask: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> FlowEvent:
        with self._lock:
            run.sequence += 1
            event = FlowEvent(
                run_id=run.run_id,
                sequence=run.sequence,
                event_type=event_type,
                status=status,
                conversation_id=str(context_value(run, "conversation_id") or "") or None,
                chat_id=str(context_value(run, "chat_id") or "") or None,
                step=step,
                delta=list(delta or []),
                answer=answer,
                ask=ask,
                error=error,
            )
            if event_type in {"ask", "answer", "error", "done"}:
                run.final_event = event
            run.events.put(event)
            return event

    def _execute(self, run: FlowRun, context: FlowContext) -> None:
        try:
            self.emit(run, event_type="status", status="running")
            self._execute_graph(run.graph, context)
            if not run.cancel_requested.is_set():
                self.emit(run, event_type="done", status=(run.final_event.status if run.final_event else "finished"))
        except FlowCancelled as exc:
            self.emit(run, event_type="error", status="cancelled", error=str(exc))
            self.emit(run, event_type="done", status="cancelled")
        except Exception as exc:  # pragma: no cover - defensive boundary
            self.emit(run, event_type="error", status="failed", error=str(exc))
            self.emit(run, event_type="done", status="failed")
        finally:
            run.done.set()

    def _execute_graph(self, graph: FlowGraph, context: FlowContext) -> None:
        if graph.start not in graph.nodes:
            raise ValueError(f"Flow start node does not exist: {graph.start}")
        ready = [graph.start]
        completed: set[str] = set()
        executed_count: dict[str, int] = {}
        max_node_executions = 1000

        while ready:
            context.check_cancelled()
            node_id = ready.pop(0)
            node = graph.nodes[node_id]
            executed_count[node_id] = executed_count.get(node_id, 0) + 1
            if executed_count[node_id] > max_node_executions:
                raise RuntimeError(f"Flow node exceeded execution limit: {node_id}")
            context.emit_step(code=node.id, title=node.title or node.id, status="running")
            node.handler(context)
            completed.add(node_id)
            context.emit_step(code=node.id, title=node.title or node.id, status="finished")

            for edge in graph.outgoing(node_id):
                if edge.condition is not None and not edge.condition(context):
                    continue
                incoming = graph.incoming(edge.target)
                if incoming and all(item.source in completed for item in incoming if item.condition is None):
                    if edge.target not in ready:
                        ready.append(edge.target)
                elif edge.target not in ready:
                    ready.append(edge.target)


def context_value(run: FlowRun, key: str) -> Any:
    return run.state.get(key)

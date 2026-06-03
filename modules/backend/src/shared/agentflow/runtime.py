"""内存态 Agent Flow 运行器。"""

from __future__ import annotations

import queue
import threading
import uuid
import copy
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .checkpoints import CheckpointSaver, FlowCheckpoint, InMemoryCheckpointSaver
from .events import FlowEvent, FlowSignal, FlowStep
from .graph import FlowEdge, FlowGraph, FlowNode
from .hooks import FlowHook, HookContext, HookDecision
from .prompts import PromptAssembler, PromptMessage, PromptTemplate
from .subflows import SubflowEventPolicy, SubflowRegistry
from .termination import FlowCancelled, FlowRefused, FlowTerminated
from .tools import ToolCall, ToolRegistry


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
    active_node_id: str | None = None
    completed_nodes: set[str] = field(default_factory=set)


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

    def emit_step(
        self,
        *,
        code: str,
        title: str | None = None,
        status: str = "running",
        detail: str | None = None,
        parent_step_id: str | None = None,
        step_path: list[str] | None = None,
    ) -> FlowEvent:
        return self.runtime.emit(
            self.run,
            event_type="step_delta",
            status=status,
            step=FlowStep(code=code, title=title, status=status, detail=detail, parent_step_id=parent_step_id, step_path=list(step_path or [])),
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

    def emit_tool_call(self, call: ToolCall) -> FlowEvent:
        return self.runtime.emit(self.run, event_type="tool_call", status="running", tool_call=asdict(call))

    def emit_tool_result(self, result) -> FlowEvent:
        return self.runtime.emit(self.run, event_type="tool_result", status="running", tool_result=asdict(result))

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self.runtime.call_tool(self, name=name, arguments=dict(arguments or {}))

    def call_subflow(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        alias: str | None = None,
        event_policy: SubflowEventPolicy | None = None,
    ) -> Any:
        return self.runtime.call_subflow(self, name=name, arguments=dict(arguments or {}), alias=alias, event_policy=event_policy)

    def render_prompt(self, template: PromptTemplate, variables: dict[str, Any]) -> list[PromptMessage]:
        return self.runtime.prompt_assembler.render(template, variables)

    def save_checkpoint(self, *, reason: str = "manual") -> FlowCheckpoint:
        return self.runtime.save_checkpoint(self.run, reason=reason)

    def request_terminate(self, reason: str) -> None:
        self.runtime.emit(self.run, event_type="error", status="terminated", error=reason)
        raise FlowTerminated(reason)

    def refuse(self, reason: str, answer: dict[str, Any] | None = None) -> None:
        payload = answer or {"answerType": "REFUSAL", "answer": {"reason": reason}}
        self.runtime.emit(self.run, event_type="answer", status="refused", answer=payload, refusal={"reason": reason})
        raise FlowRefused(reason)

    def add_node(self, node: FlowNode) -> None:
        self.runtime.add_node(self.run, node)

    def add_edge(self, edge: FlowEdge) -> None:
        self.runtime.add_edge(self.run, edge)

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

    def __init__(
        self,
        *,
        checkpoint_saver: CheckpointSaver | None = None,
        tool_registry: ToolRegistry | None = None,
        prompt_assembler: PromptAssembler | None = None,
        subflow_registry: SubflowRegistry | None = None,
        hooks: list[FlowHook] | None = None,
    ) -> None:
        self._runs: dict[str, FlowRun] = {}
        self._chat_index: dict[str, str] = {}
        self._lock = threading.RLock()
        self.checkpoint_saver = checkpoint_saver or InMemoryCheckpointSaver()
        self.tool_registry = tool_registry or ToolRegistry()
        self.prompt_assembler = prompt_assembler or PromptAssembler()
        self.subflow_registry = subflow_registry or SubflowRegistry()
        self.hooks = list(hooks or [])

    def start(self, graph: FlowGraph, *, state: dict[str, Any] | None = None) -> FlowRun:
        run = FlowRun(run_id=f"run_{uuid.uuid4().hex[:16]}", graph=graph, state=dict(state or {}))
        context = FlowContext(run=run, runtime=self, state=run.state)
        thread = threading.Thread(target=self._execute, args=(run, context), name=f"agentflow-{run.run_id}", daemon=True)
        run.thread = thread
        with self._lock:
            self._runs[run.run_id] = run
            chat_id = str(run.state.get("chat_id") or "")
            if chat_id:
                self._chat_index[chat_id] = run.run_id
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

    def cancel_by_chat(self, chat_id: str, *, user_id: str | None = None) -> bool:
        with self._lock:
            run_id = self._chat_index.get(chat_id)
            run = self._runs.get(run_id or "")
            if run is None or run.done.is_set():
                return False
            if user_id is not None and str(run.state.get("user_id") or "") != user_id:
                return False
        return self.cancel(run.run_id)

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
        tool_call: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
        refusal: dict[str, Any] | None = None,
        checkpoint: dict[str, Any] | None = None,
        source_subflow: dict[str, Any] | None = None,
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
                tool_call=tool_call,
                tool_result=tool_result,
                refusal=refusal,
                checkpoint=checkpoint,
                source_subflow=source_subflow,
            )
            if event_type in {"ask", "answer", "error", "done"}:
                run.final_event = event
            run.events.put(event)
            return event

    def save_checkpoint(self, run: FlowRun, *, reason: str) -> FlowCheckpoint:
        with self._lock:
            sequence = run.sequence
            node_id = run.active_node_id
            state = dict(run.state)
        checkpoint = self.checkpoint_saver.save(
            FlowCheckpoint(run_id=run.run_id, sequence=sequence, node_id=node_id, state=state, reason=reason)
        )
        self.emit(
            run,
            event_type="checkpoint",
            status="running",
            checkpoint={
                "sequence": checkpoint.sequence,
                "nodeId": checkpoint.node_id,
                "reason": checkpoint.reason,
                "createdAt": checkpoint.created_at,
            },
        )
        return checkpoint

    def call_tool(self, context: FlowContext, *, name: str, arguments: dict[str, Any]) -> Any:
        call = ToolCall(id=f"tool_{uuid.uuid4().hex[:12]}", name=name, arguments=dict(arguments))
        self._apply_hook_decision(context, self._run_hooks("before_tool", context, tool_name=name))
        context.emit_tool_call(call)
        result = self.tool_registry.execute(call)
        context.emit_tool_result(result)
        self._apply_hook_decision(context, self._run_hooks("after_tool", context, tool_name=name))
        if result.error:
            raise RuntimeError(result.error)
        return result.output

    def call_subflow(
        self,
        context: FlowContext,
        *,
        name: str,
        arguments: dict[str, Any],
        alias: str | None = None,
        event_policy: SubflowEventPolicy | None = None,
    ) -> Any:
        spec = self.subflow_registry.get(name)
        policy = event_policy or spec.event_policy
        subflow_alias = alias or name
        call_id = f"subflow_{uuid.uuid4().hex[:12]}"
        child_run = FlowRun(
            run_id=f"run_{uuid.uuid4().hex[:16]}",
            graph=spec.build_graph(dict(arguments)),
            state={**copy.deepcopy(context.state), "subflow_alias": subflow_alias, "subflow_call_id": call_id},
            cancel_requested=context.run.cancel_requested,
        )
        child_context = FlowContext(run=child_run, runtime=self, state=child_run.state)
        original_events = child_run.events
        child_run.events = queue.Queue()
        try:
            self._execute_graph(child_run.graph, child_context)
        except Exception as exc:
            if policy.error_policy == "capture":
                context.state.setdefault("subflows", {})[subflow_alias] = {"error": str(exc)}
                return {"error": str(exc)}
            raise
        finally:
            child_events = list(child_run.events.queue)
            child_run.events = original_events
        last_answer = None
        for event in child_events:
            if event.event_type == "done":
                continue
            self._map_subflow_event(context.run, event, alias=subflow_alias, call_id=call_id, bubble_answer=policy.bubble_answer)
            if event.answer is not None:
                last_answer = event.answer
        context.state.setdefault("subflows", {})[subflow_alias] = {"callId": call_id, "answer": last_answer}
        return last_answer

    def _map_subflow_event(self, parent_run: FlowRun, child_event: FlowEvent, *, alias: str, call_id: str, bubble_answer: bool) -> FlowEvent | None:
        source = {"type": "subflow", "alias": alias, "callId": call_id}
        event_type = child_event.event_type
        answer = child_event.answer
        delta = [self._with_subflow_source(item, source) for item in child_event.delta]
        if event_type == "answer" and not bubble_answer:
            event_type = "delta"
            delta = [{"action": "subflow_result", "source": source, "answer": answer}]
            answer = None
        step = child_event.step
        if step is not None:
            step = FlowStep(
                code=f"{alias}.{step.code}",
                title=step.title,
                status=step.status,
                detail=step.detail,
                parent_step_id=f"{alias}.{step.parent_step_id}" if step.parent_step_id else None,
                step_path=[alias, *step.step_path],
            )
        return self.emit(
            parent_run,
            event_type=event_type,
            status=child_event.status,
            step=step,
            delta=delta,
            answer=answer,
            ask=child_event.ask,
            error=child_event.error,
            tool_call=child_event.tool_call,
            tool_result=child_event.tool_result,
            refusal=child_event.refusal,
            checkpoint=child_event.checkpoint,
            source_subflow=source,
        )

    def _with_subflow_source(self, payload: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
        copied = dict(payload)
        copied["source"] = source
        return copied

    def add_node(self, run: FlowRun, node: FlowNode) -> None:
        with self._lock:
            if node.id in run.graph.nodes:
                raise ValueError(f"Duplicate flow node id: {node.id}")
            if node.id in run.completed_nodes:
                raise ValueError(f"Cannot add completed flow node: {node.id}")
            run.graph.add_node(node)

    def add_edge(self, run: FlowRun, edge: FlowEdge) -> None:
        with self._lock:
            if edge.source in run.completed_nodes and edge.source != run.active_node_id:
                raise ValueError(f"Cannot add edge from completed node: {edge.source}")
            if edge.target in run.completed_nodes:
                raise ValueError(f"Cannot add edge to completed node: {edge.target}")
            run.graph.add_edge(edge)

    def _execute(self, run: FlowRun, context: FlowContext) -> None:
        try:
            self.emit(run, event_type="status", status="running")
            self._execute_graph(run.graph, context)
            if not run.cancel_requested.is_set():
                self.emit(run, event_type="done", status=(run.final_event.status if run.final_event else "finished"))
        except FlowCancelled as exc:
            self.emit(run, event_type="error", status="cancelled", error=str(exc))
            self.emit(run, event_type="done", status="cancelled")
        except FlowTerminated:
            self.emit(run, event_type="done", status="terminated")
        except FlowRefused:
            self.emit(run, event_type="done", status="refused")
        except Exception as exc:  # pragma: no cover - defensive boundary
            self.emit(run, event_type="error", status="failed", error=str(exc))
            self.emit(run, event_type="done", status="failed")
        finally:
            run.done.set()

    def _execute_graph(self, graph: FlowGraph, context: FlowContext) -> None:
        if graph.start not in graph.nodes:
            raise ValueError(f"Flow start node does not exist: {graph.start}")
        run = context.run
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
            run.active_node_id = node_id
            context.emit_step(code=node.id, title=node.title or node.id, status="running")
            skip_node = False
            try:
                decision = self._run_hooks("before_node", context, node=node)
                skip_node = self._apply_hook_decision(context, decision)
                if not skip_node:
                    node.handler(context)
                if node.checkpoint_policy.get("after"):
                    context.save_checkpoint(reason=f"after_node:{node.id}")
                self._apply_hook_decision(context, self._run_hooks("after_node", context, node=node))
            except Exception as exc:
                decision = self._run_hooks("on_error", context, node=node, error=exc)
                self._apply_hook_decision(context, decision)
                raise
            completed.add(node_id)
            run.completed_nodes.add(node_id)
            context.emit_step(code=node.id, title=node.title or node.id, status="finished")
            run.active_node_id = None

            for edge in graph.outgoing(node_id):
                if edge.condition is not None and not edge.condition(context):
                    continue
                incoming = graph.incoming(edge.target)
                if incoming and all(item.source in completed for item in incoming if item.condition is None):
                    if edge.target not in ready:
                        ready.append(edge.target)
                elif edge.target not in ready:
                    ready.append(edge.target)

    def _run_hooks(
        self,
        method_name: str,
        context: FlowContext,
        *,
        node: FlowNode | None = None,
        tool_name: str | None = None,
        error: Exception | None = None,
    ) -> HookDecision | None:
        hook_context = HookContext(
            run_id=context.run_id,
            node_id=node.id if node else context.run.active_node_id,
            tool_name=tool_name,
            state=context.state,
            metadata=dict(node.metadata if node else {}),
        )
        for hook in [*self.hooks, *(node.hooks if node else [])]:
            method = getattr(hook, method_name, None)
            if method is None:
                continue
            decision = method(hook_context, error) if method_name == "on_error" else method(hook_context)
            if decision is not None and decision.action != "continue":
                return decision
        return None

    def _apply_hook_decision(self, context: FlowContext, decision: HookDecision | None) -> bool:
        if decision is None or decision.action == "continue":
            return False
        if decision.action == "skip":
            return True
        if decision.action == "terminate":
            context.request_terminate(decision.reason or "flow terminated by hook")
        if decision.action == "refuse":
            context.refuse(decision.reason or "flow refused by hook", answer=decision.answer)
        raise ValueError(f"Unsupported hook decision: {decision.action}")


def context_value(run: FlowRun, key: str) -> Any:
    return run.state.get(key)

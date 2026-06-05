import threading
import time
from pathlib import Path

from src.shared.agentflow import (
    FlowEdge,
    FlowGraph,
    FlowGraphRenderer,
    FlowNode,
    InMemoryFlowRuntime,
    InMemoryMetricsSink,
    MetricsCenter,
    ReactFlow,
    SequentialFlow,
)


def test_sequential_flow_emits_steps_and_answer():
    def first(context):
        context.state["value"] = 1

    def second(context):
        context.emit_answer({"answerType": "TEXT", "answer": {"value": context.state["value"]}})

    runtime = InMemoryFlowRuntime()
    events = runtime.run_sync(SequentialFlow(
        FlowNode(id="first", handler=first),
        FlowNode(id="second", handler=second),
    ).to_graph())

    assert [event.event_type for event in events if event.event_type == "answer"]
    assert events[-1].event_type == "done"
    assert events[-1].status == "finished"


def test_node_can_disable_automatic_lifecycle_steps():
    def only_business_step(context):
        context.emit_step(code="business.step", title="业务步骤", status="finished")

    events = InMemoryFlowRuntime().run_sync(SequentialFlow(
        FlowNode(id="internal.node", handler=only_business_step, emit_lifecycle_step=False),
    ).to_graph())

    step_codes = [event.step.code for event in events if event.step is not None]
    assert step_codes == ["business.step"]


def test_graph_condition_loop_and_join():
    visited = []

    def start(context):
        visited.append("start")
        context.state["run_right"] = True

    def left(context):
        visited.append("left")

    def right(context):
        visited.append("right")

    def join(context):
        visited.append("join")

    graph = FlowGraph(start="start")
    graph.add_node(FlowNode(id="start", handler=start))
    graph.add_node(FlowNode(id="left", handler=left))
    graph.add_node(FlowNode(id="right", handler=right))
    graph.add_node(FlowNode(id="join", handler=join))
    graph.add_edge(FlowEdge(source="start", target="left"))
    graph.add_edge(FlowEdge(source="start", target="right", condition=lambda context: bool(context.state["run_right"])))
    graph.add_edge(FlowEdge(source="left", target="join"))
    graph.add_edge(FlowEdge(source="right", target="join"))

    InMemoryFlowRuntime().run_sync(graph)

    assert visited == ["start", "left", "right", "join"]


def test_react_flow_stops_on_decision():
    calls = []

    def reason(context):
        calls.append("reason")

    def act(context):
        calls.append("act")

    def observe(context):
        calls.append("observe")

    flow = ReactFlow(reason=reason, act=act, observe=observe, should_continue=lambda context: False, max_turns=3)

    InMemoryFlowRuntime().run_sync(flow.to_graph())

    assert calls == ["reason", "act", "observe"]


def test_human_input_wakes_waiting_node():
    runtime = InMemoryFlowRuntime()

    def wait_node(context):
        signal = context.wait_for_input({"type": "clarify", "title": "补充信息", "text": "请输入"})
        context.emit_answer({"answerType": "TEXT", "answer": {"text": signal.payload["text"]}})

    run = runtime.start(SequentialFlow(FlowNode(id="wait", handler=wait_node)).to_graph())
    events = []

    def collect():
        events.extend(runtime.iter_events(run.run_id))

    thread = threading.Thread(target=collect)
    thread.start()
    deadline = time.time() + 2
    while time.time() < deadline and not any(event.event_type == "ask" for event in events):
        time.sleep(0.01)
    assert runtime.send_input(run.run_id, {"text": "ok"})
    thread.join(timeout=2)

    assert any(event.event_type == "answer" and event.answer["answer"]["text"] == "ok" for event in events)


def test_cancel_signal_stops_cooperative_node():
    runtime = InMemoryFlowRuntime()

    def slow_node(context):
        while True:
            context.check_cancelled()
            time.sleep(0.01)

    run = runtime.start(SequentialFlow(FlowNode(id="slow", handler=slow_node)).to_graph())
    time.sleep(0.05)
    assert runtime.cancel(run.run_id)
    events = list(runtime.iter_events(run.run_id))

    assert any(event.status == "cancelled" for event in events)


def test_cancel_by_run_id_reports_running_state():
    runtime = InMemoryFlowRuntime()

    def slow_node(context):
        while True:
            context.check_cancelled()
            time.sleep(0.01)

    run = runtime.start(SequentialFlow(FlowNode(id="slow", handler=slow_node)).to_graph())
    time.sleep(0.05)

    assert runtime.is_running(run.run_id)
    assert runtime.cancel(run.run_id)
    events = list(runtime.iter_events(run.run_id))

    assert any(event.status == "cancelled" for event in events)
    assert not runtime.is_running(run.run_id)


def test_parallel_branches_run_concurrently_and_preserve_event_sequence():
    completed = []

    def start(context):
        context.emit_step(code="start.inner", title="start inner")

    def section(name):
        def handler(context):
            time.sleep(0.15)
            context.mutate_state("sections", [], lambda items: items.append(name))
            completed.append(name)

        return handler

    def join(context):
        context.emit_answer({"answerType": "TEXT", "answer": {"sections": sorted(context.get_state("sections", []))}})

    graph = FlowGraph(start="start")
    graph.add_node(FlowNode(id="start", handler=start))
    graph.add_node(FlowNode(id="section.a", handler=section("a")))
    graph.add_node(FlowNode(id="section.b", handler=section("b")))
    graph.add_node(FlowNode(id="section.c", handler=section("c")))
    graph.add_node(FlowNode(id="join", handler=join))
    graph.add_edge(FlowEdge(source="start", target="section.a"))
    graph.add_edge(FlowEdge(source="start", target="section.b"))
    graph.add_edge(FlowEdge(source="start", target="section.c"))
    graph.add_edge(FlowEdge(source="section.a", target="join"))
    graph.add_edge(FlowEdge(source="section.b", target="join"))
    graph.add_edge(FlowEdge(source="section.c", target="join"))

    started = time.perf_counter()
    events = InMemoryFlowRuntime(max_workers=3).run_sync(graph)
    elapsed = time.perf_counter() - started

    assert sorted(completed) == ["a", "b", "c"]
    assert elapsed < 0.35
    assert [event.sequence for event in events] == sorted(event.sequence for event in events)
    assert any(event.event_type == "answer" and event.answer["answer"]["sections"] == ["a", "b", "c"] for event in events)


def test_parallel_failure_collects_started_nodes_and_skips_downstream():
    finished = []

    def start(context):
        pass

    def ok(context):
        time.sleep(0.05)
        finished.append("ok")

    def failed(context):
        time.sleep(0.02)
        raise RuntimeError("boom")

    def downstream(context):
        finished.append("downstream")

    graph = FlowGraph(start="start")
    graph.add_node(FlowNode(id="start", handler=start))
    graph.add_node(FlowNode(id="ok", handler=ok))
    graph.add_node(FlowNode(id="failed", handler=failed))
    graph.add_node(FlowNode(id="downstream", handler=downstream))
    graph.add_edge(FlowEdge(source="start", target="ok"))
    graph.add_edge(FlowEdge(source="start", target="failed"))
    graph.add_edge(FlowEdge(source="ok", target="downstream"))
    graph.add_edge(FlowEdge(source="failed", target="downstream"))

    events = InMemoryFlowRuntime(max_workers=2).run_sync(graph)

    assert "ok" in finished
    assert "downstream" not in finished
    assert events[-1].status == "failed"
    assert any(event.event_type == "error" and "failed" in event.error.get("errorMsg", "") and "boom" in event.error.get("errorMsg", "") for event in events)


def test_graph_renderer_outputs_mermaid_for_before_and_after_build():
    flow = SequentialFlow(
        FlowNode(id="start", title="开始", handler=lambda context: None),
        FlowNode(id="finish", title="结束", handler=lambda context: None),
    )

    artifact = FlowGraphRenderer().build_artifact(flow, title="demo")

    assert artifact.before_mermaid.startswith("flowchart TD")
    assert 'start["开始"]' in artifact.after_mermaid
    assert "start --> finish" in artifact.after_mermaid


def test_metrics_center_receives_terminal_metrics_on_success_and_failure():
    sink = InMemoryMetricsSink()
    runtime = InMemoryFlowRuntime(metrics_center=MetricsCenter([sink]))

    def success(context):
        context.record_unique_metric("business.resource.used", "device")
        context.record_unique_metric("business.resource.used", "device")
        context.record_llm_output_tokens(42)
        context.emit_answer({"answerType": "TEXT", "answer": {"ok": True}})

    runtime.run_sync(SequentialFlow(FlowNode(id="success", handler=success)).to_graph())

    assert sink.items[-1].status == "finished"
    assert sink.items[-1].unique_counts["business.resource.used"] == 1
    assert sink.items[-1].llm_output_tokens == 42

    def fail(context):
        raise RuntimeError("bad")

    runtime.run_sync(SequentialFlow(FlowNode(id="fail", handler=fail)).to_graph())

    assert sink.items[-1].status == "failed"
    assert sink.items[-1].failed_node_count == 1


def test_agentflow_public_api_avoids_business_specific_helpers():
    root = Path(__file__).parents[2] / "src" / "shared" / "agentflow"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    forbidden_terms = [
        "cancel_by_chat",
        "is_conversation_running",
        "record_datacatalog_logical_entity",
        "record_logical_resource",
        "logical_entity_count",
    ]
    for term in forbidden_terms:
        assert term not in source

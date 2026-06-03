import threading
import time

from src.shared.agentflow import FlowEdge, FlowGraph, FlowNode, InMemoryFlowRuntime, ReactFlow, SequentialFlow


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

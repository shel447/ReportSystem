from src.shared.agentflow import (
    FlowEdge,
    FlowNode,
    HookDecision,
    InMemoryCheckpointSaver,
    InMemoryFlowRuntime,
    PromptMessage,
    PromptTemplate,
    SequentialFlow,
    ToolRegistry,
    ToolSpec,
)


def test_tool_call_emits_call_and_result_events():
    registry = ToolRegistry([
        ToolSpec(name="sum", handler=lambda args: args["left"] + args["right"]),
    ])
    runtime = InMemoryFlowRuntime(tool_registry=registry)

    def node(context):
        output = context.call_tool("sum", {"left": 2, "right": 3})
        context.emit_answer({"answerType": "TEXT", "answer": {"value": output}})

    events = runtime.run_sync(SequentialFlow(FlowNode(id="tool", handler=node)).to_graph())

    assert any(event.event_type == "tool_call" and event.tool_call["name"] == "sum" for event in events)
    assert any(event.event_type == "tool_result" and event.tool_result["output"] == 5 for event in events)
    assert any(event.event_type == "answer" and event.answer["answer"]["value"] == 5 for event in events)


def test_prompt_assembler_renders_messages_and_rejects_missing_variables():
    runtime = InMemoryFlowRuntime()
    template = PromptTemplate(
        name="report",
        messages=[
            PromptMessage(role="system", content="你是{role}"),
            PromptMessage(role="user", content="生成{topic}"),
        ],
    )

    def node(context):
        messages = context.render_prompt(template, {"role": "报告助手", "topic": "日报"})
        context.emit_answer({"answerType": "TEXT", "answer": {"messages": [item.content for item in messages]}})

    events = runtime.run_sync(SequentialFlow(FlowNode(id="prompt", handler=node)).to_graph())

    assert any(event.event_type == "answer" and event.answer["answer"]["messages"] == ["你是报告助手", "生成日报"] for event in events)
    try:
        runtime.prompt_assembler.render(template, {"role": "报告助手"})
    except ValueError as exc:
        assert "topic" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing prompt variable should fail")


def test_hook_can_skip_node_and_terminate_flow():
    calls = []

    class SkipHook:
        def before_node(self, context):
            return HookDecision.skip("skip this node")

    class TerminateHook:
        def after_node(self, context):
            return HookDecision.terminate("stop after first node")

    def skipped(context):
        calls.append("skipped")

    def first(context):
        calls.append("first")

    runtime = InMemoryFlowRuntime(hooks=[TerminateHook()])
    events = runtime.run_sync(
        SequentialFlow(
            FlowNode(id="first", handler=first),
            FlowNode(id="skipped", handler=skipped, hooks=[SkipHook()]),
        ).to_graph()
    )

    assert calls == ["first"]
    assert events[-1].status == "terminated"


def test_checkpoint_saver_records_state_and_event():
    saver = InMemoryCheckpointSaver()
    runtime = InMemoryFlowRuntime(checkpoint_saver=saver)

    def node(context):
        context.state["phase"] = "after-query"
        context.save_checkpoint(reason="query_done")

    run_events = runtime.run_sync(SequentialFlow(FlowNode(id="checkpoint", handler=node)).to_graph())
    run_id = run_events[0].run_id

    assert saver.latest(run_id).state["phase"] == "after-query"
    assert any(event.event_type == "checkpoint" and event.checkpoint["reason"] == "query_done" for event in run_events)


def test_refusal_finishes_with_refused_status_and_refusal_payload():
    def node(context):
        context.refuse("unsafe request")

    events = InMemoryFlowRuntime().run_sync(SequentialFlow(FlowNode(id="guard", handler=node)).to_graph())

    assert any(event.event_type == "answer" and event.status == "refused" for event in events)
    assert events[-1].status == "refused"


def test_dynamic_node_can_append_follow_up_branch():
    visited = []

    def start(context):
        visited.append("start")
        context.add_node(FlowNode(id="dynamic", handler=lambda dynamic_context: visited.append("dynamic")))
        context.add_edge(FlowEdge(source="start", target="dynamic"))

    InMemoryFlowRuntime().run_sync(SequentialFlow(FlowNode(id="start", handler=start)).to_graph())

    assert visited == ["start", "dynamic"]


def test_dynamic_edge_cannot_target_completed_node():
    def start(context):
        pass

    def late(context):
        context.add_edge(FlowEdge(source="late", target="start"))

    events = InMemoryFlowRuntime().run_sync(
        SequentialFlow(
            FlowNode(id="start", handler=start),
            FlowNode(id="late", handler=late),
        ).to_graph()
    )

    assert any(event.event_type == "error" and "completed node" in event.error for event in events)

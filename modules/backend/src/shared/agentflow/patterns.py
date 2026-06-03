"""高层 Agent Flow 模式。"""

from __future__ import annotations

from typing import Callable

from .graph import FlowEdge, FlowGraph, FlowNode
from .runtime import FlowContext


class SequentialFlow:
    """顺序流程构造器。"""

    def __init__(self, *nodes: FlowNode) -> None:
        self.nodes = list(nodes)

    def to_graph(self) -> FlowGraph:
        if not self.nodes:
            raise ValueError("SequentialFlow requires at least one node")
        graph = FlowGraph(start=self.nodes[0].id)
        for node in self.nodes:
            graph.add_node(node)
        for left, right in zip(self.nodes, self.nodes[1:]):
            graph.add_edge(FlowEdge(source=left.id, target=right.id))
        return graph


class ReactFlow:
    """reason -> act -> observe -> decide 循环流程。"""

    def __init__(
        self,
        *,
        reason: Callable[[FlowContext], None],
        act: Callable[[FlowContext], None],
        observe: Callable[[FlowContext], None],
        should_continue: Callable[[FlowContext], bool],
        max_turns: int = 6,
    ) -> None:
        self.reason = reason
        self.act = act
        self.observe = observe
        self.should_continue = should_continue
        self.max_turns = max_turns

    def to_graph(self) -> FlowGraph:
        def decide(context: FlowContext) -> None:
            context.state["react_turn"] = int(context.state.get("react_turn") or 0) + 1

        graph = FlowGraph(start="reason")
        graph.add_node(FlowNode(id="reason", title="推理", handler=self.reason, kind="react"))
        graph.add_node(FlowNode(id="act", title="行动", handler=self.act, kind="react"))
        graph.add_node(FlowNode(id="observe", title="观察", handler=self.observe, kind="react"))
        graph.add_node(FlowNode(id="decide", title="决策", handler=decide, kind="react"))
        graph.add_edge(FlowEdge(source="reason", target="act"))
        graph.add_edge(FlowEdge(source="act", target="observe"))
        graph.add_edge(FlowEdge(source="observe", target="decide"))
        graph.add_edge(
            FlowEdge(
                source="decide",
                target="reason",
                condition=lambda context: int(context.state.get("react_turn") or 0) < self.max_turns and self.should_continue(context),
            )
        )
        return graph

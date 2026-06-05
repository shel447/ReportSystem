"""低层图式流程模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
from typing import Any, Callable, Protocol

if False:  # pragma: no cover
    from .runtime import FlowContext


class FlowNodeHandler(Protocol):
    """流程节点处理函数。"""

    def __call__(self, context: "FlowContext") -> None: ...


FlowCondition = Callable[["FlowContext"], bool]


@dataclass(slots=True)
class FlowNode:
    """流程节点。"""

    id: str
    handler: FlowNodeHandler
    kind: str = "task"
    title: str | None = None
    hooks: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_policy: dict[str, Any] = field(default_factory=dict)
    checkpoint_policy: dict[str, Any] = field(default_factory=dict)
    emit_lifecycle_step: bool = True


@dataclass(slots=True)
class FlowEdge:
    """流程边；无 condition 表示默认可走。"""

    source: str
    target: str
    condition: FlowCondition | None = None


@dataclass(slots=True)
class FlowGraph:
    """可执行流程图。"""

    start: str
    nodes: dict[str, FlowNode] = field(default_factory=dict)
    edges: list[FlowEdge] = field(default_factory=list)

    def add_node(self, node: FlowNode) -> "FlowGraph":
        if not node.id:
            raise ValueError("Flow node id is required")
        if node.id in self.nodes:
            raise ValueError(f"Duplicate flow node id: {node.id}")
        self.nodes[node.id] = node
        return self

    def add_edge(self, edge: FlowEdge) -> "FlowGraph":
        if edge.source not in self.nodes:
            raise ValueError(f"Flow edge source does not exist: {edge.source}")
        if edge.target not in self.nodes:
            raise ValueError(f"Flow edge target does not exist: {edge.target}")
        self.edges.append(edge)
        return self

    def outgoing(self, node_id: str) -> list[FlowEdge]:
        return [item for item in self.edges if item.source == node_id]

    def incoming(self, node_id: str) -> list[FlowEdge]:
        return [item for item in self.edges if item.target == node_id]

    def copy(self) -> "FlowGraph":
        return FlowGraph(
            start=self.start,
            nodes=dict(self.nodes),
            edges=list(self.edges),
        )

    def deepcopy(self) -> "FlowGraph":
        return copy.deepcopy(self)

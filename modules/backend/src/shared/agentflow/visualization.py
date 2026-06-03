"""Flow graph visualization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .graph import FlowGraph


class GraphLike(Protocol):
    def to_graph(self) -> FlowGraph: ...


@dataclass(slots=True)
class FlowBuildArtifact:
    """Graph snapshots before and after high-level flow build/normalization."""

    before_graph: FlowGraph
    after_graph: FlowGraph
    before_mermaid: str
    after_mermaid: str


class FlowGraphRenderer:
    """Render flow graphs for design review and debugging."""

    def render_mermaid(self, graph: FlowGraph, *, title: str | None = None) -> str:
        lines = ["flowchart TD"]
        if title:
            lines.append(f"    %% {title}")
        for node_id, node in graph.nodes.items():
            label = node.title or node.id
            lines.append(f"    {self._node_ref(node_id)}[\"{self._escape(label)}\"]")
        for index, edge in enumerate(graph.edges, start=1):
            label = f"condition {index}" if edge.condition is not None else ""
            arrow = f" -->|\"{label}\"| " if label else " --> "
            lines.append(f"    {self._node_ref(edge.source)}{arrow}{self._node_ref(edge.target)}")
        return "\n".join(lines) + "\n"

    def build_artifact(self, flow_or_graph: FlowGraph | GraphLike, *, title: str | None = None) -> FlowBuildArtifact:
        if isinstance(flow_or_graph, FlowGraph):
            before_graph = flow_or_graph.copy()
            after_graph = flow_or_graph.copy()
        else:
            after_graph = flow_or_graph.to_graph()
            before_graph = self._before_graph_from_after(after_graph)
        return FlowBuildArtifact(
            before_graph=before_graph,
            after_graph=after_graph,
            before_mermaid=self.render_mermaid(before_graph, title=f"{title or 'flow'} before build"),
            after_mermaid=self.render_mermaid(after_graph, title=f"{title or 'flow'} after build"),
        )

    def _before_graph_from_after(self, graph: FlowGraph) -> FlowGraph:
        # High-level patterns in this codebase are already materialized through
        # to_graph(). Keep a stable before snapshot so callers can compare it
        # with future builder-normalized graphs without changing the API.
        return graph.copy()

    def _node_ref(self, node_id: str) -> str:
        safe = "".join(ch if ch.isalnum() else "_" for ch in node_id)
        if not safe:
            safe = "node"
        if safe[0].isdigit():
            safe = f"n_{safe}"
        return safe

    def _escape(self, label: str) -> str:
        return str(label).replace("\\", "\\\\").replace('"', '\\"')

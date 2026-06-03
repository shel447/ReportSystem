"""Agent Flow checkpoint 接口。"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class FlowCheckpoint:
    """一次流程 checkpoint。"""

    run_id: str
    sequence: int
    node_id: str | None
    state: dict[str, Any]
    reason: str
    created_at: float = field(default_factory=time.time)


class CheckpointSaver(Protocol):
    """Checkpoint 保存器接口；后续可替换为数据库实现。"""

    def save(self, checkpoint: FlowCheckpoint) -> FlowCheckpoint: ...

    def list(self, run_id: str) -> list[FlowCheckpoint]: ...

    def latest(self, run_id: str) -> FlowCheckpoint | None: ...


class InMemoryCheckpointSaver:
    """单进程内存 checkpoint 保存器。"""

    def __init__(self) -> None:
        self._items: dict[str, list[FlowCheckpoint]] = {}

    def save(self, checkpoint: FlowCheckpoint) -> FlowCheckpoint:
        stored = FlowCheckpoint(
            run_id=checkpoint.run_id,
            sequence=checkpoint.sequence,
            node_id=checkpoint.node_id,
            state=copy.deepcopy(checkpoint.state),
            reason=checkpoint.reason,
            created_at=checkpoint.created_at,
        )
        self._items.setdefault(stored.run_id, []).append(stored)
        return stored

    def list(self, run_id: str) -> list[FlowCheckpoint]:
        return list(self._items.get(run_id, []))

    def latest(self, run_id: str) -> FlowCheckpoint | None:
        items = self._items.get(run_id, [])
        return items[-1] if items else None

"""Infrastructure messaging adapters for transaction-bound delivery."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from ..shared.messaging import CommandReceipt, MessageEnvelope, MessagePublisher


@dataclass(slots=True)
class _PendingEvent:
    values: dict[str, object]


class AfterCommitMessagePublisher(MessagePublisher):
    """Buffers events until the owning infrastructure transaction commits."""

    def __init__(self, *, publisher: MessagePublisher) -> None:
        self.publisher = publisher
        self._pending: list[_PendingEvent] = []

    def publish_event(self, **values) -> MessageEnvelope:
        pending = _PendingEvent(values=dict(values))
        self._pending.append(pending)
        return MessageEnvelope(
            message_id=f"pending_{uuid.uuid4().hex[:20]}",
            kind="event",
            channel=values["channel"],
            topic=str(values["topic"]),
            source=str(values["source"]),
            occurred_at=time.time(),
            partition_key=str(values["partition_key"]),
            payload=values["payload"],
            source_sequence=values.get("source_sequence"),
            correlation_id=values.get("correlation_id"),
            causation_id=values.get("causation_id"),
        )

    def send_command(self, **values) -> CommandReceipt:
        return self.publisher.send_command(**values)

    def flush(self) -> None:
        pending, self._pending = self._pending, []
        for event in pending:
            self.publisher.publish_event(**event.values)

    def discard(self) -> None:
        self._pending.clear()

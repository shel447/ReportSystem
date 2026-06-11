"""Flow-specific event normalization before unified publication."""

from __future__ import annotations

from dataclasses import dataclass

from ..messaging import InteractionEvent, InteractionStep, MessageEnvelope, MessagePublisher
from .events import FlowEvent


@dataclass(frozen=True, slots=True)
class FlowEventPolicy:
    publish_tool_events_as_interaction: bool = False
    publish_checkpoint_as_interaction: bool = False


class FlowEventProcessor:
    def __init__(self, *, publisher: MessagePublisher, policy: FlowEventPolicy | None = None) -> None:
        self.publisher = publisher
        self.policy = policy or FlowEventPolicy()

    def publish(
        self,
        event: FlowEvent,
        *,
        partition_key: str,
        correlation_id: str | None,
        source: str,
    ) -> MessageEnvelope:
        channel = self._channel(event.event_type)
        topic_name = {
            "step_delta": "step",
            "tool_call": "tool_call",
            "tool_result": "tool_result",
            "checkpoint": "checkpoint",
        }.get(event.event_type, event.event_type)
        payload = self._interaction_event(event) if channel == "interaction" else event
        return self.publisher.publish_event(
            channel=channel,
            topic=f"{channel}.{topic_name}",
            source=source,
            partition_key=partition_key,
            correlation_id=correlation_id,
            source_sequence=event.sequence,
            payload=payload,
        )

    def _channel(self, event_type: str) -> str:
        if event_type in {"tool_call", "tool_result"} and not self.policy.publish_tool_events_as_interaction:
            return "observability"
        if event_type == "checkpoint" and not self.policy.publish_checkpoint_as_interaction:
            return "observability"
        return "interaction"

    def _interaction_event(self, event: FlowEvent) -> InteractionEvent:
        step = None
        if event.step is not None:
            step = InteractionStep(
                step_id=event.step.code,
                title=event.step.title,
                status=event.step.status,
                detail=event.step.detail,
                parent_step_id=event.step.parent_step_id,
                step_path=list(event.step.step_path),
            )
        return InteractionEvent(
            event_type=event.event_type,
            status=event.status,
            step=step,
            delta=list(event.delta),
            answer=event.answer,
            ask=event.ask,
            error=event.error,
            tool_call=event.tool_call,
            tool_result=event.tool_result,
            refusal=event.refusal,
            checkpoint=event.checkpoint,
            source_subflow=event.source_subflow,
        )

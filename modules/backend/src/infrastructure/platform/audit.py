"""MessageCenter consumer for best-effort platform audit delivery."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import logging
from .http_client import PlatformHttpClient
from ...shared.kernel.audit import AuditEvent, AuditPublisher
from ...shared.messaging import MessageEnvelope, MessagePublisher

LOGGER = logging.getLogger(__name__)


class ExternalAuditGateway:
    def __init__(self, *, client: PlatformHttpClient) -> None:
        self.client = client

    def write(self, event: AuditEvent) -> None:
        path = "/rest/plat/audit/v1/seculogs" if event.kind == "security" else "/rest/plat/audit/v1/logs"
        self.client.post_json(path_or_url=path, payload=_to_payload(event), user_id=event.user_id)


class AuditEventPublisher(AuditPublisher):
    def __init__(self, *, publisher: MessagePublisher) -> None:
        self.publisher = publisher

    def submit(self, event: AuditEvent) -> None:
        self.publisher.publish_event(
            channel="observability",
            topic="observability.audit.requested",
            source="shared.kernel.audit",
            partition_key=event.user_id or "audit",
            payload=event,
        )


class ExternalAuditConsumer:
    def __init__(self, *, gateway: ExternalAuditGateway) -> None:
        self.gateway = gateway

    def __call__(self, message: MessageEnvelope) -> None:
        if isinstance(message.payload, AuditEvent):
            self.gateway.write(message.payload)


def _to_payload(event: AuditEvent) -> dict[str, object]:
    payload = asdict(event)
    payload.pop("kind")
    payload["userId"] = payload.pop("user_id")
    payload["targetObj"] = payload.pop("target_obj")
    payload["dateTime"] = int(datetime.now(timezone.utc).timestamp() * 1000)
    return payload

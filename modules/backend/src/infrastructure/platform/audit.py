"""Non-blocking best-effort platform audit delivery."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import logging
from queue import Empty, Queue
from .http_client import PlatformHttpClient
from ...shared.kernel.audit import AuditEvent

LOGGER = logging.getLogger(__name__)


class ExternalAuditGateway:
    def __init__(self, *, client: PlatformHttpClient) -> None:
        self.client = client

    def write(self, event: AuditEvent) -> None:
        path = "/rest/plat/audit/v1/seculogs" if event.kind == "security" else "/rest/plat/audit/v1/logs"
        self.client.post_json(path_or_url=path, payload=_to_payload(event), user_id=event.user_id)


class AsyncAuditDispatcher:
    def __init__(self, *, gateway: ExternalAuditGateway) -> None:
        self.gateway = gateway
        self.queue: Queue[AuditEvent] = Queue()

    def submit(self, event: AuditEvent) -> None:
        self.queue.put_nowait(event)

    def drain(self, *, limit: int = 100) -> None:
        for _ in range(limit):
            try:
                event = self.queue.get_nowait()
            except Empty:
                return
            try:
                self.gateway.write(event)
            except Exception as exc:  # audit delivery never blocks business flows
                LOGGER.warning("audit delivery failed: %s", exc)


def _to_payload(event: AuditEvent) -> dict[str, object]:
    payload = asdict(event)
    payload.pop("kind")
    payload["userId"] = payload.pop("user_id")
    payload["targetObj"] = payload.pop("target_obj")
    payload["dateTime"] = int(datetime.now(timezone.utc).timestamp() * 1000)
    return payload

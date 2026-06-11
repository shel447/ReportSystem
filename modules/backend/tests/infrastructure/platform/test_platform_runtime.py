from __future__ import annotations

from src.infrastructure.platform.audit import AuditEventPublisher, ExternalAuditConsumer
from src.shared.kernel.audit import AuditEvent
from src.shared.messaging import InMemoryMessageCenter


def test_message_center_audit_delivery_failure_does_not_escape_business_flow():
    class _FailingGateway:
        def write(self, event):
            raise RuntimeError("audit unavailable")

    center = InMemoryMessageCenter()
    center.subscribe(
        name="failing-audit",
        channels={"observability"},
        topics={"observability.audit.requested"},
        handler=ExternalAuditConsumer(gateway=_FailingGateway()),
    )
    center.start()
    AuditEventPublisher(publisher=center).submit(AuditEvent(operation="test", detail="best effort", user_id="default"))
    center.stop()

from __future__ import annotations

from src.infrastructure.platform.audit import AuditEventPublisher, ExternalAuditConsumer
from src.infrastructure.platform import runtime
from src.shared.kernel.audit import AuditEvent
from src.shared.messaging import InMemoryMessageCenter


class _ConfigurationStore:
    def __init__(self, payload):
        self.payload = payload

    def current(self):
        return self.payload


def test_platform_service_url_prefers_service_environment_override(monkeypatch):
    monkeypatch.setattr(runtime, "configuration_store", _ConfigurationStore({"externalServices": {"agentcore": {"baseUrl": "http://nodeagent"}}}))
    monkeypatch.setenv("REPORT_AGENTCORE_BASE_URL", "http://emergency")

    assert runtime._service_base_url(service_key="agentcore") == "http://emergency"


def test_platform_service_url_uses_last_known_good_nodeagent_snapshot(monkeypatch):
    monkeypatch.delenv("REPORT_AGENTCORE_BASE_URL", raising=False)
    monkeypatch.delenv("REPORT_EXTERNAL_BUSINESS_BASE_URL", raising=False)
    monkeypatch.setattr(runtime, "configuration_store", _ConfigurationStore({"externalServices": {"agentcore": {"baseUrl": "http://nodeagent"}}}))

    assert runtime._service_base_url(service_key="agentcore") == "http://nodeagent"


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

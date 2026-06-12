from __future__ import annotations

from src.infrastructure.platform.audit import AuditEventPublisher, ExternalAuditConsumer
from src.infrastructure.platform import runtime as platform_runtime
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


def test_platform_runtime_registers_runtime_schedule_once(monkeypatch):
    calls = []

    class _Schedule:
        def add(self, **kwargs):
            calls.append(("add", kwargs))
            return True

        def run(self):
            calls.append(("run", None))

    class _Thread:
        def __init__(self, *, target, name, daemon):
            calls.append(("thread", {"name": name, "daemon": daemon}))
            self.target = target

        def start(self):
            calls.append(("start", None))

    schedule = _Schedule()
    monkeypatch.setattr(platform_runtime, "_scheduler", schedule)
    monkeypatch.setattr(platform_runtime, "_schedule_thread", None)
    monkeypatch.setattr(platform_runtime, "_metadata_refresh_registered", False)
    monkeypatch.setattr(platform_runtime, "_platform_started", False)
    monkeypatch.setattr(platform_runtime, "_consumers_registered", True)
    monkeypatch.setattr(platform_runtime, "Thread", _Thread)
    monkeypatch.setattr(platform_runtime.message_center, "start", lambda: calls.append(("center_start", None)))
    monkeypatch.setattr(platform_runtime.message_center, "stop", lambda: calls.append(("center_stop", None)))
    monkeypatch.setattr(platform_runtime, "_safe_refresh_metadata", lambda: calls.append(("refresh", None)))

    platform_runtime.start_platform_runtime()
    platform_runtime.start_platform_runtime()
    platform_runtime.stop_platform_runtime()
    platform_runtime.start_platform_runtime()

    assert [name for name, _ in calls].count("add") == 1
    assert [name for name, _ in calls].count("thread") == 1
    assert [name for name, _ in calls].count("start") == 1
    assert [name for name, _ in calls].count("refresh") == 2
    assert [name for name, _ in calls].count("center_start") == 2
    assert [name for name, _ in calls].count("center_stop") == 1
    add_call = next(value for name, value in calls if name == "add")
    assert add_call["func"] is platform_runtime._run_metadata_refresh
    assert add_call["interval"] == 300


def test_metadata_schedule_adapter_ignores_runtime_params(monkeypatch):
    calls = []
    monkeypatch.setattr(platform_runtime, "_safe_refresh_metadata", lambda: calls.append("refresh"))

    platform_runtime._run_metadata_refresh({"runtime": "params"})

    assert calls == ["refresh"]

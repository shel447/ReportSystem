from contextlib import contextmanager

import pytest

from src.infrastructure import dependencies
from src.infrastructure.messaging import AfterCommitMessagePublisher
from src.shared.messaging import InMemoryMessageCenter


def test_after_commit_publisher_holds_domain_event_until_flush():
    center = InMemoryMessageCenter()
    subscription = center.subscribe(name="domain", channels={"domain"})
    center.start()
    publisher = AfterCommitMessagePublisher(publisher=center)

    pending = publisher.publish_event(
        channel="domain",
        topic="domain.report.generated",
        source="report",
        partition_key="report_1",
        payload={"reportId": "report_1"},
    )

    assert pending.sequence == 0
    assert subscription.messages.empty()
    publisher.flush()
    assert subscription.messages.get(timeout=1).payload == {"reportId": "report_1"}


def test_after_commit_publisher_discards_event_on_rollback():
    center = InMemoryMessageCenter()
    subscription = center.subscribe(name="domain", channels={"domain"})
    center.start()
    publisher = AfterCommitMessagePublisher(publisher=center)

    publisher.publish_event(
        channel="domain",
        topic="domain.report.generated",
        source="report",
        partition_key="report_1",
        payload={"reportId": "report_1"},
    )
    publisher.discard()
    publisher.flush()

    assert subscription.messages.empty()


class RecordingPublisher:
    def __init__(self, events):
        self.events = events

    def flush(self):
        self.events.append("flush")

    def discard(self):
        self.events.append("discard")


def _install_transaction_fakes(monkeypatch, events):
    @contextmanager
    def transaction(*, reraise):
        assert reraise is True
        events.append("open")
        try:
            yield "session"
        except Exception:
            events.append("rollback")
            raise
        else:
            events.append("commit")
        finally:
            events.append("close")

    monkeypatch.setattr(dependencies, "db_session", transaction)
    monkeypatch.setattr(
        dependencies,
        "AfterCommitMessagePublisher",
        lambda **_kwargs: RecordingPublisher(events),
    )


def test_report_scope_flushes_events_after_runtime_transaction_commits(monkeypatch):
    events = []
    _install_transaction_fakes(monkeypatch, events)
    monkeypatch.setattr(
        dependencies,
        "build_report_service",
        lambda session, **_kwargs: ("report-service", session),
    )

    with dependencies.report_service_scope() as service:
        assert service == ("report-service", "session")

    assert events == ["open", "commit", "close", "flush"]


def test_conversation_scope_shares_runtime_session_and_flushes_after_commit(monkeypatch):
    events = []
    _install_transaction_fakes(monkeypatch, events)
    monkeypatch.setattr(dependencies, "build_data_query_gateway", lambda: "query")
    monkeypatch.setattr(
        dependencies,
        "build_data_analysis_service",
        lambda: type("Analysis", (), {"subflow_specs": lambda self: ()})(),
    )
    monkeypatch.setattr(
        dependencies,
        "build_report_scenario_provider",
        lambda session, **_kwargs: ("report-provider", session),
    )
    monkeypatch.setattr(
        dependencies,
        "build_data_analysis_scenario_provider",
        lambda **_kwargs: "analysis-provider",
    )
    monkeypatch.setattr(
        dependencies,
        "_build_conversation_service",
        lambda **kwargs: kwargs["scenario_providers"],
    )

    with dependencies.conversation_service_scope() as providers:
        assert providers == [("report-provider", "session"), "analysis-provider"]

    assert events == ["open", "commit", "close", "flush"]


def test_service_scope_discards_events_after_runtime_transaction_rolls_back(monkeypatch):
    events = []
    _install_transaction_fakes(monkeypatch, events)
    monkeypatch.setattr(
        dependencies,
        "build_report_service",
        lambda session, **_kwargs: ("report-service", session),
    )

    with pytest.raises(RuntimeError, match="boom"):
        with dependencies.report_service_scope():
            raise RuntimeError("boom")

    assert events == ["open", "rollback", "close", "discard"]

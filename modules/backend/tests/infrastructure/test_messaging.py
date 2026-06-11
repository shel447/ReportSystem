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

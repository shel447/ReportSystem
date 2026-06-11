from __future__ import annotations

import threading
import time

from src.shared.messaging import CommandFailure, FlowControlCommand, InMemoryMessageCenter, InteractionEvent


def test_message_center_filters_topics_and_does_not_replay_old_messages():
    center = InMemoryMessageCenter()
    center.start()
    first = center.subscribe(name="first", channels={"interaction"}, topics={"interaction.step"}, partition_key="chat_1")

    center.publish_event(
        channel="interaction",
        topic="interaction.step",
        source="test",
        partition_key="chat_1",
        payload={"step": "first"},
    )
    center.publish_event(
        channel="interaction",
        topic="interaction.answer",
        source="test",
        partition_key="chat_1",
        payload={"answer": "ignored"},
    )

    assert first.messages.get(timeout=1).payload == {"step": "first"}
    late = center.subscribe(name="late", channels={"interaction"}, partition_key="chat_1")
    assert late.messages.empty()


def test_non_flow_module_can_publish_standard_interaction_event():
    center = InMemoryMessageCenter()
    interaction = center.subscribe(name="conversation", channels={"interaction"}, partition_key="chat_1")
    center.start()

    center.publish_event(
        channel="interaction",
        topic="interaction.answer",
        source="contexts.example",
        partition_key="chat_1",
        payload=InteractionEvent(
            event_type="answer",
            status="finished",
            answer={"answerType": "TEXT", "answer": {"text": "done"}},
        ),
    )

    message = interaction.messages.get(timeout=1)
    assert isinstance(message.payload, InteractionEvent)
    assert message.payload.answer["answer"]["text"] == "done"


def test_message_center_assigns_strict_partition_sequence_under_parallel_publish():
    center = InMemoryMessageCenter()
    center.start()
    subscription = center.subscribe(name="ordered", channels={"interaction"}, partition_key="chat_1")

    threads = [
        threading.Thread(
            target=lambda value=value: center.publish_event(
                channel="interaction",
                topic="interaction.delta",
                source="test",
                partition_key="chat_1",
                payload=value,
            )
        )
        for value in range(20)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    messages = [subscription.messages.get(timeout=1) for _ in range(20)]
    assert [item.sequence for item in messages] == list(range(1, 21))


def test_async_consumer_preserves_each_partition_and_runs_partitions_in_parallel():
    center = InMemoryMessageCenter()
    delivered = {"a": [], "b": []}
    completed = threading.Event()

    def consume(message):
        time.sleep(0.1)
        delivered[message.partition_key].append(message.payload)
        if sum(len(items) for items in delivered.values()) == 4:
            completed.set()

    center.subscribe(name="partitioned", channels={"domain"}, handler=consume)
    center.start()
    started = time.perf_counter()
    for value in range(2):
        center.publish_event(channel="domain", topic="domain.test", source="test", partition_key="a", payload=value)
        center.publish_event(channel="domain", topic="domain.test", source="test", partition_key="b", payload=value)

    assert completed.wait(timeout=1)
    assert time.perf_counter() - started < 0.35
    assert delivered == {"a": [0, 1], "b": [0, 1]}


def test_consumer_failure_is_isolated_and_emits_observability_event():
    center = InMemoryMessageCenter()
    failures = center.subscribe(
        name="failure-observer",
        channels={"observability"},
        topics={"observability.consumer.failed"},
    )
    delivered = threading.Event()
    center.subscribe(
        name="broken",
        channels={"domain"},
        handler=lambda _message: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    center.subscribe(
        name="healthy",
        channels={"domain"},
        handler=lambda _message: delivered.set(),
    )
    center.start()

    center.publish_event(channel="domain", topic="domain.report.generated", source="test", partition_key="report_1", payload={})

    assert delivered.wait(timeout=1)
    assert failures.messages.get(timeout=1).payload.consumer_name == "broken"


def test_command_is_queued_only_for_unique_target_handler():
    center = InMemoryMessageCenter()
    received = []
    center.register_command_handler(target="agentflow.runtime.test", topic="control.agentflow.cancel", handler=lambda message: received.append(message.payload))
    center.start()

    receipt = center.send_command(
        topic="control.agentflow.cancel",
        target="agentflow.runtime.test",
        source="conversation",
        partition_key="chat_1",
        payload=FlowControlCommand(run_id="run_1"),
    )

    deadline = time.time() + 1
    while not received and time.time() < deadline:
        time.sleep(0.01)
    assert receipt.status == "queued"
    assert received == [FlowControlCommand(run_id="run_1")]


def test_duplicate_command_handler_is_rejected():
    center = InMemoryMessageCenter()
    center.register_command_handler(target="agentflow", topic="control.agentflow.cancel", handler=lambda _message: None)

    try:
        center.register_command_handler(target="agentflow", topic="control.agentflow.cancel", handler=lambda _message: None)
    except ValueError as exc:
        assert "Duplicate command handler" in str(exc)
    else:
        raise AssertionError("duplicate command handler should fail")


def test_missing_command_target_emits_follow_up_failure_event():
    center = InMemoryMessageCenter()
    failures = center.subscribe(
        name="command-failures",
        channels={"observability"},
        topics={"observability.command.unhandled"},
        partition_key="chat_1",
    )
    center.start()

    receipt = center.send_command(
        topic="control.agentflow.cancel",
        target="missing-runtime",
        source="conversation",
        partition_key="chat_1",
        payload=FlowControlCommand(run_id="run_1"),
    )

    failure = failures.messages.get(timeout=1)
    assert isinstance(failure.payload, CommandFailure)
    assert failure.payload.command_id == receipt.command_id
    assert failure.payload.target == "missing-runtime"
    assert failure.causation_id == receipt.command_id


def test_message_center_can_restart_registered_consumers():
    center = InMemoryMessageCenter()
    delivered = []
    center.subscribe(
        name="restartable",
        channels={"domain"},
        topics={"domain.report.generated"},
        handler=lambda message: delivered.append(message.payload),
    )
    center.start()
    center.stop()
    center.start()

    center.publish_event(
        channel="domain",
        topic="domain.report.generated",
        source="test",
        partition_key="report_1",
        payload={"reportId": "report_1"},
    )

    deadline = time.time() + 1
    while not delivered and time.time() < deadline:
        time.sleep(0.01)
    assert delivered == [{"reportId": "report_1"}]

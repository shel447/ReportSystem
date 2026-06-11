"""In-memory unified message center."""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from .models import CommandFailure, CommandReceipt, ConsumerFailure, MessageChannel, MessageEnvelope

LOGGER = logging.getLogger(__name__)
MessageHandler = Callable[[MessageEnvelope], None]


class MessagePublisher(Protocol):
    def publish_event(
        self,
        *,
        channel: MessageChannel,
        topic: str,
        source: str,
        partition_key: str,
        payload: object,
        source_sequence: int | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> MessageEnvelope: ...

    def send_command(
        self,
        *,
        topic: str,
        target: str,
        source: str,
        partition_key: str,
        payload: object,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> CommandReceipt: ...


@dataclass(slots=True)
class MessageSubscription:
    id: str
    name: str
    channels: frozenset[str]
    topics: frozenset[str] = frozenset()
    partition_key: str | None = None
    handler: MessageHandler | None = None
    messages: "queue.Queue[MessageEnvelope]" = field(default_factory=queue.Queue)
    active: bool = True

    def accepts(self, message: MessageEnvelope) -> bool:
        if not self.active or message.channel not in self.channels:
            return False
        if self.topics and message.topic not in self.topics:
            return False
        return self.partition_key is None or message.partition_key == self.partition_key


class MessageConsumer(Protocol):
    def __call__(self, message: MessageEnvelope) -> None: ...


class MessageCenter(MessagePublisher, Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def subscribe(self, *, name: str, channels: Iterable[str], topics: Iterable[str] = (), partition_key: str | None = None, handler: MessageHandler | None = None) -> MessageSubscription: ...
    def unsubscribe(self, subscription: MessageSubscription) -> None: ...
    def register_command_handler(self, *, target: str, topic: str, handler: MessageHandler) -> None: ...


class InMemoryMessageCenter(MessageCenter):
    """At-most-once in-process messaging with partition ordering."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sequences: dict[str, int] = {}
        self._subscriptions: dict[str, MessageSubscription] = {}
        self._workers: dict[str, threading.Thread] = {}
        self._command_handlers: dict[tuple[str, str], MessageSubscription] = {}
        self._consumer_executor: ThreadPoolExecutor | None = None
        self._partition_futures: dict[tuple[str, str], Future[None]] = {}
        self._running = False

    def start(self) -> None:
        with self._lock:
            self._running = True
            if self._consumer_executor is None:
                self._consumer_executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="message-delivery")
            for subscription in self._subscriptions.values():
                subscription.active = True
                self._start_worker(subscription)
            for subscription in self._command_handlers.values():
                subscription.active = True
                self._start_worker(subscription)

    def stop(self) -> None:
        with self._lock:
            self._running = False
            subscriptions = [*self._subscriptions.values(), *self._command_handlers.values()]
            for subscription in subscriptions:
                subscription.active = False
                subscription.messages.put(_sentinel())
            workers = list(self._workers.values())
            self._workers.clear()
            executor = self._consumer_executor
            self._consumer_executor = None
            self._partition_futures.clear()
        for worker in workers:
            worker.join(timeout=1)
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    def subscribe(
        self,
        *,
        name: str,
        channels: Iterable[str],
        topics: Iterable[str] = (),
        partition_key: str | None = None,
        handler: MessageHandler | None = None,
    ) -> MessageSubscription:
        subscription = MessageSubscription(
            id=f"subscription_{uuid.uuid4().hex[:16]}",
            name=name,
            channels=frozenset(channels),
            topics=frozenset(topics),
            partition_key=partition_key,
            handler=handler,
        )
        with self._lock:
            self._subscriptions[subscription.id] = subscription
            if self._running:
                self._start_worker(subscription)
        return subscription

    def unsubscribe(self, subscription: MessageSubscription) -> None:
        with self._lock:
            self._subscriptions.pop(subscription.id, None)
            subscription.active = False
            subscription.messages.put(_sentinel())

    def register_command_handler(self, *, target: str, topic: str, handler: MessageHandler) -> None:
        key = (target, topic)
        with self._lock:
            if key in self._command_handlers:
                raise ValueError(f"Duplicate command handler: {target}/{topic}")
            subscription = MessageSubscription(
                id=f"command_{uuid.uuid4().hex[:16]}",
                name=target,
                channels=frozenset({"control"}),
                topics=frozenset({topic}),
                handler=handler,
            )
            self._command_handlers[key] = subscription
            if self._running:
                self._start_worker(subscription)

    def publish_event(
        self,
        *,
        channel: MessageChannel,
        topic: str,
        source: str,
        partition_key: str,
        payload: object,
        source_sequence: int | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> MessageEnvelope:
        with self._lock:
            message = self._envelope_locked(
                kind="event",
                channel=channel,
                topic=topic,
                source=source,
                partition_key=partition_key,
                payload=payload,
                source_sequence=source_sequence,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            subscriptions = [item for item in self._subscriptions.values() if item.accepts(message)]
            for subscription in subscriptions:
                subscription.messages.put(message)
        return message

    def send_command(
        self,
        *,
        topic: str,
        target: str,
        source: str,
        partition_key: str,
        payload: object,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> CommandReceipt:
        with self._lock:
            message = self._envelope_locked(
                kind="command",
                channel="control",
                topic=topic,
                source=source,
                partition_key=partition_key,
                payload=payload,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            handler = self._command_handlers.get((target, topic))
            if handler is not None:
                handler.messages.put(message)
            else:
                failure = self._envelope_locked(
                    kind="event",
                    channel="observability",
                    topic="observability.command.unhandled",
                    source="shared.messaging",
                    partition_key=partition_key,
                    correlation_id=correlation_id,
                    causation_id=message.message_id,
                    payload=CommandFailure(
                        command_id=message.message_id,
                        target=target,
                        topic=topic,
                        reason="target handler is not registered",
                    ),
                )
                for subscription in self._subscriptions.values():
                    if subscription.accepts(failure):
                        subscription.messages.put(failure)
        return CommandReceipt(command_id=message.message_id)

    def _envelope_locked(self, **values) -> MessageEnvelope:
        partition_key = str(values["partition_key"] or "")
        sequence = self._sequences.get(partition_key, 0) + 1
        self._sequences[partition_key] = sequence
        return MessageEnvelope(
            message_id=f"message_{uuid.uuid4().hex[:20]}",
            occurred_at=time.time(),
            sequence=sequence,
            **values,
        )

    def _start_worker(self, subscription: MessageSubscription) -> None:
        if subscription.handler is None or subscription.id in self._workers:
            return
        worker = threading.Thread(
            target=self._consume,
            args=(subscription,),
            name=f"message-consumer-{subscription.name}",
            daemon=True,
        )
        self._workers[subscription.id] = worker
        worker.start()

    def _consume(self, subscription: MessageSubscription) -> None:
        while subscription.active:
            message = subscription.messages.get()
            if not subscription.active or message.topic == "__message_center_stop__":
                return
            with self._lock:
                executor = self._consumer_executor
                if executor is None:
                    return
                key = (subscription.id, message.partition_key)
                previous = self._partition_futures.get(key)
                self._partition_futures[key] = executor.submit(self._deliver_after, previous, subscription, message)

    def _deliver_after(
        self,
        previous: Future[None] | None,
        subscription: MessageSubscription,
        message: MessageEnvelope,
    ) -> None:
        if previous is not None:
            try:
                previous.result()
            except Exception:
                pass
        if not subscription.active:
            return
        try:
            subscription.handler(message)
        except Exception as exc:
            LOGGER.warning("message consumer failed name=%s topic=%s: %s", subscription.name, message.topic, exc)
            if message.topic != "observability.consumer.failed":
                self.publish_event(
                    channel="observability",
                    topic="observability.consumer.failed",
                    source="shared.messaging",
                    partition_key=message.partition_key,
                    correlation_id=message.correlation_id,
                    causation_id=message.message_id,
                    payload=ConsumerFailure(
                        consumer_name=subscription.name,
                        message_id=message.message_id,
                        topic=message.topic,
                        error=str(exc),
                    ),
                )


def _sentinel() -> MessageEnvelope:
    return MessageEnvelope(
        message_id="",
        kind="event",
        channel="observability",
        topic="__message_center_stop__",
        source="shared.messaging",
        occurred_at=0,
        partition_key="",
        payload=None,
    )

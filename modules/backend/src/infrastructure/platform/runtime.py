"""Application-lifetime platform refresh and asynchronous audit runtime."""

from __future__ import annotations

from threading import Thread

from runtime.schedule import Schedule

from .audit import AuditEventPublisher, ExternalAuditConsumer, ExternalAuditGateway
from .cache import platform_cache
from .client import RuntimeHttpClient
from .configuration import ExternalMetadataSyncGateway
from .policy_auth import ExternalPolicyAuthenticationGateway
from ...shared.kernel.log import logger
from ...shared.messaging import InMemoryMessageCenter

def build_runtime_client() -> RuntimeHttpClient:
    return RuntimeHttpClient()


def build_policy_auth_gateway() -> ExternalPolicyAuthenticationGateway:
    return ExternalPolicyAuthenticationGateway(client=build_runtime_client())


metadata_gateway = ExternalMetadataSyncGateway(client=build_runtime_client())
message_center = InMemoryMessageCenter()
audit_publisher = AuditEventPublisher(publisher=message_center)
audit_consumer = ExternalAuditConsumer(gateway=ExternalAuditGateway(client=build_runtime_client()))
_scheduler = Schedule()
_schedule_thread: Thread | None = None
_metadata_refresh_registered = False
_platform_started = False
_metadata_version: str | None = None
_consumers_registered = False


def start_platform_runtime() -> None:
    global _consumers_registered, _metadata_refresh_registered, _platform_started, _schedule_thread
    if _platform_started:
        return
    if not _consumers_registered:
        message_center.subscribe(
            name="external-audit",
            channels={"observability"},
            topics={"observability.audit.requested"},
            handler=audit_consumer,
        )
        _consumers_registered = True
    message_center.start()
    _safe_refresh_metadata()
    if not _metadata_refresh_registered:
        _scheduler.add(func=_run_metadata_refresh, interval=300)
        _metadata_refresh_registered = True
    if _schedule_thread is None:
        _schedule_thread = Thread(
            target=_scheduler.run,
            name="runtime-schedule",
            daemon=True,
        )
        _schedule_thread.start()
    _platform_started = True


def stop_platform_runtime() -> None:
    global _platform_started
    if not _platform_started:
        return
    message_center.stop()
    _platform_started = False


def _run_metadata_refresh(_params) -> None:
    _safe_refresh_metadata()


def _safe_refresh_metadata() -> None:
    global _metadata_version
    try:
        payload = metadata_gateway.check_package_register_process()
        version = str(payload.get("version") or payload.get("process") or payload)
        if _metadata_version is not None and version != _metadata_version:
            platform_cache.clear(prefix="datacatalog:")
            platform_cache.clear(prefix="rag:")
        _metadata_version = version
    except Exception as exc:
        logger.warn("metadata refresh failed: %s", exc)

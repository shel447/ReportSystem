"""Application-lifetime platform refresh and asynchronous audit runtime."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

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
_scheduler: BackgroundScheduler | None = None
_metadata_version: str | None = None
_consumers_registered = False


def start_platform_runtime() -> None:
    global _scheduler, _consumers_registered
    if _scheduler is not None:
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
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_safe_refresh_metadata, "interval", seconds=300, id="metadata-refresh", replace_existing=True)
    _scheduler.start()


def stop_platform_runtime() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    message_center.stop()


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

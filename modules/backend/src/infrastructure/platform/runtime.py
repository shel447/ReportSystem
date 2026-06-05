"""Application-lifetime platform refresh and asynchronous audit runtime."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from .audit import AsyncAuditDispatcher, ExternalAuditGateway
from .cache import platform_cache
from .configuration import ExternalMetadataSyncGateway, ExternalNodeAgentGateway, RuntimeConfigurationStore
from .http_client import ExternalServiceConfig, PlatformHttpClient
from .policy_auth import ExternalPolicyAuthenticationGateway

LOGGER = logging.getLogger(__name__)
DEFAULT_PLATFORM_BASE_URL = "http://127.0.0.1:8310"


def build_platform_client(*, service_key: str | None = None) -> PlatformHttpClient:
    return PlatformHttpClient(
        config=ExternalServiceConfig(
            base_url=_service_base_url(service_key=service_key),
            timeout_seconds=float(os.getenv("REPORT_EXTERNAL_TIMEOUT_SECONDS") or 10),
        )
    )


def build_policy_auth_gateway() -> ExternalPolicyAuthenticationGateway:
    return ExternalPolicyAuthenticationGateway(client=build_platform_client(service_key="policy"))


def _service_base_url(*, service_key: str | None) -> str:
    if service_key:
        env_key = f"REPORT_{service_key.upper().replace('-', '_')}_BASE_URL"
        configured = str(os.getenv(env_key) or "").strip()
        if configured:
            return configured
    emergency = str(os.getenv("REPORT_EXTERNAL_BUSINESS_BASE_URL") or "").strip()
    if emergency:
        return emergency
    store = globals().get("configuration_store")
    snapshot = store.current() if store is not None else {}
    services = snapshot.get("externalServices") if isinstance(snapshot, dict) else None
    service = services.get(service_key) if isinstance(services, dict) and service_key else None
    if isinstance(service, dict) and str(service.get("baseUrl") or "").strip():
        return str(service["baseUrl"]).strip()
    return DEFAULT_PLATFORM_BASE_URL


configuration_store = RuntimeConfigurationStore(gateway=ExternalNodeAgentGateway(client=build_platform_client()))
metadata_gateway = ExternalMetadataSyncGateway(client=build_platform_client())
audit_dispatcher = AsyncAuditDispatcher(gateway=ExternalAuditGateway(client=build_platform_client(service_key="audit")))
_scheduler: BackgroundScheduler | None = None
_metadata_version: str | None = None


def start_platform_runtime() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _safe_refresh_configuration()
    _safe_refresh_metadata()
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_safe_refresh_configuration, "interval", seconds=300, id="nodeagent-refresh", replace_existing=True)
    _scheduler.add_job(_safe_refresh_metadata, "interval", seconds=300, id="metadata-refresh", replace_existing=True)
    _scheduler.add_job(audit_dispatcher.drain, "interval", seconds=2, id="audit-drain", replace_existing=True)
    _scheduler.start()


def stop_platform_runtime() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None


def _safe_refresh_configuration() -> None:
    try:
        configuration_store.refresh()
    except Exception as exc:
        LOGGER.warning("NodeAgent refresh failed; keeping last-known-good config: %s", exc)


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
        LOGGER.warning("metadata refresh failed: %s", exc)

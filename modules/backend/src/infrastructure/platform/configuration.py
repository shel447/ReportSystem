"""NodeAgent configuration snapshot with last-known-good semantics."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

from .cache import MemoryTtlCache, platform_cache
from .http_client import PlatformHttpClient


class ExternalNodeAgentGateway:
    def __init__(self, *, client: PlatformHttpClient) -> None:
        self.client = client

    def get_app_config(self) -> dict[str, Any]:
        return self.client.get_json(path_or_url="/rest/nodeagent/v2/csi/appconf", params={"watch": "false"})


class RuntimeConfigurationStore:
    def __init__(self, *, gateway: ExternalNodeAgentGateway, cache: MemoryTtlCache | None = None) -> None:
        self.gateway = gateway
        self.cache = cache or platform_cache
        self._snapshot: dict[str, Any] = {}
        self._lock = RLock()

    def refresh(self) -> dict[str, Any]:
        payload = self.gateway.get_app_config()
        with self._lock:
            self._snapshot = deepcopy(payload)
            self.cache.set("nodeagent:appconf", deepcopy(payload), ttl_seconds=300)
            return deepcopy(self._snapshot)

    def current(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._snapshot)


class ExternalMetadataSyncGateway:
    def __init__(self, *, client: PlatformHttpClient) -> None:
        self.client = client

    def check_package_register_process(self) -> dict[str, Any]:
        return self.client.get_json(path_or_url="/rest/entassistantservice/v1/chatbi/package/register/process")

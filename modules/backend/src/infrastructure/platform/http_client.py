"""Shared HTTP mechanics for platform adapters."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any
from urllib.parse import urljoin

import httpx

from ...shared.kernel.errors import UpstreamError, ValidationError


@dataclass(frozen=True, slots=True)
class ExternalServiceConfig:
    base_url: str
    timeout_seconds: float = 10.0


class PlatformHeaderProvider:
    """Build transport headers without leaking authentication into contexts."""

    def headers(self, *, user_id: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if user_id:
            headers["X-User-Id"] = user_id
        authorization = str(os.getenv("REPORT_PLATFORM_AUTHORIZATION") or "").strip()
        if authorization:
            headers["Authorization"] = authorization
        return headers


class PlatformHttpClient:
    def __init__(self, *, config: ExternalServiceConfig, header_provider: PlatformHeaderProvider | None = None) -> None:
        self.config = config
        self.header_provider = header_provider or PlatformHeaderProvider()

    def resolve_url(self, path_or_url: str) -> str:
        value = str(path_or_url or "").strip()
        if not value:
            raise ValidationError("external service url is required")
        if value.startswith(("http://", "https://")):
            return value
        if not value.startswith("/"):
            raise ValidationError(f"external service relative url must start with /: {value}")
        return urljoin(f"{self.config.base_url.rstrip('/')}/", value.lstrip("/"))

    def get_json(self, *, path_or_url: str, user_id: str | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path_or_url=path_or_url, user_id=user_id, params=params)

    def post_json(self, *, path_or_url: str, payload: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
        return self._request("POST", path_or_url=path_or_url, user_id=user_id, payload=payload)

    def _request(
        self,
        method: str,
        *,
        path_or_url: str,
        user_id: str | None,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self.resolve_url(path_or_url)
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.request(method, url, json=payload, params=params, headers=self.header_provider.headers(user_id=user_id))
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise UpstreamError(f"外部服务超时: {url}") from exc
        except UpstreamError:
            raise
        except Exception as exc:
            raise UpstreamError(f"外部服务调用失败: {url}: {exc}") from exc
        if not isinstance(data, dict):
            raise UpstreamError(f"外部服务响应必须为 JSON object: {url}")
        return data

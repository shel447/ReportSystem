"""Shared HTTP mechanics for platform adapters."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any
from urllib.parse import urljoin

import httpx

from ...shared.kernel.errors import ErrorCode, UpstreamError, ValidationError


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
            raise UpstreamError(
                "系统处理超时，请稍后重试。",
                details={"url": url},
                error_code=ErrorCode.BASE_OVERTIME,
                category="timeout",
                retryable=True,
                http_status=504,
            ) from exc
        except UpstreamError:
            raise
        except httpx.HTTPStatusError as exc:
            upstream_details = _http_error_details(exc.response)
            raise UpstreamError(
                "外部服务调用失败，请稍后重试。",
                details={"url": url, "statusCode": exc.response.status_code, **upstream_details},
                error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                source="platform",
                retryable=exc.response.status_code >= 500,
                http_status=502,
            ) from exc
        except ValueError as exc:
            raise UpstreamError(
                "外部服务响应格式无效。",
                details={"url": url},
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="platform",
                http_status=502,
            ) from exc
        except Exception as exc:
            raise UpstreamError(
                "外部服务调用失败，请稍后重试。",
                details={"url": url, "reason": str(exc)},
                error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                source="platform",
                http_status=502,
            ) from exc
        if not isinstance(data, dict):
            raise UpstreamError(
                "外部服务响应格式无效。",
                details={"url": url},
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="platform",
                http_status=502,
            )
        return data


def _http_error_details(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return {"upstreamMessage": text[:240]} if text else {}
    if not isinstance(payload, dict):
        return {}
    code = payload.get("errorCode") or payload.get("code") or payload.get("retCode")
    message = payload.get("errorMsg") or payload.get("message") or payload.get("retInfo")
    details: dict[str, Any] = {}
    if code is not None:
        details["upstreamCode"] = str(code)
    if message is not None:
        details["upstreamMessage"] = str(message)
    return details

"""External platform policy authentication adapter."""

from __future__ import annotations

from typing import Any

import httpx

from ...shared.kernel.errors import ErrorCode, UpstreamError
from ...shared.kernel.policy_auth import (
    PolicyAuthenticationGateway,
    PolicyAuthenticationRequest,
    PolicyAuthenticationResult,
)
from .http_client import PlatformHttpClient

POLICY_AUTH_PATH = "/rest/dte/smartbi/v1/proxy/auth/chat"


class ExternalPolicyAuthenticationGateway(PolicyAuthenticationGateway):
    def __init__(self, *, client: PlatformHttpClient) -> None:
        self._client = client

    def authenticate(self, request: PolicyAuthenticationRequest) -> PolicyAuthenticationResult:
        url = self._client.resolve_url(POLICY_AUTH_PATH)
        try:
            with httpx.Client(timeout=self._client.config.timeout_seconds) as client:
                response = client.get(url, headers=request.headers)
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                "系统处理超时，请稍后重试。",
                details={"url": url},
                error_code=ErrorCode.BASE_OVERTIME,
                category="timeout",
                retryable=True,
                http_status=504,
            ) from exc
        except Exception as exc:
            raise UpstreamError(
                "外部服务调用失败，请稍后重试。",
                details={"url": url, "reason": str(exc)},
                error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                source="platform",
                http_status=502,
            ) from exc

        if response.status_code in {401, 403}:
            details = _response_details(response)
            return PolicyAuthenticationResult(
                allowed=False,
                upstream_code=details.get("upstreamCode"),
                upstream_message=details.get("upstreamMessage"),
            )
        if response.status_code >= 400:
            details = _response_details(response)
            raise UpstreamError(
                "外部服务调用失败，请稍后重试。",
                details={"url": url, "statusCode": response.status_code, **details},
                error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                source="platform",
                retryable=response.status_code >= 500,
                http_status=502,
            )

        payload = _json_or_empty(response)
        if payload is None:
            return PolicyAuthenticationResult(allowed=True)
        allowed, explicit = _extract_allowed(payload)
        if explicit:
            return PolicyAuthenticationResult(
                allowed=allowed,
                upstream_code=_first_text(payload, "errorCode", "code", "retCode"),
                upstream_message=_first_text(payload, "errorMsg", "message", "retInfo", "reason"),
            )
        ret_code = payload.get("retCode")
        if ret_code is not None:
            return PolicyAuthenticationResult(
                allowed=str(ret_code) == "0",
                upstream_code=str(ret_code),
                upstream_message=_first_text(payload, "retInfo", "errorMsg", "message"),
            )
        return PolicyAuthenticationResult(allowed=True)


def _json_or_empty(response: httpx.Response) -> dict[str, Any] | None:
    text = (response.text or "").strip()
    if not text:
        return None
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpstreamError(
            "外部服务响应格式无效。",
            details={"url": str(response.url)},
            error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
            source="platform",
            http_status=502,
        ) from exc
    if not isinstance(payload, dict):
        raise UpstreamError(
            "外部服务响应格式无效。",
            details={"url": str(response.url)},
            error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
            source="platform",
            http_status=502,
        )
    return payload


def _extract_allowed(payload: dict[str, Any]) -> tuple[bool, bool]:
    for key in ("allowed", "isAllowed", "authenticated", "pass"):
        if key in payload:
            return _as_bool(payload.get(key)), True
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("allowed", "isAllowed", "authenticated", "pass"):
            if key in data:
                return _as_bool(data.get(key)), True
    return True, False


def _response_details(response: httpx.Response) -> dict[str, str]:
    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return {"upstreamMessage": text[:240]} if text else {}
    if not isinstance(payload, dict):
        return {}
    details: dict[str, str] = {}
    code = _first_text(payload, "errorCode", "code", "retCode")
    message = _first_text(payload, "errorMsg", "message", "retInfo", "reason")
    if code:
        details["upstreamCode"] = code
    if message:
        details["upstreamMessage"] = message
    return details


def _first_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return str(value)
    data = payload.get("data")
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if value is not None:
                return str(value)
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if text in {"false", "0", "no", "n", "deny", "denied", "unauthorized"}:
        return False
    return bool(text)

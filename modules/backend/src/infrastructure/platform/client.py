"""JSON transport over the platform runtime shared HTTP session."""

from __future__ import annotations

from typing import Any

from requests import Response, Session
from requests.exceptions import RequestException, Timeout
from runtime.client._session import GLOBAL_HTTP_SESSION

from ...shared.kernel.errors import ErrorCode, UpstreamError, ValidationError


class RuntimeHttpClient:
    def __init__(self, *, session: Session | None = None) -> None:
        self.session = session or GLOBAL_HTTP_SESSION

    def get_json(
        self,
        *,
        path_or_url: str,
        user_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request("GET", path_or_url=path_or_url, user_id=user_id, params=params)

    def post_json(
        self,
        *,
        path_or_url: str,
        payload: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
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
        path = str(path_or_url or "").strip()
        if not path:
            raise ValidationError("external service url is required")
        if not path.startswith(("http://", "https://", "/")):
            raise ValidationError(f"external service relative url must start with /: {path}")
        headers = {"Content-Type": "application/json"}
        if user_id:
            headers["X-User-Id"] = user_id
        response: Response | None = None
        try:
            response = self.session.request(
                method,
                path,
                json=payload,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except Timeout as exc:
            raise UpstreamError(
                "系统处理超时，请稍后重试。",
                details={"url": path},
                error_code=ErrorCode.BASE_OVERTIME,
                category="timeout",
                retryable=True,
                http_status=504,
            ) from exc
        except UpstreamError:
            raise
        except RequestException as exc:
            details: dict[str, Any] = {"url": path}
            if response is not None:
                details["statusCode"] = response.status_code
                details.update(_http_error_details(response))
            raise UpstreamError(
                "外部服务调用失败，请稍后重试。",
                details=details,
                error_code=ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                source="platform",
                retryable=response is None or response.status_code >= 500,
                http_status=502,
            ) from exc
        except ValueError as exc:
            raise UpstreamError(
                "外部服务响应格式无效。",
                details={"url": path},
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="platform",
                http_status=502,
            ) from exc
        finally:
            if response is not None:
                response.close()
        if not isinstance(data, dict):
            raise UpstreamError(
                "外部服务响应格式无效。",
                details={"url": path},
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="platform",
                http_status=502,
            )
        return data


def _http_error_details(response: Response) -> dict[str, Any]:
    details: dict[str, Any] = {}
    try:
        payload = response.json()
    except ValueError:
        return details
    if not isinstance(payload, dict):
        return details
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = payload.get("errorCode") or payload.get("code") or error.get("code")
    message = payload.get("errorMsg") or payload.get("message") or error.get("message")
    if code:
        details["upstreamCode"] = str(code)
    if message:
        details["upstreamMessage"] = str(message)
    return details

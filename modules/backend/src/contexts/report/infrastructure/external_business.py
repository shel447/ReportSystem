"""同源外部业务服务 HTTP 适配器。"""

from __future__ import annotations

from typing import Any

from ....infrastructure.platform.client import RuntimeHttpClient
from ....shared.kernel.errors import ErrorCode, UpstreamError, ValidationError


class ExternalBusinessGateway:
    """Validate declared sources and call them through the runtime client."""

    def __init__(self, *, client: RuntimeHttpClient | None = None) -> None:
        self.client = client or RuntimeHttpClient()

    def validate_url(self, path_or_url: str) -> str:
        value = str(path_or_url or "").strip()
        if not value:
            raise ValidationError("external business source url is required")
        if value.startswith(("http://", "https://")):
            return value
        if not value.startswith("/rest/"):
            raise ValidationError(f"external business relative url must start with /rest/: {value}")
        return value

    def post_json(self, *, path_or_url: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        self.validate_url(path_or_url)
        try:
            return self.client.post_json(path_or_url=path_or_url, payload=payload, user_id=user_id)
        except UpstreamError as exc:
            raise UpstreamError(
                str(exc),
                details=dict(exc.details),
                error_code=exc.error_code or ErrorCode.BASE_UPSTREAM_UNAVAILABLE,
                category=exc.category,
                retryable=exc.retryable,
                source="external_business",
                http_status=exc.http_status,
            ) from exc

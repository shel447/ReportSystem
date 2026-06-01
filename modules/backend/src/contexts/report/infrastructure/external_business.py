"""同源外部业务服务 HTTP 适配器。"""

from __future__ import annotations

import os
from typing import Any

from ....infrastructure.platform.http_client import ExternalServiceConfig, PlatformHttpClient
from ....shared.kernel.errors import UpstreamError, ValidationError

DEFAULT_EXTERNAL_BUSINESS_BASE_URL = "http://127.0.0.1:8310"


class ExternalBusinessGateway:
    """解析同源相对地址，并以统一身份头调用外部业务服务。"""

    def __init__(self, *, base_url: str | None = None, timeout_seconds: float = 10.0, client: PlatformHttpClient | None = None) -> None:
        self.base_url = str(base_url or os.environ.get("REPORT_EXTERNAL_BUSINESS_BASE_URL") or DEFAULT_EXTERNAL_BUSINESS_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or PlatformHttpClient(config=ExternalServiceConfig(base_url=self.base_url, timeout_seconds=timeout_seconds))

    def resolve_url(self, path_or_url: str) -> str:
        value = str(path_or_url or "").strip()
        if not value:
            raise ValidationError("external business source url is required")
        if value.startswith(("http://", "https://")):
            return value
        if not value.startswith("/rest/"):
            raise ValidationError(f"external business relative url must start with /rest/: {value}")
        return self.client.resolve_url(value)

    def post_json(self, *, path_or_url: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        self.resolve_url(path_or_url)
        try:
            return self.client.post_json(path_or_url=path_or_url, payload=payload, user_id=user_id)
        except UpstreamError as exc:
            raise ValidationError(str(exc), details=dict(exc.details)) from exc

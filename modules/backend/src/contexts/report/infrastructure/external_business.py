"""同源外部业务服务 HTTP 适配器。"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import httpx

from ....shared.kernel.errors import ValidationError

DEFAULT_EXTERNAL_BUSINESS_BASE_URL = "http://127.0.0.1:8310"


class ExternalBusinessGateway:
    """解析同源相对地址，并以统一身份头调用外部业务服务。"""

    def __init__(self, *, base_url: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.base_url = str(base_url or os.environ.get("REPORT_EXTERNAL_BUSINESS_BASE_URL") or DEFAULT_EXTERNAL_BUSINESS_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def resolve_url(self, path_or_url: str) -> str:
        value = str(path_or_url or "").strip()
        if not value:
            raise ValidationError("external business source url is required")
        if value.startswith(("http://", "https://")):
            return value
        if not value.startswith("/rest/"):
            raise ValidationError(f"external business relative url must start with /rest/: {value}")
        return urljoin(f"{self.base_url}/", value.lstrip("/"))

    def post_json(self, *, path_or_url: str, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        url = self.resolve_url(path_or_url)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload, headers={"X-User-Id": user_id})
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise ValidationError(f"外部业务服务超时: {url}") from exc
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(f"外部业务服务调用失败: {url}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValidationError(f"外部业务服务响应必须为 JSON object: {url}")
        return data

"""动态参数候选值数据源适配器。"""

from __future__ import annotations

from typing import Any

import httpx

from ....infrastructure.demo.dynamic_sources import get_dynamic_option_items
from ....shared.kernel.errors import ValidationError
from .template_schema import validate_parameter_option_source_response

MAX_REQUEST_BODY_BYTES = 32 * 1024
UPSTREAM_TIMEOUT_SECONDS = 3.0


class ParameterOptionsGateway:
    """统一调用本地演示源或远端 HTTP 动态候选源。"""

    def resolve(self, *, source: str, request_payload: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        source_url = str(source or "").strip()
        if not source_url:
            raise ValidationError("source is required")
        body_size = len(httpx.Request("POST", "http://local", json=request_payload).content)
        if body_size > MAX_REQUEST_BODY_BYTES:
            raise ValidationError("request body too large")
        if source_url.startswith("api:/"):
            return validate_parameter_option_source_response(
                {"options": get_dynamic_option_items(source_url), "defaultValue": []}
            )
        try:
            with httpx.Client(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
                response = client.post(source_url, json=request_payload)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise ValidationError(f"动态参数数据源超时: {source_url}") from exc
        except Exception as exc:
            raise ValidationError(f"动态参数数据源调用失败: {exc}") from exc
        return validate_parameter_option_source_response(payload)

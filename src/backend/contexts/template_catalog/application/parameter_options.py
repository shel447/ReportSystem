from __future__ import annotations

from typing import Any

import httpx

from ....infrastructure.demo.dynamic_sources import get_dynamic_option_items
from ....shared.kernel.errors import ValidationError
from ..infrastructure.schema import validate_parameter_option_source_response

MAX_REQUEST_BODY_BYTES = 32 * 1024
UPSTREAM_TIMEOUT_SECONDS = 3.0


class ParameterOptionService:
    def resolve(
        self,
        *,
        user_id: str,
        parameter_id: str,
        open_source: dict[str, Any],
        context_values: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        source_url = str((open_source or {}).get("url") or "").strip()
        if not source_url:
            raise ValidationError("openSource.url is required")

        request_payload = dict(context_values or {})
        body_size = len(httpx.Request("POST", "http://local", json=request_payload).content)
        if body_size > MAX_REQUEST_BODY_BYTES:
            raise ValidationError("request body too large")

        if source_url.startswith("api:/"):
            response = {
                "options": get_dynamic_option_items(source_url),
                "defaultValue": [],
            }
            return validate_parameter_option_source_response(response)

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

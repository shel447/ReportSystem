"""用于从模板定义的数据源解析参数候选值的应用服务。"""

from __future__ import annotations

from typing import Any

import httpx

from ....infrastructure.demo.dynamic_sources import get_dynamic_option_items
from ....shared.kernel.errors import ValidationError
from ..infrastructure.schema import validate_parameter_option_source_response

MAX_REQUEST_BODY_BYTES = 32 * 1024
UPSTREAM_TIMEOUT_SECONDS = 3.0


class ParameterOptionService:
    """通过正式外部数据源端点解析动态参数候选值。"""

    def resolve(
        self,
        *,
        user_id: str,
        parameter_id: str,
        source: str,
        context_values: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        # 报告系统始终通过统一的提交契约调用动态源，即使是本地演示源也不例外，
        # 这样对话层只需要面对一种返回结构。
        source_url = str(source or "").strip()
        if not source_url:
            raise ValidationError("source is required")

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

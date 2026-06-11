"""动态参数候选值数据源适配器。"""

from __future__ import annotations

from typing import Any

from ....shared.kernel.errors import ValidationError
from ..application.interfaces import ParameterOptionsResolver
from .external_business import ExternalBusinessGateway
from .template_schema import validate_parameter_option_source_response


class ParameterOptionsGateway(ParameterOptionsResolver):
    """通过正式 HTTP 契约调用动态候选源。"""

    def __init__(self, *, gateway: ExternalBusinessGateway | None = None) -> None:
        self.gateway = gateway or ExternalBusinessGateway()

    def resolve(self, *, source: str, request_payload: dict[str, list[dict[str, Any]]], user_id: str) -> dict[str, Any]:
        source_url = str(source or "").strip()
        if not source_url:
            raise ValidationError("source is required")
        payload = self.gateway.post_json(path_or_url=source_url, payload=request_payload, user_id=user_id)
        return validate_parameter_option_source_response(payload)

"""在应用边界解析 custom dynamic 内容，再交给纯领域 compiler。"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from ....shared.kernel.errors import ValidationError
from ..domain.generation_models import ReportCatalog, ReportSection, report_catalog_from_dict, report_section_from_dict
from ..domain.template_models import Parameter, parameter_value_to_dict


@dataclass(slots=True)
class ResolvedCustomContent:
    catalogs: dict[str, ReportCatalog] = field(default_factory=dict)
    sections: dict[str, ReportSection] = field(default_factory=dict)


class CustomContentResolver:
    """负责 custom 外部调用和片段结构校验。"""

    def __init__(self, *, gateway=None, schema_gateway=None) -> None:
        self.gateway = gateway
        self.schema_gateway = schema_gateway

    def resolve(self, *, template_instance) -> ResolvedCustomContent:
        resolved = ResolvedCustomContent()
        for catalog in list(template_instance.catalogs or []):
            self._resolve_catalog(catalog, inherited_parameters={}, resolved=resolved)
        return resolved

    def _resolve_catalog(self, catalog, *, inherited_parameters: dict[str, list[dict[str, Any]]], resolved: ResolvedCustomContent) -> None:
        visible_parameters = _merge_parameter_payloads(inherited_parameters, list(catalog.parameters or []))
        if _is_custom_context(catalog.dynamic_context, "catalog"):
            prompt = str(catalog.rendered_title or catalog.title or catalog.id or "")
            payload = self._fetch(
                url=str(catalog.dynamic_context.url or ""),
                node_type="catalog",
                node_id=str(catalog.id or ""),
                parameters=visible_parameters,
                prompt=prompt,
            )
            resolved.catalogs[str(catalog.id or "")] = report_catalog_from_dict(self.schema_gateway.validate_catalog(payload))
            return
        for section in list(catalog.sections or []):
            if not _is_custom_context(section.dynamic_context, "section"):
                continue
            prompt = str(section.outline.rendered_requirement or section.outline.requirement or "")
            payload = self._fetch(
                url=str(section.dynamic_context.url or ""),
                node_type="section",
                node_id=str(section.id or ""),
                parameters=_merge_parameter_payloads(visible_parameters, list(section.parameters or [])),
                prompt=prompt,
            )
            resolved.sections[str(section.id or "")] = report_section_from_dict(self.schema_gateway.validate_section(payload))
        for sub_catalog in list(catalog.sub_catalogs or []):
            self._resolve_catalog(sub_catalog, inherited_parameters=visible_parameters, resolved=resolved)

    def _fetch(
        self,
        *,
        url: str,
        node_type: str,
        node_id: str,
        parameters: dict[str, list[dict[str, Any]]],
        prompt: str,
    ) -> dict[str, Any]:
        if self.gateway is None:
            raise ValidationError("custom dynamic content gateway is not configured")
        if not url:
            raise ValidationError(f"custom dynamic {node_type} {node_id} missing url")
        try:
            response = self.gateway.post_json(
                url=url,
                payload={"nodeType": node_type, "nodeId": node_id, "parameters": parameters, "prompt": prompt},
            )
        except Exception as exc:
            raise ValidationError(f"custom dynamic {node_type} {node_id} request failed: {exc}") from exc
        if not isinstance(response, dict):
            raise ValidationError(f"custom dynamic {node_type} {node_id} response must be a JSON object")
        return response


def _is_custom_context(dynamic_context, expected_node_type: str) -> bool:
    if dynamic_context is None or dynamic_context.type != "custom":
        return False
    return str(dynamic_context.node_type or expected_node_type) == expected_node_type


def _merge_parameter_payloads(
    inherited: dict[str, list[dict[str, Any]]],
    parameters: list[Parameter],
) -> dict[str, list[dict[str, Any]]]:
    merged = copy.deepcopy(inherited)
    for parameter in parameters:
        merged[str(parameter.id or "")] = [parameter_value_to_dict(value) for value in list(parameter.values or [])]
    return merged

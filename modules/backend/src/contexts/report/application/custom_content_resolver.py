"""在应用边界解析 Dynamic Custom v6 内容，再交给纯领域 compiler。"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from ....shared.kernel.errors import ValidationError
from ..domain.generation_models import (
    ReportCatalog,
    ReportComponent,
    ReportSection,
    ReportSlide,
    report_catalog_from_dict,
    report_component_from_dict,
    report_section_from_dict,
    report_slide_from_dict,
)
from ..domain.template_models import Parameter, outline_definition_to_dict, parameter_value_to_dict, slide_layout_to_dict


@dataclass(slots=True)
class ResolvedCustomContent:
    catalogs: dict[str, ReportCatalog] = field(default_factory=dict)
    sections: dict[str, ReportSection] = field(default_factory=dict)
    slides: dict[str, ReportSlide] = field(default_factory=dict)
    components: dict[str, list[ReportComponent]] = field(default_factory=dict)


class CustomContentResolver:
    """负责 custom 外部调用、v6 包络解析和 DSL 片段校验。"""

    def __init__(self, *, gateway=None, schema_gateway=None) -> None:
        self.gateway = gateway
        self.schema_gateway = schema_gateway

    def resolve(self, *, template_instance, user_id: str = "default") -> ResolvedCustomContent:
        resolved = ResolvedCustomContent()
        root = _merge_parameter_payloads({}, list(template_instance.parameters or []))
        if (template_instance.structure_type or "flow") == "paged":
            for chapter in list(template_instance.chapters or []):
                chapter_parameters = _merge_parameter_payloads(root, list(chapter.parameters or []))
                for slide in list(chapter.slides or []):
                    self._resolve_slide(
                        slide,
                        inherited_parameters=chapter_parameters,
                        resolved=resolved,
                        user_id=user_id,
                    )
        else:
            for catalog in list(template_instance.catalogs or []):
                self._resolve_catalog(catalog, inherited_parameters=root, resolved=resolved, user_id=user_id)
        return resolved

    def _resolve_catalog(self, catalog, *, inherited_parameters, resolved: ResolvedCustomContent, user_id: str) -> None:
        visible = _merge_parameter_payloads(inherited_parameters, list(catalog.parameters or []))
        if _is_custom_context(catalog.dynamic_context, "catalog"):
            payload = self._fetch(
                url=str(catalog.dynamic_context.url or ""),
                expected_type="Catalog",
                template_node={
                    "id": str(catalog.id or ""),
                    "title": str(catalog.title or ""),
                    "dynamic": {"type": "custom", "url": str(catalog.dynamic_context.url or "")},
                },
                parameters=visible,
                question=str(catalog.rendered_title or catalog.title or catalog.id or ""),
                structure_type="flow",
                user_id=user_id,
            )
            resolved.catalogs[str(catalog.id or "")] = report_catalog_from_dict(self.schema_gateway.validate_catalog(payload))
            return
        for section in list(catalog.sections or []):
            self._resolve_section(section, inherited_parameters=visible, resolved=resolved, structure_type="flow", user_id=user_id)
        for sub_catalog in list(catalog.sub_catalogs or []):
            self._resolve_catalog(sub_catalog, inherited_parameters=visible, resolved=resolved, user_id=user_id)

    def _resolve_slide(self, slide, *, inherited_parameters, resolved: ResolvedCustomContent, user_id: str) -> None:
        visible = _merge_parameter_payloads(inherited_parameters, list(slide.parameters or []))
        if _is_custom_context(slide.dynamic_context, "slide"):
            node = {
                "id": str(slide.id or ""),
                "dynamic": {"type": "custom", "url": str(slide.dynamic_context.url or "")},
            }
            if slide.title is not None:
                node["title"] = slide.title
            if slide.layout is not None:
                node["layout"] = slide_layout_to_dict(slide.layout)
            payload = self._fetch(
                url=str(slide.dynamic_context.url or ""),
                expected_type="Slide",
                template_node=node,
                parameters=visible,
                question=str(slide.title or slide.id or ""),
                structure_type="paged",
                user_id=user_id,
            )
            resolved.slides[str(slide.id or "")] = report_slide_from_dict(self.schema_gateway.validate_slide(payload))
            return
        for section in list(slide.sections or []):
            self._resolve_section(section, inherited_parameters=visible, resolved=resolved, structure_type="paged", user_id=user_id)

    def _resolve_section(self, section, *, inherited_parameters, resolved: ResolvedCustomContent, structure_type: str, user_id: str) -> None:
        if not _is_custom_context(section.dynamic_context, "section"):
            return
        visible = _merge_parameter_payloads(inherited_parameters, list(section.parameters or []))
        expected = "Components" if structure_type == "paged" else "Section"
        payload = self._fetch(
            url=str(section.dynamic_context.url or ""),
            expected_type=expected,
            allowed_types={expected, "Section"} if structure_type == "paged" else {expected},
            template_node={
                "id": str(section.id or ""),
                "dynamic": {"type": "custom", "url": str(section.dynamic_context.url or "")},
                "outline": outline_definition_to_dict(section.outline),
            },
            parameters=visible,
            question=str(section.outline.rendered_requirement or section.outline.requirement or ""),
            structure_type=structure_type,
            user_id=user_id,
        )
        if structure_type == "paged":
            if isinstance(payload, list):
                resolved.components[str(section.id or "")] = [
                    report_component_from_dict(item) for item in self.schema_gateway.validate_components(payload)
                ]
            else:
                resolved.components[str(section.id or "")] = report_section_from_dict(
                    self.schema_gateway.validate_section(payload)
                ).components
        else:
            resolved.sections[str(section.id or "")] = report_section_from_dict(self.schema_gateway.validate_section(payload))

    def _fetch(
        self,
        *,
        url: str,
        expected_type: str,
        template_node: dict[str, Any],
        parameters: dict[str, list[dict[str, Any]]],
        question: str,
        structure_type: str,
        user_id: str,
        allowed_types: set[str] | None = None,
    ) -> Any:
        if self.gateway is None:
            raise ValidationError("custom dynamic content gateway is not configured")
        if not url:
            raise ValidationError(f"custom dynamic {expected_type} missing url")
        response = self.gateway.post_json(
            url=url,
            payload={
                "parameters": parameters,
                "templateNode": template_node,
                "context": {
                    "structureType": structure_type,
                    "question": question,
                    "locale": "zh-CN",
                    "timezone": "Asia/Shanghai",
                },
            },
            user_id=user_id,
        )
        envelope = self.schema_gateway.validate_dynamic_custom_response(response)
        if envelope.get("status") != "success":
            error = envelope.get("error") or {}
            raise ValidationError(f"custom dynamic request failed: {error.get('code')}: {error.get('message')}")
        actual_type = str((envelope.get("meta") or {}).get("dslType") or "")
        if actual_type not in (allowed_types or {expected_type}):
            raise ValidationError(f"custom dynamic response dslType mismatch: expected {expected_type}, got {actual_type}")
        return copy.deepcopy(envelope.get("dsl"))


def _is_custom_context(dynamic_context, expected_node_type: str) -> bool:
    if dynamic_context is None or dynamic_context.type != "custom":
        return False
    return str(dynamic_context.node_type or expected_node_type) == expected_node_type


def _merge_parameter_payloads(inherited: dict[str, list[dict[str, Any]]], parameters: list[Parameter]) -> dict[str, list[dict[str, Any]]]:
    merged = copy.deepcopy(inherited)
    for parameter in parameters:
        merged[str(parameter.id or "")] = [parameter_value_to_dict(value) for value in list(parameter.values or [])]
    return merged

from __future__ import annotations

import json
import re
from typing import Any, List

from ....shared.kernel.errors import NotFoundError, ValidationError
from ..domain.models import ReportTemplate


class TemplateCatalogService:
    def __init__(self, *, repository, matcher, schema_gateway) -> None:
        self.repository = repository
        self.matcher = matcher
        self.schema_gateway = schema_gateway

    def create_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._clean_payload(payload)
        template = self.repository.create(cleaned)
        self.matcher.mark_stale(template.template_id, "模板新建后尚未建立语义索引。")
        return self.serialize_detail(template)

    def list_templates(self) -> list[dict[str, Any]]:
        return [self.serialize_summary(item) for item in self.repository.list_all()]

    def get_template(self, template_id: str) -> dict[str, Any]:
        template = self.repository.get(template_id)
        if not template:
            raise NotFoundError("Template not found")
        return self.serialize_detail(template)

    def update_template(self, template_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.repository.get(template_id):
            raise NotFoundError("Template not found")
        cleaned = self._clean_payload(payload)
        template = self.repository.update(template_id, cleaned)
        self.matcher.mark_stale(template.template_id, "模板已更新，请重建语义索引。")
        return self.serialize_detail(template)

    def delete_template(self, template_id: str) -> None:
        if not self.repository.get(template_id):
            raise NotFoundError("Template not found")
        self.repository.delete(template_id)
        self.matcher.delete_index(template_id)

    def export_template(self, template_id: str) -> tuple[dict[str, Any], str]:
        template = self.repository.get(template_id)
        if not template:
            raise NotFoundError("Template not found")
        return self._export_payload(template), self._build_export_filename(template)

    def match_templates(self, message: str, gateway) -> dict[str, Any]:
        return self.matcher.match(message, gateway)

    def serialize_summary(self, template: ReportTemplate) -> dict[str, Any]:
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scenario,
            "type": template.template_type or "",
            "scene": template.scene or "",
            "schema_version": template.schema_version or "",
            "parameter_count": len(template.parameters or []),
            "top_level_section_count": len(template.sections or []),
            "created_at": str(template.created_at),
        }

    def serialize_detail(self, template: ReportTemplate) -> dict[str, Any]:
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scenario,
            "type": template.template_type or "",
            "scene": template.scene or "",
            "match_keywords": self._normalize_keywords(template.match_keywords),
            "content_params": template.content_params,
            "parameters": template.parameters,
            "outline": template.outline,
            "sections": template.sections,
            "schema_version": template.schema_version or "",
            "output_formats": template.output_formats,
            "created_at": str(template.created_at),
            "version": template.version,
        }

    def _export_payload(self, template: ReportTemplate) -> dict[str, Any]:
        return {
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scenario,
            "type": template.template_type or "",
            "scene": template.scene or "",
            "match_keywords": self._normalize_keywords(template.match_keywords),
            "parameters": template.parameters or [],
            "sections": template.sections or [],
            "schema_version": template.schema_version or "",
            "output_formats": template.output_formats or [],
        }

    def _clean_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            cleaned = self.schema_gateway.validate(payload)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if "type" in cleaned:
            cleaned["template_type"] = cleaned.pop("type") or ""
        if "scene" in cleaned:
            cleaned["scene"] = cleaned.get("scene") or ""
        if "match_keywords" in cleaned:
            cleaned["match_keywords"] = self._normalize_keywords(cleaned.get("match_keywords"))
        return cleaned

    @staticmethod
    def _normalize_keywords(items: List[Any] | None) -> list[str]:
        if not isinstance(items, list):
            return []
        seen: set[str] = set()
        normalized: list[str] = []
        for item in items:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _build_export_filename(template: ReportTemplate) -> str:
        base = re.sub(r"[^0-9A-Za-z._-]+", "-", str(template.name or "").strip()).strip("-")
        if not base:
            base = f"template-{template.template_id}"
        return f"{base}.json"

from __future__ import annotations

import json
import re
from datetime import datetime
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

    def preview_import_template(self, payload: dict[str, Any], filename: str | None = None) -> dict[str, Any]:
        source_kind, candidate_payload, candidate_id, warnings = self._normalize_import_payload(payload, filename)
        cleaned = self._clean_payload(candidate_payload)
        return {
            "normalized_template": self._serialize_import_draft(cleaned),
            "source_kind": source_kind,
            "warnings": warnings,
            "conflict": self._detect_import_conflict(candidate_id, str(cleaned.get("name") or "").strip()),
        }

    def match_templates(self, message: str, gateway) -> dict[str, Any]:
        return self.matcher.match(message, gateway)

    def serialize_summary(self, template: ReportTemplate) -> dict[str, Any]:
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scenario,
            "category": template.template_type or "",
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
            "category": template.template_type or "",
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
            "category": template.template_type or "",
            "match_keywords": self._normalize_keywords(template.match_keywords),
            "parameters": template.parameters or [],
            "sections": template.sections or [],
            "schema_version": template.schema_version or "",
            "output_formats": template.output_formats or [],
        }

    def _serialize_import_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": str(payload.get("name") or ""),
            "description": str(payload.get("description") or ""),
            "report_type": str(payload.get("report_type") or "daily"),
            "scenario": str(payload.get("scenario") or ""),
            "category": str(payload.get("template_type") or payload.get("category") or ""),
            "match_keywords": self._normalize_keywords(payload.get("match_keywords")),
            "content_params": list(payload.get("content_params") or []),
            "parameters": list(payload.get("parameters") or []),
            "outline": list(payload.get("outline") or []),
            "sections": list(payload.get("sections") or []),
            "schema_version": str(payload.get("schema_version") or "v2.0"),
            "output_formats": list(payload.get("output_formats") or ["md"]),
        }

    def _clean_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            cleaned = self.schema_gateway.validate(payload)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if "category" in cleaned:
            cleaned["template_type"] = cleaned.pop("category") or ""
        if "type" in cleaned:
            cleaned["template_type"] = cleaned.pop("type") or ""
        cleaned.pop("scene", None)
        if "match_keywords" in cleaned:
            cleaned["match_keywords"] = self._normalize_keywords(cleaned.get("match_keywords"))
        return cleaned

    def _normalize_import_payload(
        self,
        payload: dict[str, Any],
        filename: str | None = None,
    ) -> tuple[str, dict[str, Any], str | None, list[str]]:
        candidate = dict(payload or {})
        if not candidate:
            raise ValidationError("不支持的模板结构。")

        if self._looks_like_system_export(candidate):
            candidate_id = str(candidate.get("template_id") or "").strip() or None
            return "system_export", candidate, candidate_id, []

        if self._looks_like_external_report_template(candidate):
            candidate_id = str(candidate.get("id") or "").strip() or None
            normalized = {
                "name": str(candidate.get("name") or ""),
                "description": str(candidate.get("description") or ""),
                "report_type": str(candidate.get("report_type") or "daily"),
                "scenario": str(candidate.get("scenario") or ""),
                "category": str(candidate.get("category") or candidate.get("type") or ""),
                "match_keywords": list(candidate.get("match_keywords") or []),
                "content_params": list(candidate.get("content_params") or []),
                "parameters": list(candidate.get("parameters") or []),
                "outline": list(candidate.get("outline") or []),
                "sections": list(candidate.get("sections") or []),
                "schema_version": str(candidate.get("schema_version") or "v2.0"),
                "output_formats": list(candidate.get("output_formats") or ["md"]),
            }
            warnings: list[str] = []
            if filename:
                warnings.append(f"已按外部 ReportTemplate 模板定义解析：{filename}")
            return "external_report_template", normalized, candidate_id, warnings

        raise ValidationError("不支持的模板结构。")

    @staticmethod
    def _looks_like_system_export(payload: dict[str, Any]) -> bool:
        return any(
            key in payload
            for key in (
                "template_id",
                "report_type",
                "scenario",
                "match_keywords",
                "output_formats",
                "schema_version",
                "content_params",
                "outline",
            )
        )

    @staticmethod
    def _looks_like_external_report_template(payload: dict[str, Any]) -> bool:
        required_fields = {"id", "name", "parameters", "sections"}
        return required_fields.issubset(payload.keys())

    def _detect_import_conflict(self, candidate_id: str | None, candidate_name: str) -> dict[str, Any]:
        templates = list(self.repository.list_all())
        matches: list[ReportTemplate] = []
        if candidate_id:
            matches = [item for item in templates if item.template_id == candidate_id]
        if not matches and candidate_name:
            matches = [item for item in templates if (item.name or "") == candidate_name]

        status = "none"
        overwrite_supported = False
        if len(matches) == 1:
            status = "single_match"
            overwrite_supported = True
        elif len(matches) > 1:
            status = "multiple_matches"

        return {
            "status": status,
            "matched_templates": [
                {
                    "template_id": item.template_id,
                    "name": item.name,
                }
                for item in matches
            ],
            "overwrite_supported": overwrite_supported,
            "default_action": "create_copy",
        }

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
        raw_name = str(template.name or "").strip()
        base = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]+', "-", raw_name)
        base = re.sub(r"\s+", "-", base).strip("-.")
        if not base:
            base = f"template-{template.template_id}"
        exported_at = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{base}-{exported_at}.json"

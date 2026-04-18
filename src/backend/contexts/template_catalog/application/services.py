from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from ....shared.kernel.errors import ConflictError, NotFoundError, ValidationError
from ..domain.models import ReportTemplate


class TemplateCatalogService:
    def __init__(self, *, repository, schema_gateway) -> None:
        self.repository = repository
        self.schema_gateway = schema_gateway

    def create_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._validate_template_payload(payload)
        try:
            template = self.repository.create(cleaned)
        except ConflictError:
            raise
        return self.serialize_detail(template)

    def update_template(self, template_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if template_id != str(payload.get("id") or "").strip():
            raise ValidationError("Template id mismatch")
        cleaned = self._validate_template_payload(payload)
        template = self.repository.update(template_id, cleaned)
        return self.serialize_detail(template)

    def delete_template(self, template_id: str) -> None:
        self.repository.delete(template_id)

    def get_template(self, template_id: str) -> dict[str, Any]:
        template = self.repository.get(template_id)
        if template is None:
            raise NotFoundError("Template not found")
        return self.serialize_detail(template)

    def list_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "category": item.category,
                "name": item.name,
                "description": item.description,
                "schemaVersion": item.schema_version,
                "updatedAt": item.updated_at.isoformat().replace("+00:00", "Z") if item.updated_at else None,
            }
            for item in self.repository.list_summaries()
        ]

    def export_template(self, template_id: str) -> tuple[dict[str, Any], str]:
        template = self.repository.get(template_id)
        if template is None:
            raise NotFoundError("Template not found")
        payload = self.serialize_detail(template)
        return payload, self._build_export_filename(template)

    def preview_import_template(self, raw_content: Any) -> dict[str, Any]:
        normalized = self._parse_import_content(raw_content)
        cleaned = self._validate_template_payload(normalized)
        return {
            "normalizedTemplate": cleaned,
            "warnings": [],
        }

    def serialize_detail(self, template: ReportTemplate) -> dict[str, Any]:
        return {
            "id": template.id,
            "category": template.category,
            "name": template.name,
            "description": template.description,
            "schemaVersion": template.schema_version,
            "tags": list(template.tags or []),
            "parameters": list(template.parameters or []),
            "catalogs": list(template.catalogs or []),
            "createdAt": template.created_at.isoformat().replace("+00:00", "Z") if template.created_at else None,
            "updatedAt": template.updated_at.isoformat().replace("+00:00", "Z") if template.updated_at else None,
        }

    def _validate_template_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.schema_gateway.validate(dict(payload or {}))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @staticmethod
    def _parse_import_content(raw_content: Any) -> dict[str, Any]:
        if isinstance(raw_content, dict):
            return raw_content
        if isinstance(raw_content, str):
            try:
                loaded = json.loads(raw_content)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"模板导入内容不是合法 JSON: {exc.msg}") from exc
            if not isinstance(loaded, dict):
                raise ValidationError("模板导入内容必须是 JSON 对象")
            return loaded
        raise ValidationError("模板导入内容必须是对象或 JSON 文本")

    @staticmethod
    def _build_export_filename(template: ReportTemplate) -> str:
        raw_name = str(template.name or "").strip()
        base = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]+', "-", raw_name)
        base = re.sub(r"\s+", "-", base).strip("-.")
        if not base:
            base = template.id
        exported_at = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{base}-{exported_at}.json"

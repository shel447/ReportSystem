from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from ..domain.models import ReportInstance
from ..domain.services import OutlineExpansionService, is_v2_template
from ...template_catalog.domain.models import ReportTemplate


class ReportInstanceCreationService:
    def __init__(
        self,
        *,
        template_reader,
        instance_writer,
        content_generator,
        outline_expansion_service: OutlineExpansionService | None = None,
    ) -> None:
        self.template_reader = template_reader
        self.instance_writer = instance_writer
        self.content_generator = content_generator
        self.outline_expansion_service = outline_expansion_service or OutlineExpansionService()

    def create_instance(
        self,
        *,
        template_id: str,
        input_params: dict[str, Any],
        outline_override: list[Any] | None = None,
        report_time: datetime | None = None,
        report_time_source: str = "",
    ) -> dict[str, Any]:
        template = self.template_reader.get_by_id(template_id)
        if not template:
            raise ValueError("Template not found")

        warnings: list[str] = []
        if is_v2_template(template):
            if outline_override:
                outline_content, warnings = self.content_generator.generate_v2_from_outline(
                    template,
                    outline_override,
                    input_params or {},
                )
            else:
                outline_content, warnings = self.content_generator.generate_v2(template, input_params or {})
        else:
            if outline_override and any(isinstance(item, dict) and "children" in item for item in outline_override):
                outline_content = self.content_generator.generate(
                    template,
                    _flatten_review_outline(outline_override),
                    input_params or {},
                )
                warnings = []
            else:
                active_outline = outline_override if outline_override else template.outline
                expansion = self.outline_expansion_service.expand(active_outline or [], input_params or {})
                outline_content = self.content_generator.generate(template, expansion.nodes, input_params or {})
                warnings = expansion.warnings

        created = self.instance_writer.create(
            template_id=template.template_id,
            template_version=template.version,
            input_params=input_params or {},
            outline_content=outline_content,
            status="draft",
            report_time=report_time,
            report_time_source=report_time_source,
        )
        payload = asdict(created)
        if payload.get("report_time") is not None:
            payload["report_time"] = str(payload["report_time"])
        if payload.get("created_at") is not None:
            payload["created_at"] = str(payload["created_at"])
        if payload.get("updated_at") is not None:
            payload["updated_at"] = str(payload["updated_at"])
        payload["warnings"] = warnings
        return payload


class ScheduledReportRunService:
    def __init__(
        self,
        *,
        instance_service: ReportInstanceCreationService,
        instance_reader,
    ) -> None:
        self.instance_service = instance_service
        self.instance_reader = instance_reader

    def create_instance_from_schedule(
        self,
        *,
        template_id: str,
        source_instance_id: str,
        override_params: dict[str, Any],
        report_time: datetime | None = None,
        report_time_source: str = "",
    ) -> dict[str, Any]:
        base_params: dict[str, Any] = {}
        if source_instance_id:
            source = self.instance_reader.get_input_params(source_instance_id)
            if source:
                base_params = dict(source)

        merged = dict(base_params)
        merged.update(override_params or {})

        return self.instance_service.create_instance(
            template_id=template_id,
            input_params=merged,
            outline_override=None,
            report_time=report_time,
            report_time_source=report_time_source,
        )


def _flatten_review_outline(outline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for node in outline or []:
        if not isinstance(node, dict):
            continue
        payload = {
            "title": str(node.get("title") or "").strip(),
            "description": str(node.get("description") or "").strip(),
            "level": max(1, int(node.get("level") or 1)),
        }
        if isinstance(node.get("dynamic_meta"), dict):
            payload["dynamic_meta"] = dict(node.get("dynamic_meta"))
        flattened.append(payload)
        flattened.extend(_flatten_review_outline(node.get("children") or []))
    return flattened

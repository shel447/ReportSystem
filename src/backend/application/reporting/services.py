from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .ports import ContentGenerator, InstanceReader, InstanceWriter, TemplateReader
from ...domain.reporting.entities import ReportInstanceEntity, ReportTemplateEntity
from ...domain.reporting.services import OutlineExpansionService


def is_v2_template(template: ReportTemplateEntity) -> bool:
    schema_version = getattr(template, "schema_version", None)
    sections = getattr(template, "sections", None)
    return bool(schema_version == "v2" or sections)


class InstanceApplicationService:
    def __init__(
        self,
        *,
        template_reader: TemplateReader,
        instance_writer: InstanceWriter,
        content_generator: ContentGenerator,
        outline_expansion_service: Optional[OutlineExpansionService] = None,
    ) -> None:
        self.template_reader = template_reader
        self.instance_writer = instance_writer
        self.content_generator = content_generator
        self.outline_expansion_service = outline_expansion_service or OutlineExpansionService()

    def create_instance(
        self,
        *,
        template_id: str,
        input_params: Dict[str, Any],
        outline_override: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        template = self.template_reader.get_by_id(template_id)
        if not template:
            raise ValueError("Template not found")

        warnings: List[str] = []
        if is_v2_template(template):
            outline_content, warnings = self.content_generator.generate_v2(template, input_params or {})
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
        )
        payload = asdict(created)
        if payload.get("created_at") is not None:
            payload["created_at"] = str(payload["created_at"])
        if payload.get("updated_at") is not None:
            payload["updated_at"] = str(payload["updated_at"])
        payload["warnings"] = warnings
        return payload


class ScheduledRunApplicationService:
    def __init__(
        self,
        *,
        instance_service: InstanceApplicationService,
        instance_reader: InstanceReader,
    ) -> None:
        self.instance_service = instance_service
        self.instance_reader = instance_reader

    def create_instance_from_schedule(
        self,
        *,
        template_id: str,
        source_instance_id: str,
        override_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        base_params: Dict[str, Any] = {}
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
        )

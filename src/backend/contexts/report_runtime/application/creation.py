from __future__ import annotations

from dataclasses import asdict
import inspect
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
        user_id: str = "default",
        source_session_id: str | None = None,
        source_message_id: str | None = None,
    ) -> dict[str, Any]:
        template = self.template_reader.get_by_id(template_id)
        if not template:
            raise ValueError("Template not found")

        warnings: list[str] = []
        if outline_override:
            outline_content, warnings = self.content_generator.generate_v2_from_outline(
                template,
                outline_override,
                input_params or {},
            )
        else:
            outline_content, warnings = self.content_generator.generate_v2(template, input_params or {})

        create_kwargs = {
            "template_id": template.template_id,
            "template_version": template.version,
            "input_params": input_params or {},
            "outline_content": outline_content,
            "status": "draft",
            "report_time": report_time,
            "report_time_source": report_time_source,
            "user_id": user_id,
            "source_session_id": source_session_id,
            "source_message_id": source_message_id,
        }
        created = self._create_instance_row(create_kwargs)
        payload = asdict(created)
        if payload.get("report_time") is not None:
            payload["report_time"] = str(payload["report_time"])
        if payload.get("created_at") is not None:
            payload["created_at"] = str(payload["created_at"])
        if payload.get("updated_at") is not None:
            payload["updated_at"] = str(payload["updated_at"])
        payload["warnings"] = warnings
        return payload

    def _create_instance_row(self, create_kwargs: dict[str, Any]):
        signature = inspect.signature(self.instance_writer.create)
        allowed = {key: value for key, value in create_kwargs.items() if key in signature.parameters}
        return self.instance_writer.create(**allowed)


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
        user_id: str = "default",
        source_session_id: str | None = None,
        source_message_id: str | None = None,
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
            user_id=user_id,
            source_session_id=source_session_id,
            source_message_id=source_message_id,
        )

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List

from ...template_catalog.domain.models import ReportTemplate


@dataclass(slots=True)
class ReportInstance:
    instance_id: str
    template_id: str
    status: str
    user_id: str = "default"
    source_session_id: str | None = None
    source_message_id: str | None = None
    input_params: dict[str, Any] = field(default_factory=dict)
    outline_content: list[Any] = field(default_factory=list)
    report_time: datetime | None = None
    report_time_source: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class TemplateInstance:
    template_instance_id: str
    template_id: str
    template_name: str
    session_id: str
    capture_stage: str
    base_template: ReportTemplate | None = None
    schema_version: str = "ti.v1.0"
    status: str = "draft"
    revision: int = 1
    input_params_snapshot: dict[str, Any] = field(default_factory=dict)
    outline_snapshot: list[dict[str, Any]] = field(default_factory=list)
    resolved_view: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    generated_content: dict[str, Any] = field(default_factory=dict)
    fragments: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    report_instance_id: str | None = None
    created_at: datetime | None = None


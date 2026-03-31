from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List


@dataclass(slots=True)
class ReportInstance:
    instance_id: str
    template_id: str
    status: str
    input_params: dict[str, Any] = field(default_factory=dict)
    outline_content: list[Any] = field(default_factory=list)
    report_time: datetime | None = None
    report_time_source: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class GenerationBaseline:
    template_instance_id: str
    template_id: str
    template_name: str
    session_id: str
    capture_stage: str
    input_params_snapshot: dict[str, Any] = field(default_factory=dict)
    outline_snapshot: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_instance_id: str | None = None
    created_at: datetime | None = None

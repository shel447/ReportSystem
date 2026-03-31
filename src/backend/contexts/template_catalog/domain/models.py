from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List


@dataclass(slots=True)
class ReportTemplate:
    template_id: str
    name: str
    description: str = ""
    report_type: str = "daily"
    scenario: str = ""
    template_type: str = ""
    scene: str = ""
    match_keywords: List[str] = field(default_factory=list)
    content_params: List[Any] = field(default_factory=list)
    parameters: List[Any] = field(default_factory=list)
    outline: List[Any] = field(default_factory=list)
    sections: List[Any] = field(default_factory=list)
    schema_version: str = ""
    output_formats: List[str] = field(default_factory=lambda: ["pdf"])
    version: str = "1.0"
    created_at: datetime | None = None


@dataclass(slots=True)
class TemplateMatchResult:
    auto_match: bool
    best: dict[str, Any]
    candidates: list[dict[str, Any]]

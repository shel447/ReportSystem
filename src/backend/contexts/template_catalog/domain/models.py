from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ReportTemplate:
    id: str
    category: str
    name: str
    description: str
    schema_version: str
    parameters: list[dict[str, Any]] = field(default_factory=list)
    catalogs: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class TemplateSummary:
    id: str
    category: str
    name: str
    description: str
    schema_version: str
    updated_at: datetime | None = None


@dataclass(slots=True)
class TemplateMatchCandidate:
    template_id: str
    template_name: str
    category: str
    description: str
    score: float
    reasons: list[str] = field(default_factory=list)

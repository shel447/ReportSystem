from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List


@dataclass(slots=True)
class ReportTemplate:
    id: str
    category: str
    name: str
    description: str = ""
    parameters: List[Any] = field(default_factory=list)
    sections: List[Any] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime | None = None

    @property
    def template_id(self) -> str:
        return self.id


@dataclass(slots=True)
class TemplateMatchResult:
    auto_match: bool
    best: dict[str, Any]
    candidates: list[dict[str, Any]]

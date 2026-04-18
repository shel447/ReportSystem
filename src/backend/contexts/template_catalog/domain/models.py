"""静态报告模板目录及其匹配候选的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ReportTemplate:
    """模板目录与运行时共用的正式静态模板聚合。"""

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
    """用于列表页和轻量选择器的紧凑投影。"""

    id: str
    category: str
    name: str
    description: str
    schema_version: str
    updated_at: datetime | None = None


@dataclass(slots=True)
class TemplateMatchCandidate:
    """当模板排序外置时使用的语义匹配候选投影。"""

    template_id: str
    template_name: str
    category: str
    description: str
    score: float
    reasons: list[str] = field(default_factory=list)

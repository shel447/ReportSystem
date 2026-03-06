from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RepeatRule:
    enabled: bool = False
    source_param: str = ""
    item_alias: str = "item"
    index_alias: str = "index"


@dataclass(frozen=True)
class BindingRule:
    title: Optional[str] = None
    description: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class OutlineNode:
    title: str = ""
    description: str = ""
    level: int = 1
    title_template: Optional[str] = None
    description_template: Optional[str] = None
    bindings: BindingRule = field(default_factory=BindingRule)
    repeat: RepeatRule = field(default_factory=RepeatRule)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportTemplateEntity:
    template_id: str
    name: str
    description: str
    report_type: str
    scenario: str
    match_keywords: List[str]
    content_params: List[Dict[str, Any]]
    version: str
    outline: List[Dict[str, Any]]


@dataclass(frozen=True)
class ExpandedOutline:
    nodes: List[Dict[str, Any]]
    warnings: List[str]


@dataclass(frozen=True)
class ReportInstanceEntity:
    instance_id: str
    template_id: str
    template_version: str
    status: str
    input_params: Dict[str, Any]
    outline_content: List[Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

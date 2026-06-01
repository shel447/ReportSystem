"""Transport-neutral audit event shared by application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class AuditEvent:
    operation: str
    detail: str
    user_id: str
    target_obj: str = ""
    source: str = "ReportSystem"
    terminal: str = "server"
    result: str = "SUCCESSFUL"
    level: str = "INFORMATION"
    kind: Literal["operation", "security"] = "operation"

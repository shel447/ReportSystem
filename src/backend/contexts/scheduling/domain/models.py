from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ScheduledTask:
    task_id: str
    user_id: str
    name: str
    description: str = ""
    source_instance_id: str = ""
    template_id: str = ""
    schedule_type: str = "recurring"
    cron_expression: str = ""
    enabled: bool = True
    auto_generate_doc: bool = True
    time_param_name: str = "date"
    time_format: str = "%Y-%m-%d"
    use_schedule_time_as_report_time: bool = False
    status: str = "active"
    total_runs: int = 0
    success_runs: int = 0
    failed_runs: int = 0
    last_run_at: datetime | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class TaskExecution:
    execution_id: str
    task_id: str
    status: str
    generated_instance_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

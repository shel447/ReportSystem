from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..domain.models import ScheduledTask
from ....models import ScheduledTask as ScheduledTaskModel, ScheduledTaskExecution, gen_id


class SqlAlchemyScheduledTaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict) -> ScheduledTask:
        row = ScheduledTaskModel(task_id=gen_id(), **payload)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_task(row)

    def get(self, task_id: str) -> ScheduledTask | None:
        row = self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.task_id == task_id).first()
        return _to_task(row) if row else None

    def list_for_user(self, user_id: str) -> list[ScheduledTask]:
        return [_to_task(row) for row in self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.user_id == user_id).all()]

    def count_active_for_user(self, user_id: str) -> int:
        return self.db.query(ScheduledTaskModel).filter(
            ScheduledTaskModel.user_id == user_id,
            ScheduledTaskModel.status.in_(["active", "paused"]),
        ).count()

    def count_active_global(self) -> int:
        return self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.status.in_(["active", "paused"])).count()

    def update(self, task_id: str, updates: dict) -> ScheduledTask | None:
        row = self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.task_id == task_id).first()
        if not row:
            return None
        for key, value in updates.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return _to_task(row)

    def delete(self, task_id: str) -> bool:
        row = self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.task_id == task_id).first()
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def record_success(self, task_id: str, run_at: datetime, *, complete_once: bool) -> None:
        row = self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.task_id == task_id).first()
        if not row:
            return
        row.total_runs += 1
        row.success_runs += 1
        row.last_run_at = run_at
        if complete_once:
            row.status = "completed"
        self.db.commit()

    def record_failure(self, task_id: str, run_at: datetime) -> None:
        row = self.db.query(ScheduledTaskModel).filter(ScheduledTaskModel.task_id == task_id).first()
        if not row:
            return
        row.total_runs += 1
        row.failed_runs += 1
        row.last_run_at = run_at
        self.db.commit()


class SqlAlchemyTaskExecutionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_success(self, task_id: str, instance_id: str, input_params: dict, completed_at: datetime) -> None:
        row = ScheduledTaskExecution(
            execution_id=gen_id(),
            task_id=task_id,
            status="success",
            generated_instance_id=instance_id,
            completed_at=completed_at,
            input_params_used=input_params,
        )
        self.db.add(row)
        self.db.commit()

    def record_failure(self, task_id: str, input_params: dict, error_message: str, completed_at: datetime) -> None:
        row = ScheduledTaskExecution(
            execution_id=gen_id(),
            task_id=task_id,
            status="failed",
            completed_at=completed_at,
            error_message=error_message,
            input_params_used=input_params,
        )
        self.db.add(row)
        self.db.commit()

    def list_for_task(self, task_id: str) -> list[dict]:
        rows = self.db.query(ScheduledTaskExecution).filter(ScheduledTaskExecution.task_id == task_id).all()
        return [{
            "execution_id": item.execution_id,
            "status": item.status,
            "generated_instance_id": item.generated_instance_id,
            "started_at": str(item.started_at),
            "completed_at": str(item.completed_at),
            "error_message": item.error_message,
        } for item in rows]


def _to_task(row: ScheduledTaskModel) -> ScheduledTask:
    return ScheduledTask(
        task_id=row.task_id,
        user_id=row.user_id,
        name=row.name,
        description=row.description or "",
        source_instance_id=row.source_instance_id or "",
        template_id=row.template_id or "",
        schedule_type=row.schedule_type or "recurring",
        cron_expression=row.cron_expression or "",
        enabled=bool(row.enabled),
        auto_generate_doc=bool(row.auto_generate_doc),
        time_param_name=row.time_param_name or "",
        time_format=row.time_format or "%Y-%m-%d",
        use_schedule_time_as_report_time=bool(row.use_schedule_time_as_report_time),
        status=row.status or "active",
        total_runs=int(row.total_runs or 0),
        success_runs=int(row.success_runs or 0),
        failed_runs=int(row.failed_runs or 0),
        last_run_at=row.last_run_at,
        created_at=row.created_at,
    )

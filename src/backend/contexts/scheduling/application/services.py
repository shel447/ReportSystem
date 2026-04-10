from __future__ import annotations

from datetime import datetime
from typing import Any

from ....shared.kernel.errors import NotFoundError, ValidationError
from ..domain.models import ScheduledTask

MAX_TASKS_PER_USER = 5
MAX_TASKS_GLOBAL = 100


class SchedulingService:
    def __init__(self, *, task_repository, execution_repository, scheduled_instance_creator, document_service, clock) -> None:
        self.task_repository = task_repository
        self.execution_repository = execution_repository
        self.scheduled_instance_creator = scheduled_instance_creator
        self.document_service = document_service
        self.clock = clock

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id") or "default"
        if self.task_repository.count_active_for_user(user_id) >= MAX_TASKS_PER_USER:
            raise ValidationError(f"每位用户最多创建 {MAX_TASKS_PER_USER} 个定时任务")
        if self.task_repository.count_active_global() >= MAX_TASKS_GLOBAL:
            raise ValidationError(f"系统全局最多 {MAX_TASKS_GLOBAL} 个定时任务")
        task = self.task_repository.create(payload)
        return serialize_task(task)

    def list_tasks(self, *, user_id: str) -> list[dict[str, Any]]:
        return [serialize_task(task) for task in self.task_repository.list_for_user(user_id)]

    def get_task(self, task_id: str, *, user_id: str) -> dict[str, Any]:
        return serialize_task(self._require_task(task_id, user_id=user_id))

    def update_task(self, task_id: str, updates: dict[str, Any], *, user_id: str) -> dict[str, Any]:
        task = self.task_repository.update(task_id, updates, user_id=user_id)
        if not task:
            raise NotFoundError("Task not found")
        return serialize_task(task)

    def delete_task(self, task_id: str, *, user_id: str) -> dict[str, Any]:
        if not self.task_repository.delete(task_id, user_id=user_id):
            raise NotFoundError("Task not found")
        return {"message": "deleted"}

    def pause_task(self, task_id: str, *, user_id: str) -> dict[str, Any]:
        task = self.task_repository.update(task_id, {"status": "paused", "enabled": False}, user_id=user_id)
        if not task:
            raise NotFoundError("Task not found")
        return {"message": "paused"}

    def resume_task(self, task_id: str, *, user_id: str) -> dict[str, Any]:
        task = self.task_repository.update(task_id, {"status": "active", "enabled": True}, user_id=user_id)
        if not task:
            raise NotFoundError("Task not found")
        return {"message": "resumed"}

    def run_task_now(self, task_id: str, *, user_id: str) -> dict[str, Any]:
        task = self._require_task(task_id, user_id=user_id)
        actual_run_time = self.clock.now()
        scheduled_time = actual_run_time
        params: dict[str, Any] = {}
        if task.time_param_name:
            params[task.time_param_name] = scheduled_time.strftime(task.time_format or "%Y-%m-%d")
        try:
            created = self.scheduled_instance_creator.create_instance_from_schedule(
                template_id=task.template_id,
                source_instance_id=task.source_instance_id,
                override_params=params,
                report_time=scheduled_time if task.use_schedule_time_as_report_time else None,
                report_time_source="scheduled_execution" if task.use_schedule_time_as_report_time else "",
                user_id=task.user_id or "default",
            )
        except Exception as exc:
            self.execution_repository.record_failure(task.task_id, params, str(exc), actual_run_time)
            self.task_repository.record_failure(task.task_id, actual_run_time)
            raise

        self.execution_repository.record_success(task.task_id, created["instance_id"], created["input_params"], actual_run_time)
        self.task_repository.record_success(task.task_id, actual_run_time, complete_once=(task.schedule_type == "once"))

        generated_document_id = None
        if task.auto_generate_doc:
            try:
                document = self.document_service.create_document(instance_id=created["instance_id"], format_name="markdown")
                generated_document_id = document["document_id"]
            except Exception:
                generated_document_id = None

        return {
            "message": "executed",
            "instance_id": created["instance_id"],
            "document_id": generated_document_id,
        }

    def list_executions(self, task_id: str, *, user_id: str) -> list[dict[str, Any]]:
        self._require_task(task_id, user_id=user_id)
        return self.execution_repository.list_for_task(task_id)

    def _require_task(self, task_id: str, *, user_id: str) -> ScheduledTask:
        task = self.task_repository.get(task_id, user_id=user_id)
        if not task:
            raise NotFoundError("Task not found")
        return task


def serialize_task(task: ScheduledTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "user_id": task.user_id,
        "name": task.name,
        "description": task.description,
        "source_instance_id": task.source_instance_id,
        "template_id": task.template_id,
        "schedule_type": task.schedule_type,
        "cron_expression": task.cron_expression,
        "enabled": task.enabled,
        "auto_generate_doc": task.auto_generate_doc,
        "time_param_name": task.time_param_name,
        "time_format": task.time_format,
        "use_schedule_time_as_report_time": task.use_schedule_time_as_report_time,
        "status": task.status,
        "total_runs": task.total_runs,
        "success_runs": task.success_runs,
        "last_run_at": str(task.last_run_at) if task.last_run_at else None,
        "created_at": str(task.created_at),
    }

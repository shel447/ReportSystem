"""定时任务管理路由"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai_gateway import AIConfigurationError, AIRequestError
from ..database import get_db
from ..document_service import DocumentGenerationError, create_markdown_document
from ..infrastructure.dependencies import build_scheduled_run_application_service
from ..models import ScheduledTask, ScheduledTaskExecution, gen_id

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])

MAX_TASKS_PER_USER = 5
MAX_TASKS_GLOBAL = 100


class TaskCreate(BaseModel):
    name: str
    description: str = ""
    source_instance_id: str = ""
    template_id: str = ""
    schedule_type: str = "recurring"
    cron_expression: str = ""
    auto_generate_doc: bool = True
    time_param_name: str = "date"
    time_format: str = "%Y-%m-%d"
    use_schedule_time_as_report_time: bool = False
    user_id: str = "default"


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    auto_generate_doc: Optional[bool] = None
    time_param_name: Optional[str] = None
    time_format: Optional[str] = None
    use_schedule_time_as_report_time: Optional[bool] = None


@router.post("")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    user_count = db.query(ScheduledTask).filter(
        ScheduledTask.user_id == data.user_id,
        ScheduledTask.status.in_(["active", "paused"]),
    ).count()
    if user_count >= MAX_TASKS_PER_USER:
        raise HTTPException(status_code=400, detail=f"每位用户最多创建 {MAX_TASKS_PER_USER} 个定时任务")

    global_count = db.query(ScheduledTask).filter(
        ScheduledTask.status.in_(["active", "paused"])
    ).count()
    if global_count >= MAX_TASKS_GLOBAL:
        raise HTTPException(status_code=400, detail=f"系统全局最多 {MAX_TASKS_GLOBAL} 个定时任务")

    task = ScheduledTask(task_id=gen_id(), **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.get("")
def list_tasks(user_id: str = "default", db: Session = Depends(get_db)):
    tasks = db.query(ScheduledTask).filter(ScheduledTask.user_id == user_id).all()
    return [_task_dict(task) for task in tasks]


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict(task)


@router.put("/{task_id}")
def update_task(task_id: str, data: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "deleted"}


@router.post("/{task_id}/pause")
def pause_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "paused"
    task.enabled = False
    db.commit()
    return {"message": "paused"}


@router.post("/{task_id}/resume")
def resume_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "active"
    task.enabled = True
    db.commit()
    return {"message": "resumed"}


@router.post("/{task_id}/run-now")
def run_task_now(task_id: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    actual_run_time = datetime.now()
    scheduled_time = actual_run_time
    params = {}
    if task.time_param_name:
        params[task.time_param_name] = scheduled_time.strftime(task.time_format or "%Y-%m-%d")
    app_service = build_scheduled_run_application_service(db)
    try:
        created = app_service.create_instance_from_schedule(
            template_id=task.template_id,
            source_instance_id=task.source_instance_id,
            override_params=params,
            report_time=scheduled_time if task.use_schedule_time_as_report_time else None,
            report_time_source="scheduled_execution" if task.use_schedule_time_as_report_time else "",
        )
    except (AIConfigurationError, AIRequestError, ValueError) as exc:
        _record_failed_execution(db, task, params, str(exc))
        status_code = 400 if isinstance(exc, (AIConfigurationError, ValueError)) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    execution = ScheduledTaskExecution(
        execution_id=gen_id(),
        task_id=task_id,
        status="success",
        generated_instance_id=created["instance_id"],
        completed_at=actual_run_time,
        input_params_used=created["input_params"],
    )
    db.add(execution)

    task.total_runs += 1
    task.success_runs += 1
    task.last_run_at = actual_run_time
    if task.schedule_type == "once":
        task.status = "completed"

    generated_document_id = None
    if task.auto_generate_doc:
        try:
            document = create_markdown_document(db, created["instance_id"])
            generated_document_id = document.document_id
        except DocumentGenerationError:
            generated_document_id = None

    db.commit()
    return {
        "message": "executed",
        "instance_id": created["instance_id"],
        "document_id": generated_document_id,
    }


@router.get("/{task_id}/executions")
def list_executions(task_id: str, db: Session = Depends(get_db)):
    executions = db.query(ScheduledTaskExecution).filter(ScheduledTaskExecution.task_id == task_id).all()
    return [{
        "execution_id": item.execution_id,
        "status": item.status,
        "generated_instance_id": item.generated_instance_id,
        "started_at": str(item.started_at),
        "completed_at": str(item.completed_at),
        "error_message": item.error_message,
    } for item in executions]



def _record_failed_execution(db: Session, task: ScheduledTask, params: dict, error_message: str) -> None:
    execution = ScheduledTaskExecution(
        execution_id=gen_id(),
        task_id=task.task_id,
        status="failed",
        completed_at=datetime.now(),
        error_message=error_message,
        input_params_used=params,
    )
    db.add(execution)
    task.total_runs += 1
    task.failed_runs += 1
    task.last_run_at = datetime.now()
    db.commit()



def _task_dict(task: ScheduledTask):
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

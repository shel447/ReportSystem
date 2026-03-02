"""定时任务管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..database import get_db
from ..models import ScheduledTask, ScheduledTaskExecution, ReportInstance, gen_id
from ..llm_mock import generate_report_content

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
    user_id: str = "default"


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    auto_generate_doc: Optional[bool] = None


@router.post("")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    # 配额校验
    user_count = db.query(ScheduledTask).filter(
        ScheduledTask.user_id == data.user_id,
        ScheduledTask.status.in_(["active", "paused"])
    ).count()
    if user_count >= MAX_TASKS_PER_USER:
        raise HTTPException(status_code=400,
                            detail=f"每位用户最多创建 {MAX_TASKS_PER_USER} 个定时任务")

    global_count = db.query(ScheduledTask).filter(
        ScheduledTask.status.in_(["active", "paused"])
    ).count()
    if global_count >= MAX_TASKS_GLOBAL:
        raise HTTPException(status_code=400,
                            detail=f"系统全局最多 {MAX_TASKS_GLOBAL} 个定时任务")

    task = ScheduledTask(task_id=gen_id(), **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.get("")
def list_tasks(user_id: str = "default", db: Session = Depends(get_db)):
    # 用户隔离
    tasks = db.query(ScheduledTask).filter(
        ScheduledTask.user_id == user_id).all()
    return [_task_dict(t) for t in tasks]


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
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(task, k, v)
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
    """立即执行一次定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 模拟执行：创建新实例
    from ..models import ReportTemplate
    template = db.query(ReportTemplate).filter(
        ReportTemplate.template_id == task.template_id).first()

    params = {}
    if task.source_instance_id:
        source = db.query(ReportInstance).filter(
            ReportInstance.instance_id == task.source_instance_id).first()
        if source:
            params = dict(source.input_params or {})

    params[task.time_param_name] = datetime.now().strftime(task.time_format)

    content = generate_report_content(
        template.name if template else "Unknown",
        template.outline if template else [],
        params
    )

    new_inst = ReportInstance(
        instance_id=gen_id(),
        template_id=task.template_id,
        input_params=params,
        outline_content=content,
        status="draft",
    )
    db.add(new_inst)

    # 记录执行
    execution = ScheduledTaskExecution(
        execution_id=gen_id(),
        task_id=task_id,
        status="success",
        generated_instance_id=new_inst.instance_id,
        completed_at=datetime.now(),
        input_params_used=params,
    )
    db.add(execution)

    task.total_runs += 1
    task.success_runs += 1
    task.last_run_at = datetime.now()
    if task.schedule_type == "once":
        task.status = "completed"

    db.commit()
    return {"message": "executed", "instance_id": new_inst.instance_id}


@router.get("/{task_id}/executions")
def list_executions(task_id: str, db: Session = Depends(get_db)):
    execs = db.query(ScheduledTaskExecution).filter(
        ScheduledTaskExecution.task_id == task_id).all()
    return [{"execution_id": e.execution_id, "status": e.status,
             "generated_instance_id": e.generated_instance_id,
             "started_at": str(e.started_at),
             "completed_at": str(e.completed_at)} for e in execs]


def _task_dict(t):
    return {
        "task_id": t.task_id,
        "user_id": t.user_id,
        "name": t.name,
        "description": t.description,
        "source_instance_id": t.source_instance_id,
        "template_id": t.template_id,
        "schedule_type": t.schedule_type,
        "cron_expression": t.cron_expression,
        "enabled": t.enabled,
        "auto_generate_doc": t.auto_generate_doc,
        "status": t.status,
        "total_runs": t.total_runs,
        "success_runs": t.success_runs,
        "last_run_at": str(t.last_run_at) if t.last_run_at else None,
        "created_at": str(t.created_at),
    }

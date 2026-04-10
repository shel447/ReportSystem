"""定时任务管理路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.persistence.database import get_db
from ..infrastructure.dependencies import build_scheduling_service
from ..shared.kernel.http import resolve_user_id
from ..shared.kernel.errors import NotFoundError, UpstreamError, ValidationError

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


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
def create_task(data: TaskCreate, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        payload = data.model_dump()
        payload["user_id"] = resolve_user_id(user_id)
        return build_scheduling_service(db).create_task(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_tasks(db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    return build_scheduling_service(db).list_tasks(user_id=resolve_user_id(user_id))


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).get_task(task_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{task_id}")
def update_task(task_id: str, data: TaskUpdate, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).update_task(task_id, data.model_dump(exclude_none=True), user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).delete_task(task_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/pause")
def pause_task(task_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).pause_task(task_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/resume")
def resume_task(task_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).resume_task(task_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/run-now")
def run_task_now(task_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).run_task_now(task_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{task_id}/executions")
def list_executions(task_id: str, db: Session = Depends(get_db), user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    try:
        return build_scheduling_service(db).list_executions(task_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

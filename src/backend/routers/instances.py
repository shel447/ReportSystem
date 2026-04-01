"""Report instance routes."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.persistence.database import get_db
from ..infrastructure.dependencies import build_conversation_service, build_report_runtime_service
from ..shared.kernel.errors import ConflictError, NotFoundError, UpstreamError, ValidationError

router = APIRouter(prefix="/instances", tags=["instances"])


class InstanceCreate(BaseModel):
    template_id: str
    input_params: Dict[str, Any] = {}
    outline_override: Optional[List[Any]] = None


class InstanceUpdate(BaseModel):
    outline_content: Optional[List[Any]] = None
    status: Optional[str] = None


@router.post("")
def create_instance(data: InstanceCreate, db: Session = Depends(get_db)):
    service = build_report_runtime_service(db)
    try:
        result = service.create_instance(
            template_id=data.template_id,
            input_params=data.input_params or {},
            outline_override=data.outline_override,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "instance_id": result["instance_id"],
        "template_id": result["template_id"],
        "status": result["status"],
        "input_params": result["input_params"],
        "outline_content": result["outline_content"],
        "report_time": result.get("report_time"),
        "report_time_source": result.get("report_time_source", ""),
        "created_at": result.get("created_at"),
        "updated_at": result.get("updated_at"),
        "warnings": result.get("warnings", []),
    }


@router.get("/{instance_id}/baseline")
def get_instance_baseline(instance_id: str, db: Session = Depends(get_db)):
    try:
        return build_report_runtime_service(db).get_generation_baseline(instance_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{instance_id}/update-chat")
def update_instance_chat(instance_id: str, db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).update_session_from_instance(instance_id=instance_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{instance_id}/fork-sources")
def list_instance_fork_sources(instance_id: str, db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).list_instance_fork_sources(instance_id=instance_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{instance_id}/fork-chat")
def fork_instance_chat(instance_id: str, data: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        return build_conversation_service(db).fork_instance_chat(
            instance_id=instance_id,
            source_message_id=str((data or {}).get("source_message_id") or "").strip(),
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{instance_id}")
def get_instance(instance_id: str, db: Session = Depends(get_db)):
    try:
        return build_report_runtime_service(db).get_instance(instance_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{instance_id}")
def update_instance(instance_id: str, data: InstanceUpdate, db: Session = Depends(get_db)):
    try:
        return build_report_runtime_service(db).update_instance(instance_id, data.model_dump(exclude_none=True))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{instance_id}")
def delete_instance(instance_id: str, db: Session = Depends(get_db)):
    try:
        return build_report_runtime_service(db).delete_instance(instance_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{instance_id}/finalize")
def finalize_instance(instance_id: str, db: Session = Depends(get_db)):
    try:
        return build_report_runtime_service(db).finalize_instance(instance_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{instance_id}/regenerate/{section_index}")
def regenerate_section(instance_id: str, section_index: int, db: Session = Depends(get_db)):
    try:
        return build_report_runtime_service(db).regenerate_section(instance_id, section_index)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("")
def list_instances(template_id: Optional[str] = None, db: Session = Depends(get_db)):
    return build_report_runtime_service(db).list_instances(template_id=template_id)

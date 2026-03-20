"""Report instance routes."""
from copy import deepcopy
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ..chat_fork_service import fork_session_from_message, fork_session_from_template_instance
from ..chat_session_service import ensure_session_metadata, truncate_text, visible_chat_messages
from ..database import get_db
from ..infrastructure.dependencies import build_instance_application_service
from ..models import ChatSession, ReportInstance, ReportTemplate, TemplateInstance
from ..report_generation_service import generate_single_section
from ..template_instance_service import build_generation_baseline_payload, get_generation_baseline
from ..application.reporting.services import is_v2_template
from ..infrastructure.reporting.repositories import OpenAIContentGenerator, SqlAlchemyTemplateRepository

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
    app_service = build_instance_application_service(db)
    try:
        result = app_service.create_instance(
            template_id=data.template_id,
            input_params=data.input_params or {},
            outline_override=data.outline_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AIConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "instance_id": result["instance_id"],
        "template_id": result["template_id"],
        "status": result["status"],
        "input_params": result["input_params"],
        "outline_content": result["outline_content"],
        "created_at": result.get("created_at"),
        "updated_at": result.get("updated_at"),
        "warnings": result.get("warnings", []),
    }


@router.get("/{instance_id}/baseline")
def get_instance_baseline(instance_id: str, db: Session = Depends(get_db)):
    _instance = _require_instance(db, instance_id)
    baseline = _require_generation_baseline(db, instance_id)
    return build_generation_baseline_payload(baseline)


@router.post("/{instance_id}/update-chat")
def update_instance_chat(instance_id: str, db: Session = Depends(get_db)):
    _instance = _require_instance(db, instance_id)
    baseline = _require_generation_baseline(db, instance_id)
    return fork_session_from_template_instance(db, template_instance=baseline)


@router.get("/{instance_id}/fork-sources")
def list_instance_fork_sources(instance_id: str, db: Session = Depends(get_db)):
    _instance = _require_instance(db, instance_id)
    baseline = _require_generation_baseline(db, instance_id)
    source_session = _require_source_session(db, baseline)
    ensure_session_metadata(source_session)
    visible = visible_chat_messages(source_session.messages or [])
    return [_serialize_fork_source_message(item) for item in visible]


@router.post("/{instance_id}/fork-chat")
def fork_instance_chat(instance_id: str, data: Dict[str, Any], db: Session = Depends(get_db)):
    _instance = _require_instance(db, instance_id)
    baseline = _require_generation_baseline(db, instance_id)
    source_session = _require_source_session(db, baseline)
    source_message_id = str((data or {}).get("source_message_id") or "").strip()
    if not source_message_id:
        raise HTTPException(status_code=404, detail="Source message not found")
    return fork_session_from_message(
        db,
        source_session=source_session,
        source_message_id=source_message_id,
    )


@router.get("/{instance_id}")
def get_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = _require_instance(db, instance_id)
    baseline = get_generation_baseline(db, instance_id)
    return _inst_dict(inst, baseline)


@router.put("/{instance_id}")
def update_instance(instance_id: str, data: InstanceUpdate, db: Session = Depends(get_db)):
    inst = _require_instance(db, instance_id)
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(inst, key, value)
    db.commit()
    db.refresh(inst)
    baseline = get_generation_baseline(db, instance_id)
    return _inst_dict(inst, baseline)


@router.delete("/{instance_id}")
def delete_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = _require_instance(db, instance_id)
    for baseline in db.query(TemplateInstance).filter(TemplateInstance.report_instance_id == instance_id).all():
        db.delete(baseline)
    db.delete(inst)
    db.commit()
    return {"message": "deleted"}


@router.post("/{instance_id}/finalize")
def finalize_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = _require_instance(db, instance_id)
    inst.status = "finalized"
    db.commit()
    return {"message": "finalized", "instance_id": instance_id}


@router.post("/{instance_id}/regenerate/{section_index}")
def regenerate_section(instance_id: str, section_index: int, db: Session = Depends(get_db)):
    inst = _require_instance(db, instance_id)

    content = list(inst.outline_content or [])
    if section_index < 0 or section_index >= len(content):
        raise HTTPException(status_code=400, detail="Invalid section index")

    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == inst.template_id).first()
    template_entity = SqlAlchemyTemplateRepository(db).get_by_id(inst.template_id)
    current = content[section_index]
    regenerated: Dict[str, Any]
    try:
        if template_entity and is_v2_template(template_entity):
            generator = OpenAIContentGenerator(db, gateway=OpenAICompatGateway())
            outline_node = ((current.get("debug") or {}).get("outline_node")) if isinstance(current, dict) else None
            if outline_node:
                sections, _warnings = generator.generate_v2_from_outline(
                    template_entity,
                    [outline_node],
                    inst.input_params or {},
                )
                if not sections:
                    raise HTTPException(status_code=400, detail="Invalid section index")
                regenerated = sections[0]
            else:
                sections, _warnings = generator.generate_v2(template_entity, inst.input_params or {})
                if section_index >= len(sections):
                    raise HTTPException(status_code=400, detail="Invalid section index")
                regenerated = sections[section_index]
        else:
            section_spec = {
                "title": current.get("title", "未命名章节"),
                "description": current.get("description", ""),
                "dynamic_meta": current.get("dynamic_meta"),
                "level": 1,
            }
            regenerated = generate_single_section(
                db,
                OpenAICompatGateway(),
                {
                    "template_id": template.template_id if template else "",
                    "name": template.name if template else "报告章节",
                    "description": template.description if template else "",
                    "report_type": template.report_type if template else "",
                    "scenario": template.scenario if template else "",
                    "match_keywords": template.match_keywords if template else [],
                    "content_params": template.content_params if template else [],
                    "outline": template.outline if template else [],
                },
                section_spec,
                inst.input_params or {},
                existing_sections=content,
                section_index=section_index,
            )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    content[section_index] = {**current, **regenerated, "regenerated": True}
    inst.outline_content = content

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(inst, "outline_content")
    db.commit()
    db.refresh(inst)
    baseline = get_generation_baseline(db, instance_id)
    return _inst_dict(inst, baseline)


@router.get("")
def list_instances(template_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ReportInstance)
    if template_id:
        query = query.filter(ReportInstance.template_id == template_id)
    instances = query.order_by(ReportInstance.created_at.desc()).all()
    baseline_map = _baseline_map(db, [inst.instance_id for inst in instances])
    return [_inst_dict(inst, baseline_map.get(inst.instance_id)) for inst in instances]


def _baseline_map(db: Session, instance_ids: List[str]) -> Dict[str, Any]:
    if not instance_ids:
        return {}
    records = (
        db.query(TemplateInstance)
        .filter(TemplateInstance.report_instance_id.in_(instance_ids))
        .order_by(TemplateInstance.created_at.desc(), TemplateInstance.template_instance_id.desc())
        .all()
    )
    mapping: Dict[str, Any] = {}
    for record in records:
        if record.report_instance_id in mapping:
            continue
        mapping[record.report_instance_id] = record
    return mapping


def _inst_dict(inst: ReportInstance, baseline=None):
    has_generation_baseline = baseline is not None
    supports_fork_chat = bool(has_generation_baseline and getattr(baseline, "session_id", ""))
    return {
        "instance_id": inst.instance_id,
        "template_id": inst.template_id,
        "status": inst.status,
        "input_params": deepcopy(inst.input_params or {}),
        "outline_content": deepcopy(inst.outline_content or []),
        "created_at": str(inst.created_at),
        "updated_at": str(inst.updated_at),
        "has_generation_baseline": has_generation_baseline,
        "supports_update_chat": has_generation_baseline,
        "supports_fork_chat": supports_fork_chat,
    }


def _require_instance(db: Session, instance_id: str) -> ReportInstance:
    inst = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return inst


def _require_generation_baseline(db: Session, instance_id: str):
    baseline = get_generation_baseline(db, instance_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Generation baseline not found")
    return baseline


def _require_source_session(db: Session, baseline) -> ChatSession:
    session_id = str(getattr(baseline, "session_id", "") or "").strip()
    if not session_id:
        raise HTTPException(status_code=404, detail="Source session not found")
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Source session not found")
    return session


def _serialize_fork_source_message(message: Dict[str, Any]) -> Dict[str, Any]:
    action = message.get("action") if isinstance(message.get("action"), dict) else {}
    content = str(message.get("content") or "").strip()
    preview = truncate_text(content, 48) if content else str(action.get("type") or "消息")
    return {
        "message_id": message.get("message_id"),
        "role": message.get("role"),
        "preview": preview,
        "created_at": message.get("created_at"),
        "action_type": str(action.get("type") or "") or None,
    }

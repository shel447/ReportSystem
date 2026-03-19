"""Report instance routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ..ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ..database import get_db
from ..infrastructure.dependencies import build_instance_application_service
from ..models import ReportInstance, ReportTemplate
from ..report_generation_service import generate_single_section
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


@router.get("/{instance_id}")
def get_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return _inst_dict(inst)


@router.put("/{instance_id}")
def update_instance(instance_id: str, data: InstanceUpdate, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(inst, key, value)
    db.commit()
    db.refresh(inst)
    return _inst_dict(inst)


@router.delete("/{instance_id}")
def delete_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    db.delete(inst)
    db.commit()
    return {"message": "deleted"}


@router.post("/{instance_id}/finalize")
def finalize_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    inst.status = "finalized"
    db.commit()
    return {"message": "finalized", "instance_id": instance_id}


@router.post("/{instance_id}/regenerate/{section_index}")
def regenerate_section(instance_id: str, section_index: int, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

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
    return _inst_dict(inst)


@router.get("")
def list_instances(template_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ReportInstance)
    if template_id:
        query = query.filter(ReportInstance.template_id == template_id)
    instances = query.order_by(ReportInstance.created_at.desc()).all()
    return [_inst_dict(inst) for inst in instances]



def _inst_dict(inst):
    return {
        "instance_id": inst.instance_id,
        "template_id": inst.template_id,
        "status": inst.status,
        "input_params": inst.input_params,
        "outline_content": inst.outline_content,
        "created_at": str(inst.created_at),
        "updated_at": str(inst.updated_at),
    }

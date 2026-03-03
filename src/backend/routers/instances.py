"""报告实例管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ..database import get_db
from ..models import ReportInstance, ReportTemplate, gen_id
from ..llm_mock import generate_report_content

router = APIRouter(prefix="/instances", tags=["instances"])


class InstanceCreate(BaseModel):
    template_id: str
    input_params: Dict[str, Any] = {}


class InstanceUpdate(BaseModel):
    outline_content: Optional[List[Any]] = None
    status: Optional[str] = None


@router.post("")
def create_instance(data: InstanceCreate, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(
        ReportTemplate.template_id == data.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 使用 mock LLM 生成内容
    content = generate_report_content(template.name, template.outline, data.input_params)

    inst = ReportInstance(
        instance_id=gen_id(),
        template_id=data.template_id,
        template_version=template.version,
        input_params=data.input_params,
        outline_content=content,
        status="draft",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return _inst_dict(inst)


@router.get("/{instance_id}")
def get_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(
        ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return _inst_dict(inst)


@router.put("/{instance_id}")
def update_instance(instance_id: str, data: InstanceUpdate,
                    db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(
        ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(inst, k, v)
    db.commit()
    db.refresh(inst)
    return _inst_dict(inst)


@router.delete("/{instance_id}")
def delete_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(
        ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    db.delete(inst)
    db.commit()
    return {"message": "deleted"}


@router.post("/{instance_id}/finalize")
def finalize_instance(instance_id: str, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(
        ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    inst.status = "finalized"
    db.commit()
    return {"message": "finalized", "instance_id": instance_id}


@router.post("/{instance_id}/regenerate/{section_index}")
def regenerate_section(instance_id: str, section_index: int,
                       db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(
        ReportInstance.instance_id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    content = inst.outline_content or []
    if section_index < 0 or section_index >= len(content):
        raise HTTPException(status_code=400, detail="Invalid section index")

    section = content[section_index]
    section["content"] = f"[重新生成] {section.get('title', '未命名章节')}的分析内容已更新。基于最新数据重新评估，各项指标表现良好。"
    section["regenerated"] = True

    inst.outline_content = content
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(inst, "outline_content")
    db.commit()
    db.refresh(inst)
    return _inst_dict(inst)


@router.get("")
def list_instances(template_id: Optional[str] = None, 
                   db: Session = Depends(get_db)):
    q = db.query(ReportInstance)
    if template_id:
        q = q.filter(ReportInstance.template_id == template_id)
    # 按创建时间倒序
    instances = q.order_by(ReportInstance.created_at.desc()).all()
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

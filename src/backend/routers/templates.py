"""报告模板管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any
from ..database import get_db
from ..models import ReportTemplate, gen_id

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    report_type: str = "daily"
    scenario: str = ""
    content_params: List[Any] = []
    outline: List[Any] = []
    output_formats: List[str] = ["pdf"]


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    report_type: Optional[str] = None
    scenario: Optional[str] = None
    content_params: Optional[List[Any]] = None
    outline: Optional[List[Any]] = None


@router.post("")
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    t = ReportTemplate(template_id=gen_id(), **data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"template_id": t.template_id, "name": t.name, "description": t.description,
            "report_type": t.report_type, "scenario": t.scenario,
            "content_params": t.content_params, "outline": t.outline,
            "output_formats": t.output_formats,
            "created_at": str(t.created_at), "version": t.version}


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(ReportTemplate).all()
    return [{"template_id": t.template_id, "name": t.name, "description": t.description,
             "report_type": t.report_type, "scenario": t.scenario,
             "created_at": str(t.created_at)} for t in templates]


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    t = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template_id": t.template_id, "name": t.name, "description": t.description,
            "report_type": t.report_type, "scenario": t.scenario,
            "content_params": t.content_params, "outline": t.outline,
            "output_formats": t.output_formats,
            "created_at": str(t.created_at), "version": t.version}


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpdate, db: Session = Depends(get_db)):
    t = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return {"template_id": t.template_id, "name": t.name}


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    t = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()
    return {"message": "deleted"}

"""报告模板管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Any

from ..database import get_db
from ..models import ReportTemplate, gen_id
from ..template_index_service import delete_template_index, mark_template_index_stale

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    report_type: str = "daily"
    scenario: str = ""
    match_keywords: List[str] = []
    content_params: List[Any] = []
    outline: List[Any] = []
    output_formats: List[str] = ["pdf"]


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    report_type: Optional[str] = None
    scenario: Optional[str] = None
    match_keywords: Optional[List[str]] = None
    content_params: Optional[List[Any]] = None
    outline: Optional[List[Any]] = None
    output_formats: Optional[List[str]] = None


@router.post("")
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    payload = _clean_template_payload(data.model_dump())
    template = ReportTemplate(template_id=gen_id(), **payload)
    db.add(template)
    db.commit()
    db.refresh(template)
    mark_template_index_stale(db, template.template_id, "模板新建后尚未建立语义索引。")
    return _template_detail(template)


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(ReportTemplate).all()
    return [{
        "template_id": item.template_id,
        "name": item.name,
        "description": item.description,
        "report_type": item.report_type,
        "scenario": item.scenario,
        "created_at": str(item.created_at),
    } for item in templates]


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_detail(template)


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in _clean_template_payload(data.model_dump(exclude_none=True)).items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    mark_template_index_stale(db, template.template_id, "模板已更新，请重建语义索引。")
    return _template_detail(template)


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    delete_template_index(db, template_id)
    return {"message": "deleted"}



def _template_detail(template: ReportTemplate):
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "report_type": template.report_type,
        "scenario": template.scenario,
        "match_keywords": _normalize_keywords(template.match_keywords),
        "content_params": template.content_params,
        "outline": template.outline,
        "output_formats": template.output_formats,
        "created_at": str(template.created_at),
        "version": template.version,
    }


def _clean_template_payload(payload):
    if "match_keywords" in payload:
        payload["match_keywords"] = _normalize_keywords(payload.get("match_keywords"))
    return payload


def _normalize_keywords(items):
    if not isinstance(items, list):
        return []
    seen = set()
    normalized = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized

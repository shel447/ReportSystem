"""报告模板路由"""
import json
import re
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReportTemplate, gen_id
from ..template_index_service import delete_template_index, mark_template_index_stale
from ..template_schema_service import validate_template_payload

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    report_type: str = "daily"
    type: str = ""
    scenario: str = ""
    scene: str = ""
    match_keywords: List[str] = []
    content_params: List[Any] = []
    parameters: List[Any] = []
    outline: List[Any] = []
    sections: List[Any] = []
    schema_version: str = ""
    output_formats: List[str] = ["pdf"]


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    report_type: Optional[str] = None
    type: Optional[str] = None
    scenario: Optional[str] = None
    scene: Optional[str] = None
    match_keywords: Optional[List[str]] = None
    content_params: Optional[List[Any]] = None
    parameters: Optional[List[Any]] = None
    outline: Optional[List[Any]] = None
    sections: Optional[List[Any]] = None
    schema_version: Optional[str] = None
    output_formats: Optional[List[str]] = None


@router.post("")
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    try:
        payload = _clean_template_payload(data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    template = ReportTemplate(template_id=gen_id(), **payload)
    db.add(template)
    db.commit()
    db.refresh(template)
    mark_template_index_stale(db, template.template_id, "模板新建后尚未建立语义索引。")
    return _template_detail(template)


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(ReportTemplate).all()
    return [
        {
            "template_id": item.template_id,
            "name": item.name,
            "description": item.description,
            "report_type": item.report_type,
            "scenario": item.scenario,
            "type": item.template_type or "",
            "scene": item.scene or "",
            "schema_version": item.schema_version or "",
            "parameter_count": len(item.parameters or []),
            "top_level_section_count": len(item.sections or []),
            "created_at": str(item.created_at),
        }
        for item in templates
    ]


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_detail(template)


@router.get("/{template_id}/export")
def export_template_definition(template_id: str, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    payload = _export_template_payload(template)
    filename = _build_export_filename(template)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        updates = _clean_template_payload(data.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    for key, value in updates.items():
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
        "type": template.template_type or "",
        "scene": template.scene or "",
        "match_keywords": _normalize_keywords(template.match_keywords),
        "content_params": template.content_params,
        "parameters": template.parameters,
        "outline": template.outline,
        "sections": template.sections,
        "schema_version": template.schema_version or "",
        "output_formats": template.output_formats,
        "created_at": str(template.created_at),
        "version": template.version,
    }


def _export_template_payload(template: ReportTemplate):
    return {
        "name": template.name,
        "description": template.description,
        "report_type": template.report_type,
        "scenario": template.scenario,
        "type": template.template_type or "",
        "scene": template.scene or "",
        "match_keywords": _normalize_keywords(template.match_keywords),
        "parameters": template.parameters or [],
        "sections": template.sections or [],
        "schema_version": template.schema_version or "",
        "output_formats": template.output_formats or [],
    }


def _clean_template_payload(payload):
    payload = validate_template_payload(payload)
    if "type" in payload:
        payload["template_type"] = payload.pop("type") or ""
    if "scene" in payload:
        payload["scene"] = payload.get("scene") or ""
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


def _build_export_filename(template: ReportTemplate) -> str:
    base = re.sub(r"[^0-9A-Za-z._-]+", "-", str(template.name or "").strip()).strip("-")
    if not base:
        base = f"template-{template.template_id}"
    return f"{base}.json"

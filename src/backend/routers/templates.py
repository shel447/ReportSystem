"""报告模板路由"""
import json
import re
from urllib.parse import quote
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.persistence.database import get_db
from ..infrastructure.dependencies import build_template_catalog_service
from ..contexts.template_catalog.application.services import TemplateCatalogService
from ..contexts.template_catalog.infrastructure.repositories import TemplateSchemaGateway
from ..shared.kernel.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = ""
    parameters: List[Any] = []
    sections: List[Any] = []


class TemplateUpdate(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    parameters: Optional[List[Any]] = None
    sections: Optional[List[Any]] = None


class TemplateImportPreviewRequest(BaseModel):
    payload: dict[str, Any]
    filename: Optional[str] = None


def _clean_template_payload(payload: dict[str, Any]) -> dict[str, Any]:
    service = TemplateCatalogService(repository=None, matcher=None, schema_gateway=TemplateSchemaGateway())
    return service._clean_payload(dict(payload))


@router.post("")
def create_template(data: TemplateCreate, db: Session = Depends(get_db)):
    service = build_template_catalog_service(db)
    try:
        return service.create_template(data.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    return build_template_catalog_service(db).list_templates()


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    try:
        return build_template_catalog_service(db).get_template(template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{template_id}/export")
def export_template_definition(template_id: str, db: Session = Depends(get_db)):
    try:
        payload, filename = build_template_catalog_service(db).export_template(template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": _build_download_header(filename)},
    )


@router.post("/import/preview")
def preview_import_template(data: TemplateImportPreviewRequest, db: Session = Depends(get_db)):
    try:
        return build_template_catalog_service(db).preview_import_template(data.payload, data.filename)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpdate, db: Session = Depends(get_db)):
    service = build_template_catalog_service(db)
    try:
        return service.update_template(template_id, data.model_dump(exclude_none=True))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    try:
        build_template_catalog_service(db).delete_template(template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": "deleted"}


def _build_download_header(filename: str) -> str:
    fallback = re.sub(r"[^0-9A-Za-z._-]+", "-", filename).strip("-")
    if not fallback:
        fallback = "template-export.json"
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'

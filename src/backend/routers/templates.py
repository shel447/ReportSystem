from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.dependencies import build_template_catalog_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import ConflictError, NotFoundError, ValidationError

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateUpsertRequest(BaseModel):
    id: str
    category: str
    name: str
    description: str
    schemaVersion: str
    tags: list[str] = []
    parameters: list[dict[str, Any]]
    catalogs: list[dict[str, Any]]


class TemplateImportPreviewRequest(BaseModel):
    content: Any


@router.post("")
def create_template(data: TemplateUpsertRequest, db: Session = Depends(get_db)):
    service = build_template_catalog_service(db)
    try:
        return service.create_template(data.model_dump())
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpsertRequest, db: Session = Depends(get_db)):
    service = build_template_catalog_service(db)
    try:
        return service.update_template(template_id, data.model_dump())
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    try:
        build_template_catalog_service(db).delete_template(template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": "deleted"}


@router.post("/import/preview")
def preview_import_template(data: TemplateImportPreviewRequest, db: Session = Depends(get_db)):
    try:
        return build_template_catalog_service(db).preview_import_template(data.content)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


def _build_download_header(filename: str) -> str:
    fallback = re.sub(r"[^0-9A-Za-z._-]+", "-", filename).strip("-")
    if not fallback:
        fallback = "template-export.json"
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'

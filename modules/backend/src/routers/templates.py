from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..contexts.report.application.template_models import (
    template_import_preview_to_dict,
    template_summary_to_dict,
)
from ..contexts.report.domain.template_models import report_template_from_dict, report_template_to_dict
from ..infrastructure.dependencies import build_report_service
from ..infrastructure.persistence.database import get_db

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateUpsertRequest(BaseModel):
    id: str
    category: str
    name: str
    description: str
    schemaVersion: str
    structureType: str | None = None
    parameters: list[dict[str, Any]]
    catalogs: list[dict[str, Any]] | None = None
    chapters: list[dict[str, Any]] | None = None


class TemplateImportPreviewRequest(BaseModel):
    content: Any


@router.post("")
def create_template(data: TemplateUpsertRequest, db: Session = Depends(get_db)):
    service = build_report_service(db)
    return report_template_to_dict(service.create_template(report_template_from_dict(data.model_dump())))


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    return [template_summary_to_dict(item) for item in build_report_service(db).list_templates()]


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    return report_template_to_dict(build_report_service(db).get_template(template_id))


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpsertRequest, db: Session = Depends(get_db)):
    service = build_report_service(db)
    return report_template_to_dict(service.update_template(template_id, report_template_from_dict(data.model_dump())))


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    build_report_service(db).delete_template(template_id)
    return {"message": "deleted"}


@router.post("/import/preview")
def preview_import_template(data: TemplateImportPreviewRequest, db: Session = Depends(get_db)):
    return template_import_preview_to_dict(build_report_service(db).preview_import_template(data.content))


@router.get("/{template_id}/export")
def export_template_definition(template_id: str, db: Session = Depends(get_db)):
    payload, filename = build_report_service(db).export_template(template_id)
    return Response(
        content=json.dumps(report_template_to_dict(payload), ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": _build_download_header(filename)},
    )


def _build_download_header(filename: str) -> str:
    fallback = re.sub(r"[^0-9A-Za-z._-]+", "-", filename).strip("-")
    if not fallback:
        fallback = "template-export.json"
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'

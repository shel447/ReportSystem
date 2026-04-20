from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..contexts.report_runtime.application.models import (
    document_generation_result_to_dict,
    report_view_to_dict,
)
from ..infrastructure.dependencies import build_report_document_service, build_report_runtime_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import NotFoundError, ValidationError
from ..shared.kernel.http import resolve_user_id

router = APIRouter(prefix="/reports", tags=["reports"])


class DocumentGenerationRequest(BaseModel):
    formats: list[str]
    pdfSource: str | None = None
    theme: str = "default"
    strictValidation: bool = True
    regenerateIfExists: bool = False


@router.get("/{report_id}")
def get_report_view(
    report_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return report_view_to_dict(build_report_runtime_service(db).get_report_view(report_id, user_id=resolve_user_id(user_id)))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{report_id}/document-generations")
def generate_report_documents(
    report_id: str,
    data: DocumentGenerationRequest,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return document_generation_result_to_dict(build_report_runtime_service(db).generate_documents(
            report_id=report_id,
            user_id=resolve_user_id(user_id),
            formats=data.formats,
            pdf_source=data.pdfSource,
            theme=data.theme,
            strict_validation=data.strictValidation,
            regenerate_if_exists=data.regenerateIfExists,
        ))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{report_id}/documents/{document_id}/download")
def download_report_document(
    report_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    resolved_user_id = resolve_user_id(user_id)
    try:
        report = build_report_runtime_service(db).get_report_view(report_id, user_id=resolved_user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    documents = report.answer.documents
    if not any(item.id == document_id for item in documents):
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        resolved = build_report_document_service(db).resolve_download(
            report_id=report_id,
            document_id=document_id,
            user_id=resolved_user_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Document file not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return FileResponse(
        path=resolved.absolute_path,
        filename=resolved.document.file_name or f"{document_id}.md",
        media_type=resolved.document.mime_type or "application/octet-stream",
    )

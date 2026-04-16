"""Aggregated report view routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..infrastructure.dependencies import build_report_document_service, build_report_runtime_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import NotFoundError, ValidationError
from ..shared.kernel.http import resolve_user_id

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}")
def get_report_view(
    report_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return build_report_runtime_service(db).get_report_view(report_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{report_id}/documents/{document_id}/download")
def download_report_document(
    report_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        report = build_report_runtime_service(db).get_report_view(report_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    documents = (report.get("generated_content") or {}).get("documents") or []
    if not any(str(item.get("document_id") or "") == document_id for item in documents if isinstance(item, dict)):
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        document, absolute_path = build_report_document_service(db).resolve_download(document_id=document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Document file not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return FileResponse(
        path=absolute_path,
        filename=document.get("file_name") or f"{document_id}.md",
        media_type="text/markdown; charset=utf-8",
    )

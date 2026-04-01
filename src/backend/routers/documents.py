"""Report document routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..infrastructure.persistence.database import get_db
from ..infrastructure.dependencies import build_report_document_service
from ..shared.kernel.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    instance_id: str
    format: str = "markdown"


@router.post("")
def create_document(data: DocumentCreate, db: Session = Depends(get_db)):
    service = build_report_document_service(db)
    try:
        return service.create_document(instance_id=data.instance_id, format_name=data.format)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        status_code = 404 if str(exc) == "Instance not found" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("")
def list_documents(instance_id: str | None = None, db: Session = Depends(get_db)):
    return build_report_document_service(db).list_documents(instance_id=instance_id)


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    try:
        return build_report_document_service(db).get_document(document_id=document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)):
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


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    try:
        return build_report_document_service(db).delete_document(document_id=document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

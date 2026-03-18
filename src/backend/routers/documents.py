"""Report document routes."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..document_service import (
    DocumentGenerationError,
    create_markdown_document,
    normalize_document_format,
    remove_document_file,
    resolve_document_absolute_path,
    serialize_document,
)
from ..models import ReportDocument

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    instance_id: str
    format: str = "markdown"


@router.post("")
def create_document(data: DocumentCreate, db: Session = Depends(get_db)):
    try:
        fmt = normalize_document_format(data.format)
        if fmt != "md":
            raise DocumentGenerationError("当前仅支持生成 Markdown 文档。")
        document = create_markdown_document(db, data.instance_id)
    except DocumentGenerationError as exc:
        status_code = 404 if str(exc) == "Instance not found" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return serialize_document(document)


@router.get("")
def list_documents(instance_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ReportDocument)
    if instance_id:
        query = query.filter(ReportDocument.instance_id == instance_id)
    documents = query.order_by(ReportDocument.created_at.desc()).all()
    return [serialize_document(item) for item in documents if _document_has_file(item)]


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = _get_document_or_404(db, document_id)
    return serialize_document(document)


@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)):
    document = _get_document_or_404(db, document_id)
    try:
        absolute_path = resolve_document_absolute_path(document.file_path)
    except DocumentGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not absolute_path or not document.file_path or not os.path.exists(absolute_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(
        path=absolute_path,
        filename=serialize_document(document)["file_name"] or f"{document.document_id}.md",
        media_type="text/markdown; charset=utf-8",
    )


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = _get_document_or_404(db, document_id)
    remove_document_file(document)
    db.delete(document)
    db.commit()
    return {"message": "deleted"}


def _get_document_or_404(db: Session, document_id: str) -> ReportDocument:
    document = db.query(ReportDocument).filter(ReportDocument.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _document_has_file(document: ReportDocument) -> bool:
    if not document.file_path:
        return False
    try:
        absolute_path = resolve_document_absolute_path(document.file_path)
    except DocumentGenerationError:
        return False
    return os.path.exists(absolute_path)

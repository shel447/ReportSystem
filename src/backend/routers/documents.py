"""报告文档管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models import ReportDocument, ReportInstance, gen_id

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    instance_id: str
    format: str = "pdf"


@router.post("")
def create_document(data: DocumentCreate, db: Session = Depends(get_db)):
    inst = db.query(ReportInstance).filter(
        ReportInstance.instance_id == data.instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    doc = ReportDocument(
        document_id=gen_id(),
        instance_id=data.instance_id,
        template_id=inst.template_id,
        format=data.format,
        file_path=f"/documents/{data.instance_id}.{data.format}",
        file_size=1024,
        status="ready",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_dict(doc)


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(ReportDocument).filter(
        ReportDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_dict(doc)


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(ReportDocument).filter(
        ReportDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"message": "deleted"}


@router.get("")
def list_documents(instance_id: Optional[str] = None,
                   db: Session = Depends(get_db)):
    q = db.query(ReportDocument)
    if instance_id:
        q = q.filter(ReportDocument.instance_id == instance_id)
    docs = q.all()
    return [_doc_dict(d) for d in docs]


def _doc_dict(doc):
    return {
        "document_id": doc.document_id,
        "instance_id": doc.instance_id,
        "template_id": doc.template_id,
        "format": doc.format,
        "file_path": doc.file_path,
        "file_size": doc.file_size,
        "status": doc.status,
        "created_at": str(doc.created_at),
    }

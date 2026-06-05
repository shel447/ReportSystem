from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..contexts.report.application.generation_models import (
    document_generation_result_to_dict,
    report_view_to_dict,
)
from ..infrastructure.dependencies import build_report_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import ErrorCode, NotFoundError, ValidationError
from ..shared.kernel.http import get_current_user_id
from ..shared.kernel.policy_auth import policy_auth

router = APIRouter(prefix="/reports", tags=["reports"])


class DocumentGenerationRequest(BaseModel):
    formats: list[str]
    pdfSource: str | None = None
    theme: str = "default"
    strictValidation: bool = True
    regenerateIfExists: bool = False


@router.get("/{report_id}")
@policy_auth(resource="report", action="read")
def get_report_view(
    report_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return report_view_to_dict(build_report_service(db).get_report_view(report_id, user_id=user_id))


@router.post("/{report_id}/document-generations")
@policy_auth(resource="report_document", action="generate")
def generate_report_documents(
    report_id: str,
    data: DocumentGenerationRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return document_generation_result_to_dict(build_report_service(db).generate_documents(
        report_id=report_id,
        user_id=user_id,
        formats=data.formats,
        pdf_source=data.pdfSource,
        theme=data.theme,
        strict_validation=data.strictValidation,
        regenerate_if_exists=data.regenerateIfExists,
    ))


@router.get("/{report_id}/documents/{document_id}/download")
@policy_auth(resource="report_document", action="download")
def download_report_document(
    report_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    report = build_report_service(db).get_report_view(report_id, user_id=user_id)

    documents = report.answer.documents
    if not any(item.id == document_id for item in documents):
        raise NotFoundError("Document not found")

    try:
        resolved = build_report_service(db).resolve_download(
            report_id=report_id,
            document_id=document_id,
            user_id=user_id,
        )
    except FileNotFoundError as exc:
        raise NotFoundError(
            "Document file not found",
            error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING,
        ) from exc
    except ValidationError as exc:
        if str(exc) == "Document file not found":
            raise NotFoundError(
                "Document file not found",
                error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING,
            ) from exc
        raise

    return FileResponse(
        path=resolved.absolute_path,
        filename=resolved.document.file_name or f"{document_id}.md",
        media_type=resolved.document.mime_type or "application/octet-stream",
    )

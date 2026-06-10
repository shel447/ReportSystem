from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from runtime.server import router
from tornado.web import RequestHandler

from ..contexts.report.application.generation_models import document_generation_result_to_dict, report_view_to_dict
from ..shared.kernel.authenticated import authenticated
from ..shared.kernel.errors import ErrorCode, NotFoundError, ValidationError
from .common import parse_body, required_query, user_id

PRIVILEGE = ["dte.bi.chat.edit"]


class DocumentGenerationRequest(BaseModel):
    formats: list[str]
    pdfSource: str | None = None
    theme: str = "default"
    strictValidation: bool = True
    regenerateIfExists: bool = False


class ReportController:
    def __init__(self, server) -> None:
        self.server = server

    @router.GET("/rest/chatbi/v1/reports/detail", user_handler=True)
    @authenticated(origin_url="/rest/chatbi/v1/reports/detail", privilege=PRIVILEGE)
    async def get_report(self, req: RequestHandler, **query):
        report_id = required_query(req, query, "reportId")
        def action():
            with self.server.report_service_scope() as service:
                return report_view_to_dict(service.get_report_view(report_id, user_id=user_id(req)))
        return await self.server.run_blocking(action)

    @router.POST("/rest/chatbi/v1/reports/document-generations", user_handler=True, use_body=True)
    @authenticated(origin_url="/rest/chatbi/v1/reports/document-generations", privilege=PRIVILEGE)
    async def generate_documents(self, req: RequestHandler, body, **query):
        report_id = required_query(req, query, "reportId")
        data = parse_body(body, DocumentGenerationRequest)
        def action():
            with self.server.report_service_scope() as service:
                return document_generation_result_to_dict(service.generate_documents(
                    report_id=report_id,
                    user_id=user_id(req),
                    formats=data.formats,
                    pdf_source=data.pdfSource,
                    theme=data.theme,
                    strict_validation=data.strictValidation,
                    regenerate_if_exists=data.regenerateIfExists,
                ))
        return await self.server.run_blocking(action)

    @router.GET("/rest/chatbi/v1/reports/documents/download", user_handler=True)
    @authenticated(origin_url="/rest/chatbi/v1/reports/documents/download", privilege=PRIVILEGE)
    async def download_document(self, req: RequestHandler, **query):
        report_id = required_query(req, query, "reportId")
        document_id = required_query(req, query, "documentId")
        def action():
            with self.server.report_service_scope() as service:
                report = service.get_report_view(report_id, user_id=user_id(req))
                if not any(item.id == document_id for item in report.answer.documents):
                    raise NotFoundError("Document not found")
                try:
                    return service.resolve_download(report_id=report_id, document_id=document_id, user_id=user_id(req))
                except FileNotFoundError as exc:
                    raise NotFoundError("Document file not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING) from exc
                except ValidationError as exc:
                    if str(exc) == "Document file not found":
                        raise NotFoundError("Document file not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING) from exc
                    raise
        resolved = await self.server.run_blocking(action)
        path = Path(resolved.absolute_path)
        if not path.is_file():
            raise NotFoundError("Document file not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING)
        req.set_header("Content-Type", resolved.document.mime_type or "application/octet-stream")
        req.set_header("Content-Disposition", f'attachment; filename="{resolved.document.file_name or document_id}"')
        req.finish(path.read_bytes())

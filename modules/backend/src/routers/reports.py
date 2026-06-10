from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..contexts.report.application.generation_models import document_generation_result_to_dict, report_view_to_dict
from ..shared.kernel.errors import ErrorCode, NotFoundError, ValidationError
from ..shared.kernel.policy_auth import policy_auth
from ..web.base import BusinessHandler


class DocumentGenerationRequest(BaseModel):
    formats: list[str]
    pdfSource: str | None = None
    theme: str = "default"
    strictValidation: bool = True
    regenerateIfExists: bool = False


class ReportHandler(BusinessHandler):
    @policy_auth(resource="report", action="read")
    async def get(self, report_id: str):
        def action():
            with self.container.report_service_scope() as service:
                return report_view_to_dict(service.get_report_view(report_id, user_id=self.user_id))
        self.write_json(await self.run_blocking(action))


class ReportDocumentGenerationHandler(BusinessHandler):
    @policy_auth(resource="report_document", action="generate")
    async def post(self, report_id: str):
        data = self.parse_json(DocumentGenerationRequest)
        def action():
            with self.container.report_service_scope() as service:
                return document_generation_result_to_dict(service.generate_documents(
                    report_id=report_id,
                    user_id=self.user_id,
                    formats=data.formats,
                    pdf_source=data.pdfSource,
                    theme=data.theme,
                    strict_validation=data.strictValidation,
                    regenerate_if_exists=data.regenerateIfExists,
                ))
        self.write_json(await self.run_blocking(action))


class ReportDocumentDownloadHandler(BusinessHandler):
    @policy_auth(resource="report_document", action="download")
    async def get(self, report_id: str, document_id: str):
        def action():
            with self.container.report_service_scope() as service:
                report = service.get_report_view(report_id, user_id=self.user_id)
                if not any(item.id == document_id for item in report.answer.documents):
                    raise NotFoundError("Document not found")
                try:
                    return service.resolve_download(report_id=report_id, document_id=document_id, user_id=self.user_id)
                except FileNotFoundError as exc:
                    raise NotFoundError("Document file not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING) from exc
                except ValidationError as exc:
                    if str(exc) == "Document file not found":
                        raise NotFoundError("Document file not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING) from exc
                    raise
        resolved = await self.run_blocking(action)
        path = Path(resolved.absolute_path)
        if not path.is_file():
            raise NotFoundError("Document file not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING)
        self.set_header("Content-Type", resolved.document.mime_type or "application/octet-stream")
        self.set_header("Content-Disposition", f'attachment; filename="{resolved.document.file_name or document_id}"')
        self.finish(path.read_bytes())


ROUTES = [
    (r"/rest/chatbi/v1/reports/([^/]+)/document-generations", ReportDocumentGenerationHandler),
    (r"/rest/chatbi/v1/reports/([^/]+)/documents/([^/]+)/download", ReportDocumentDownloadHandler),
    (r"/rest/chatbi/v1/reports/([^/]+)", ReportHandler),
]

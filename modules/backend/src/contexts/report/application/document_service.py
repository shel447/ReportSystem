"""报告文档生成、列表与下载应用服务。"""

from __future__ import annotations

import hashlib
import json

from ....shared.kernel.errors import ErrorCode, NotFoundError, ValidationError
from .generation_models import DocumentGenerationJobView, DocumentGenerationResult, DocumentView, DownloadResolution


class ReportDocumentService:
    """拥有 report-scoped 文档生命周期。"""

    def __init__(self, *, report_reader, document_repository, export_job_repository, document_gateway) -> None:
        self.report_reader = report_reader
        self.document_repository = document_repository
        self.export_job_repository = export_job_repository
        self.document_gateway = document_gateway

    def list_documents(self, *, report_id: str) -> list[DocumentView]:
        return [self.document_gateway.serialize_document(item) for item in self.document_repository.list_by_report(report_id)]

    def generate_documents(
        self,
        *,
        report_id: str,
        user_id: str,
        formats: list[str],
        pdf_source: str | None,
        theme: str,
        strict_validation: bool,
        regenerate_if_exists: bool,
    ) -> DocumentGenerationResult:
        normalized_formats = [str(item or "").strip().lower() for item in formats]
        if "pdf" in normalized_formats:
            raise ValidationError(
                "PDF export is not available yet",
                error_code=ErrorCode.REPORT_DOCUMENT_PDF_NOT_AVAILABLE,
                category="capability",
            )
        unsupported_formats = sorted(set(normalized_formats) - {"word", "ppt", "markdown"})
        if unsupported_formats:
            raise ValidationError(
                f"Unsupported document format: {unsupported_formats[0]}",
                error_code="chatbi.report.document.format_unsupported",
                category="param",
            )
        report = self.report_reader.get_report_instance(report_id, user_id=user_id).report
        existing = self.document_repository.list_by_report(report_id)
        reusable = [] if regenerate_if_exists else [self.document_gateway.serialize_document(item) for item in existing]
        jobs: list[DocumentGenerationJobView] = []
        documents: list[DocumentView] = []
        request_hash = hashlib.sha1(
            json.dumps(
                {
                    "formats": normalized_formats,
                    "pdfSource": pdf_source,
                    "theme": theme,
                    "strictValidation": strict_validation,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        dependency_job_id = None
        for format_name in normalized_formats:
            job = self.export_job_repository.create(
                report_instance_id=report_id,
                user_id=user_id,
                current_format=format_name,
                status="queued",
                dependency_job_id=dependency_job_id,
                exporter_backend="java_office_exporter" if format_name in {"word", "ppt", "pdf"} else "local_markdown",
                request_payload_hash=request_hash,
            )
            jobs.append(
                DocumentGenerationJobView(
                    job_id=job.id,
                    format=format_name,
                    status="queued" if dependency_job_id is None else "blocked_by_dependency",
                    depends_on=dependency_job_id,
                )
            )
            artifact = self.document_gateway.generate_document(
                report=report,
                report_id=report_id,
                format_name=format_name,
                theme=theme,
                strict_validation=strict_validation,
                pdf_source=pdf_source,
            )
            document = self.document_repository.create(
                report_instance_id=report_id,
                artifact_kind=format_name,
                source_format=pdf_source if format_name == "pdf" else None,
                generation_mode="sync",
                mime_type=artifact.mime_type,
                storage_key=artifact.storage_key,
                status="ready",
            )
            documents.append(self.document_gateway.serialize_document(document))
            dependency_job_id = job.id if format_name in {"word", "ppt"} else dependency_job_id
        return DocumentGenerationResult(report_id=report_id, jobs=jobs, documents=reusable + documents)

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> DownloadResolution:
        self.report_reader.get_report_instance(report_id, user_id=user_id)
        document = self.document_repository.get_for_report(report_id, document_id)
        if document is None:
            raise NotFoundError("Document not found", error_code=ErrorCode.REPORT_DOCUMENT_FILE_MISSING)
        return self.document_gateway.resolve_download(document)

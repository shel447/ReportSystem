"""报告文档生成与下载应用服务。"""

from __future__ import annotations

from .generation_models import DocumentGenerationResult, DownloadResolution
from .generation_service import ReportGenerationService


class ReportDocumentService:
    """对外提供 report-scoped 文档生命周期能力。"""

    def __init__(self, *, generation_service: ReportGenerationService) -> None:
        self.generation_service = generation_service

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
        return self.generation_service.generate_documents(
            report_id=report_id,
            user_id=user_id,
            formats=formats,
            pdf_source=pdf_source,
            theme=theme,
            strict_validation=strict_validation,
            regenerate_if_exists=regenerate_if_exists,
        )

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> DownloadResolution:
        return self.generation_service.resolve_download(report_id=report_id, document_id=document_id, user_id=user_id)

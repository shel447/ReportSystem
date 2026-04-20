"""报告运行时应用层使用的文档与导出适配器。"""

from __future__ import annotations

import json
from pathlib import Path

from ....infrastructure.exporter.java_office import JavaOfficeExporterGateway
from ..application.models import DownloadResolution, DocumentView, GeneratedArtifact, document_view_from_artifact
from ..domain.models import DocumentArtifact, ReportDsl, report_dsl_to_dict

DOCUMENTS_DIR = Path(__file__).resolve().parent / "generated_documents"
MIME_TYPES = {
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
    "markdown": "text/markdown; charset=utf-8",
}
EXTENSIONS = {
    "word": ".docx",
    "ppt": ".pptx",
    "pdf": ".pdf",
    "markdown": ".md",
}


class ReportDocumentGateway:
    """隔离文稿导出与办公文档导出后端的文档适配器。"""

    def __init__(self, *, office_exporter: JavaOfficeExporterGateway | None = None) -> None:
        self.office_exporter = office_exporter or JavaOfficeExporterGateway()

    def generate_document(
        self,
        *,
        report: ReportDsl,
        report_id: str,
        format_name: str,
        theme: str,
        strict_validation: bool = True,
        pdf_source: str | None = None,
    ) -> GeneratedArtifact:
        # 文稿格式直接由已冻结的报告结构在本地生成；办公文档格式则委托给
        # 导出服务，以便把渲染细节隔离在应用层之外。
        normalized_format = str(format_name or "").strip().lower()
        if normalized_format == "markdown":
            return self._generate_markdown(report=report, report_id=report_id, theme=theme)
        if normalized_format not in {"word", "ppt", "pdf"}:
            raise ValueError(f"Unsupported document format: {format_name}")
        return self.office_exporter.export(
            report=report,
            report_id=report_id,
            format_name=normalized_format,
            theme=theme,
            strict_validation=strict_validation,
            pdf_source=pdf_source,
        )

    def resolve_download(self, document: DocumentArtifact) -> DownloadResolution:
        path = Path(document.storage_key)
        if not path.exists():
            raise FileNotFoundError("Document file not found")
        return DownloadResolution(document=self.serialize_document(document), absolute_path=str(path))

    def serialize_document(self, document: DocumentArtifact) -> DocumentView:
        return document_view_from_artifact(document)

    def _generate_markdown(self, *, report: ReportDsl, report_id: str, theme: str) -> GeneratedArtifact:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"{report_id}-markdown{EXTENSIONS['markdown']}"
        file_path = DOCUMENTS_DIR / file_name
        file_path.write_text(_serialize_report_payload(report, theme=theme, format_name="markdown"), encoding="utf-8")
        return GeneratedArtifact(
            file_name=file_name,
            storage_key=str(file_path),
            mime_type=MIME_TYPES["markdown"],
        )


def _serialize_report_payload(report: ReportDsl, *, theme: str, format_name: str) -> str:
    """生成确定性的文稿导出结果，用于调试和轻量分发。"""
    return "\n".join(
        [
            f"# Report Export ({format_name})",
            "",
            f"- theme: {theme}",
            "",
            "```json",
            json.dumps(report_dsl_to_dict(report), ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )

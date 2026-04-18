from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ....infrastructure.exporter.java_office import JavaOfficeExporterGateway
from ..domain.models import DocumentArtifact

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
    def __init__(self, *, office_exporter: JavaOfficeExporterGateway | None = None) -> None:
        self.office_exporter = office_exporter or JavaOfficeExporterGateway()

    def generate_document(
        self,
        *,
        report: dict[str, Any],
        report_id: str,
        format_name: str,
        theme: str,
        strict_validation: bool = True,
        pdf_source: str | None = None,
    ) -> dict[str, Any]:
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

    def resolve_download(self, document: DocumentArtifact) -> tuple[dict[str, Any], str]:
        path = Path(document.storage_key)
        if not path.exists():
            raise FileNotFoundError("Document file not found")
        return self.serialize_document(document), str(path)

    def serialize_document(self, document: DocumentArtifact) -> dict[str, Any]:
        return {
            "id": document.id,
            "format": document.artifact_kind,
            "mimeType": document.mime_type,
            "fileName": Path(document.storage_key).name,
            "downloadUrl": f"/rest/chatbi/v1/reports/{document.report_instance_id}/documents/{document.id}/download",
            "status": document.status,
        }

    def _generate_markdown(self, *, report: dict[str, Any], report_id: str, theme: str) -> dict[str, Any]:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"{report_id}-markdown{EXTENSIONS['markdown']}"
        file_path = DOCUMENTS_DIR / file_name
        file_path.write_text(_serialize_report_payload(report, theme=theme, format_name="markdown"), encoding="utf-8")
        return {
            "fileName": file_name,
            "storageKey": str(file_path),
            "mimeType": MIME_TYPES["markdown"],
        }


def _serialize_report_payload(report: dict[str, Any], *, theme: str, format_name: str) -> str:
    return "\n".join(
        [
            f"# Report Export ({format_name})",
            "",
            f"- theme: {theme}",
            "",
            "```json",
            json.dumps(report, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )

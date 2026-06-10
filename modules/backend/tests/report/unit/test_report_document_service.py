from pathlib import Path
from types import SimpleNamespace

import pytest

from src.contexts.report.application.document_service import ReportDocumentService
from src.contexts.report.application.generation_models import DocumentView, DownloadResolution, GeneratedArtifact
from src.contexts.report.domain.generation_models import DocumentArtifact
from src.shared.kernel.errors import ValidationError
from tests.support.builders import build_flow_report


class _DocumentRepository:
    def __init__(self):
        self.rows = []

    def list_by_report(self, report_id):
        return [item for item in self.rows if item.report_instance_id == report_id]

    def create(self, **kwargs):
        artifact = DocumentArtifact(id=f"doc_{len(self.rows) + 1}", **kwargs)
        self.rows.append(artifact)
        return artifact

    def get_for_report(self, report_id, document_id):
        return next((item for item in self.rows if item.report_instance_id == report_id and item.id == document_id), None)


class _DocumentGateway:
    def generate_document(self, **kwargs):
        return GeneratedArtifact(file_name="report.md", storage_key="/tmp/report.md", mime_type="text/markdown")

    def serialize_document(self, document):
        return DocumentView(
            id=document.id,
            format=document.artifact_kind,
            mime_type=document.mime_type,
            file_name=Path(document.storage_key).name,
            download_url=f"/rest/chatbi/v1/reports/documents/download?reportId={document.report_instance_id}&documentId={document.id}",
            status=document.status,
        )

    def resolve_download(self, document):
        return DownloadResolution(document=self.serialize_document(document), absolute_path=document.storage_key)


def _service():
    repository = _DocumentRepository()
    jobs = []
    return (
        ReportDocumentService(
            report_reader=SimpleNamespace(
                get_report_instance=lambda report_id, user_id: SimpleNamespace(report=build_flow_report())
            ),
            document_repository=repository,
            export_job_repository=SimpleNamespace(
                create=lambda **kwargs: jobs.append(kwargs) or SimpleNamespace(id=f"job_{len(jobs)}")
            ),
            document_gateway=_DocumentGateway(),
        ),
        repository,
        jobs,
    )


def test_document_service_generates_tracks_lists_and_downloads_report_document():
    service, repository, jobs = _service()

    result = service.generate_documents(
        report_id="rpt_001",
        user_id="default",
        formats=["markdown"],
        pdf_source=None,
        theme="default",
        strict_validation=False,
        regenerate_if_exists=False,
    )

    assert len(jobs) == 1
    assert result.documents[0].format == "markdown"
    assert service.list_documents(report_id="rpt_001")[0].id == repository.rows[0].id
    assert service.resolve_download(report_id="rpt_001", document_id=repository.rows[0].id, user_id="default").absolute_path == "/tmp/report.md"


def test_document_service_rejects_pdf_before_creating_job():
    service, _, jobs = _service()
    with pytest.raises(ValidationError, match="PDF export is not available yet"):
        service.generate_documents(
            report_id="rpt_001",
            user_id="default",
            formats=["pdf"],
            pdf_source="word",
            theme="default",
            strict_validation=False,
            regenerate_if_exists=False,
        )
    assert jobs == []

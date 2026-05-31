from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.contexts.report.application.generation_models import (
    DocumentGenerationJobView,
    DocumentGenerationResult,
    DocumentView,
)
from src.contexts.report.infrastructure.documents import ReportDocumentGateway
from src.infrastructure.exporter.java_office import JavaOfficeExporterGateway
from src.infrastructure.persistence.database import get_db
from src.routers.reports import router as reports_router
from tests.support.builders import build_flow_report, build_paged_report


def _document_view(format_name, artifact):
    return DocumentView(
        id=f"doc_{format_name}",
        format=format_name,
        mime_type=artifact.mime_type,
        file_name=artifact.file_name,
        download_url=f"/reports/rpt_e2e_{format_name}/documents/doc_{format_name}/download",
        status="ready",
    )


@pytest.mark.exporter_e2e
@pytest.mark.parametrize(
    ("format_name", "builder", "required_entry"),
    [
        ("word", build_flow_report, "word/document.xml"),
        ("ppt", build_paged_report, "ppt/presentation.xml"),
    ],
)
def test_report_document_generation_api_invokes_real_java_cli(format_name, builder, required_entry):
    artifacts = []

    def generate_documents(**kwargs):
        artifact = JavaOfficeExporterGateway().export(
            report=builder(),
            report_id=kwargs["report_id"],
            format_name=format_name,
            theme=kwargs["theme"],
            strict_validation=kwargs["strict_validation"],
            pdf_source=kwargs["pdf_source"],
        )
        artifacts.append(artifact)
        return DocumentGenerationResult(
            report_id=kwargs["report_id"],
            jobs=[DocumentGenerationJobView(job_id=f"job_{format_name}", format=format_name, status="queued")],
            documents=[_document_view(format_name, artifact)],
        )

    app = FastAPI()
    app.include_router(reports_router, prefix="/rest/chatbi/v1")
    app.dependency_overrides[get_db] = lambda: object()
    with patch("src.routers.reports.build_report_service", return_value=type("Service", (), {"generate_documents": staticmethod(generate_documents)})()):
        response = TestClient(app).post(
            f"/rest/chatbi/v1/reports/rpt_e2e_{format_name}/document-generations",
            headers={"X-User-Id": "e2e-user"},
            json={"formats": [format_name], "theme": "default", "strictValidation": False},
        )

    assert response.status_code == 200
    assert response.json()["documents"][0]["format"] == format_name
    output_path = Path(artifacts[0].storage_key)
    assert ".test" in output_path.parts
    assert output_path.exists()
    with ZipFile(output_path) as package:
        assert required_entry in package.namelist()


def test_report_document_generation_api_generates_markdown_in_test_directory():
    artifacts = []

    def generate_documents(**kwargs):
        artifact = ReportDocumentGateway().generate_document(
            report=build_flow_report(),
            report_id=kwargs["report_id"],
            format_name="markdown",
            theme=kwargs["theme"],
        )
        artifacts.append(artifact)
        return DocumentGenerationResult(
            report_id=kwargs["report_id"],
            jobs=[DocumentGenerationJobView(job_id="job_markdown", format="markdown", status="queued")],
            documents=[_document_view("markdown", artifact)],
        )

    app = FastAPI()
    app.include_router(reports_router, prefix="/rest/chatbi/v1")
    app.dependency_overrides[get_db] = lambda: object()
    with patch("src.routers.reports.build_report_service", return_value=type("Service", (), {"generate_documents": staticmethod(generate_documents)})()):
        response = TestClient(app).post(
            "/rest/chatbi/v1/reports/rpt_e2e_markdown/document-generations",
            headers={"X-User-Id": "e2e-user"},
            json={"formats": ["markdown"], "theme": "default"},
        )

    assert response.status_code == 200
    output_path = Path(artifacts[0].storage_key)
    assert ".test" in output_path.parts
    assert output_path.read_text(encoding="utf-8").startswith("# Report Export (markdown)")

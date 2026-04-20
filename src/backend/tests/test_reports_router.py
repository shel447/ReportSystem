import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.contexts.report_runtime.application.models import (
    DocumentView,
    DownloadResolution,
    ReportAnswerView,
    ReportView,
)
from backend.contexts.report_runtime.domain.models import (
    DocumentArtifact,
    ParameterConfirmation,
    ReportBasicInfo,
    ReportDsl,
    ReportLayout,
    TemplateInstance,
    GridDefinition,
)
from backend.contexts.template_catalog.domain.models import ReportTemplate
from backend.infrastructure.persistence.database import get_db
from backend.routers.reports import router as reports_router


def _sample_template_instance():
    return TemplateInstance(
        id="ti_001",
        schema_version="template-instance.vNext-draft",
        template_id="tpl_network_daily",
        template=ReportTemplate(
            id="tpl_network_daily",
            category="network_operations",
            name="网络运行日报",
            description="面向网络运维中心的统一日报模板。",
            schema_version="template.v3",
        ),
        conversation_id="conv_001",
        chat_id="chat_003",
        status="completed",
        capture_stage="report_ready",
        revision=3,
        parameters=[],
        parameter_confirmation=ParameterConfirmation(missing_parameter_ids=[], confirmed=True),
        catalogs=[],
    )


def _sample_report():
    return ReportDsl(
        basic_info=ReportBasicInfo(
            id="rpt_001",
            schema_version="1.0.0",
            mode="published",
            status="Success",
        ),
        catalogs=[],
        layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
    )


class ReportsRouterTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(reports_router, prefix="/rest/chatbi/v1")

        def override_get_db():
            yield object()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def test_get_report_view_returns_formal_report_answer_wrapper(self):
        fake_service = SimpleNamespace(
            get_report_view=lambda report_id, user_id: ReportView(
                report_id=report_id,
                status="available",
                answer_type="REPORT",
                answer=ReportAnswerView(
                    report_id=report_id,
                    status="available",
                    report=_sample_report(),
                    template_instance=_sample_template_instance(),
                    documents=[],
                ),
            )
        )

        with patch("backend.routers.reports.build_report_runtime_service", return_value=fake_service):
            response = self.client.get("/rest/chatbi/v1/reports/rpt_001", headers={"X-User-Id": "default"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reportId"], "rpt_001")
        self.assertEqual(payload["answer"]["templateInstance"]["id"], "ti_001")
        self.assertEqual(payload["answer"]["report"]["basicInfo"]["schemaVersion"], "1.0.0")

    def test_download_report_document_uses_report_scoped_download(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "network-daily.md"
            file_path.write_text("# report\n", encoding="utf-8")
            fake_runtime = SimpleNamespace(
                get_report_view=lambda report_id, user_id: ReportView(
                    report_id=report_id,
                    status="available",
                    answer_type="REPORT",
                    answer=ReportAnswerView(
                        report_id=report_id,
                        status="available",
                        report=_sample_report(),
                        template_instance=_sample_template_instance(),
                        documents=[
                            DocumentView(
                                id="doc_001",
                                format="markdown",
                                mime_type="text/markdown",
                                file_name="network-daily.md",
                                download_url="/rest/chatbi/v1/reports/rpt_001/documents/doc_001/download",
                                status="ready",
                            )
                        ],
                    ),
                )
            )
            fake_document_service = SimpleNamespace(
                resolve_download=lambda report_id, document_id, user_id: DownloadResolution(
                    document=DocumentView(
                        id=document_id,
                        format="markdown",
                        mime_type="text/markdown",
                        file_name="network-daily.md",
                        download_url="/rest/chatbi/v1/reports/rpt_001/documents/doc_001/download",
                        status="ready",
                    ),
                    absolute_path=str(file_path),
                )
            )

            with patch("backend.routers.reports.build_report_runtime_service", return_value=fake_runtime), patch(
                "backend.routers.reports.build_report_document_service", return_value=fake_document_service
            ):
                response = self.client.get(
                    "/rest/chatbi/v1/reports/rpt_001/documents/doc_001/download",
                    headers={"X-User-Id": "default"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.replace("\r\n", "\n"), "# report\n")


if __name__ == "__main__":
    unittest.main()

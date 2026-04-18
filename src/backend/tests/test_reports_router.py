import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.infrastructure.persistence.database import get_db
from backend.routers.reports import router as reports_router


def _sample_template_instance():
    return {
        "id": "ti_001",
        "schemaVersion": "template-instance.vNext-draft",
        "templateId": "tpl_network_daily",
        "template": {
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [],
        },
        "conversationId": "conv_001",
        "chatId": "chat_003",
        "status": "completed",
        "captureStage": "report_ready",
        "revision": 3,
        "parameters": [],
        "parameterConfirmation": {"missingParameterIds": [], "confirmed": True},
        "catalogs": [],
        "createdAt": "2026-04-18T09:00:00Z",
        "updatedAt": "2026-04-18T09:01:00Z",
    }


def _sample_report():
    return {
        "basicInfo": {
            "id": "rpt_001",
            "schemaVersion": "1.0.0",
            "mode": "published",
            "status": "Success",
        },
        "catalogs": [],
        "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
    }


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
            get_report_view=lambda report_id, user_id: {
                "reportId": report_id,
                "status": "available",
                "answerType": "REPORT",
                "answer": {
                    "reportId": report_id,
                    "status": "available",
                    "report": _sample_report(),
                    "templateInstance": _sample_template_instance(),
                    "documents": [],
                },
            }
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
                get_report_view=lambda report_id, user_id: {
                    "reportId": report_id,
                    "status": "available",
                    "answerType": "REPORT",
                    "answer": {
                        "reportId": report_id,
                        "status": "available",
                        "report": _sample_report(),
                        "templateInstance": _sample_template_instance(),
                        "documents": [{"id": "doc_001", "fileName": "network-daily.md"}],
                    },
                }
            )
            fake_document_service = SimpleNamespace(
                resolve_download=lambda report_id, document_id, user_id: (
                    {"id": document_id, "fileName": "network-daily.md", "mimeType": "text/markdown"},
                    str(file_path),
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

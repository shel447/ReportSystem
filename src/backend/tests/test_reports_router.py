import unittest
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.infrastructure.persistence.database import Base, get_db
from backend.infrastructure.persistence.models import ReportInstance, ReportTemplate, TemplateInstance
from backend.routers.reports import router as reports_router


class ReportsRouterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = testing_session_local()

        self.db.add(
            ReportTemplate(
                id="tpl-1",
                name="运维日报模板",
                description="模板描述",
                category="ops_daily",
                parameters=[],
                sections=[],
            )
        )
        self.db.add(
            ReportInstance(
                instance_id="rpt-1",
                template_id="tpl-1",
                user_id="default",
                status="completed",
                input_params={"report_date": "2026-04-16"},
                outline_content=[],
            )
        )
        self.db.add(
            TemplateInstance(
                template_instance_id="ti-1",
                template_id="tpl-1",
                template_name="运维日报模板",
                session_id="conv-1",
                capture_stage="generation_baseline",
                report_instance_id="rpt-1",
                content={
                    "schema_version": "ti.v1.0",
                    "base_template": {
                        "id": "tpl-1",
                        "name": "运维日报模板",
                        "category": "ops_daily",
                        "description": "模板描述",
                    },
                    "instance_meta": {"status": "completed", "revision": 3},
                    "resolved_view": {
                        "parameters": {
                            "report_date": {
                                "display": "2026-04-16",
                                "value": "2026-04-16",
                                "query": "2026-04-16",
                            }
                        },
                        "outline": [],
                        "sections": [],
                    },
                    "generated_content": {
                        "sections": [{"node_id": "n1", "title": "总览", "content": "ok"}],
                        "documents": [{
                            "document_id": "doc-1",
                            "format": "md",
                            "download_url": "/rest/chatbi/v1/reports/rpt-1/documents/doc-1/download",
                        }],
                    },
                    "fragments": {},
                },
            )
        )
        self.db.commit()

        app = FastAPI()
        app.include_router(reports_router, prefix="/rest/chatbi/v1")

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()

    def test_get_report_view_returns_template_instance_and_generated_content(self):
        response = self.client.get("/rest/chatbi/v1/reports/rpt-1", headers={"X-User-Id": "default"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reportId"], "rpt-1")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["template_instance"]["id"], "ti-1")
        self.assertEqual(payload["generated_content"]["sections"][0]["title"], "总览")

    def test_get_report_view_not_found_returns_404(self):
        response = self.client.get("/rest/chatbi/v1/reports/rpt-missing", headers={"X-User-Id": "default"})
        self.assertEqual(response.status_code, 404)

    def test_download_report_document_uses_report_scoped_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "report.md"
            file_path.write_text("# report\n", encoding="utf-8")
            from backend.infrastructure.persistence.models import ReportDocument

            self.db.add(
                ReportDocument(
                    document_id="doc-1",
                    instance_id="rpt-1",
                    template_id="tpl-1",
                    format="md",
                    file_path=str(file_path),
                    file_size=file_path.stat().st_size,
                    status="ready",
                    version=1,
                )
            )
            self.db.commit()

            response = self.client.get(
                "/rest/chatbi/v1/reports/rpt-1/documents/doc-1/download",
                headers={"X-User-Id": "default"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.replace("\r\n", "\n"), "# report\n")


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.contexts.template_catalog.application.services import TemplateCatalogService
from backend.contexts.template_catalog.domain.models import ReportTemplate
from backend.contexts.template_catalog.infrastructure.repositories import SqlAlchemyTemplateCatalogRepository
from backend.contexts.template_catalog.infrastructure.repositories import TemplateSchemaGateway
from backend.infrastructure.persistence.database import Base
from backend.shared.kernel.errors import ValidationError


class _FakeRepository:
    def __init__(self, templates=None):
        self.templates = templates or []

    def list_all(self):
        return list(self.templates)


class _FakeMatcher:
    def mark_stale(self, *_args, **_kwargs):
        return None

    def delete_index(self, *_args, **_kwargs):
        return None

    def match(self, *_args, **_kwargs):
        return {}


def _build_service(existing_templates=None):
    return TemplateCatalogService(
        repository=_FakeRepository(existing_templates),
        matcher=_FakeMatcher(),
        schema_gateway=TemplateSchemaGateway(),
    )


class TemplateCatalogImportPreviewTests(unittest.TestCase):
    def test_preview_import_template_normalizes_system_export_payload(self):
        service = _build_service()

        payload = {
            "id": "inspection_report",
            "name": "设备巡检报告",
            "description": "巡检模板",
            "category": "巡检",
            "parameters": [{"id": "date", "label": "日期", "required": True, "input_type": "date"}],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "模板内容"}}}],
        }

        result = service.preview_import_template(payload, filename="inspection.json")

        self.assertEqual(result["source_kind"], "system_export")
        self.assertEqual(result["normalized_template"]["id"], "inspection_report")
        self.assertEqual(result["normalized_template"]["name"], "设备巡检报告")
        self.assertEqual(result["normalized_template"]["sections"][0]["title"], "概览")
        self.assertEqual(result["conflict"]["status"], "none")
        self.assertEqual(result["conflict"]["default_action"], "create_copy")

    def test_preview_import_template_normalizes_external_report_template_payload_with_defaults(self):
        service = _build_service()

        payload = {
            "id": "device_health_report",
            "name": "设备健康报告",
            "category": "设备健康评估",
            "parameters": [{"id": "date", "label": "日期", "required": True, "input_type": "date"}],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
        }

        result = service.preview_import_template(payload, filename="external.json")

        self.assertEqual(result["source_kind"], "external_report_template")
        self.assertEqual(result["normalized_template"]["description"], "")
        self.assertEqual(result["normalized_template"]["id"], "device_health_report")

    def test_preview_import_template_detects_single_template_id_conflict(self):
        existing = ReportTemplate(
            id="tpl_1",
            name="已有模板",
            description="",
            category="巡检",
        )
        service = _build_service([existing])

        payload = {
            "id": "tpl_1",
            "name": "导入模板",
            "description": "",
            "category": "巡检",
            "parameters": [],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
        }

        result = service.preview_import_template(payload)

        self.assertEqual(result["conflict"]["status"], "single_match")
        self.assertTrue(result["conflict"]["overwrite_supported"])
        self.assertEqual(result["conflict"]["matched_templates"][0]["template_id"], "tpl_1")

    def test_preview_import_template_detects_single_name_conflict(self):
        existing = ReportTemplate(
            id="tpl-1",
            name="设备巡检报告",
            description="",
            category="巡检",
        )
        service = _build_service([existing])

        payload = {
            "id": "inspection_report",
            "name": "设备巡检报告",
            "description": "",
            "category": "巡检",
            "parameters": [],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
        }

        result = service.preview_import_template(payload)

        self.assertEqual(result["conflict"]["status"], "single_match")
        self.assertTrue(result["conflict"]["overwrite_supported"])
        self.assertEqual(result["conflict"]["matched_templates"][0]["name"], "设备巡检报告")

    def test_preview_import_template_detects_multiple_name_conflicts(self):
        existing_templates = [
            ReportTemplate(id="tpl-1", category="", name="设备巡检报告"),
            ReportTemplate(id="tpl-2", category="", name="设备巡检报告"),
        ]
        service = _build_service(existing_templates)

        payload = {
            "id": "inspection_report",
            "name": "设备巡检报告",
            "description": "",
            "category": "巡检",
            "parameters": [],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
        }

        result = service.preview_import_template(payload)

        self.assertEqual(result["conflict"]["status"], "multiple_matches")
        self.assertFalse(result["conflict"]["overwrite_supported"])
        self.assertEqual(len(result["conflict"]["matched_templates"]), 2)

    def test_preview_import_template_rejects_unsupported_payload(self):
        service = _build_service()

        with self.assertRaises(ValidationError):
            service.preview_import_template({"foo": "bar"})


class TemplateCatalogRepositoryTests(unittest.TestCase):
    def test_sqlalchemy_repository_create_accepts_explicit_id(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db = testing_session_local()
        try:
            repository = SqlAlchemyTemplateCatalogRepository(db)

            created = repository.create(
                {
                    "id": "tpl_repo_create",
                    "name": "仓储模板",
                    "description": "用于回归测试",
                    "category": "ops_daily",
                    "parameters": [],
                    "sections": [],
                }
            )

            self.assertEqual(created.id, "tpl_repo_create")
            self.assertEqual(created.category, "ops_daily")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

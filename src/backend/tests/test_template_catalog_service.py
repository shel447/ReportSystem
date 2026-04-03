import unittest

from backend.contexts.template_catalog.application.services import TemplateCatalogService
from backend.contexts.template_catalog.domain.models import ReportTemplate
from backend.contexts.template_catalog.infrastructure.repositories import TemplateSchemaGateway
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
            "name": "设备巡检报告",
            "description": "巡检模板",
            "report_type": "daily",
            "scenario": "集团",
            "type": "巡检",
            "scene": "总部",
            "match_keywords": ["巡检"],
            "parameters": [{"id": "date", "label": "日期", "required": True, "input_type": "date"}],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "模板内容"}}}],
            "schema_version": "v2.0",
            "output_formats": ["md"],
        }

        result = service.preview_import_template(payload, filename="inspection.json")

        self.assertEqual(result["source_kind"], "system_export")
        self.assertEqual(result["normalized_template"]["name"], "设备巡检报告")
        self.assertEqual(result["normalized_template"]["sections"][0]["title"], "概览")
        self.assertEqual(result["conflict"]["status"], "none")
        self.assertEqual(result["conflict"]["default_action"], "create_copy")

    def test_preview_import_template_normalizes_external_report_template_payload_with_defaults(self):
        service = _build_service()

        payload = {
            "id": "device_health_report",
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [{"id": "date", "label": "日期", "required": True, "input_type": "date"}],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
        }

        result = service.preview_import_template(payload, filename="external.json")

        self.assertEqual(result["source_kind"], "external_report_template")
        self.assertEqual(result["normalized_template"]["report_type"], "daily")
        self.assertEqual(result["normalized_template"]["description"], "")
        self.assertEqual(result["normalized_template"]["match_keywords"], [])
        self.assertEqual(result["normalized_template"]["output_formats"], ["md"])
        self.assertEqual(result["normalized_template"]["schema_version"], "v2.0")

    def test_preview_import_template_detects_single_template_id_conflict(self):
        existing = ReportTemplate(
            template_id="tpl-1",
            name="已有模板",
            description="",
            report_type="daily",
            scenario="",
            template_type="巡检",
            scene="总部",
        )
        service = _build_service([existing])

        payload = {
            "template_id": "tpl-1",
            "name": "导入模板",
            "description": "",
            "report_type": "daily",
            "scenario": "",
            "type": "巡检",
            "scene": "总部",
            "match_keywords": [],
            "parameters": [],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
            "schema_version": "v2.0",
            "output_formats": ["md"],
        }

        result = service.preview_import_template(payload)

        self.assertEqual(result["conflict"]["status"], "single_match")
        self.assertTrue(result["conflict"]["overwrite_supported"])
        self.assertEqual(result["conflict"]["matched_templates"][0]["template_id"], "tpl-1")

    def test_preview_import_template_detects_single_name_conflict(self):
        existing = ReportTemplate(
            template_id="tpl-1",
            name="设备巡检报告",
            description="",
            report_type="daily",
            scenario="",
            template_type="巡检",
            scene="总部",
        )
        service = _build_service([existing])

        payload = {
            "name": "设备巡检报告",
            "description": "",
            "report_type": "daily",
            "scenario": "",
            "type": "巡检",
            "scene": "总部",
            "match_keywords": [],
            "parameters": [],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
            "schema_version": "v2.0",
            "output_formats": ["md"],
        }

        result = service.preview_import_template(payload)

        self.assertEqual(result["conflict"]["status"], "single_match")
        self.assertTrue(result["conflict"]["overwrite_supported"])
        self.assertEqual(result["conflict"]["matched_templates"][0]["name"], "设备巡检报告")

    def test_preview_import_template_detects_multiple_name_conflicts(self):
        existing_templates = [
            ReportTemplate(template_id="tpl-1", name="设备巡检报告"),
            ReportTemplate(template_id="tpl-2", name="设备巡检报告"),
        ]
        service = _build_service(existing_templates)

        payload = {
            "name": "设备巡检报告",
            "description": "",
            "report_type": "daily",
            "scenario": "",
            "type": "巡检",
            "scene": "总部",
            "match_keywords": [],
            "parameters": [],
            "sections": [{"title": "概览", "content": {"presentation": {"type": "text", "template": "内容"}}}],
            "schema_version": "v2.0",
            "output_formats": ["md"],
        }

        result = service.preview_import_template(payload)

        self.assertEqual(result["conflict"]["status"], "multiple_matches")
        self.assertFalse(result["conflict"]["overwrite_supported"])
        self.assertEqual(len(result["conflict"]["matched_templates"]), 2)

    def test_preview_import_template_rejects_unsupported_payload(self):
        service = _build_service()

        with self.assertRaises(ValidationError):
            service.preview_import_template({"foo": "bar"})


if __name__ == "__main__":
    unittest.main()

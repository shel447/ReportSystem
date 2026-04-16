import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.routers.templates import (
    TemplateImportPreviewRequest,
    _clean_template_payload,
    export_template_definition,
    list_templates,
    preview_import_template,
)
from backend.shared.kernel.errors import ValidationError


class TemplatesRouterTests(unittest.TestCase):
    def test_list_templates_includes_v2_summary_fields(self):
        template = SimpleNamespace(
            template_id="tpl-1",
            name="设备巡检报告",
            description="巡检模板",
            category="巡检",
            created_at="2026-03-19T00:00:00",
            parameters=[{"id": "date"}, {"id": "devices"}],
            sections=[{"title": "概览"}, {"title": "详情"}],
        )

        class FakeQuery:
            def all(self):
                return [template]

        class FakeDb:
            def query(self, _model):
                return FakeQuery()

        payload = list_templates(db=FakeDb())

        self.assertEqual(payload[0]["category"], "巡检")
        self.assertEqual(payload[0]["parameter_count"], 2)
        self.assertEqual(payload[0]["top_level_section_count"], 2)
        self.assertNotIn("report_type", payload[0])
        self.assertNotIn("schema_version", payload[0])

    def test_clean_template_payload_validates_and_normalizes_v2_template(self):
        payload = {
            "id": "device_health_report",
            "name": "设备健康报告",
            "category": "设备健康评估",
            "description": "模板描述",
            "parameters": [],
            "sections": [
                {
                    "title": "概述",
                    "content": {
                        "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        cleaned = _clean_template_payload(payload)

        self.assertEqual(cleaned["id"], "device_health_report")
        self.assertEqual(cleaned["category"], "设备健康评估")
        self.assertEqual(cleaned["sections"][0]["content"]["datasets"][0]["id"], "ds_main")

    def test_export_template_definition_returns_portable_json_attachment(self):
        template = SimpleNamespace(
            template_id="tpl-1",
            name="设备巡检报告",
            description="巡检模板",
            category="巡检",
            parameters=[{"id": "date", "label": "日期", "required": True, "input_type": "date"}],
            sections=[{"title": "概览", "content": {"presentation": {"type": "text", "template": "周期 {date}"}}}],
            created_at="2026-03-19T00:00:00",
            version="1.0",
        )

        class FakeQuery:
            def __init__(self, value):
                self.value = value

            def filter(self, *_args, **_kwargs):
                return self

            def first(self):
                return self.value

        class FakeDb:
            def query(self, _model):
                return FakeQuery(template)

        response = export_template_definition("tpl-1", db=FakeDb())

        self.assertEqual(response.media_type, "application/json")
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn('filename*=', response.headers["content-disposition"])
        self.assertIn("%E8%AE%BE%E5%A4%87%E5%B7%A1%E6%A3%80%E6%8A%A5%E5%91%8A-", response.headers["content-disposition"])
        self.assertRegex(response.headers["content-disposition"], r"\d{8}-\d{6}\.json")

        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(payload["name"], "设备巡检报告")
        self.assertEqual(payload["category"], "巡检")
        self.assertEqual(payload["description"], "巡检模板")
        self.assertEqual(payload["id"], "tpl-1")
        self.assertEqual(payload["parameters"][0]["id"], "date")
        self.assertEqual(payload["sections"][0]["title"], "概览")
        self.assertNotIn("created_at", payload)
        self.assertNotIn("version", payload)
        self.assertNotIn("report_type", payload)
        self.assertNotIn("schema_version", payload)

    def test_preview_import_template_returns_service_payload(self):
        payload = {
            "normalized_template": {"name": "导入模板"},
            "source_kind": "system_export",
            "warnings": [],
            "conflict": {
                "status": "none",
                "matched_templates": [],
                "overwrite_supported": False,
                "default_action": "create_copy",
            },
        }
        fake_service = SimpleNamespace(preview_import_template=lambda *_args, **_kwargs: payload)

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            result = preview_import_template(
                TemplateImportPreviewRequest(payload={"name": "导入模板"}, filename="template.json"),
                db=object(),
            )

        self.assertEqual(result, payload)

    def test_preview_import_template_maps_validation_error_to_http_400(self):
        fake_service = SimpleNamespace(
            preview_import_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("不支持的模板结构。"))
        )

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as exc:
                preview_import_template(
                    TemplateImportPreviewRequest(payload={"foo": "bar"}, filename="template.json"),
                    db=object(),
                )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.detail, "不支持的模板结构。")


if __name__ == "__main__":
    unittest.main()

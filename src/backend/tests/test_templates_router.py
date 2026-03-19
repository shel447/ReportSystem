import json
import unittest
from types import SimpleNamespace

from backend.routers.templates import _clean_template_payload, export_template_definition, list_templates


class TemplatesRouterTests(unittest.TestCase):
    def test_list_templates_includes_v2_summary_fields(self):
        template = SimpleNamespace(
            template_id="tpl-1",
            name="设备巡检报告",
            description="巡检模板",
            report_type="daily",
            scenario="集团",
            template_type="巡检",
            scene="总部",
            created_at="2026-03-19T00:00:00",
            schema_version="v2.0",
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

        self.assertEqual(payload[0]["schema_version"], "v2.0")
        self.assertEqual(payload[0]["parameter_count"], 2)
        self.assertEqual(payload[0]["top_level_section_count"], 2)

    def test_clean_template_payload_validates_and_normalizes_v2_template(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
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

        self.assertEqual(cleaned["schema_version"], "v2.0")
        self.assertEqual(cleaned["template_type"], "设备健康评估")
        self.assertEqual(cleaned["sections"][0]["content"]["datasets"][0]["id"], "ds_main")

    def test_export_template_definition_returns_portable_json_attachment(self):
        template = SimpleNamespace(
            template_id="tpl-1",
            name="设备巡检报告",
            description="巡检模板",
            report_type="daily",
            scenario="集团",
            template_type="巡检",
            scene="总部",
            match_keywords=["巡检", "设备"],
            content_params=[{"legacy": True}],
            parameters=[{"id": "date", "label": "日期", "required": True, "input_type": "date"}],
            outline=[{"title": "旧大纲"}],
            sections=[{"title": "概览", "content": {"presentation": {"type": "text", "template": "周期 {date}"}}}],
            schema_version="v2.0",
            output_formats=["md"],
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
        self.assertIn(".json", response.headers["content-disposition"])

        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(payload["name"], "设备巡检报告")
        self.assertEqual(payload["type"], "巡检")
        self.assertEqual(payload["scene"], "总部")
        self.assertEqual(payload["parameters"][0]["id"], "date")
        self.assertEqual(payload["sections"][0]["title"], "概览")
        self.assertNotIn("template_id", payload)
        self.assertNotIn("created_at", payload)
        self.assertNotIn("version", payload)
        self.assertNotIn("content_params", payload)
        self.assertNotIn("outline", payload)


if __name__ == "__main__":
    unittest.main()

import unittest

from backend.template_schema_service import normalize_template_payload, validate_template_payload


class TemplateSchemaServiceTests(unittest.TestCase):
    def test_normalize_legacy_single_source_content_to_dataset(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [],
            "sections": [
                {
                    "title": "整体指标",
                    "content": {
                        "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        normalized = normalize_template_payload(payload)

        content = normalized["sections"][0]["content"]
        self.assertNotIn("source", content)
        self.assertEqual(content["datasets"][0]["id"], "ds_main")
        self.assertEqual(content["datasets"][0]["source"]["kind"], "sql")
        self.assertEqual(content["presentation"]["type"], "value")

    def test_validate_template_payload_sets_schema_version_and_keeps_v2_sections(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [
                {"id": "device_id", "label": "设备编号", "required": True, "input_type": "free_text"}
            ],
            "sections": [
                {
                    "title": "概述",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_main",
                                "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                            }
                        ],
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        validated = validate_template_payload(payload)

        self.assertEqual(validated["schema_version"], "v2.0")
        self.assertEqual(validated["sections"][0]["content"]["datasets"][0]["id"], "ds_main")

    def test_validate_template_payload_accepts_date_input_type(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [
                {"id": "report_date", "label": "报告日期", "required": True, "input_type": "date"}
            ],
            "sections": [
                {
                    "title": "概述",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_main",
                                "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                            }
                        ],
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        validated = validate_template_payload(payload)

        self.assertEqual(validated["parameters"][0]["input_type"], "date")

    def test_validate_template_payload_accepts_section_description(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [],
            "sections": [
                {
                    "title": "概述",
                    "description": "章节说明",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_main",
                                "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                            }
                        ],
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        validated = validate_template_payload(payload)

        self.assertEqual(validated["sections"][0]["description"], "章节说明")

    def test_validate_template_payload_accepts_presentation_dataset_id(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [],
            "sections": [
                {
                    "title": "概述",
                    "content": {
                        "datasets": [
                            {
                                "id": "inventory",
                                "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                            }
                        ],
                        "presentation": {"type": "simple_table", "dataset_id": "inventory"},
                    },
                }
            ],
        }

        validated = validate_template_payload(payload)

        self.assertEqual(validated["sections"][0]["content"]["presentation"]["dataset_id"], "inventory")

    def test_validate_template_payload_rejects_invalid_v2_template(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [],
            "sections": [
                {
                    "title": "概述",
                    "content": {
                        "datasets": [{"id": "ds_main"}],
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        with self.assertRaises(ValueError):
            validate_template_payload(payload)


if __name__ == "__main__":
    unittest.main()

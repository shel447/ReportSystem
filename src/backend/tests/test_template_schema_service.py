import unittest

from backend.contexts.template_catalog.infrastructure.schema import normalize_template_payload, validate_template_payload


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

    def test_validate_template_payload_accepts_parameter_interaction_mode(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [
                {
                    "id": "report_date",
                    "label": "报告日期",
                    "required": True,
                    "input_type": "date",
                    "interaction_mode": "chat",
                }
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

        self.assertEqual(validated["parameters"][0]["interaction_mode"], "chat")

    def test_validate_template_payload_accepts_parameter_value_mapping(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [
                {
                    "id": "region",
                    "label": "区域",
                    "required": True,
                    "input_type": "enum",
                    "value_mode": "key",
                    "options": [
                        {"key": "east_1", "label": "华东一"},
                        {"key": "east_2", "label": "华东二"},
                    ],
                    "value_mapping": {
                        "query": {
                            "by": "key",
                            "map": {
                                "east_1": "E1",
                                "east_2": ["E2A", "E2B"],
                            },
                            "on_unmapped": "error",
                        }
                    },
                }
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

        self.assertEqual(validated["parameters"][0]["value_mode"], "key")
        self.assertEqual(validated["parameters"][0]["options"][0]["key"], "east_1")
        self.assertEqual(validated["parameters"][0]["value_mapping"]["query"]["map"]["east_2"], ["E2A", "E2B"])

    def test_validate_template_payload_rejects_value_mapping_for_free_text_parameter(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [
                {
                    "id": "region",
                    "label": "区域",
                    "required": True,
                    "input_type": "free_text",
                    "value_mode": "key",
                }
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

        with self.assertRaises(ValueError):
            validate_template_payload(payload)

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

    def test_validate_template_payload_accepts_section_outline_requirement(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [
                {"id": "device_id", "label": "设备编号", "required": True, "input_type": "free_text"}
            ],
            "sections": [
                {
                    "title": "趋势分析",
                    "outline": {
                        "requirement": "分析 {@target_device} 在 {@analysis_period} 内的振动趋势",
                        "items": [
                            {"id": "target_device", "type": "param_ref", "hint": "目标设备", "param_id": "device_id"},
                            {"id": "analysis_period", "type": "time_range", "hint": "分析周期", "default": "最近7天", "widget": "date_range"},
                        ],
                    },
                    "content": {
                        "datasets": [
                            {
                                "id": "trend",
                                "source": {"kind": "nl2sql", "description": "查询 {@target_device} 在 {@analysis_period} 内的振动趋势"},
                            }
                        ],
                        "presentation": {"type": "chart", "dataset_id": "trend", "chart_type": "line"},
                    },
                }
            ],
        }

        validated = validate_template_payload(payload)

        self.assertEqual(validated["sections"][0]["outline"]["requirement"], "分析 {@target_device} 在 {@analysis_period} 内的振动趋势")
        self.assertEqual(validated["sections"][0]["outline"]["items"][0]["id"], "target_device")
        self.assertEqual(validated["sections"][0]["outline"]["items"][1]["type"], "time_range")

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

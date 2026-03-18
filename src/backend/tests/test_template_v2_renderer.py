import unittest

from backend.template_v2_renderer import generate_report_sections_v2


class TemplateV2RendererTests(unittest.TestCase):
    def test_render_value_from_dataset_list(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "总数",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_main",
                                "source": {"kind": "sql", "query": "SELECT 42 AS value"},
                            }
                        ],
                        "presentation": {"type": "value", "anchor": "总数 {$value}"},
                    },
                }
            ],
        }
        sections, _ = generate_report_sections_v2(template, {})
        self.assertIn("总数 42", sections[0]["content"])
        self.assertEqual(sections[0]["debug"]["datasets"][0]["dataset_id"], "ds_main")

    def test_render_sections_with_placeholders_and_foreach(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "概览 {date}",
                    "content": {
                        "presentation": {"type": "text", "template": "周期 {date}"}
                    },
                },
                {
                    "title": "设备 {$device}",
                    "foreach": {"param": "device_ids", "as": "device"},
                    "content": {
                        "presentation": {"type": "text", "template": "设备 {$device} 状态"}
                    },
                },
            ],
        }
        params = {"date": "2026-01-01", "device_ids": ["A", "B"]}
        sections, warnings = generate_report_sections_v2(template, params)
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0]["title"], "概览 2026-01-01")
        self.assertIn("周期 2026-01-01", sections[0]["content"])
        self.assertEqual(sections[1]["title"], "设备 A")
        self.assertIn("设备 A 状态", sections[1]["content"])
        self.assertEqual(sections[2]["title"], "设备 B")
        self.assertEqual(warnings, [])

    def test_nested_foreach_warns_and_ignores_inner(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "外层 {$device}",
                    "foreach": {"param": "device_ids", "as": "device"},
                    "subsections": [
                        {
                            "title": "内层 {$item}",
                            "foreach": {"param": "item_ids", "as": "item"},
                            "content": {
                                "presentation": {"type": "text", "template": "内层 {$item}"}
                            },
                        }
                    ],
                }
            ],
        }
        params = {"device_ids": ["A"], "item_ids": ["X", "Y"]}
        sections, warnings = generate_report_sections_v2(template, params)
        inner_titles = [s["title"] for s in sections if "内层" in s["title"]]
        self.assertEqual(len(inner_titles), 1)
        self.assertTrue(warnings)

    def test_render_value_from_sql(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "总数",
                    "content": {
                        "source": {"kind": "sql", "query": "SELECT 42 AS value"},
                        "presentation": {"type": "value", "anchor": "总数 {$value}"},
                    },
                }
            ],
        }
        sections, _ = generate_report_sections_v2(template, {})
        self.assertIn("总数 42", sections[0]["content"])

    def test_render_simple_table_from_sql(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "表格",
                    "content": {
                        "source": {"kind": "sql", "query": "SELECT 1 AS col1, 2 AS col2"},
                        "presentation": {"type": "simple_table"},
                    },
                }
            ],
        }
        sections, _ = generate_report_sections_v2(template, {})
        content = sections[0]["content"]
        self.assertIn("| col1 | col2 |", content)
        self.assertIn("| 1 | 2 |", content)

    def test_render_chart_outputs_placeholder(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "图表",
                    "content": {
                        "source": {"kind": "sql", "query": "SELECT 'A' AS name, 10 AS value"},
                        "presentation": {"type": "chart", "chart_type": "bar"},
                    },
                }
            ],
        }
        sections, _ = generate_report_sections_v2(template, {})
        content = sections[0]["content"]
        self.assertIn("[chart:bar]", content)
        self.assertIn("| name | value |", content)

    def test_render_composite_table_kv_grid_static(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "综合表",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_base",
                                "source": {"kind": "sql", "query": "SELECT 'A1' AS device, '2026-01-01' AS stat_date"},
                            }
                        ],
                        "presentation": {
                            "type": "composite_table",
                            "columns": 2,
                            "sections": [
                                {
                                    "id": "base",
                                    "band": "基本信息",
                                    "dataset_id": "ds_base",
                                    "layout": {
                                        "type": "kv_grid",
                                        "cols_per_row": 1,
                                        "key_span": 1,
                                        "value_span": 1,
                                        "fields": [
                                            {"key": "设备", "col": "device"},
                                            {"key": "日期", "col": "stat_date"},
                                        ],
                                    },
                                }
                            ],
                        }
                    },
                }
            ],
        }
        sections, _ = generate_report_sections_v2(template, {})
        content = sections[0]["content"]
        self.assertIn("设备", content)
        self.assertIn("A1", content)

    def test_nl2sql_runner_used(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "表格",
                    "content": {
                        "source": {"kind": "nl2sql", "description": "查询"},
                        "presentation": {"type": "simple_table"},
                    },
                }
            ],
        }
        calls = {"count": 0}

        def runner(*_args, **_kwargs):
            calls["count"] += 1
            return {"rows": [{"col1": 1}], "columns": ["col1"], "debug": {"row_count": 1}}

        sections, _ = generate_report_sections_v2(template, {}, nl2sql_runner=runner)
        self.assertEqual(calls["count"], 1)
        self.assertIn("| col1 |", sections[0]["content"])

    def test_ai_synthesis_runner_used(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "AI",
                    "content": {
                        "source": {"kind": "ai_synthesis", "prompt": "总结"},
                        "presentation": {"type": "text"},
                    },
                }
            ],
        }

        def runner(*_args, **_kwargs):
            return "AI SUMMARY"

        sections, _ = generate_report_sections_v2(template, {}, ai_synthesis_runner=runner)
        self.assertIn("AI SUMMARY", sections[0]["content"])

    def test_dataset_cycle_marks_section_failed(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "循环依赖",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_a",
                                "depends_on": ["ds_b"],
                                "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                            },
                            {
                                "id": "ds_b",
                                "depends_on": ["ds_a"],
                                "source": {"kind": "sql", "query": "SELECT 2 AS value"},
                            },
                        ],
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        sections, warnings = generate_report_sections_v2(template, {})

        self.assertTrue(warnings)
        self.assertEqual(sections[0]["status"], "failed")
        self.assertEqual(sections[0]["data_status"], "failed")
        self.assertEqual(sections[0]["debug"]["datasets"][0]["error_message"], "dataset 依赖无法解析")

    def test_ai_synthesis_receives_refs_context(self):
        template = {
            "name": "测试模板",
            "sections": [
                {
                    "title": "AI 结论",
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_main",
                                "source": {"kind": "sql", "query": "SELECT 42 AS value"},
                            },
                            {
                                "id": "ds_summary",
                                "depends_on": ["ds_main"],
                                "source": {
                                    "kind": "ai_synthesis",
                                    "context": {"refs": ["ds_main"]},
                                    "prompt": "总结",
                                },
                            },
                        ],
                        "presentation": {"type": "text"},
                    },
                }
            ],
        }
        captured = {}

        def runner(*_args, **kwargs):
            captured["refs"] = kwargs.get("refs")
            return "AI CONTEXT OK"

        sections, _ = generate_report_sections_v2(template, {}, ai_synthesis_runner=runner)
        self.assertEqual(captured["refs"]["ds_main"]["rows"][0]["value"], 42)
        self.assertIn("AI CONTEXT OK", sections[0]["content"])


if __name__ == "__main__":
    unittest.main()

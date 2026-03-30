import unittest

from backend.domain.reporting.entities import ReportTemplateEntity
from backend.outline_review_service import (
    build_frontend_outline,
    build_pending_outline_review,
    flatten_review_outline,
    merge_outline_override,
    resolve_outline_execution_baseline,
)


class OutlineReviewServiceTests(unittest.TestCase):
    def test_build_pending_outline_review_expands_v2_placeholders_and_foreach(self):
        template = ReportTemplateEntity(
            template_id="tpl-1",
            name="设备巡检报告",
            description="",
            report_type="special",
            scenario="总部",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[],
            parameters=[],
            sections=[
                {
                    "title": "概览 {date}",
                    "description": "场景 {scene}",
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                },
                {
                    "title": "设备 {$device}",
                    "foreach": {"param": "devices", "as": "device"},
                    "content": {"presentation": {"type": "text", "template": "设备 {$device}"}},
                },
            ],
            schema_version="v2.0",
        )

        outline, warnings = build_pending_outline_review(
            template,
            {"date": "2026-03-19", "scene": "总部", "devices": ["D001", "D002"]},
        )

        self.assertEqual(warnings, [])
        self.assertEqual([node["title"] for node in outline], ["概览 2026-03-19", "设备 D001", "设备 D002"])
        self.assertEqual(outline[1]["dynamic_meta"]["item"], "D001")
        self.assertEqual(outline[1]["section_kind"], "structured_leaf")

    def test_build_pending_outline_review_uses_legacy_expansion(self):
        template = ReportTemplateEntity(
            template_id="tpl-2",
            name="资产统计报告",
            description="",
            report_type="daily",
            scenario="资产",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[
                {
                    "title_template": "资产清单 {{item}}",
                    "description_template": "日期 {{date}}",
                    "repeat": {"enabled": True, "source_param": "devices"},
                }
            ],
            parameters=[],
            sections=[],
            schema_version="",
        )

        outline, warnings = build_pending_outline_review(
            template,
            {"date": "2026-03-19", "devices": ["A001", "A002"]},
        )

        self.assertEqual(warnings, [])
        self.assertEqual([node["title"] for node in outline], ["资产清单 A001", "资产清单 A002"])
        self.assertEqual(flatten_review_outline(outline)[0]["title"], "资产清单 A001")

    def test_build_pending_outline_review_marks_ai_generated_nodes_for_frontend(self):
        template = ReportTemplateEntity(
            template_id="tpl-3",
            name="综合报告",
            description="",
            report_type="special",
            scenario="总部",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[],
            parameters=[],
            sections=[
                {
                    "title": "总览",
                    "subsections": [
                        {
                            "title": "SQL 章节",
                            "description": "纯查询",
                            "content": {
                                "datasets": [{"id": "d1", "source": {"kind": "sql", "sql": "select 1"}}],
                                "presentation": {"type": "text", "template": "ok"},
                            },
                        },
                        {
                            "title": "NL2SQL 章节",
                            "description": "模型转查询",
                            "content": {
                                "datasets": [{"id": "d2", "source": {"kind": "nl2sql", "query": "查站点"}}],
                                "presentation": {"type": "text", "template": "ok"},
                            },
                        },
                        {
                            "title": "AI 综合章节",
                            "description": "模型总结",
                            "content": {
                                "datasets": [{"id": "d3", "source": {"kind": "ai_synthesis", "prompt": "总结"}}],
                                "presentation": {"type": "text", "template": "ok"},
                            },
                        },
                        {
                            "title": "自由撰写章节",
                            "description": "直接生成",
                        },
                    ],
                }
            ],
            schema_version="v2.0",
        )

        outline, warnings = build_pending_outline_review(template, {})

        self.assertEqual(warnings, [])
        self.assertEqual(outline[0]["node_kind"], "group")
        self.assertFalse(outline[0]["ai_generated"])
        self.assertEqual(outline[0]["display_text"], "总览")
        children = outline[0]["children"]
        self.assertEqual(children[0]["node_kind"], "structured_leaf")
        self.assertFalse(children[0]["ai_generated"])
        self.assertEqual(children[0]["display_text"], "SQL 章节：纯查询")
        self.assertTrue(children[1]["ai_generated"])
        self.assertTrue(children[2]["ai_generated"])
        self.assertEqual(children[3]["node_kind"], "freeform_leaf")
        self.assertTrue(children[3]["ai_generated"])

    def test_build_pending_outline_review_derives_leaf_content_preview(self):
        template = ReportTemplateEntity(
            template_id="tpl-4",
            name="巡检报告",
            description="",
            report_type="special",
            scenario="总部",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[],
            parameters=[],
            sections=[
                {
                    "title": "文字章节",
                    "content": {
                        "presentation": {"type": "text", "template": "统计 {scene} 的重点指标"},
                    },
                },
                {
                    "title": "表格章节",
                    "content": {
                        "datasets": [{"id": "d1", "source": {"kind": "sql", "sql": "select 1"}}],
                        "presentation": {"type": "simple_table"},
                    },
                },
                {
                    "title": "自由章节",
                },
            ],
            schema_version="v2.0",
        )

        outline, warnings = build_pending_outline_review(template, {"scene": "总部"})

        self.assertEqual(warnings, [])
        self.assertEqual(outline[0]["display_text"], "文字章节：统计 总部 的重点指标")
        self.assertEqual(outline[1]["display_text"], "表格章节：展示数据表格")
        self.assertEqual(outline[2]["display_text"], "自由章节：系统生成本节内容")

    def test_build_pending_outline_review_materializes_outline_blueprint_and_bindings(self):
        template = ReportTemplateEntity(
            template_id="tpl-5",
            name="设备分析报告",
            description="",
            report_type="special",
            scenario="总部",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[],
            parameters=[],
            sections=[
                {
                    "title": "概览 {date}",
                    "outline": {
                        "document": "分析 {@focus_metric} 在 {date} 的变化",
                        "blocks": [
                            {
                                "id": "focus_metric",
                                "type": "indicator",
                                "default": "温度",
                            }
                        ],
                    },
                    "content": {
                        "presentation": {
                            "type": "text",
                            "template": "展示 {@focus_metric}",
                        }
                    },
                }
            ],
            schema_version="v2.0",
        )

        outline, warnings = build_pending_outline_review(template, {"date": "2026-03-19"})

        self.assertEqual(warnings, [])
        self.assertEqual(outline[0]["display_text"], "分析 温度 在 2026-03-19 的变化")
        self.assertEqual(outline[0]["outline_instance"]["rendered_document"], "分析 温度 在 2026-03-19 的变化")
        self.assertEqual(outline[0]["outline_instance"]["blocks"][0]["value"], "温度")
        self.assertEqual(outline[0]["execution_bindings"][0]["block_id"], "focus_metric")
        self.assertEqual(outline[0]["execution_bindings"][0]["targets"], ["presentation.template"])

    def test_merge_outline_override_preserves_structured_content_and_marks_new_nodes(self):
        current = [
            {
                "node_id": "node-1",
                "title": "概览",
                "description": "说明",
                "level": 1,
                "children": [],
                "section_kind": "structured_leaf",
                "source_kind": "v2",
                "content": {"presentation": {"type": "text", "template": "ok"}},
            }
        ]
        override = [
            {
                "node_id": "node-1",
                "title": "更新后的概览",
                "description": "新的说明",
                "level": 1,
                "children": [
                    {
                        "node_id": "node-new",
                        "title": "新增章节",
                        "description": "人工新增",
                        "level": 2,
                        "children": [],
                    }
                ],
            }
        ]

        merged = merge_outline_override(current, override)

        self.assertEqual(merged[0]["title"], "更新后的概览")
        self.assertEqual(merged[0]["section_kind"], "group")
        self.assertNotIn("content", merged[0])
        self.assertEqual(merged[0]["children"][0]["section_kind"], "freeform_leaf")
        self.assertEqual(merged[0]["children"][0]["source_kind"], "manual")
        self.assertNotIn("display_text", merged[0])
        self.assertNotIn("ai_generated", merged[0])

    def test_merge_outline_override_keeps_structured_outline_instance_edits(self):
        current = [
            {
                "node_id": "node-1",
                "title": "分析章节",
                "description": "查看章节内容",
                "level": 1,
                "children": [],
                "section_kind": "structured_leaf",
                "source_kind": "v2",
                "content": {
                    "presentation": {
                        "type": "text",
                        "template": "展示 {@focus_metric}",
                    }
                },
                "outline_instance": {
                    "document_template": "分析 {@focus_metric} 的变化",
                    "rendered_document": "分析 温度 的变化",
                    "segments": [
                        {"kind": "text", "text": "分析 "},
                        {"kind": "block", "block_id": "focus_metric", "block_type": "indicator", "value": "温度"},
                        {"kind": "text", "text": " 的变化"},
                    ],
                    "blocks": [
                        {"id": "focus_metric", "type": "indicator", "hint": "指标", "value": "温度"},
                    ],
                },
            }
        ]
        override = [
            {
                "node_id": "node-1",
                "title": "分析章节",
                "description": "查看章节内容",
                "level": 1,
                "children": [],
                "outline_instance": {
                    "document_template": "分析 {@focus_metric} 的变化",
                    "rendered_document": "分析 湿度 的变化",
                    "segments": [
                        {"kind": "text", "text": "分析 "},
                        {"kind": "block", "block_id": "focus_metric", "block_type": "indicator", "value": "湿度"},
                        {"kind": "text", "text": " 的变化"},
                    ],
                    "blocks": [
                        {"id": "focus_metric", "type": "indicator", "hint": "指标", "value": "湿度"},
                    ],
                },
            }
        ]

        merged = merge_outline_override(current, override)
        frontend = build_frontend_outline(merged)
        resolved = resolve_outline_execution_baseline(merged)

        self.assertEqual(frontend[0]["display_text"], "分析 湿度 的变化")
        self.assertEqual(frontend[0]["outline_instance"]["blocks"][0]["value"], "湿度")
        self.assertEqual(
            resolved[0]["resolved_content"]["presentation"]["template"],
            "展示 湿度",
        )


if __name__ == "__main__":
    unittest.main()

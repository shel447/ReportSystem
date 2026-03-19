import unittest

from backend.domain.reporting.entities import ReportTemplateEntity
from backend.outline_review_service import (
    build_pending_outline_review,
    flatten_review_outline,
    merge_outline_override,
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


if __name__ == "__main__":
    unittest.main()

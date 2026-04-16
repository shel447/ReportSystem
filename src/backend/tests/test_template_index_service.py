import unittest
from types import SimpleNamespace

from backend.contexts.template_catalog.infrastructure import indexing as tis


class TemplateIndexServiceTests(unittest.TestCase):
    def test_effective_parameters_reads_single_track_parameters(self):
        template = SimpleNamespace(parameters=[{"id": "p1"}])
        result = tis._effective_parameters(template)
        self.assertEqual(result, [{"id": "p1"}])

    def test_collect_section_lines_reads_sections(self):
        template = SimpleNamespace(sections=[{"title": "章节", "description": "说明"}])
        lines = tis._collect_section_lines(tis._effective_sections(template))
        self.assertEqual(lines, [("章节", "说明")])

    def test_build_template_semantic_text_includes_dataset_source_descriptions(self):
        template = SimpleNamespace(
            name="巡检报告",
            description="设备巡检",
            category="设备巡检",
            parameters=[],
            sections=[
                {
                    "title": "异常分析",
                    "content": {
                        "datasets": [
                            {
                                "id": "alarms",
                                "source": {
                                    "kind": "ai_synthesis",
                                    "description": "汇总近期设备告警",
                                    "prompt": "分析高频告警与站点影响",
                                },
                            }
                        ]
                    },
                }
            ],
        )
        text = tis.build_template_semantic_text(template)
        self.assertIn("汇总近期设备告警", text)
        self.assertIn("分析高频告警与站点影响", text)


if __name__ == "__main__":
    unittest.main()

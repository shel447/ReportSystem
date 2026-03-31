import unittest
from dataclasses import asdict
from datetime import datetime

from backend.application.reporting.services import InstanceApplicationService
from backend.domain.reporting.entities import ReportInstanceEntity, ReportTemplateEntity


class FakeTemplateReader:
    def __init__(self, template):
        self.template = template

    def get_by_id(self, template_id: str):
        return self.template if self.template.template_id == template_id else None


class FakeInstanceWriter:
    def create(
        self,
        *,
        template_id,
        template_version,
        input_params,
        outline_content,
        status="draft",
        report_time=None,
        report_time_source="",
    ):
        return ReportInstanceEntity(
            instance_id="inst-1",
            template_id=template_id,
            template_version=template_version,
            status=status,
            input_params=input_params,
            outline_content=outline_content,
            created_at=datetime(2026, 3, 19, 12, 0, 0),
            updated_at=datetime(2026, 3, 19, 12, 0, 0),
            report_time=report_time,
            report_time_source=report_time_source,
        )


class FakeContentGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, template, outline, params):
        self.calls.append(("generate", outline))
        return [{"title": item["title"], "description": item.get("description", ""), "content": "legacy"} for item in outline]

    def generate_v2(self, template, params):
        self.calls.append(("generate_v2", template.sections))
        return ([{"title": "default", "description": "", "content": "default"}], [])

    def generate_v2_from_outline(self, template, outline, params):
        self.calls.append(("generate_v2_from_outline", outline))
        return ([{"title": outline[0]["title"], "description": "", "content": "from-outline"}], [])


class InstanceApplicationServiceTests(unittest.TestCase):
    def test_create_instance_uses_confirmed_outline_for_v2_template(self):
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
            sections=[{"title": "模板原始章节"}],
            schema_version="v2.0",
        )
        generator = FakeContentGenerator()
        service = InstanceApplicationService(
            template_reader=FakeTemplateReader(template),
            instance_writer=FakeInstanceWriter(),
            content_generator=generator,
        )

        result = service.create_instance(
            template_id="tpl-1",
            input_params={"scene": "总部"},
            outline_override=[
                {
                    "node_id": "node-1",
                    "title": "确认后的章节",
                    "description": "确认后的说明",
                    "level": 1,
                    "children": [],
                }
            ],
        )

        self.assertEqual(generator.calls[0][0], "generate_v2_from_outline")
        self.assertEqual(result["outline_content"][0]["title"], "确认后的章节")

    def test_create_instance_flattens_confirmed_outline_for_legacy_template(self):
        template = ReportTemplateEntity(
            template_id="tpl-2",
            name="资产报告",
            description="",
            report_type="daily",
            scenario="资产",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[{"title": "原始章节"}],
            parameters=[],
            sections=[],
            schema_version="",
        )
        generator = FakeContentGenerator()
        service = InstanceApplicationService(
            template_reader=FakeTemplateReader(template),
            instance_writer=FakeInstanceWriter(),
            content_generator=generator,
        )

        result = service.create_instance(
            template_id="tpl-2",
            input_params={"scene": "总部"},
            outline_override=[
                {
                    "node_id": "node-1",
                    "title": "一级",
                    "description": "",
                    "level": 1,
                    "children": [
                        {
                            "node_id": "node-2",
                            "title": "二级",
                            "description": "",
                            "level": 2,
                            "children": [],
                        }
                    ],
                }
            ],
        )

        self.assertEqual(generator.calls[0][0], "generate")
        self.assertEqual([item["title"] for item in generator.calls[0][1]], ["一级", "二级"])
        self.assertEqual(result["outline_content"][1]["title"], "二级")

    def test_create_instance_preserves_business_report_time(self):
        template = ReportTemplateEntity(
            template_id="tpl-3",
            name="定时报告",
            description="",
            report_type="daily",
            scenario="总部",
            match_keywords=[],
            content_params=[],
            version="1.0",
            outline=[],
            parameters=[],
            sections=[{"title": "模板章节"}],
            schema_version="v2.0",
        )
        generator = FakeContentGenerator()
        service = InstanceApplicationService(
            template_reader=FakeTemplateReader(template),
            instance_writer=FakeInstanceWriter(),
            content_generator=generator,
        )

        report_time = datetime(2026, 3, 31, 8, 0, 0)
        result = service.create_instance(
            template_id="tpl-3",
            input_params={"date": "2026-03-31"},
            report_time=report_time,
            report_time_source="scheduled_execution",
        )

        self.assertEqual(result["report_time"], str(report_time))
        self.assertEqual(result["report_time_source"], "scheduled_execution")


if __name__ == "__main__":
    unittest.main()

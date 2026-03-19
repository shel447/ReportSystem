import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import ReportInstance, ReportTemplate
from backend.routers.instances import regenerate_section


class FakeOutlineAwareGenerator:
    last_outline = None

    def __init__(self, *_args, **_kwargs):
        pass

    def generate_v2(self, *_args, **_kwargs):
        raise AssertionError("generate_v2 should not be used when debug.outline_node exists")

    def generate_v2_from_outline(self, _template, outline, _params):
        FakeOutlineAwareGenerator.last_outline = outline
        return (
            [
                {
                    "title": outline[0]["title"],
                    "description": outline[0].get("description", ""),
                    "content": "regenerated-from-outline",
                    "debug": {"outline_node": outline[0]},
                }
            ],
            [],
        )


class InstancesRouterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.template = ReportTemplate(
            template_id="tpl-1",
            name="设备巡检报告",
            description="",
            report_type="special",
            scenario="总部",
            parameters=[],
            sections=[{"title": "模板原始章节"}],
            schema_version="v2.0",
        )
        self.instance = ReportInstance(
            instance_id="inst-1",
            template_id="tpl-1",
            input_params={"scene": "总部"},
            outline_content=[
                {
                    "title": "确认后的章节",
                    "description": "确认后的说明",
                    "content": "old-content",
                    "debug": {
                        "outline_node": {
                            "node_id": "node-1",
                            "title": "确认后的章节",
                            "description": "确认后的说明",
                            "level": 1,
                            "children": [],
                        }
                    },
                }
            ],
        )
        self.db.add(self.template)
        self.db.add(self.instance)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_regenerate_section_uses_confirmed_outline_node_for_v2_instance(self):
        with patch("backend.routers.instances.OpenAICompatGateway"), \
             patch("backend.routers.instances.OpenAIContentGenerator", FakeOutlineAwareGenerator):
            result = regenerate_section("inst-1", 0, db=self.db)

        self.assertEqual(FakeOutlineAwareGenerator.last_outline[0]["title"], "确认后的章节")
        self.assertEqual(result["outline_content"][0]["content"], "regenerated-from-outline")
        self.assertTrue(result["outline_content"][0]["regenerated"])


if __name__ == "__main__":
    unittest.main()

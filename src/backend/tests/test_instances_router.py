import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import ChatSession, ReportInstance, ReportTemplate, TemplateInstance
from backend.routers.instances import (
    fork_instance_chat,
    get_instance,
    get_instance_baseline,
    list_instance_fork_sources,
    list_instances,
    regenerate_section,
    update_instance_chat,
)


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
        self.source_session = ChatSession(
            session_id="sess-1",
            title="设备巡检报告",
            matched_template_id="tpl-1",
            messages=[
                {"role": "user", "content": "制作设备巡检报告", "message_id": "msg-u1", "created_at": "2026-03-20T09:00:00Z"},
                {
                    "role": "assistant",
                    "content": "请输入参数",
                    "message_id": "msg-a1",
                    "created_at": "2026-03-20T09:00:01Z",
                    "action": {"type": "ask_param", "param": {"id": "scene", "label": "场景"}},
                },
            ],
        )
        self.template_instance = TemplateInstance(
            template_instance_id="ti-1",
            template_id="tpl-1",
            template_name="设备巡检报告",
            template_version="1.0",
            session_id="sess-1",
            capture_stage="generation_baseline",
            input_params_snapshot={"scene": "总部"},
            outline_snapshot=[
                {
                    "node_id": "node-1",
                    "title": "确认后的章节",
                    "description": "确认后的说明",
                    "display_text": "确认后的章节：确认后的说明",
                    "level": 1,
                    "children": [],
                }
            ],
            report_instance_id="inst-1",
        )
        self.legacy_instance = ReportInstance(
            instance_id="inst-legacy",
            template_id="tpl-1",
            input_params={"scene": "旧实例"},
            outline_content=[],
        )
        self.db.add(self.template)
        self.db.add(self.instance)
        self.db.add(self.source_session)
        self.db.add(self.template_instance)
        self.db.add(self.legacy_instance)
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

    def test_list_and_get_instance_expose_generation_baseline_capabilities(self):
        payload = list_instances(db=self.db)
        inst = next(item for item in payload if item["instance_id"] == "inst-1")
        legacy = next(item for item in payload if item["instance_id"] == "inst-legacy")

        self.assertTrue(inst["has_generation_baseline"])
        self.assertTrue(inst["supports_update_chat"])
        self.assertTrue(inst["supports_fork_chat"])
        self.assertFalse(legacy["has_generation_baseline"])
        self.assertFalse(legacy["supports_update_chat"])
        self.assertFalse(legacy["supports_fork_chat"])

        detail = get_instance("inst-1", db=self.db)
        self.assertTrue(detail["has_generation_baseline"])
        self.assertTrue(detail["supports_update_chat"])
        self.assertTrue(detail["supports_fork_chat"])

    def test_get_instance_baseline_returns_snapshot(self):
        payload = get_instance_baseline("inst-1", db=self.db)

        self.assertEqual(payload["instance_id"], "inst-1")
        self.assertEqual(payload["params_snapshot"]["scene"], "总部")
        self.assertEqual(payload["outline"][0]["title"], "确认后的章节")

    def test_update_instance_chat_restores_outline_review_from_generation_baseline(self):
        payload = update_instance_chat("inst-1", db=self.db)

        self.assertEqual(payload["matched_template_id"], "tpl-1")
        visible = [
            item for item in payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertEqual(visible[-1]["action"]["type"], "review_outline")
        self.assertEqual(payload["fork_meta"]["source_kind"], "template_instance")

    def test_list_instance_fork_sources_and_fork_instance_chat_use_source_session(self):
        sources = list_instance_fork_sources("inst-1", db=self.db)

        self.assertEqual([item["message_id"] for item in sources], ["msg-u1", "msg-a1"])
        self.assertEqual(sources[1]["action_type"], "ask_param")

        payload = fork_instance_chat("inst-1", {"source_message_id": "msg-a1"}, db=self.db)

        visible = [
            item for item in payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertEqual(visible[-1]["action"]["type"], "ask_param")
        self.assertEqual(payload["fork_meta"]["source_session_id"], "sess-1")


if __name__ == "__main__":
    unittest.main()

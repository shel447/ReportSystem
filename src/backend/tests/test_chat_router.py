import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import ChatSession, ReportTemplate, TemplateInstance
from backend.routers.chat import ChatMessage, get_session, list_sessions, send_message


class ChatRouterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.template = ReportTemplate(
            template_id="tpl-1",
            name="设备巡检报告",
            template_type="设备健康评估",
            scene="总部",
            parameters=[
                {"id": "scene", "label": "场景", "required": True, "input_type": "enum", "options": ["总部"]},
                {
                    "id": "devices",
                    "label": "设备编号",
                    "required": True,
                    "input_type": "dynamic",
                    "multi": True,
                    "source": "api:/devices/list",
                },
            ],
            sections=[
                {
                    "title": "{scene}概述",
                    "description": "巡检范围",
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                },
                {
                    "title": "设备 {$device}",
                    "description": "检查项",
                    "foreach": {"param": "devices", "as": "device"},
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                },
            ],
            schema_version="v2.0",
        )
        self.db.add(self.template)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_send_message_returns_review_params_before_generation(self):
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.routers.chat.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.routers.chat.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001", "A002"]},
             ):
            response = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        self.assertEqual(response["action"]["type"], "review_params")
        self.assertEqual(response["reply"], "参数已收集完成，请确认后生成大纲。")
        self.assertEqual(response["action"]["params"][0]["id"], "scene")

    def test_send_message_confirms_then_generates_document(self):
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.routers.chat.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.routers.chat.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
            ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="prepare_outline_review"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "review_outline")
        self.assertEqual(second["action"]["outline"][0]["title"], "总部概述")
        self.assertEqual(second["action"]["outline"][1]["title"], "设备 A001")
        self.assertEqual(self.db.query(TemplateInstance).count(), 0)

        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}):
            saved = send_message(
                ChatMessage(session_id=first["session_id"], command="edit_outline", outline_override=second["action"]["outline"]),
                db=self.db,
            )

        self.assertEqual(saved["action"]["type"], "review_outline")
        saved_record = self.db.query(TemplateInstance).filter(TemplateInstance.capture_stage == "outline_saved").first()
        self.assertIsNotNone(saved_record)
        self.assertEqual(saved_record.template_id, "tpl-1")
        self.assertEqual(saved_record.session_id, first["session_id"])
        self.assertEqual(saved_record.report_instance_id, None)
        self.assertEqual(len(saved_record.outline_snapshot or []), 2)

        fake_app_service = SimpleNamespace(create_instance=lambda **_kwargs: {"instance_id": "inst-1"})
        fake_doc = SimpleNamespace(document_id="doc-1", instance_id="inst-1", template_id="tpl-1", format="md", file_path="x.md", file_size=10, status="ready", version=1, created_at="now")
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.routers.chat.build_instance_application_service", return_value=fake_app_service), \
             patch("backend.routers.chat.create_markdown_document", return_value=fake_doc), \
             patch(
                 "backend.routers.chat.serialize_document",
                 return_value={"document_id": "doc-1", "download_url": "/api/documents/doc-1/download"},
             ):
            third = send_message(
                ChatMessage(
                    session_id=first["session_id"],
                    command="confirm_outline_generation",
                    outline_override=[
                        {
                            "node_id": second["action"]["outline"][0]["node_id"],
                            "title": "总部总览",
                            "description": "巡检范围",
                            "level": 1,
                            "children": [],
                        },
                        second["action"]["outline"][1],
                    ],
                ),
                db=self.db,
            )

        self.assertEqual(third["action"]["type"], "download_document")
        self.assertEqual(third["action"]["document"]["document_id"], "doc-1")
        confirmed_record = self.db.query(TemplateInstance).filter(TemplateInstance.capture_stage == "outline_confirmed").first()
        self.assertIsNotNone(confirmed_record)
        self.assertEqual(confirmed_record.report_instance_id, "inst-1")

    def test_send_message_reset_params_restarts_required_collection(self):
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.routers.chat.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.routers.chat.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="reset_params"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "ask_param")
        self.assertEqual(second["action"]["param"]["id"], "scene")

    def test_send_message_edit_param_rewinds_following_slots(self):
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.routers.chat.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.routers.chat.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="edit_param", target_param_id="devices"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "ask_param")
        self.assertEqual(second["action"]["param"]["id"], "devices")

    def test_send_message_edit_param_from_outline_review_returns_review_params(self):
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.routers.chat.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.routers.chat.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="prepare_outline_review"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "review_outline")

        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}):
            third = send_message(
                ChatMessage(session_id=first["session_id"], command="edit_param"),
                db=self.db,
            )

        self.assertEqual(third["action"]["type"], "review_params")

    def test_send_message_empty_payload_does_not_create_session(self):
        response = send_message(ChatMessage(), db=self.db)

        self.assertEqual(response["session_id"], "")
        self.assertEqual(response["messages"], [])
        self.assertEqual(self.db.query(ChatSession).count(), 0)

    def test_send_message_persists_message_timestamps(self):
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.param_dialog_service.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.routers.chat.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.routers.chat.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001", "A002"]},
             ):
            response = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        visible_response_messages = [
            item for item in response["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertGreaterEqual(len(visible_response_messages), 2)
        self.assertTrue(all(item.get("created_at") for item in visible_response_messages))

        session_payload = get_session(response["session_id"], db=self.db)
        visible_session_messages = [
            item for item in session_payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertGreaterEqual(len(visible_session_messages), 2)
        self.assertTrue(all(item.get("created_at") for item in visible_session_messages))

    def test_list_sessions_returns_recent_summaries_with_generated_title(self):
        first = ChatSession(
            session_id="s-1",
            messages=[
                {"role": "user", "content": "制作设备巡检报告并输出总部结果"},
                {"role": "assistant", "content": "请补充参数。"},
            ],
            matched_template_id="tpl-1",
            instance_id="inst-1",
        )
        second = ChatSession(
            session_id="s-2",
            messages=[
                {"role": "user", "content": "统计昨日告警"},
                {
                    "role": "assistant",
                    "content": "",
                    "meta": {"type": "context_state", "schema_version": "ctx.v1", "state": {}},
                },
                {"role": "assistant", "content": "已生成结果。"},
            ],
        )
        self.db.add_all([first, second])
        self.db.commit()

        sessions = list_sessions(db=self.db)

        self.assertEqual([item["session_id"] for item in sessions], ["s-2", "s-1"])
        self.assertEqual(sessions[0]["title"], "统计昨日告警")
        self.assertEqual(sessions[0]["message_count"], 2)
        self.assertEqual(sessions[0]["last_message_preview"], "已生成结果。")
        self.assertEqual(sessions[1]["title"], "制作设备巡检报告并输出总部结果")
        self.assertEqual(sessions[1]["matched_template_id"], "tpl-1")
        self.assertEqual(sessions[1]["instance_id"], "inst-1")


if __name__ == "__main__":
    unittest.main()



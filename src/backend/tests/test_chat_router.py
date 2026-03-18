import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import ChatSession, ReportTemplate
from backend.routers.chat import ChatMessage, send_message


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
            sections=[{"title": "概述", "content": {"presentation": {"type": "text", "template": "ok"}}}],
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
        self.assertEqual(response["reply"], "参数已收集完成，请确认后生成报告。")
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

        fake_app_service = SimpleNamespace(create_instance=lambda **_kwargs: {"instance_id": "inst-1"})
        fake_doc = SimpleNamespace(document_id="doc-1", instance_id="inst-1", template_id="tpl-1", format="md", file_path="x.md", file_size=10, status="ready", version=1, created_at="now")
        with patch("backend.routers.chat.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.routers.chat.build_instance_application_service", return_value=fake_app_service), \
             patch("backend.routers.chat.create_markdown_document", return_value=fake_doc), \
             patch(
                 "backend.routers.chat.serialize_document",
                 return_value={"document_id": "doc-1", "download_url": "/api/documents/doc-1/download"},
             ):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="confirm_generation"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "download_document")
        self.assertEqual(second["action"]["document"]["document_id"], "doc-1")

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


if __name__ == "__main__":
    unittest.main()

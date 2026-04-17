import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.infrastructure.persistence.database import Base, get_db
from backend.infrastructure.persistence.models import ReportTemplate
from backend.routers.chat import router as chat_router


class ChatContractApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = testing_session_local()
        self.db.add(
            ReportTemplate(
                id="tpl-1",
                name="设备巡检报告",
                description="用于巡检分析",
                category="inspection",
                parameters=[
                    {"id": "scene", "label": "场景", "required": True, "input_type": "enum", "options": ["总部"]},
                    {"id": "devices", "label": "设备", "required": True, "input_type": "dynamic", "multi": True, "source": "api:/devices/list"},
                ],
                sections=[{"title": "巡检概览", "content": {"presentation": {"type": "text", "template": "ok"}}}],
            )
        )
        self.db.commit()

        app = FastAPI()
        app.include_router(chat_router, prefix="/rest/chatbi/v1")

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()

    def test_post_chat_accepts_new_contract_and_returns_unified_envelope(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv-001",
                    "chatId": "chat-001",
                    "instruction": "generate_report",
                    "question": "帮我生成总部设备巡检报告，先看 A001",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["conversationId"], "conv-001")
        self.assertEqual(payload["chatId"], "chat-001")
        self.assertEqual(payload["status"], "waiting_user")
        self.assertIsInstance(payload["steps"], list)
        self.assertIsInstance(payload["delta"], list)
        self.assertIsNone(payload["answer"])
        self.assertEqual(payload["ask"]["mode"], "form")
        self.assertEqual(payload["ask"]["type"], "confirm")
        self.assertEqual(payload["ask"]["parameters"][0]["id"], "scene")

    def test_post_chat_reply_parameters_advance_form_collection(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={},
             ):
            first = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv-form-001",
                    "chatId": "chat-001",
                    "instruction": "generate_report",
                    "question": "帮我生成设备巡检报告",
                },
            )

        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertEqual(first_payload["ask"]["mode"], "form")
        self.assertEqual(first_payload["ask"]["parameters"][0]["id"], "scene")

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={},
             ):
            second = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv-form-001",
                    "chatId": "chat-002",
                    "instruction": "generate_report",
                    "question": "",
                    "reply": {
                        "type": "fill_params",
                        "parameters": {
                            "scene": "总部",
                        },
                    },
                },
            )

        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertEqual(second_payload["status"], "waiting_user")
        self.assertEqual(second_payload["ask"]["mode"], "form")
        self.assertEqual(second_payload["ask"]["type"], "fill_params")
        self.assertEqual(second_payload["ask"]["parameters"][0]["id"], "devices")

    def test_post_chat_final_confirm_returns_finished_report_answer(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv-002",
                    "chatId": "chat-001",
                    "instruction": "generate_report",
                    "question": "帮我生成总部设备巡检报告，先看 A001",
                },
            )

        self.assertEqual(first.status_code, 200)

        fake_app_service = type(
            "FakeAppService",
            (),
            {"create_instance": lambda self, **_kwargs: {"instance_id": "rpt-001"}},
        )()
        fake_doc = type(
            "FakeDocument",
            (),
            {
                "document_id": "doc-001",
                "instance_id": "rpt-001",
                "template_id": "tpl-1",
                "format": "md",
                "file_path": "report.md",
                "file_size": 100,
                "status": "ready",
                "version": 1,
                "created_at": "now",
            },
        )()

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.gateways.build_instance_application_service", return_value=fake_app_service), \
             patch("backend.contexts.conversation.infrastructure.gateways.create_markdown_document", return_value=fake_doc), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.serialize_document",
                 return_value={"document_id": "doc-001", "download_url": "/rest/chatbi/v1/reports/rpt-001/documents/doc-001/download"},
             ):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv-002",
                    "chatId": "chat-002",
                    "instruction": "generate_report",
                    "question": "确认开始生成",
                    "reply": {
                        "type": "final_confirm",
                        "parameters": {
                            "scene": "总部",
                            "devices": ["A001"],
                        },
                    },
                    "command": {"name": "confirm_generate_report"},
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "finished")
        self.assertIsNone(payload["ask"])
        self.assertEqual(payload["answer"]["answerType"], "report_ready")
        self.assertEqual(payload["answer"]["reportId"], "rpt-001")
        self.assertTrue(payload["answer"]["templateInstanceId"])

    def test_post_chat_supports_sse_when_accept_header_is_event_stream(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={
                    "X-User-Id": "default",
                    "Accept": "text/event-stream",
                },
                json={
                    "conversationId": "conv-003",
                    "chatId": "chat-003",
                    "instruction": "generate_report",
                    "question": "帮我生成总部设备巡检报告，先看 A001",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("content-type", ""))
        body = response.text
        self.assertIn("event: message", body)
        self.assertIn("\"conversationId\": \"conv-003\"", body)


if __name__ == "__main__":
    unittest.main()



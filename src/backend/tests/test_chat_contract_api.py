import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.infrastructure.persistence.database import get_db
from backend.routers.chat import router as chat_router
from backend.shared.kernel.errors import ValidationError


def _sample_template_instance(status: str = "ready_for_confirmation", capture_stage: str = "confirm_params"):
    return {
        "id": "ti_001",
        "schemaVersion": "template-instance.vNext-draft",
        "templateId": "tpl_network_daily",
        "template": {
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [],
        },
        "conversationId": "conv_001",
        "status": status,
        "captureStage": capture_stage,
        "revision": 2,
        "parameters": [
            {
                "id": "scope",
                "label": "分析对象",
                "inputType": "dynamic",
                "required": True,
                "multi": True,
                "interactionMode": "natural_language",
                "source": "https://example.internal/api/network/scopes/options",
                "values": [],
            }
        ],
        "parameterConfirmation": {"missingParameterIds": ["scope"], "confirmed": False},
        "catalogs": [],
        "createdAt": "2026-04-18T09:00:00Z",
        "updatedAt": "2026-04-18T09:01:00Z",
    }


class ChatContractApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(chat_router, prefix="/rest/chatbi/v1")

        def override_get_db():
            yield object()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def test_post_chat_returns_confirm_params_with_full_template_instance(self):
        fake_service = type(
            "FakeConversationService",
            (),
            {
                "list_sessions": lambda self, user_id: [],
                "send_message": lambda self, data, user_id: {
                    "conversationId": "conv_001",
                    "chatId": "chat_001",
                    "status": "waiting_user",
                    "steps": [],
                    "ask": {
                        "status": "pending",
                        "mode": "form",
                        "type": "confirm_params",
                        "title": "请确认报告诉求",
                        "text": "请确认报告诉求后开始生成。",
                        "parameters": [
                            {
                                "id": "scope",
                                "label": "分析对象",
                                "inputType": "dynamic",
                                "required": True,
                                "multi": True,
                                "interactionMode": "natural_language",
                                "source": "https://example.internal/api/network/scopes/options",
                                "values": [],
                            }
                        ],
                        "reportContext": {"templateInstance": _sample_template_instance()},
                    },
                    "answer": None,
                    "errors": [],
                    "requestId": "req_001",
                    "timestamp": 1713427200000,
                    "apiVersion": "v1",
                }
            },
        )()

        with patch("backend.routers.chat.build_conversation_service", return_value=fake_service):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv_001",
                    "chatId": "chat_001",
                    "instruction": "generate_report",
                    "question": "帮我生成网络运行日报",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ask"]["status"], "pending")
        self.assertEqual(payload["ask"]["type"], "confirm_params")
        self.assertEqual(payload["ask"]["parameters"][0]["id"], "scope")
        self.assertEqual(payload["ask"]["reportContext"]["templateInstance"]["id"], "ti_001")

    def test_post_chat_confirm_params_returns_report_answer(self):
        fake_service = type(
            "FakeConversationService",
            (),
            {
                "send_message": lambda self, data, user_id: {
                    "conversationId": "conv_001",
                    "chatId": "chat_002",
                    "status": "finished",
                    "steps": [],
                    "ask": None,
                    "answer": {
                        "answerType": "REPORT",
                        "answer": {
                            "reportId": "rpt_001",
                            "status": "generating",
                            "report": {
                                "basicInfo": {
                                    "id": "rpt_001",
                                    "schemaVersion": "1.0.0",
                                    "mode": "draft",
                                    "status": "Running",
                                },
                                "catalogs": [],
                                "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
                            },
                            "templateInstance": _sample_template_instance(status="generating", capture_stage="generate_report"),
                            "documents": [],
                            "generationProgress": {"totalSections": 8, "completedSections": 2},
                        },
                    },
                    "errors": [],
                    "requestId": "req_002",
                    "timestamp": 1713427200001,
                    "apiVersion": "v1",
                }
            },
        )()

        with patch("backend.routers.chat.build_conversation_service", return_value=fake_service):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv_001",
                    "chatId": "chat_002",
                    "instruction": "generate_report",
                    "reply": {
                        "type": "confirm_params",
                        "parameters": _sample_template_instance()["parameters"],
                        "reportContext": {"templateInstance": _sample_template_instance()},
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["answer"]["answerType"], "REPORT")
        self.assertEqual(payload["answer"]["answer"]["reportId"], "rpt_001")
        self.assertEqual(payload["answer"]["answer"]["templateInstance"]["id"], "ti_001")

    def test_post_chat_maps_confirm_param_validation_error_to_http_400(self):
        fake_service = type(
            "FakeConversationService",
            (),
            {
                "send_message": lambda self, data, user_id: (_ for _ in ()).throw(
                    ValidationError("confirm_params requires all required parameters: scope")
                )
            },
        )()

        with patch("backend.routers.chat.build_conversation_service", return_value=fake_service):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv_001",
                    "chatId": "chat_003",
                    "instruction": "generate_report",
                    "reply": {
                        "type": "confirm_params",
                        "parameters": [],
                        "reportContext": {"templateInstance": {"id": "ti_001", "templateId": "tpl_network_daily"}},
                    },
                },
            )

        self.assertEqual(response.status_code, 400)

    def test_post_chat_stream_returns_delta_events_and_final_answer(self):
        fake_service = type(
            "FakeConversationService",
            (),
            {
                "send_message": lambda self, data, user_id: {
                    "conversationId": "conv_001",
                    "chatId": "chat_010",
                    "status": "finished",
                    "steps": [{"code": "generate_report", "status": "running"}],
                    "ask": None,
                    "answer": {
                        "answerType": "REPORT",
                        "answer": {
                            "reportId": "rpt_001",
                            "status": "available",
                            "report": {
                                "basicInfo": {
                                    "id": "rpt_001",
                                    "schemaVersion": "1.0.0",
                                    "mode": "published",
                                    "status": "Success",
                                    "name": "网络运行日报",
                                },
                                "catalogs": [
                                    {
                                        "id": "catalog_1",
                                        "name": "总览",
                                        "sections": [
                                            {
                                                "id": "section_1",
                                                "title": "总体运行态势",
                                                "components": [{"id": "component_1", "type": "markdown"}],
                                            }
                                        ],
                                    }
                                ],
                                "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
                            },
                            "templateInstance": _sample_template_instance(status="completed", capture_stage="report_ready"),
                            "documents": [],
                            "generationProgress": {
                                "totalSections": 1,
                                "completedSections": 1,
                                "totalCatalogs": 1,
                                "completedCatalogs": 1,
                            },
                        },
                    },
                    "errors": [],
                    "requestId": "req_stream",
                    "timestamp": 1713427200200,
                    "apiVersion": "v1",
                }
            },
        )()

        with patch("backend.routers.chat.build_conversation_service", return_value=fake_service):
            with self.client.stream(
                "POST",
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default", "Accept": "text/event-stream"},
                json={
                    "conversationId": "conv_001",
                    "chatId": "chat_010",
                    "instruction": "generate_report",
                    "reply": {
                        "type": "confirm_params",
                        "parameters": _sample_template_instance()["parameters"],
                        "reportContext": {"templateInstance": _sample_template_instance()},
                    },
                },
            ) as response:
                body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"eventType": "status"', body)
        self.assertIn('"eventType": "answer"', body)
        self.assertIn('"eventType": "done"', body)
        self.assertIn('"action": "init_report"', body)
        self.assertIn('"action": "add_catalog"', body)
        self.assertIn('"action": "add_section"', body)
        self.assertIn('"reportId": "rpt_001"', body)


if __name__ == "__main__":
    unittest.main()

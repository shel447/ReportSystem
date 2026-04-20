import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.contexts.conversation.application.models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatResponse,
)
from backend.contexts.report_runtime.application.models import GenerationProgressView, ReportAnswerView
from backend.contexts.report_runtime.domain.models import (
    MarkdownComponent,
    MarkdownDataProperties,
    ParameterConfirmation,
    ReportBasicInfo,
    ReportCatalog,
    ReportDsl,
    ReportLayout,
    ReportSection,
    TemplateInstance,
    GridDefinition,
    template_instance_to_dict,
)
from backend.contexts.template_catalog.domain.models import Parameter, ReportTemplate
from backend.infrastructure.persistence.database import get_db
from backend.routers.chat import router as chat_router
from backend.shared.kernel.errors import ValidationError


def _sample_template_instance(status: str = "ready_for_confirmation", capture_stage: str = "confirm_params"):
    return TemplateInstance(
        id="ti_001",
        schema_version="template-instance.vNext-draft",
        template_id="tpl_network_daily",
        template=ReportTemplate(
            id="tpl_network_daily",
            category="network_operations",
            name="网络运行日报",
            description="面向网络运维中心的统一日报模板。",
            schema_version="template.v3",
        ),
        conversation_id="conv_001",
        chat_id="chat_003",
        status=status,
        capture_stage=capture_stage,
        revision=2,
        parameters=[
            Parameter(
                id="scope",
                label="分析对象",
                input_type="dynamic",
                required=True,
                multi=True,
                interaction_mode="natural_language",
                source="https://example.internal/api/network/scopes/options",
            )
        ],
        parameter_confirmation=ParameterConfirmation(missing_parameter_ids=["scope"], confirmed=False),
        catalogs=[],
    )


def _sample_report_dsl() -> ReportDsl:
    return ReportDsl(
        basic_info=ReportBasicInfo(
            id="rpt_001",
            schema_version="1.0.0",
            mode="published",
            status="Success",
            name="网络运行日报",
        ),
        catalogs=[],
        layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
    )


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
                "send_message": lambda self, data, user_id: ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    status="waiting_user",
                    steps=[],
                    ask=ChatAsk(
                        status="pending",
                        mode="form",
                        type="confirm_params",
                        title="请确认报告诉求",
                        text="请确认报告诉求后开始生成。",
                        parameters=_sample_template_instance().parameters,
                        template_instance=_sample_template_instance(),
                    ),
                    answer=None,
                    errors=[],
                    request_id="req_001",
                    timestamp=1713427200000,
                    api_version="v1",
                )
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
                "send_message": lambda self, data, user_id: ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_002",
                    status="finished",
                    steps=[],
                    ask=None,
                    answer=ChatAnswerEnvelope(
                        answer_type="REPORT",
                        report=ReportAnswerView(
                            report_id="rpt_001",
                            status="generating",
                            report=ReportDsl(
                                basic_info=ReportBasicInfo(
                                    id="rpt_001",
                                    schema_version="1.0.0",
                                    mode="draft",
                                    status="Running",
                                ),
                                catalogs=[],
                                layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
                            ),
                            template_instance=_sample_template_instance(status="generating", capture_stage="generate_report"),
                            documents=[],
                            generation_progress=GenerationProgressView(total_sections=8, completed_sections=2, total_catalogs=0, completed_catalogs=0),
                        ),
                    ),
                    errors=[],
                    request_id="req_002",
                    timestamp=1713427200001,
                    api_version="v1",
                )
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
                        "sourceChatId": "chat_001",
                        "parameters": {"scope": ["hq-network"]},
                        "reportContext": {"templateInstance": template_instance_to_dict(_sample_template_instance())},
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
                        "sourceChatId": "chat_ask_001",
                        "parameters": {},
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
                "send_message": lambda self, data, user_id: ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_010",
                    status="finished",
                    steps=[],
                    ask=None,
                    answer=ChatAnswerEnvelope(
                        answer_type="REPORT",
                        report=ReportAnswerView(
                            report_id="rpt_001",
                            status="available",
                            report=ReportDsl(
                                basic_info=ReportBasicInfo(
                                    id="rpt_001",
                                    schema_version="1.0.0",
                                    mode="published",
                                    status="Success",
                                    name="网络运行日报",
                                ),
                                catalogs=[
                                    ReportCatalog(
                                        id="catalog_1",
                                        name="总览",
                                        sections=[
                                            ReportSection(
                                                id="section_1",
                                                title="总体运行态势",
                                                components=[
                                                    MarkdownComponent(
                                                        id="component_1",
                                                        type="markdown",
                                                        data_properties=MarkdownDataProperties(data_type="static", content="内容"),
                                                    )
                                                ],
                                            )
                                        ],
                                    )
                                ],
                                layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
                            ),
                            template_instance=_sample_template_instance(status="completed", capture_stage="report_ready"),
                            documents=[],
                            generation_progress=GenerationProgressView(
                                total_sections=1,
                                completed_sections=1,
                                total_catalogs=1,
                                completed_catalogs=1,
                            ),
                        ),
                    ),
                    errors=[],
                    request_id="req_stream",
                    timestamp=1713427200200,
                    api_version="v1",
                )
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
                        "sourceChatId": "chat_ask_009",
                        "parameters": {"scope": ["hq-network"]},
                        "reportContext": {"templateInstance": template_instance_to_dict(_sample_template_instance())},
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

    def test_post_chat_reply_requires_source_chat_id(self):
        fake_service = type("FakeConversationService", (), {"send_message": lambda self, data, user_id: data})()
        # 这里保持 422 路径，服务不会被真正执行。

        with patch("backend.routers.chat.build_conversation_service", return_value=fake_service):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv_001",
                    "chatId": "chat_003",
                    "instruction": "generate_report",
                    "reply": {
                        "type": "fill_params",
                        "parameters": {},
                        "reportContext": {"templateInstance": {"id": "ti_001", "templateId": "tpl_network_daily"}},
                    },
                },
            )

        self.assertEqual(response.status_code, 422)

    def test_post_chat_reply_accepts_parameter_value_mapping(self):
        captured = {}

        class FakeConversationService:
            def send_message(self, data, user_id):
                captured["data"] = data
                return ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_003",
                    status="waiting_user",
                    steps=[],
                    ask=None,
                    answer=None,
                    errors=[],
                    request_id="req_003",
                    timestamp=1713427200000,
                    api_version="v1",
                )

        with patch("backend.routers.chat.build_conversation_service", return_value=FakeConversationService()):
            response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json={
                    "conversationId": "conv_001",
                    "chatId": "chat_003",
                    "instruction": "generate_report",
                    "reply": {
                        "type": "fill_params",
                        "sourceChatId": "chat_ask_003",
                        "parameters": {
                            "report_date": ["2026-04-18"],
                            "scope": ["hq-network", "bj-network"],
                        },
                        "reportContext": {"templateInstance": {"id": "ti_001", "templateId": "tpl_network_daily"}},
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["data"].reply.parameters["scope"], ["hq-network", "bj-network"])


if __name__ == "__main__":
    unittest.main()

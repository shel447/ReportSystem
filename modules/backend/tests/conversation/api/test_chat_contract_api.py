import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.contexts.conversation.application.models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatResponse,
)
from src.contexts.report.application.generation_models import GenerationProgressView, ReportAnswerView, report_answer_view_to_dict
from src.contexts.report.application.scenario_models import (
    ReportAskPayload,
    ReportContext,
    ReportSegmentAnswer,
    report_ask_payload_to_dict,
    report_segment_answer_to_dict,
)
from src.contexts.report.domain.generation_models import (
    MarkdownComponent,
    MarkdownDataProperties,
    ParameterConfirmation,
    ReportBasicInfo,
    ReportCatalog,
    ReportDsl,
    ReportGenerateMeta,
    ReportLayout,
    ReportSection,
    TemplateInstance,
    GridDefinition,
    template_instance_to_dict,
)
from src.contexts.report.domain.template_models import Parameter, ReportTemplate
from src.contexts.report.domain.template_models import OutlineDefinition
from src.infrastructure.persistence.database import get_db
from src.main import register_error_handlers
from src.routers.chat import router as chat_router
from src.shared.kernel.errors import ErrorCode, ValidationError
from src.shared.agentflow import FlowEvent, FlowStep


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


def _stream_events_from_response(response: ChatResponse, *, delta: list[dict] | None = None):
    yield FlowEvent(
        run_id="run_internal",
        sequence=1,
        event_type="status",
        status=response.status,
        conversation_id=response.conversation_id,
        chat_id=response.chat_id,
    )
    sequence = 2
    if delta:
        yield FlowEvent(
            run_id="run_internal",
            sequence=sequence,
            event_type="delta",
            status=response.status,
            conversation_id=response.conversation_id,
            chat_id=response.chat_id,
            delta=delta,
        )
        sequence += 1
    if response.answer is not None:
        yield FlowEvent(
            run_id="run_internal",
            sequence=sequence,
            event_type="answer",
            status=response.status,
            conversation_id=response.conversation_id,
            chat_id=response.chat_id,
            answer={"answerType": response.answer.answer_type, "answer": response.answer.payload},
        )
        sequence += 1
    yield FlowEvent(
        run_id="run_internal",
        sequence=sequence,
        event_type="done",
        status=response.status,
        conversation_id=response.conversation_id,
        chat_id=response.chat_id,
    )


class ChatContractApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        register_error_handlers(app)
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
                "chat": lambda self, data, user_id: ChatResponse(
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
                        fields=report_ask_payload_to_dict(
                            ReportAskPayload(
                                parameters=_sample_template_instance().parameters,
                                report_context=ReportContext(template_instance=_sample_template_instance()),
                            )
                        ),
                    ),
                    answer=None,
                    errors=[],
                    request_id="req_001",
                    timestamp=1713427200000,
                    api_version="v1",
                )
            },
        )()

        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
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
                "chat": lambda self, data, user_id: ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_002",
                    status="finished",
                    steps=[],
                    ask=None,
                    answer=ChatAnswerEnvelope(
                        answer_type="REPORT",
                        payload=report_answer_view_to_dict(ReportAnswerView(
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
                        )),
                    ),
                    errors=[],
                    request_id="req_002",
                    timestamp=1713427200001,
                    api_version="v1",
                )
            },
        )()

        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
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
                "chat": lambda self, data, user_id: (_ for _ in ()).throw(
                    ValidationError("confirm_params requires all required parameters: scope")
                )
            },
        )()

        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
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
        self.assertEqual(response.json()["errorCode"], ErrorCode.BASE_PARAM_INVALID)
        self.assertEqual(response.json()["errorMsg"], "confirm_params requires all required parameters: scope")

    def test_post_chat_stream_returns_delta_events_and_final_answer(self):
        fake_service = type(
            "FakeConversationService",
            (),
            {
                "chat": lambda self, data, user_id: ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_010",
                    status="finished",
                    steps=[],
                    ask=None,
                    answer=ChatAnswerEnvelope(
                        answer_type="REPORT",
                        payload=report_answer_view_to_dict(ReportAnswerView(
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
                        )),
                    ),
                    errors=[],
                    request_id="req_stream",
                    timestamp=1713427200200,
                    api_version="v1",
                ),
                "chat_stream": lambda self, data, user_id: _stream_events_from_response(
                    self.chat(data, user_id),
                    delta=[
                        {"action": "init_report", "report": {"reportId": "rpt_001", "structureType": "flow"}},
                        {"action": "add_catalog", "catalog": {"id": "catalog_1", "title": "总览"}},
                        {
                            "action": "add_section",
                            "sectionId": "section_1",
                            "parent": {"type": "catalog", "id": "catalog_1"},
                            "parentCatalogId": "catalog_1",
                            "section": {"id": "section_1", "title": "总体运行态势"},
                        },
                    ],
                ),
            },
        )()

        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
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
        self.assertIn('"structureType": "flow"', body)
        self.assertIn('"action": "add_catalog"', body)
        self.assertIn('"action": "add_section"', body)
        self.assertIn('"reportId": "rpt_001"', body)

    def test_post_chat_reply_requires_source_chat_id(self):
        fake_service = type("FakeConversationService", (), {"chat": lambda self, data, user_id: data})()
        # 业务接口统一使用 ChatBI 错误对象承载请求校验失败。

        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
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

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorCode"], ErrorCode.BASE_PARAM_INVALID)

    def test_post_chat_reply_accepts_parameter_value_mapping(self):
        captured = {}

        class FakeConversationService:
            def chat(self, data, user_id):
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

        with patch("src.routers.chat.build_conversation_service", return_value=FakeConversationService()):
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
        self.assertEqual(captured["data"].reply.raw_payload["parameters"]["scope"], ["hq-network", "bj-network"])

    def test_post_chat_json_and_sse_preserve_report_bootstrap_payload(self):
        captured = []

        class FakeConversationService:
            def chat(self, data, user_id):
                captured.append(data.raw_payload["report"])
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

            def chat_stream(self, data, user_id):
                return _stream_events_from_response(self.chat(data, user_id))

        request_payload = {
            "conversationId": "conv_001",
            "chatId": "chat_003",
            "instruction": "generate_report",
            "question": "重点突出异常项和趋势变化",
            "report": {
                "templateName": "网络运行日报",
                "parameters": [
                    {
                        "id": "scope",
                        "label": "分析范围",
                        "inputType": "dynamic",
                        "required": True,
                        "multi": True,
                        "interactionMode": "natural_language",
                        "source": "/rest/parameter-options/network/scopes",
                        "options": [{"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
                        "values": [{"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
                    }
                ],
            },
        }

        with patch("src.routers.chat.build_conversation_service", return_value=FakeConversationService()):
            json_response = self.client.post(
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default"},
                json=request_payload,
            )
            with self.client.stream(
                "POST",
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default", "Accept": "text/event-stream"},
                json=request_payload,
            ) as stream_response:
                "".join(stream_response.iter_text())

        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(stream_response.status_code, 200)
        self.assertEqual(captured[0]["templateName"], "网络运行日报")
        self.assertEqual(captured[1]["parameters"][0]["values"][0]["value"], "hq-network")

    def test_post_chat_stream_returns_report_segment_delta(self):
        segment = ReportSegmentAnswer(
            report_id="rpt_001",
            section_id="section_1",
            status="available",
            section=ReportSection(id="section_1", title="异常根因", components=[]),
            report_meta=ReportGenerateMeta(status="Success", question="分析异常根因"),
            outline=OutlineDefinition(requirement="分析异常根因"),
        )
        fake_service = type(
            "FakeConversationService",
            (),
            {
                "chat": lambda self, data, user_id: ChatResponse(
                    conversation_id="conv_001",
                    chat_id="chat_020",
                    status="finished",
                    answer=ChatAnswerEnvelope(answer_type="REPORT_SEGMENT", payload=report_segment_answer_to_dict(segment)),
                ),
                "chat_stream": lambda self, data, user_id: _stream_events_from_response(
                    self.chat(data, user_id),
                    delta=[
                        {
                            "action": "add_section",
                            "sectionId": "section_1",
                            "parent": {"type": "section", "id": "section_1"},
                            "section": {"id": "section_1", "title": "异常根因"},
                        }
                    ],
                ),
            },
        )()

        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
            with self.client.stream(
                "POST",
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default", "Accept": "text/event-stream"},
                json={
                    "conversationId": "conv_001",
                    "instruction": "generate_report_segment",
                    "template": {
                        "reportId": "rpt_001",
                        "sectionId": "section_1",
                        "outline": {"requirement": "分析异常根因", "items": []},
                    },
                },
            ) as response:
                body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"answerType": "REPORT_SEGMENT"', body)
        self.assertIn('"action": "add_section"', body)
        self.assertIn('"sectionId": "section_1"', body)

    def test_post_chat_stream_can_forward_runtime_events_without_public_run_id(self):
        class FakeConversationService:
            def chat_stream(self, data, user_id):
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=1,
                    event_type="status",
                    status="running",
                )
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=2,
                    event_type="tool_call",
                    status="running",
                    tool_call={"id": "tool_001", "name": "onequery", "arguments": {"sql": "select 1"}},
                    source_subflow={"type": "subflow", "alias": "analysis", "callId": "subflow_001"},
                )
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=3,
                    event_type="step_delta",
                    status="running",
                    step=FlowStep(
                        code="report.compile",
                        title="编译报告",
                        status="running",
                        parent_step_id="report.generate",
                        step_path=["report", "compile"],
                    ),
                )
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=4,
                    event_type="checkpoint",
                    status="running",
                    checkpoint={"runId": "run_001", "sequence": 3, "reason": "after_tool"},
                )
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=5,
                    event_type="answer",
                    status="finished",
                    answer={"answerType": "TEXT", "answer": {"text": "ok"}},
                )
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=6,
                    event_type="done",
                    status="finished",
                )

        with patch("src.routers.chat.build_conversation_service", return_value=FakeConversationService()):
            with self.client.stream(
                "POST",
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default", "Accept": "text/event-stream"},
                json={"conversationId": "conv_001", "chatId": "chat_001", "question": "你好"},
            ) as response:
                body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('"runId"', body)
        self.assertIn('"conversationId": "conv_001"', body)
        self.assertIn('"eventType": "step_delta"', body)
        self.assertIn('"toolCall": {"id": "tool_001"', body)
        self.assertIn('"sourceSubflow": {"type": "subflow"', body)
        self.assertIn('"parentStepId": "report.generate"', body)
        self.assertIn('"checkpoint": {"sequence": 3', body)
        self.assertIn('"answerType": "TEXT"', body)

    def test_post_chat_stream_converts_runtime_error_to_sse_error_event(self):
        class FakeConversationService:
            def chat_stream(self, data, user_id):
                yield FlowEvent(
                    run_id="run_001",
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    sequence=1,
                    event_type="status",
                    status="running",
                )
                raise ValidationError("输入参数校验失败")

        with patch("src.routers.chat.build_conversation_service", return_value=FakeConversationService()):
            with self.client.stream(
                "POST",
                "/rest/chatbi/v1/chat",
                headers={"X-User-Id": "default", "Accept": "text/event-stream"},
                json={"conversationId": "conv_001", "chatId": "chat_001", "question": "你好", "requestId": "req_001"},
            ) as response:
                body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn('"eventType": "status"', body)
        self.assertIn('"eventType": "error"', body)
        self.assertIn('"eventType": "done"', body)
        self.assertIn('"status": "failed"', body)
        self.assertIn(ErrorCode.BASE_PARAM_INVALID, body)
        self.assertIn('"requestId": "req_001"', body)
        self.assertNotIn('"runId"', body)

    def test_stop_chat_endpoint_uses_chat_id_and_old_run_endpoints_are_removed(self):
        class FakeConversationService:
            def stop_chat(self, chat_id, user_id):
                self.user_id = user_id
                return chat_id == "chat_001"

        fake_service = FakeConversationService()
        with patch("src.routers.chat.build_conversation_service", return_value=fake_service):
            stop_response = self.client.post("/rest/chatbi/v1/chat/chat_001/stop", headers={"X-User-Id": "default"})
            old_cancel_response = self.client.post("/rest/chatbi/v1/chat/runs/run_001/cancel", headers={"X-User-Id": "default"})
            old_input_response = self.client.post(
                "/rest/chatbi/v1/chat/runs/run_001/input",
                headers={"X-User-Id": "default"},
                json={"text": "继续", "payload": {"foo": "bar"}},
            )

        self.assertEqual(stop_response.status_code, 200)
        self.assertEqual(stop_response.json(), {"chatId": "chat_001", "status": "stop_requested"})
        self.assertEqual(fake_service.user_id, "default")
        self.assertEqual(old_cancel_response.status_code, 404)
        self.assertEqual(old_input_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

import unittest
from copy import deepcopy
from dataclasses import is_dataclass
from types import SimpleNamespace

from src.contexts.conversation.application.models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatReply,
    ChatResponse,
    ForkSessionCommand,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    conversation_message_action_to_dict,
    conversation_message_content_to_dict,
    conversation_message_meta_to_dict,
)
from src.contexts.conversation.application.ports import GuardrailResult, HostedChat, HostedConversation
from src.contexts.report.application.generation_models import GenerationProgressView, ReportAnswerView
from src.contexts.report.application.parameter_service import ReportParameterService
from src.contexts.conversation.application.services import ConversationService
from src.contexts.report.application.scenario_models import ReportContext, ReportReplyPayload
from src.contexts.report.application.scenario_service import ReportScenarioService, missing_required_parameters
from src.contexts.conversation.application.scenarios import ScenarioDispatchService, ScenarioRegistry
from src.infrastructure.scenarios.report_conversation import report_scenario_registration
from src.contexts.report.domain.generation_models import (
    ParameterConfirmation,
    ReportBasicInfo,
    ReportDsl,
    ReportLayout,
    TemplateInstance,
    GridDefinition,
)
from src.contexts.report.domain.template_instance_builder import instantiate_template_instance
from src.contexts.report.application.template_models import ParameterOptionsResult
from src.contexts.report.domain.template_models import ParameterValue, report_template_from_dict
from src.shared.kernel.errors import UnsupportedCapabilityError


def _service():
    return ReportScenarioService(
        template_service=SimpleNamespace(),
        template_repository=SimpleNamespace(),
        generation_service=SimpleNamespace(),
        parameter_service=ReportParameterService(),
    )


def _scoped_template():
    return {
        "id": "tpl_scoped",
        "category": "network_operations",
        "name": "作用域参数模板",
        "description": "验证目录和章节级参数。",
        "schemaVersion": "template.v3",
        "parameters": [],
        "catalogs": [
            {
                "id": "catalog_overview",
                "title": "运行概览",
                "sections": [
                    {
                        "id": "section_scope",
                        "parameters": [
                            {
                                "id": "scope",
                                "label": "分析对象",
                                "inputType": "free_text",
                                "required": True,
                                "multi": True,
                                "interactionMode": "form",
                            }
                        ],
                        "outline": {
                            "requirement": "分析{$scope.label}的总体运行态势。",
                            "items": [],
                        },
                        "content": {
                            "datasets": [],
                            "presentation": {"kind": "mixed", "blocks": []},
                        },
                    }
                ],
            }
        ],
    }


class ReportScenarioServiceScopedParameterTests(unittest.TestCase):
    def test_extract_parameter_values_reads_section_scoped_parameters(self):
        service = _service()

        values = service.parameter_service.extract_values(
            template=report_template_from_dict(_scoped_template()),
            question="请分析华东、华北的运行态势",
            user_id="default",
        )

        self.assertIn("scope", values)
        self.assertEqual(values["scope"][0].label, "请分析华东、华北的运行态势")

    def test_missing_required_parameters_includes_section_scoped_parameters(self):
        template = report_template_from_dict(_scoped_template())
        instance = instantiate_template_instance(
            instance_id="ti_001",
            template=template,
            conversation_id="conv_001",
            chat_id="chat_001",
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values={},
        )

        missing = missing_required_parameters(template=template, template_instance=instance)

        self.assertEqual([item.id for item in missing], ["scope"])

    def test_instantiate_template_instance_preserves_section_content_and_part_runtime_context(self):
        template = report_template_from_dict({
            "id": "tpl_composite_instance",
            "category": "network_operations",
            "name": "复合表实例模板",
            "description": "验证模板实例保留 section.content。",
            "schemaVersion": "template.v3",
            "parameters": [
                {
                    "id": "scope",
                    "label": "分析对象",
                    "inputType": "dynamic",
                    "required": True,
                    "multi": False,
                    "interactionMode": "form",
                }
            ],
            "catalogs": [
                {
                    "id": "catalog_overview",
                    "title": "运行概览",
                    "sections": [
                        {
                            "id": "section_device_profile",
                            "outline": {
                                "requirement": "分析{@scope_item}的设备巡检结果。",
                                "items": [
                                    {
                                        "id": "scope_item",
                                        "label": "分析对象",
                                        "kind": "search_target",
                                        "required": True,
                                        "sourceParameterId": "scope",
                                    }
                                ],
                            },
                            "content": {
                                "datasets": [
                                    {
                                        "id": "dataset_device_basic",
                                        "name": "设备基础信息",
                                        "sourceType": "sql",
                                        "sourceRef": "sql.network.device_basic",
                                    }
                                ],
                                "presentation": {
                                    "kind": "mixed",
                                    "blocks": [
                                        {
                                            "id": "block_device_inspection",
                                            "type": "composite_table",
                                            "title": "核心设备巡检信息",
                                            "parts": [
                                                {
                                                    "id": "part_basic_info",
                                                    "title": "基础信息",
                                                    "sourceType": "query",
                                                    "datasetId": "dataset_device_basic",
                                                    "tableLayout": {"kind": "table", "showHeader": True},
                                                },
                                                {
                                                    "id": "part_inspection_summary",
                                                    "title": "巡检问题及建议",
                                                    "sourceType": "summary",
                                                    "summarySpec": {
                                                        "partIds": ["part_basic_info"],
                                                        "rows": [{"id": "major_issue", "title": "主要问题"}],
                                                        "prompt": "总结问题。",
                                                    },
                                                },
                                            ],
                                        }
                                    ],
                                },
                            },
                        }
                    ],
                }
            ],
        })

        instance = instantiate_template_instance(
            instance_id="ti_002",
            template=template,
            conversation_id="conv_001",
            chat_id="chat_001",
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values={
                "scope": [
                    ParameterValue(label="总部网络", value="hq-network", query="scope_id = 'hq-network'")
                ]
            },
        )

        section = instance.catalogs[0].sections[0]
        composite_block = section.content.presentation.blocks[0]
        query_part = composite_block.parts[0]
        summary_part = composite_block.parts[1]

        self.assertTrue(is_dataclass(instance.template))
        self.assertTrue(is_dataclass(instance.catalogs[0]))
        self.assertTrue(is_dataclass(section))
        self.assertTrue(is_dataclass(composite_block))
        self.assertTrue(is_dataclass(query_part))
        self.assertEqual(section.content.datasets[0].id, "dataset_device_basic")
        self.assertEqual(query_part.runtime_context.status, "pending")
        self.assertEqual(query_part.runtime_context.resolved_dataset_id, "dataset_device_basic")
        self.assertEqual(query_part.runtime_context.resolved_query, "scope_id = 'hq-network'")
        self.assertEqual(summary_part.runtime_context.status, "pending")
        self.assertEqual(summary_part.runtime_context.resolved_part_ids, ["part_basic_info"])
        self.assertEqual(summary_part.runtime_context.prompt, "总结问题。")


class _HistoryGateway:
    def __init__(self) -> None:
        self.conversations: dict[str, HostedConversation] = {}
        self.chats: dict[str, HostedChat] = {}

    def create_conversation(self, *, title: str, description: str | None, user_id: str):
        row = HostedConversation(conversation_id=f"conv_{len(self.conversations) + 1:03d}", title=title)
        self.conversations[row.conversation_id] = row
        return row

    def create_chat(self, *, conversation_id: str, question: str, user_id: str):
        row = HostedChat(chat_id=f"chat_{len(self.chats) + 1}", conversation_id=conversation_id, question=question)
        self.chats[row.chat_id] = row
        return row

    def import_chat(self, *, chat: HostedChat, user_id: str) -> None:
        self.chats[chat.chat_id] = deepcopy(chat)

    def query_chat_history(self, *, conversation_id: str, page_num: int, page_size: int, user_id: str):
        return [deepcopy(item) for item in self.chats.values() if item.conversation_id == conversation_id]

    def get_chat_detail(self, *, chat_id: str, user_id: str):
        row = self.chats.get(chat_id)
        return deepcopy(row) if row else None

    def list_conversations(self, *, page_num: int, page_size: int, user_id: str):
        return list(self.conversations.values())


class _AllowGuardrail:
    def check_question(self, question: str, *, user_id: str) -> GuardrailResult:
        return GuardrailResult(passed=True)

    def check_answer(self, answer: str, *, user_id: str) -> GuardrailResult:
        return GuardrailResult(passed=True)

    def check_application_security(self, *, kind: str, content: str, user_id: str) -> GuardrailResult:
        return GuardrailResult(passed=True)


class _RuntimeService:
    def __init__(self) -> None:
        self.instance = None

    def get_latest_template_instance(self, *, conversation_id: str, user_id: str):
        return self.instance

    def persist_template_instance(self, instance, *, user_id: str):
        self.instance = deepcopy(instance)
        return self.instance

    def generate_report_from_template_instance(self, **kwargs):
        return ReportAnswerView(
            report_id="rpt_001",
            status="available",
            report=ReportDsl(
                basic_info=ReportBasicInfo(
                    id="rpt_001",
                    schema_version="1.0.0",
                    mode="published",
                    status="Success",
                ),
                catalogs=[],
                layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
            ),
            template_instance=deepcopy(self.instance),
            documents=[],
            generation_progress=GenerationProgressView(
                total_sections=0,
                completed_sections=0,
                total_catalogs=0,
                completed_catalogs=0,
            ),
        )


def _conversation_service(*, template, history_gateway, runtime_service, audit_dispatcher=None):
    report_scenario_service = ReportScenarioService(
        template_service=SimpleNamespace(get_template=lambda template_id: template),
        template_repository=SimpleNamespace(list_all=lambda: [template]),
        generation_service=runtime_service,
        parameter_service=ReportParameterService(),
    )
    registry = ScenarioRegistry()
    registry.register(report_scenario_registration(report_service=SimpleNamespace(chat=report_scenario_service.handle)))
    registry.seal()
    return ConversationService(
        history_gateway=history_gateway,
        guardrail_gateway=_AllowGuardrail(),
        scenario_dispatcher=ScenarioDispatchService(registry=registry),
        audit_dispatcher=audit_dispatcher,
    )


class ConversationServiceAskStatusTests(unittest.TestCase):
    def test_successful_chat_submits_best_effort_audit_event(self):
        template = report_template_from_dict({
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [],
        })
        events = []
        service = _conversation_service(
            template=template,
            history_gateway=_HistoryGateway(),
            runtime_service=_RuntimeService(),
            audit_dispatcher=SimpleNamespace(submit=events.append),
        )

        response = service.chat(
            data=ChatCommand(instruction="generate_report", question="帮我生成网络运行日报"),
            user_id="default",
        )

        self.assertEqual(events[0].operation, "conversation.chat")
        self.assertIn(response.chat_id, events[0].target_obj)

    def test_fork_is_explicitly_unavailable_while_agentcore_has_no_contract(self):
        template = report_template_from_dict({
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [],
        })
        history_gateway = _HistoryGateway()
        service = _conversation_service(
            template=template,
            history_gateway=history_gateway,
            runtime_service=_RuntimeService(),
        )
        first = service.chat(
            data=ChatCommand(instruction="generate_report", question="帮我生成网络运行日报"),
            user_id="default",
        )

        with self.assertRaises(UnsupportedCapabilityError):
            service.fork_session(
                data=ForkSessionCommand(
                    source_kind="chat",
                    source_conversation_id=first.conversation_id,
                    source_chat_id=first.chat_id,
                ),
                user_id="default",
            )

    def test_reply_marks_previous_ask_as_replied(self):
        template = report_template_from_dict({
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [
                {
                    "id": "report_date",
                    "label": "报告日期",
                    "inputType": "date",
                    "required": True,
                    "multi": False,
                    "interactionMode": "form",
                }
            ],
            "catalogs": [],
        })
        history_gateway = _HistoryGateway()
        runtime_service = _RuntimeService()
        service = _conversation_service(
            template=template,
            history_gateway=history_gateway,
            runtime_service=runtime_service,
        )

        first = service.chat(
            data=ChatCommand(instruction="generate_report", question="帮我生成 2026-04-18 网络运行日报"),
            user_id="default",
        )
        self.assertEqual(first.ask.status, "pending")

        second = service.chat(
            data=ChatCommand(
                conversation_id=first.conversation_id,
                instruction="generate_report",
                reply=ChatReply(
                    type="fill_params",
                    source_chat_id=first.chat_id,
                    raw_payload={
                        "type": "fill_params",
                        "sourceChatId": first.chat_id,
                        "parameters": {"report_date": ["2026-04-18"]},
                        "reportContext": {"templateInstance": {}},
                    },
                ),
            ),
            user_id="default",
        )

        self.assertEqual(second.ask.status, "pending")
        messages = list(history_gateway.chats.values())
        self.assertEqual(messages[0].response_payload["ask"]["status"], "replied")
        self.assertEqual(messages[-1].response_payload["ask"]["status"], "pending")
        self.assertTrue(all(row.meta["scenario"]["key"] == "report" for row in messages))

    def test_reply_uses_source_chat_id_instead_of_latest_pending_guess(self):
        template = report_template_from_dict({
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [
                {
                    "id": "report_date",
                    "label": "报告日期",
                    "inputType": "date",
                    "required": True,
                    "multi": False,
                    "interactionMode": "form",
                }
            ],
            "catalogs": [],
        })
        history_gateway = _HistoryGateway()
        runtime_service = _RuntimeService()
        service = _conversation_service(
            template=template,
            history_gateway=history_gateway,
            runtime_service=runtime_service,
        )

        first = service.chat(
            data=ChatCommand(instruction="generate_report", question="帮我生成 2026-04-18 网络运行日报"),
            user_id="default",
        )
        second = service.chat(
            data=ChatCommand(
                conversation_id=first.conversation_id,
                instruction="generate_report",
                question="我还想再看一遍同一份日报",
            ),
            user_id="default",
        )

        third = service.chat(
            data=ChatCommand(
                conversation_id=first.conversation_id,
                instruction="generate_report",
                reply=ChatReply(
                    type="fill_params",
                    source_chat_id=first.chat_id,
                    raw_payload={
                        "type": "fill_params",
                        "sourceChatId": first.chat_id,
                        "parameters": {"report_date": ["2026-04-18"]},
                        "reportContext": {"templateInstance": {}},
                    },
                ),
            ),
            user_id="default",
        )

        self.assertEqual(third.ask.status, "pending")
        messages = list(history_gateway.chats.values())
        self.assertEqual(messages[0].chat_id, first.chat_id)
        self.assertEqual(messages[0].response_payload["ask"]["status"], "replied")
        self.assertEqual(messages[1].chat_id, second.chat_id)
        self.assertEqual(messages[1].response_payload["ask"]["status"], "pending")


if __name__ == "__main__":
    unittest.main()

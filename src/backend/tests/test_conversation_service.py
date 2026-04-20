import unittest
from copy import deepcopy
from dataclasses import is_dataclass
from types import SimpleNamespace

from backend.contexts.conversation.application.models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatReply,
    ChatResponse,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    conversation_message_action_to_dict,
    conversation_message_content_to_dict,
    conversation_message_meta_to_dict,
)
from backend.contexts.report_runtime.application.models import GenerationProgressView, ReportAnswerView
from backend.contexts.conversation.application.services import ConversationService, _missing_required_parameters
from backend.contexts.report_runtime.domain.models import (
    ParameterConfirmation,
    ReportBasicInfo,
    ReportDsl,
    ReportLayout,
    TemplateInstance,
    GridDefinition,
)
from backend.contexts.report_runtime.domain.services import instantiate_template_instance
from backend.contexts.template_catalog.application.models import ParameterOptionsResult
from backend.contexts.template_catalog.domain.models import ParameterValue, report_template_from_dict


def _service():
    return ConversationService(
        conversation_repository=SimpleNamespace(),
        chat_repository=SimpleNamespace(),
        template_catalog_service=SimpleNamespace(),
        template_repository=SimpleNamespace(),
        runtime_service=SimpleNamespace(),
        parameter_option_service=SimpleNamespace(resolve=lambda **kwargs: ParameterOptionsResult(options=[])),
        db=None,
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


class ConversationServiceScopedParameterTests(unittest.TestCase):
    def test_extract_parameter_values_reads_section_scoped_parameters(self):
        service = _service()

        values = service._extract_parameter_values(report_template_from_dict(_scoped_template()), "请分析华东、华北的运行态势")

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

        missing = _missing_required_parameters(template=template, template_instance=instance)

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


class _InMemoryConversation:
    def __init__(self, conversation_id: str, user_id: str) -> None:
        self.id = conversation_id
        self.user_id = user_id
        self.title = ""
        self.status = "active"
        self.updated_at = None


class _InMemoryChat:
    def __init__(self, chat_id: str, conversation_id: str, user_id: str, role: str, content: dict, action=None, meta=None) -> None:
        self.id = chat_id
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.role = role
        self.content = content
        self.action = action
        self.meta = meta
        self.created_at = None


class _ConversationRepository:
    def __init__(self) -> None:
        self.rows: dict[str, _InMemoryConversation] = {}

    def get(self, conversation_id: str, *, user_id: str):
        row = self.rows.get(conversation_id)
        if row and row.user_id == user_id:
            return row
        return None

    def create(self, *, conversation_id: str | None, user_id: str):
        row = _InMemoryConversation(conversation_id or "conv_001", user_id)
        self.rows[row.id] = row
        return row

    def save(self, row):
        self.rows[row.id] = row
        return row

    def list_all(self, *, user_id: str):
        return [row for row in self.rows.values() if row.user_id == user_id]


class _ChatRepository:
    def __init__(self) -> None:
        self.rows: list[_InMemoryChat] = []

    def append_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: str,
        content: ConversationMessageContent,
        action: ConversationMessageAction | None = None,
        meta: ConversationMessageMeta | None = None,
        chat_id=None,
    ):
        row = _InMemoryChat(
            chat_id or f"chat_{len(self.rows) + 1}",
            conversation_id,
            user_id,
            role,
            conversation_message_content_to_dict(content),
            conversation_message_action_to_dict(action),
            conversation_message_meta_to_dict(meta),
        )
        self.rows.append(row)
        return row

    def list_by_conversation(self, conversation_id: str, *, user_id: str):
        return [row for row in self.rows if row.conversation_id == conversation_id and row.user_id == user_id]

    def mark_ask_replied(self, *, conversation_id: str, user_id: str, source_chat_id: str) -> bool:
        for row in self.rows:
            if row.id != source_chat_id or row.conversation_id != conversation_id or row.user_id != user_id or row.role != "assistant":
                continue
            response = row.content.get("response") if isinstance(row.content, dict) else None
            ask = response.get("ask") if isinstance(response, dict) else None
            if isinstance(ask, dict) and ask.get("status") == "pending":
                ask["status"] = "replied"
                return True
        return False


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


class ConversationServiceAskStatusTests(unittest.TestCase):
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
        conversation_repository = _ConversationRepository()
        chat_repository = _ChatRepository()
        runtime_service = _RuntimeService()
        service = ConversationService(
            conversation_repository=conversation_repository,
            chat_repository=chat_repository,
            template_catalog_service=SimpleNamespace(
                get_template=lambda template_id: template,
            ),
            template_repository=SimpleNamespace(list_all=lambda: [template]),
            runtime_service=runtime_service,
            parameter_option_service=SimpleNamespace(resolve=lambda **kwargs: ParameterOptionsResult(options=[])),
            db=None,
        )

        first = service.send_message(
            data=ChatCommand(instruction="generate_report", question="帮我生成 2026-04-18 网络运行日报"),
            user_id="default",
        )
        self.assertEqual(first.ask.status, "pending")

        second = service.send_message(
            data=ChatCommand(
                conversation_id=first.conversation_id,
                instruction="generate_report",
                reply=ChatReply(
                    type="fill_params",
                    source_chat_id=first.chat_id,
                    parameters={"report_date": ["2026-04-18"]},
                    template_instance=runtime_service.instance,
                ),
            ),
            user_id="default",
        )

        self.assertEqual(second.ask.status, "pending")
        assistant_messages = [row for row in chat_repository.rows if row.role == "assistant"]
        self.assertEqual(assistant_messages[0].content["response"]["ask"]["status"], "replied")
        self.assertEqual(assistant_messages[-1].content["response"]["ask"]["status"], "pending")

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
        conversation_repository = _ConversationRepository()
        chat_repository = _ChatRepository()
        runtime_service = _RuntimeService()
        service = ConversationService(
            conversation_repository=conversation_repository,
            chat_repository=chat_repository,
            template_catalog_service=SimpleNamespace(
                get_template=lambda template_id: template,
            ),
            template_repository=SimpleNamespace(list_all=lambda: [template]),
            runtime_service=runtime_service,
            parameter_option_service=SimpleNamespace(resolve=lambda **kwargs: ParameterOptionsResult(options=[])),
            db=None,
        )

        first = service.send_message(
            data=ChatCommand(instruction="generate_report", question="帮我生成 2026-04-18 网络运行日报"),
            user_id="default",
        )
        second = service.send_message(
            data=ChatCommand(
                conversation_id=first.conversation_id,
                instruction="generate_report",
                question="我还想再看一遍同一份日报",
            ),
            user_id="default",
        )

        third = service.send_message(
            data=ChatCommand(
                conversation_id=first.conversation_id,
                instruction="generate_report",
                reply=ChatReply(
                    type="fill_params",
                    source_chat_id=first.chat_id,
                    parameters={"report_date": ["2026-04-18"]},
                    template_instance=runtime_service.instance,
                ),
            ),
            user_id="default",
        )

        self.assertEqual(third.ask.status, "pending")
        assistant_messages = [row for row in chat_repository.rows if row.role == "assistant"]
        self.assertEqual(assistant_messages[0].id, first.chat_id)
        self.assertEqual(assistant_messages[0].content["response"]["ask"]["status"], "replied")
        self.assertEqual(assistant_messages[1].id, second.chat_id)
        self.assertEqual(assistant_messages[1].content["response"]["ask"]["status"], "pending")


if __name__ == "__main__":
    unittest.main()

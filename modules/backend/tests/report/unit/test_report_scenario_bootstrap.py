import unittest
from types import SimpleNamespace

from src.contexts.report.application.parameter_service import ReportParameterService
from src.contexts.report.application.scenario_models import (
    ReportScenarioCommand,
    report_bootstrap_request_from_dict,
)
from src.contexts.report.application.scenario_service import ReportScenarioService
from src.contexts.report.application.template_service import ReportTemplateService
from src.contexts.conversation.domain.models import ChatContext
from src.contexts.report.domain.template_models import report_template_from_dict
from src.contexts.report.infrastructure.conversation import ReportConversationScenarioCodec
from src.shared.kernel.errors import ConflictError, NotFoundError, ValidationError


def _template():
    return report_template_from_dict(
        {
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [
                {
                    "id": "reportDate",
                    "label": "统计日期",
                    "inputType": "date",
                    "required": True,
                    "multi": False,
                    "interactionMode": "form",
                },
                {
                    "id": "scope",
                    "label": "分析范围",
                    "inputType": "dynamic",
                    "required": True,
                    "multi": True,
                    "interactionMode": "natural_language",
                    "source": "/rest/parameter-options/network/scopes",
                },
            ],
            "catalogs": [
                {
                    "id": "catalog_overview",
                    "title": "运行概览",
                    "sections": [
                        {
                            "id": "section_detail",
                            "parameters": [
                                {
                                    "id": "detailLevel",
                                    "label": "明细层级",
                                    "inputType": "enum",
                                    "required": False,
                                    "multi": False,
                                    "interactionMode": "form",
                                    "options": [{"label": "站点", "value": "site", "query": "level = 'site'"}],
                                }
                            ],
                            "outline": {"requirement": "分析网络运行状态", "items": []},
                            "content": {"datasets": [], "presentation": {"kind": "mixed", "blocks": []}},
                        }
                    ],
                }
            ],
        }
    )


def _scope_snapshot(**overrides):
    payload = {
        "id": "scope",
        "label": "分析范围",
        "inputType": "dynamic",
        "required": True,
        "multi": True,
        "interactionMode": "natural_language",
        "source": "/rest/parameter-options/network/scopes",
        "options": [{"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
        "defaultValue": [],
        "values": [{"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
    }
    payload.update(overrides)
    return payload


def _bootstrap(parameters):
    return report_bootstrap_request_from_dict({"templateName": "网络运行日报", "parameters": parameters})


class _TemplateRepository:
    def __init__(self, templates):
        self.templates = list(templates)

    def list_all(self):
        return list(self.templates)


class _GenerationService:
    def __init__(self, latest=None):
        self.latest = latest
        self.persisted = None

    def get_latest_template_instance(self, *, conversation_id, user_id):
        return self.latest

    def persist_template_instance(self, instance, *, user_id):
        self.persisted = instance
        return instance


class _OptionsGateway:
    def __init__(self):
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return {"options": []}


class ReportScenarioBootstrapTests(unittest.TestCase):
    def test_bootstrap_merges_external_snapshot_and_extracts_missing_root_parameter(self):
        gateway = _OptionsGateway()
        generation = _GenerationService()
        template_repository = _TemplateRepository([_template()])
        service = ReportScenarioService(
            template_service=ReportTemplateService(repository=template_repository, schema_gateway=SimpleNamespace()),
            template_repository=template_repository,
            generation_service=generation,
            parameter_service=ReportParameterService(options_gateway=gateway),
        )

        result = service.handle(
            command=ReportScenarioCommand(
                conversation_id="conv_001",
                chat_id="chat_001",
                user_id="user_001",
                instruction="generate_report",
                question="请生成 2026-06-02 的网络运行日报，重点突出异常项和趋势变化",
                bootstrap=_bootstrap([_scope_snapshot()]),
            )
        )

        values = {item.id: item.values for item in generation.persisted.parameters}
        self.assertEqual(values["reportDate"][0].value, "2026-06-02")
        self.assertEqual(values["scope"][0].query, "scope_id = 'hq-network'")
        self.assertEqual(generation.persisted.template.parameters[1].options[0].label, "总部网络")
        self.assertEqual(result.ask.type, "confirm_params")
        self.assertEqual(gateway.calls, [])

    def test_bootstrap_uses_external_dynamic_options_without_refetching(self):
        gateway = _OptionsGateway()
        parameter_service = ReportParameterService(options_gateway=gateway)
        snapshot = _scope_snapshot(values=[])
        merged_template, values = parameter_service.merge_bootstrap_values(
            template=_template(),
            bootstrap=_bootstrap([snapshot]),
            question="请生成总部网络的日报",
            user_id="user_001",
        )

        self.assertEqual(values["scope"][0].value, "hq-network")
        self.assertEqual(merged_template.parameters[1].options[0].label, "总部网络")
        self.assertEqual(gateway.calls, [])

    def test_bootstrap_rejects_invalid_root_parameter_snapshots(self):
        parameter_service = ReportParameterService()
        invalid_cases = {
            "unknown parameter": [_scope_snapshot(id="unknown")],
            "scoped parameter": [
                {
                    "id": "detailLevel",
                    "label": "明细层级",
                    "inputType": "enum",
                    "required": False,
                    "multi": False,
                    "interactionMode": "form",
                    "options": [{"label": "站点", "value": "site", "query": "level = 'site'"}],
                }
            ],
            "duplicate parameter": [_scope_snapshot(), _scope_snapshot()],
            "definition conflict": [_scope_snapshot(multi=False)],
            "value outside options": [
                _scope_snapshot(values=[{"label": "分支网络", "value": "branch-network", "query": "scope_id = 'branch-network'"}])
            ],
            "single parameter with multiple values": [
                {
                    "id": "reportDate",
                    "label": "统计日期",
                    "inputType": "date",
                    "required": True,
                    "multi": False,
                    "interactionMode": "form",
                    "values": [
                        {"label": "2026-06-01", "value": "2026-06-01", "query": "dt = '2026-06-01'"},
                        {"label": "2026-06-02", "value": "2026-06-02", "query": "dt = '2026-06-02'"},
                    ],
                }
            ],
        }

        for label, parameters in invalid_cases.items():
            with self.subTest(label=label), self.assertRaises(ValidationError):
                parameter_service.merge_bootstrap_values(
                    template=_template(),
                    bootstrap=_bootstrap(parameters),
                    question="生成日报",
                    user_id="user_001",
                )

    def test_bootstrap_requires_question_and_rejects_existing_instance(self):
        template_repository = _TemplateRepository([_template()])
        template_service = ReportTemplateService(repository=template_repository, schema_gateway=SimpleNamespace())
        bootstrap = _bootstrap([_scope_snapshot()])

        for latest, question, error_type in (
            (None, None, ValidationError),
            (SimpleNamespace(id="ti_existing"), "生成日报", ConflictError),
        ):
            with self.subTest(error_type=error_type.__name__):
                service = ReportScenarioService(
                    template_service=template_service,
                    template_repository=template_repository,
                    generation_service=_GenerationService(latest=latest),
                    parameter_service=ReportParameterService(),
                )
                with self.assertRaises(error_type):
                    service.handle(
                        command=ReportScenarioCommand(
                            conversation_id="conv_001",
                            chat_id="chat_001",
                            user_id="user_001",
                            instruction="generate_report",
                            question=question,
                            bootstrap=bootstrap,
                        )
                    )

    def test_template_name_lookup_requires_exact_unique_match(self):
        template = _template()
        for templates, template_name, error_type in (
            ([], "网络运行日报", NotFoundError),
            ([template, template], "网络运行日报", ConflictError),
            ([template], "网络运行周报", NotFoundError),
        ):
            with self.subTest(template_name=template_name, error_type=error_type.__name__):
                service = ReportTemplateService(repository=_TemplateRepository(templates), schema_gateway=SimpleNamespace())
                with self.assertRaises(error_type):
                    service.get_template_by_name(template_name)

    def test_bootstrap_parser_rejects_non_strict_payloads_and_reply_combination(self):
        invalid_payloads = (
            {"templateName": "网络运行日报", "parameters": [_scope_snapshot(required="true")]},
            {"templateName": "网络运行日报", "parameters": [_scope_snapshot(values=[{"value": "hq-network"}])]},
            {"templateName": "网络运行日报", "parameters": [_scope_snapshot(runtimeContext={})]},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                report_bootstrap_request_from_dict(payload)

        with self.assertRaises(ValidationError):
            ReportConversationScenarioCodec().decode(
                context=ChatContext(
                    conversation_id="conv_001",
                    chat_id="chat_001",
                    user_id="user_001",
                    instruction="generate_report",
                    scenario_key="report",
                ),
                payload={
                    "report": {"templateName": "网络运行日报"},
                    "reply": {"type": "fill_params", "sourceChatId": "chat_000"},
                },
            )


if __name__ == "__main__":
    unittest.main()

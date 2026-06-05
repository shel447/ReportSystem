import unittest
from types import SimpleNamespace

from src.contexts.report.application.parameter_service import ReportParameterService
from src.contexts.report.application.generation_models import (
    GenerationProgressView,
    ReportAnswerView,
    ReportSegmentPreview,
    SectionRegenerationContext,
)
from src.contexts.report.application.scenario_models import (
    ReportContext,
    ReportReplyPayload,
    ReportScenarioCommand,
    report_bootstrap_request_from_dict,
)
from src.contexts.report.application.scenario_service import ReportScenarioService
from src.contexts.report.application.template_service import ReportTemplateService
from src.contexts.conversation.domain.models import ScenarioInvocationContext
from src.contexts.report.domain.generation_models import (
    GridDefinition,
    ReportBasicInfo,
    ReportDsl,
    ReportLayout,
    ReportGenerateMeta,
    ReportSection,
    TemplateInstanceSection,
    TemplateInstanceSectionContent,
    TemplateInstancePresentationDefinition,
    SectionRuntimeContext,
)
from src.contexts.report.domain.template_models import OutlineDefinition, report_template_from_dict
from src.contexts.report.infrastructure.scenario_registration import ReportScenarioCodec
from src.shared.agentflow import FlowNode, InMemoryFlowRuntime, SequentialFlow, SubflowRegistry
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

    def get(self, template_id):
        for template in self.templates:
            if template.id == template_id:
                return template
        return None


class _GenerationService:
    def __init__(self, latest=None):
        self.latest = latest
        self.persisted = None

    def get_latest_template_instance(self, *, conversation_id, user_id):
        return self.latest

    def persist_template_instance(self, instance, *, user_id):
        self.persisted = instance
        return instance

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
                    name="网络运行日报",
                ),
                catalogs=[],
                layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
            ),
            template_instance=self.persisted,
            documents=[],
            generation_progress=GenerationProgressView(
                total_sections=0,
                completed_sections=0,
                total_catalogs=0,
                completed_catalogs=0,
            ),
        )

    def load_section_regeneration_context(self, **kwargs):
        return SectionRegenerationContext(
            template_instance=SimpleNamespace(id="ti_001"),
            source_section=TemplateInstanceSection(
                id=kwargs["section_id"],
                outline=OutlineDefinition(requirement="原始章节"),
                content=TemplateInstanceSectionContent(
                    presentation=TemplateInstancePresentationDefinition(kind="mixed"),
                ),
                runtime_context=SectionRuntimeContext(),
                skeleton_status="reusable",
                user_edited=False,
            ),
        )

    def apply_section_regeneration_outline(self, *, context, outline):
        context.preview_section = TemplateInstanceSection(
            id=context.source_section.id,
            outline=outline,
            content=context.source_section.content,
            runtime_context=SectionRuntimeContext(),
            skeleton_status="reusable",
            user_edited=True,
        )
        return context

    def compile_section_regeneration(self, *, context):
        return ReportSegmentPreview(
            section=ReportSection(id=context.preview_section.id, title="异常根因", components=[]),
            report_meta=ReportGenerateMeta(status="Success", question="分析异常根因"),
        )


class _OptionsGateway:
    def __init__(self):
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return {"options": []}


class _ScopeOptionsGateway:
    def __init__(self):
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "options": [
                {"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"},
                {"label": "分支网络", "value": "branch-network", "query": "scope_id = 'branch-network'"},
            ],
            "defaultValue": [{"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
        }


class ReportScenarioBootstrapTests(unittest.TestCase):
    def test_initial_report_flow_finishes_preparation_steps_without_generation_step(self):
        service = ReportScenarioService(
            template_service=ReportTemplateService(repository=_TemplateRepository([_template()]), schema_gateway=SimpleNamespace()),
            template_repository=_TemplateRepository([_template()]),
            generation_service=_GenerationService(),
            parameter_service=ReportParameterService(options_gateway=_ScopeOptionsGateway()),
        )

        events = InMemoryFlowRuntime().run_sync(service.create_flow(
            command=ReportScenarioCommand(
                conversation_id="conv_001",
                chat_id="chat_001",
                user_id="user_001",
                instruction="generate_report",
                question="请生成 2026-06-02 的网络运行日报",
            )
        ))

        steps = [event.step for event in events if event.step is not None]
        step_by_code = {step.code: step for step in steps}
        self.assertNotIn("report.generate", step_by_code)
        self.assertEqual(step_by_code["report.template.match"].status, "finished")
        self.assertEqual(step_by_code["report.parameters.resolve"].status, "finished")

    def test_confirm_report_flow_starts_generation_step_after_confirmation(self):
        generation = _GenerationService()
        service = ReportScenarioService(
            template_service=ReportTemplateService(repository=_TemplateRepository([_template()]), schema_gateway=SimpleNamespace()),
            template_repository=_TemplateRepository([_template()]),
            generation_service=generation,
            parameter_service=ReportParameterService(options_gateway=_ScopeOptionsGateway()),
        )
        initial = service.handle(
            command=ReportScenarioCommand(
                conversation_id="conv_001",
                chat_id="chat_001",
                user_id="user_001",
                instruction="generate_report",
                question="请生成 2026-06-02 的网络运行日报",
            )
        )

        events = InMemoryFlowRuntime().run_sync(service.create_flow(
            command=ReportScenarioCommand(
                conversation_id="conv_001",
                chat_id="chat_002",
                user_id="user_001",
                instruction="generate_report",
                reply_type="confirm_params",
                reply=ReportReplyPayload(
                    report_context=ReportContext(
                        template_instance=initial.ask.payload.report_context.template_instance,
                    )
                ),
            )
        ))

        steps = [event.step for event in events if event.step is not None]
        generation_steps = [step for step in steps if step.code == "report.generate"]
        self.assertEqual([step.status for step in generation_steps], ["running", "finished"])
        compile_step = next(step for step in steps if step.code == "report.dsl.compile")
        self.assertEqual(compile_step.parent_step_id, "report.generate")

    def test_section_regeneration_flow_emits_steps_delta_and_report_segment_answer(self):
        service = ReportScenarioService(
            template_service=ReportTemplateService(repository=_TemplateRepository([_template()]), schema_gateway=SimpleNamespace()),
            template_repository=_TemplateRepository([_template()]),
            generation_service=_GenerationService(),
            parameter_service=ReportParameterService(options_gateway=_ScopeOptionsGateway()),
        )

        events = InMemoryFlowRuntime().run_sync(service.create_flow(
            command=ReportScenarioCommand(
                conversation_id="conv_001",
                chat_id="chat_003",
                user_id="user_001",
                instruction="generate_report_segment",
                segment=SimpleNamespace(
                    report_id="rpt_001",
                    section_id="section_detail",
                    outline=OutlineDefinition(requirement="分析异常根因"),
                ),
            )
        ))

        steps = [event.step for event in events if event.step is not None]
        self.assertIn("report.section_regeneration.load_context", [step.code for step in steps])
        self.assertIn("report.section_regeneration.compile_section", [step.code for step in steps])
        self.assertTrue(any(event.event_type == "delta" and event.delta[0]["action"] == "add_section" for event in events if event.delta))
        answer = next(event.answer for event in events if event.event_type == "answer")
        self.assertEqual(answer["answerType"], "REPORT_SEGMENT")
        self.assertEqual(answer["answer"]["sectionId"], "section_detail")

    def test_section_regeneration_can_run_as_subflow_without_overriding_parent_answer(self):
        service = ReportScenarioService(
            template_service=ReportTemplateService(repository=_TemplateRepository([_template()]), schema_gateway=SimpleNamespace()),
            template_repository=_TemplateRepository([_template()]),
            generation_service=_GenerationService(),
            parameter_service=ReportParameterService(options_gateway=_ScopeOptionsGateway()),
        )
        command = ReportScenarioCommand(
            conversation_id="conv_001",
            chat_id="chat_004",
            user_id="user_001",
            instruction="generate_report_segment",
            segment=SimpleNamespace(
                report_id="rpt_001",
                section_id="section_detail",
                outline=OutlineDefinition(requirement="分析异常根因"),
            ),
        )
        runtime = InMemoryFlowRuntime(
            subflow_registry=SubflowRegistry([service.section_regeneration_subflow_spec()])
        )

        def parent_node(context):
            context.call_subflow("report.section_regeneration", {"command": command}, alias="section_regen")
            context.emit_answer({"answerType": "PARENT", "answer": {"ok": True}})

        events = runtime.run_sync(
            SequentialFlow(
                FlowNode(id="parent", handler=parent_node, emit_lifecycle_step=False)
            ).to_graph()
        )

        self.assertTrue(any(event.source_subflow and event.source_subflow["alias"] == "section_regen" for event in events))
        self.assertTrue(
            any(event.event_type == "delta" and event.delta and event.delta[0].get("source", {}).get("alias") == "section_regen" for event in events)
        )
        self.assertTrue(any(event.event_type == "answer" and event.answer["answerType"] == "PARENT" for event in events))
        self.assertFalse(any(event.event_type == "answer" and event.answer["answerType"] == "REPORT_SEGMENT" for event in events))

    def test_dynamic_parameter_options_are_resolved_before_ask_reaches_frontend(self):
        gateway = _ScopeOptionsGateway()
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
                question="请生成 2026-06-02 的网络运行日报",
            )
        )

        self.assertEqual(result.ask.type, "confirm_params")
        ask_scope = next(item for item in result.ask.payload.parameters if item.id == "scope")
        context_scope = next(item for item in result.ask.payload.report_context.template_instance.parameters if item.id == "scope")
        self.assertEqual([item.label for item in ask_scope.options], ["总部网络", "分支网络"])
        self.assertEqual(context_scope.options[0].value, "hq-network")
        self.assertEqual(context_scope.default_value[0].value, "hq-network")
        self.assertEqual(context_scope.values[0].value, "hq-network")
        self.assertEqual(gateway.calls[0]["source"], "/rest/parameter-options/network/scopes")

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
            ReportScenarioCodec().decode(
                context=ScenarioInvocationContext(
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
